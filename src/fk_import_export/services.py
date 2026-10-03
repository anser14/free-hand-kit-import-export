"""Two-phase CSV import workflow with bounded, auditable processing."""

from __future__ import annotations

import csv
import hashlib
import hmac
import io
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from django.contrib.auth.models import AbstractBaseUser
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from import_export.results import Result
from tablib import Dataset  # type: ignore[import-untyped]

from .conf import ImportExportSettings, ResourceConfig, ResourceConfigurationError, get_resource
from .models import ImportJob
from .policies import resolve_scope
from .registry import resource_class
from .signals import send_lifecycle_signal


class ImportPayloadError(ValueError):
    """Raised when an uploaded source is not a bounded, well-formed CSV payload."""


class ImportJobNotFound(LookupError):
    """Raised instead of disclosing an import job owned by another user."""


class ImportJobStateError(ValueError):
    """Raised when an import job cannot make the requested lifecycle transition."""


@dataclass(frozen=True)
class UploadedSource:
    """Validated source bytes and safe original-file metadata."""

    name: str
    content: bytes
    sha256: str


@dataclass(frozen=True)
class ParsedCSV:
    """A validated CSV dataset ready for the import engine."""

    dataset: Dataset
    row_count: int


@dataclass(frozen=True)
class ImportReport:
    """Sanitized engine result safe to persist and return from the API."""

    summary: dict[str, object]
    errors: list[dict[str, object]]
    can_confirm: bool


@dataclass(frozen=True)
class ConfirmationResult:
    """Result of accepting an explicit import confirmation into the queue."""

    job: ImportJob
    accepted: bool
    idempotent: bool = False


@dataclass(frozen=True)
class RetentionReport:
    """Outcome of one bounded, operator-controlled retention cleanup invocation."""

    source_candidates: int = 0
    sources_deleted: int = 0
    source_delete_failures: int = 0
    job_candidates: int = 0
    jobs_deleted: int = 0
    job_delete_failures: int = 0


def _safe_filename(name: str) -> str:
    filename = name.replace("\\", "/").rsplit("/", 1)[-1]
    if not filename or filename in {".", ".."}:
        return "import.csv"
    return filename[:255]


def _read_upload(upload: UploadedFile[bytes], limits: ImportExportSettings) -> UploadedSource:
    filename = _safe_filename(upload.name or "")
    if not filename.lower().endswith(".csv"):
        raise ImportPayloadError("Only .csv files are accepted.")
    if upload.size and upload.size > limits.max_upload_bytes:
        raise ImportPayloadError("The uploaded file exceeds the configured size limit.")

    chunks: list[bytes] = []
    total_size = 0
    for chunk in upload.chunks():
        total_size += len(chunk)
        if total_size > limits.max_upload_bytes:
            raise ImportPayloadError("The uploaded file exceeds the configured size limit.")
        chunks.append(chunk)
    content = b"".join(chunks)
    if not content:
        raise ImportPayloadError("The uploaded file is empty.")
    return UploadedSource(
        name=filename,
        content=content,
        sha256=hashlib.sha256(content).hexdigest(),
    )


def _read_stored_source(job: ImportJob, limits: ImportExportSettings) -> UploadedSource:
    if not job.source_file:
        raise ImportPayloadError("The stored source file is unavailable.")
    with job.source_file.open("rb") as source_file:
        content = source_file.read(limits.max_upload_bytes + 1)
    if not content:
        raise ImportPayloadError("The stored source file is empty.")
    if len(content) > limits.max_upload_bytes:
        raise ImportPayloadError("The stored source file exceeds the configured size limit.")
    return UploadedSource(
        name=_safe_filename(job.source_name),
        content=content,
        sha256=hashlib.sha256(content).hexdigest(),
    )


