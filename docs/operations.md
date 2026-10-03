# Operations

`ImportJob` stores the source hash, owner, selected resource, status, summary,
sanitized row errors, attempts, progress counters, and lifecycle timestamps. A source
is previewed in a database transaction. Confirmation changes a successful preview to
`queued` and returns immediately. The bundled worker claims it as `processing`,
re-reads its storage object, checks the hash and CSV contract again, and atomically
commits host data with the terminal job state. Repeated confirmation is safe: queued and
processing jobs remain queued/processing, and committed jobs remain committed.

For a resource with `SCOPE`, the worker resolves that scope again from the submitting
user. It constrains identity matching to that owner/tenant and sets the scoped field
server-side before saving. If the submitter has been deleted or no longer has a usable
scope value, the job fails safely without changing host rows.

Run the bounded worker under your scheduler or process supervisor:

```bash
python manage.py process_import_jobs --max-jobs 10
```

Every invocation also recovers `processing` jobs older than
`PROCESSING_TIMEOUT_SECONDS`. Recovery requeues jobs until `MAX_ATTEMPTS`; exhausted
jobs fail safely. The command uses database row locking for claims, so deploy it with a
database that supports your desired multi-worker concurrency semantics. Atomic imports
intentionally expose coarse progress (`0/total` while processing, `total/total` after a
commit) rather than misleading per-row progress.

The implementation remains bounded by `MAX_UPLOAD_BYTES`, `MAX_ROWS`, and
`MAX_EXPORT_ROWS`. Record listing uses bounded page sizes; full CSV export rejects
result sets over the configured export limit.

## Retention cleanup

Set `SOURCE_RETENTION_DAYS` and/or `JOB_RETENTION_DAYS` in the package setting to opt
into terminal-data retention. Both settings default to `None`; no source file or job is
deleted merely by installing the package. A source-only policy keeps its audit record and
sets `source_deleted_at`. A job-retention policy deletes both the terminal job and its
remaining storage object.

Run this command from your scheduler after first reviewing its dry-run output:

```bash
python manage.py purge_import_jobs --batch-size 100
python manage.py purge_import_jobs --batch-size 100 --apply
```

Use `--sources` or `--jobs` to operate on one category only. The command never selects
uploaded, previewed, queued, or processing jobs, and no deletion occurs without
`--apply`. Storage failures leave the matching record intact and are reported as a
failure count; investigate and rerun after repairing storage access. Schedule this with
a service identity that has access to the private Django storage backend.
