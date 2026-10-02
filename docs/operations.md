# Operations

`ImportJob` stores the source hash, owner, selected resource, status, summary,
sanitized row errors, and preview/commit/failure timestamps. A source is previewed in a
database transaction; confirmation re-reads its storage object, checks the hash and
CSV contract again, then imports atomically. Repeating a successful confirmation is
safe and returns the committed job rather than importing twice.

The current implementation is synchronous and intentionally bounded by
`MAX_UPLOAD_BYTES`, `MAX_ROWS`, and `MAX_EXPORT_ROWS`. Record listing uses bounded page
sizes; full CSV export rejects result sets over the configured export limit. Large
imports and exports must move to an optional queue adapter with timeout, retry, and
observability policies. Operations must still define source-file retention, deletion,
failed-job recovery, and durable private storage.
