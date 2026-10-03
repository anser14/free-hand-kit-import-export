# Operations

`ImportJob` stores the source hash, owner, selected resource, status, summary,
sanitized row errors, attempts, progress counters, and lifecycle timestamps. A source
is previewed in a database transaction. Confirmation changes a successful preview to
`queued` and returns immediately. The bundled worker claims it as `processing`,
re-reads its storage object, checks the hash and CSV contract again, and atomically
commits host data with the terminal job state. Repeated confirmation is safe: queued and
processing jobs remain queued/processing, and committed jobs remain committed.

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
result sets over the configured export limit. Operations must still define source-file
retention, deletion, failed-job alerting, and durable private storage.
