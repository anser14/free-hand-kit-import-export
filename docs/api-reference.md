# API contract

All paths are relative to the prefix where the host mounts `fk_import_export.urls`.
Each endpoint requires authentication and the configured resource operation permission.
If `PERMISSIONS` is omitted, the safe compatibility policy is `$staff`. Import jobs are
additionally scoped to the submitting user; another user receives `404`.

| Method | Path | Status | Purpose |
| --- | --- | --- | --- |
| `GET` | `resources/` | Available | List approved resources only. |
| `GET` | `resources/{key}/` | Available | Show approved fields and relation lookups. |
| `GET` | `resources/{key}/template/` | Available | Download a CSV header template. |
| `GET` | `schema/`, `docs/` | Available | OpenAPI schema and Swagger UI. |
| `POST` | `resources/{key}/imports/preview/` | Available | Upload one multipart `file`, validate it, and create a dry-run job. |
| `GET` | `import-jobs/{id}/` | Available | Read a sanitized, owner-scoped job result. |
| `POST` | `import-jobs/{id}/confirm/` | Available | Queue a successful preview for worker execution. |
| `GET` | `import-jobs/{id}/errors/` | Available | Download sanitized row-level error metadata as CSV. |
| `GET` | `resources/{key}/records/` | Available | Paginated JSON records from configured export fields. |
| `GET` | `resources/{key}/export/` | Available | Bounded, spreadsheet-safe CSV from configured export fields. |

`preview/` accepts UTF-8 CSV in the multipart field `file`. Its headers must exactly
match `IMPORT_FIELDS`. It returns `201` for both successful previews and persisted row
failures; only a `previewed` job is confirmation-eligible. Invalid source structure
returns `400` without storing a job. Confirmation returns `202` after queueing work
(including a safe retry of a queued or processing job), `200` for an already committed
job, `409` if a job cannot be queued, and `404` for an unknown or foreign job. The job
detail payload exposes queue status, attempt count, and coarse atomic progress. A worker
must run `python manage.py process_import_jobs`; the public command can also be invoked
by a scheduler or wrapped by the host's preferred task runner.

`errors/` contains only a CSV header plus sanitized `line`, `code`, and field-name
metadata. It never includes uploaded cell values or database exception text. Its
`X-Freehand-Errors-Truncated` response header indicates whether `MAX_ERROR_ROWS` capped
the stored report sample.

`records/` accepts `page`, `page_size`, `search`, `ordering`, and `filter.<field>`.
`export/` accepts `search`, `ordering`, and `filter.<field>`; it rejects pagination and
returns `400` when matching records exceed `MAX_EXPORT_ROWS`. Unknown parameters or
fields outside the resource's allowlists return `400`. Search/order/filter controls are
documented in Swagger for each shared endpoint; the final allowed field names come from
the resource configuration returned by `GET resources/{key}/`.

When `SCOPE` is declared, all records, exports, preview import identity matching, and
worker commits are constrained to that caller's direct owner/tenant value. A caller cannot
override the scoped field through CSV because the server supplies it before saving.