def _parse_csv(
    source: UploadedSource,
    resource: ResourceConfig,
    limits: ImportExportSettings,
) -> ParsedCSV:
    try:
        text = source.content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ImportPayloadError("CSV files must be UTF-8 encoded.") from exc
    if "\x00" in text:
        raise ImportPayloadError("CSV files must not contain NUL bytes.")

    try:
        reader = csv.reader(io.StringIO(text, newline=""))
        headers = next(reader)
        if not headers or any(not header for header in headers):
            raise ImportPayloadError("CSV headers must be non-empty.")
        if len(headers) != len(set(headers)):
            raise ImportPayloadError("CSV headers must not contain duplicates.")

        expected_headers = list(resource.import_fields)
        missing_headers = sorted(set(expected_headers) - set(headers))
        unexpected_headers = sorted(set(headers) - set(expected_headers))
        if missing_headers or unexpected_headers:
            details: list[str] = []
            if missing_headers:
                details.append(f"missing: {', '.join(missing_headers)}")
            if unexpected_headers:
                details.append(f"unexpected: {', '.join(unexpected_headers)}")
            raise ImportPayloadError(
                f"CSV headers do not match the resource contract ({'; '.join(details)})."
            )

        dataset = Dataset(headers=headers)
        row_count = 0
        for line_number, row in enumerate(reader, start=2):
            if not any(cell.strip() for cell in row):
                raise ImportPayloadError(f"CSV line {line_number} must not be blank.")
            if len(row) != len(headers):
                raise ImportPayloadError(
                    f"CSV line {line_number} does not match the number of headers."
                )
            row_count += 1
            if row_count > limits.max_rows:
                raise ImportPayloadError("The uploaded file exceeds the configured row limit.")
            dataset.append(row)
    except csv.Error as exc:
        raise ImportPayloadError("The uploaded file is not a valid CSV document.") from exc

    if not row_count:
        raise ImportPayloadError("CSV files must include at least one data row.")
    return ParsedCSV(dataset=dataset, row_count=row_count)


def _error_entry(
    *, line: int | None, code: str, fields: list[str] | None = None
) -> dict[str, object]:
    entry: dict[str, object] = {"line": line, "code": code}
    if fields:
        entry["fields"] = fields
    return entry


def _report_from_result(
    result: Result,
    parsed: ParsedCSV,
    limits: ImportExportSettings,
) -> ImportReport:
    errors: list[dict[str, object]] = []
    for invalid_row in result.invalid_rows:
        fields = sorted(str(field_name) for field_name in invalid_row.error_dict)
        errors.append(
            _error_entry(
                line=int(invalid_row.number) + 1,
                code="validation_error",
                fields=fields,
            )
        )
    for error_row in result.error_rows:
        errors.append(_error_entry(line=int(error_row.number) + 1, code="processing_error"))
    if result.base_errors:
        errors.append(_error_entry(line=None, code="dataset_error"))

    error_count = len(errors)
    summary: dict[str, object] = {
        "total_rows": parsed.row_count,
        "new": int(result.totals["new"]),
        "update": int(result.totals["update"]),
        "delete": int(result.totals["delete"]),
        "skip": int(result.totals["skip"]),
        "error": int(result.totals["error"]),
        "invalid": int(result.totals["invalid"]),
        "error_rows": error_count,
        "errors_truncated": error_count > limits.max_error_rows,
    }
    return ImportReport(
        summary=summary,
        errors=errors[: limits.max_error_rows],
        can_confirm=not result.has_errors() and not result.has_validation_errors(),
    )


def _processing_failure(*, row_count: int) -> ImportReport:
    return ImportReport(
        summary={
            "total_rows": row_count,
            "error_rows": 1,
            "errors_truncated": False,
        },
        errors=[_error_entry(line=None, code="processing_error")],
        can_confirm=False,
    )


def _run_import(
    resource: ResourceConfig,
    parsed: ParsedCSV,
    limits: ImportExportSettings,
    *,
    dry_run: bool,
    submitted_by: AbstractBaseUser,
) -> ImportReport:
    try:
        scope = resolve_scope(scope=resource.scope, user=submitted_by)
        result = resource_class(resource, scope=scope)().import_data(
            parsed.dataset,
            dry_run=dry_run,
            raise_errors=False,
            use_transactions=True,
            collect_failed_rows=False,
            rollback_on_validation_errors=True,
        )
    except Exception:
        return _processing_failure(row_count=parsed.row_count)
    return _report_from_result(result, parsed, limits)


