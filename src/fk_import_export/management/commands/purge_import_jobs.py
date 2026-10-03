"""Report or safely purge expired terminal import sources and job records."""

from django.core.management.base import BaseCommand, CommandError

from fk_import_export.conf import get_runtime_settings
from fk_import_export.services import purge_expired_import_data


class Command(BaseCommand):
    help = (
        "Report or, with --apply, remove expired terminal Freehand Kit import sources and jobs."
    )

    def add_arguments(self, parser) -> None:  # type: ignore[no-untyped-def]
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Perform irreversible source-object and database-row deletion.",
        )
        parser.add_argument(
            "--sources",
            action="store_true",
            help="Process only configured source-file retention.",
        )
        parser.add_argument(
            "--jobs",
            action="store_true",
            help="Process only configured terminal-job retention.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Maximum candidates per retention category (default: 100).",
        )

    def handle(self, *args, **options) -> str:  # type: ignore[no-untyped-def]
        batch_size = options["batch_size"]
        if not isinstance(batch_size, int) or batch_size < 1:
            raise CommandError("--batch-size must be a positive integer.")

        only_sources = options["sources"]
        only_jobs = options["jobs"]
        report = purge_expired_import_data(
            limits=get_runtime_settings(),
            apply=options["apply"],
            include_sources=only_sources or not only_jobs,
            include_jobs=only_jobs or not only_sources,
            batch_size=batch_size,
        )
        action = "Deleted" if options["apply"] else "Dry run: would delete"
        source_count = report.sources_deleted if options["apply"] else report.source_candidates
        job_count = report.jobs_deleted if options["apply"] else report.job_candidates
        return (
            f"{action} {source_count} source file(s) and {job_count} "
            f"job record(s); source failures: {report.source_delete_failures}; "
            f"job failures: {report.job_delete_failures}."
        )
