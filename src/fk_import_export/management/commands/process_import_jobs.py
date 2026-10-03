"""Process bounded queued import jobs from the durable database queue."""

from django.core.management.base import BaseCommand, CommandError

from fk_import_export.conf import get_runtime_settings
from fk_import_export.services import process_next_import_job, recover_stale_import_jobs


class Command(BaseCommand):
    help = "Process queued Freehand Kit import jobs and recover stale work."

    def add_arguments(self, parser) -> None:  # type: ignore[no-untyped-def]
        parser.add_argument(
            "--max-jobs",
            type=int,
            default=1,
            help="Maximum queued jobs to process during this invocation (default: 1).",
        )
        parser.add_argument(
            "--skip-stale-recovery",
            action="store_true",
            help="Do not requeue or fail jobs older than PROCESSING_TIMEOUT_SECONDS.",
        )

    def handle(self, *args, **options) -> str:  # type: ignore[no-untyped-def]
        max_jobs = options["max_jobs"]
        if not isinstance(max_jobs, int) or max_jobs < 1:
            raise CommandError("--max-jobs must be a positive integer.")

        limits = get_runtime_settings()
        recovered = 0
        if not options["skip_stale_recovery"]:
            recovered = recover_stale_import_jobs(limits=limits)

        processed = 0
        for _ in range(max_jobs):
            job = process_next_import_job(limits=limits)
            if job is None:
                break
            processed += 1
            self.stdout.write(f"Processed import job {job.id}: {job.status}")

        return f"Recovered {recovered} stale job(s); processed {processed} queued job(s)."