def _summary_row_count(summary: dict[str, object]) -> int:
    value = summary.get("total_rows", 0)
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def _update_lifecycle(
    job: ImportJob,
    report: ImportReport | None,
    *,
    status: str,
    progress_total: int | None = None,
    progress_completed: int | None = None,
) -> ImportJob:
    previous_status = job.status
    now = timezone.now()
    job.status = status
    update_fields = ["status", "updated_at"]
    if report is not None:
        job.summary = report.summary
        job.errors = report.errors
        update_fields.extend(("summary", "errors"))
        if progress_total is None:
            progress_total = _summary_row_count(report.summary)
        if progress_completed is None:
            progress_completed = progress_total if status == ImportJob.Status.COMMITTED else 0
    if progress_total is not None:
        job.progress_total = progress_total
        update_fields.append("progress_total")
    if progress_completed is not None:
        job.progress_completed = progress_completed
        update_fields.append("progress_completed")
    if status == ImportJob.Status.PREVIEWED:
        job.previewed_at = now
        update_fields.append("previewed_at")
    if status == ImportJob.Status.QUEUED:
        job.queued_at = now
        job.started_at = None
        update_fields.extend(("queued_at", "started_at"))
    if status == ImportJob.Status.PROCESSING:
        job.started_at = now
        update_fields.append("started_at")
    if status == ImportJob.Status.COMMITTED:
        job.committed_at = now
        update_fields.append("committed_at")
    if status == ImportJob.Status.FAILED:
        job.failed_at = now
        update_fields.append("failed_at")
    job.save(update_fields=update_fields)
    transaction.on_commit(
        lambda: send_lifecycle_signal(
            previous_status=previous_status,
            job_id=job.id,
            resource_key=job.resource_key,
            submitted_by_id=job.submitted_by_id,
            status=status,
        )
    )
    return job


def preview_import(
    *,
    resource: ResourceConfig,
    upload: UploadedFile[bytes],
    submitted_by: AbstractBaseUser,
    limits: ImportExportSettings,
) -> ImportJob:
    """Persist and dry-run a valid CSV source without mutating host model rows."""

    source = _read_upload(upload, limits)
    parsed = _parse_csv(source, resource, limits)
    job = ImportJob(
        resource_key=resource.key,
        source_name=source.name,
        source_sha256=source.sha256,
        source_size=len(source.content),
        submitted_by_id=submitted_by.pk,
    )
    job.source_file.save(source.name, ContentFile(source.content), save=False)
    job.save()

    report = _run_import(
        resource,
        parsed,
        limits,
        dry_run=True,
        submitted_by=submitted_by,
    )
    status = ImportJob.Status.PREVIEWED if report.can_confirm else ImportJob.Status.FAILED
    return _update_lifecycle(job, report, status=status)


def get_owned_job(*, job_id: UUID, submitted_by: AbstractBaseUser) -> ImportJob:
    """Return one job without revealing identifiers owned by another user."""

    try:
        return ImportJob.objects.get(id=job_id, submitted_by_id=submitted_by.pk)
    except ImportJob.DoesNotExist as exc:
        raise ImportJobNotFound from exc


def confirm_import(
    *,
    job_id: UUID,
    submitted_by: AbstractBaseUser,
) -> ConfirmationResult:
    """Atomically enqueue one successful preview for asynchronous execution."""

    with transaction.atomic():
        try:
            job = ImportJob.objects.select_for_update().get(
                id=job_id,
                submitted_by_id=submitted_by.pk,
            )
        except ImportJob.DoesNotExist as exc:
            raise ImportJobNotFound from exc

        if job.status == ImportJob.Status.COMMITTED:
            return ConfirmationResult(job=job, accepted=True, idempotent=True)
        if job.status in {ImportJob.Status.QUEUED, ImportJob.Status.PROCESSING}:
            return ConfirmationResult(job=job, accepted=True, idempotent=True)
        if job.status != ImportJob.Status.PREVIEWED:
            raise ImportJobStateError("Only a successful preview can be confirmed.")

        return ConfirmationResult(
            job=_update_lifecycle(
                job,
                None,
                status=ImportJob.Status.QUEUED,
                progress_total=_summary_row_count(job.summary),
                progress_completed=0,
            ),
            accepted=True,
        )


def _claim_job(job: ImportJob) -> ImportJob:
    """Move an exclusively locked queued job into processing state."""

    if job.status != ImportJob.Status.QUEUED:
        raise ImportJobStateError("Only queued jobs can be processed.")
    job.attempt_count += 1
    job.save(update_fields=("attempt_count", "updated_at"))
    return _update_lifecycle(job, None, status=ImportJob.Status.PROCESSING)


