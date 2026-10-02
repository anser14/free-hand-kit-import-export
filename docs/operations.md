# Operations

The initial `ImportJob` model is an audit foundation. Stable imports will store the
source hash, owner, selected resource, status, summary, and sanitized row errors.

Large imports must move to an optional queue adapter after the synchronous CSV path
has a bounded size, row, and execution-time policy. Operations must define source-file
retention, deletion, failed-job recovery, and durable storage before enabling uploads.