def _claim_import_job(job_id: UUID) -> ImportJob | None:
    with transaction.atomic():
        try:
            job = ImportJob.objects.select_for_update().get(id=job_id)
        except ImportJob.DoesNotExist:
            return None
        if job.status != ImportJob.Status.QUEUED:
            return None
        return _claim_job(job)


def _claim_next_import_job() -> ImportJob | None:
    with transaction.atomic():
        job = (
            ImportJob.objects.select_for_update()
            .filter(status=ImportJob.Status.QUEUED)
            .order_by("created_at")
            .first()
        )
        if job is None:
            return None
        return _claim_job(job)


def _process_claimed_import_job(*, job_id: UUID, limits: ImportExportSettings) -> ImportJob:
    """Run one claimed job atomically so data and terminal job state agree."""

    with transaction.atomic():
        job = ImportJob.objects.select_for_update().get(id=job_id)
        if job.status != ImportJob.Status.PROCESSING:
            raise ImportJobStateError("Only processing jobs can be finalized.")
        try:
            resource = get_resource(job.resource_key)
            source = _read_stored_source(job, limits)
            if not hmac.compare_digest(source.sha256, job.source_sha256):
                raise ImportPayloadError("The stored source file no longer matches its preview.")
            parsed = _parse_csv(source, resource, limits)
        except (ImportPayloadError, ResourceConfigurationError):
            return _update_lifecycle(
                job,
                _processing_failure(row_count=job.progress_total),
                status=ImportJob.Status.FAILED,
                progress_total=job.progress_total,
                progress_completed=0,
            )

        if job.progress_total != parsed.row_count:
            job.progress_total = parsed.row_count
            job.save(update_fields=("progress_total", "updated_at"))
        submitted_by = job.submitted_by
        if not isinstance(submitted_by, AbstractBaseUser):
            return _update_lifecycle(
                job,
                _processing_failure(row_count=parsed.row_count),
                status=ImportJob.Status.FAILED,
                progress_total=parsed.row_count,
                progress_completed=0,
            )
        report = _run_import(
            resource,
            parsed,
            limits,
            dry_run=False,
            submitted_by=submitted_by,
        )
        if not report.can_confirm:
            return _update_lifecycle(
                job,
                report,
                status=ImportJob.Status.FAILED,
                progress_total=parsed.row_count,
                progress_completed=0,
            )
        return _update_lifecycle(
            job,
            report,
            status=ImportJob.Status.COMMITTED,
            progress_total=parsed.row_count,
            progress_completed=parsed.row_count,
        )


def process_import_job(*, job_id: UUID, limits: ImportExportSettings) -> ImportJob | None:
    """Claim and process one specific queued job; safe to call from task runners."""

    job = _claim_import_job(job_id)
    if job is None:
        return None
    return _process_claimed_import_job(job_id=job.id, limits=limits)


def process_next_import_job(*, limits: ImportExportSettings) -> ImportJob | None:
    """Claim and process the oldest queued job exactly once per worker call."""

    job = _claim_next_import_job()
    if job is None:
        return None
    return _process_claimed_import_job(job_id=job.id, limits=limits)


def recover_stale_import_jobs(*, limits: ImportExportSettings) -> int:
    """Requeue interrupted work or fail it once its bounded retry budget is exhausted."""

    cutoff = timezone.now() - timedelta(seconds=limits.processing_timeout_seconds)
    recovered = 0
    with transaction.atomic():
        jobs = list(
            ImportJob.objects.select_for_update()
            .filter(status=ImportJob.Status.PROCESSING, started_at__lt=cutoff)
            .order_by("started_at")
        )
        for job in jobs:
            if job.attempt_count >= limits.max_attempts:
                _update_lifecycle(
                    job,
                    _processing_failure(row_count=job.progress_total),
                    status=ImportJob.Status.FAILED,
                    progress_total=job.progress_total,
                    progress_completed=0,
                )
            else:
                _update_lifecycle(
                    job,
                    None,
                    status=ImportJob.Status.QUEUED,
                    progress_total=job.progress_total,
                    progress_completed=0,
                )
            recovered += 1
    return recovered


def _expired_terminal_job_ids(
    *, retention_days: int, batch_size: int, with_source: bool = False
) -> list[UUID]:
    """Select a bounded set of terminal jobs eligible for retention cleanup."""

    cutoff = timezone.now() - timedelta(days=retention_days)
    terminal_statuses = (ImportJob.Status.COMMITTED, ImportJob.Status.FAILED)
    terminal_timestamp_before_cutoff = (
        Q(status=ImportJob.Status.COMMITTED, committed_at__lt=cutoff)
        | Q(status=ImportJob.Status.FAILED, failed_at__lt=cutoff)
        | Q(
            status__in=terminal_statuses,
            committed_at__isnull=True,
            failed_at__isnull=True,
            updated_at__lt=cutoff,
        )
    )
    jobs = ImportJob.objects.filter(terminal_timestamp_before_cutoff)
    if with_source:
        jobs = jobs.filter(source_deleted_at__isnull=True).exclude(source_file="")
    return list(jobs.order_by("created_at").values_list("id", flat=True)[:batch_size])


def _delete_source_from_storage(job: ImportJob) -> bool:
    """Delete a job's source object without exposing its storage path to callers."""

    if not job.source_file.name:
        return True
    try:
        job.source_file.delete(save=False)
    except Exception:
        # Storage backends can raise provider-specific exceptions. Do not remove the
        # database evidence when the underlying private object could not be removed.
        return False
    job.source_file = ""
    return True


def _expire_source(*, job_id: UUID) -> bool:
    """Remove one terminal job's source and retain an auditable job record."""

    with transaction.atomic():
        try:
            job = ImportJob.objects.select_for_update().get(id=job_id)
        except ImportJob.DoesNotExist:
            return False
        if (
            job.status not in {ImportJob.Status.COMMITTED, ImportJob.Status.FAILED}
            or job.source_deleted_at is not None
            or not job.source_file.name
        ):
            return False
        if not _delete_source_from_storage(job):
            return False
        job.source_deleted_at = timezone.now()
        job.save(update_fields=("source_file", "source_deleted_at", "updated_at"))
    return True


def _purge_job(*, job_id: UUID) -> bool:
    """Delete one expired terminal job, removing its source object first when present."""

    with transaction.atomic():
        try:
            job = ImportJob.objects.select_for_update().get(id=job_id)
        except ImportJob.DoesNotExist:
            return False
        if job.status not in {ImportJob.Status.COMMITTED, ImportJob.Status.FAILED}:
            return False
        if not _delete_source_from_storage(job):
            return False
        job.delete()
    return True


def purge_expired_import_data(
    *,
    limits: ImportExportSettings,
    apply: bool,
    include_sources: bool = True,
    include_jobs: bool = True,
    batch_size: int = 100,
) -> RetentionReport:
    """Safely report or remove bounded terminal import data based on configured retention.

    The caller must pass ``apply=True`` to make an irreversible storage or database
    change. Pending, previewed, queued, and processing jobs are intentionally excluded.
    """

    if batch_size < 1:
        raise ValueError("batch_size must be a positive integer.")

    source_ids: list[UUID] = []
    if include_sources and limits.source_retention_days is not None:
        source_ids = _expired_terminal_job_ids(
            retention_days=limits.source_retention_days,
            batch_size=batch_size,
            with_source=True,
        )

    job_ids: list[UUID] = []
    if include_jobs and limits.job_retention_days is not None:
        job_ids = _expired_terminal_job_ids(
            retention_days=limits.job_retention_days,
            batch_size=batch_size,
        )

    if not apply:
        return RetentionReport(
            source_candidates=len(source_ids),
            job_candidates=len(job_ids),
        )

    sources_deleted = 0
    source_delete_failures = 0
    for job_id in source_ids:
        if _expire_source(job_id=job_id):
            sources_deleted += 1
        else:
            source_delete_failures += 1

    jobs_deleted = 0
    job_delete_failures = 0
    for job_id in job_ids:
        if _purge_job(job_id=job_id):
            jobs_deleted += 1
        else:
            job_delete_failures += 1

    return RetentionReport(
        source_candidates=len(source_ids),
        sources_deleted=sources_deleted,
        source_delete_failures=source_delete_failures,
        job_candidates=len(job_ids),
        jobs_deleted=jobs_deleted,
        job_delete_failures=job_delete_failures,
    )
