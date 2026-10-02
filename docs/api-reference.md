# API contract

All paths are relative to the prefix where the host mounts `fk_import_export.urls`.
All current endpoints require a staff user. Import jobs are additionally scoped to the
staff user who submitted them; another user receives `404`.

| Method | Path | Status | Purpose |
| --- | --- | --- | --- |
| `GET` | `resources/` | Available | List approved resources only. |
| `GET` | `resources/{key}/` | Available | Show approved fields and relation lookups. |
| `GET` | `resources/{key}/template/` | Available | Download a CSV header template. |
| `GET` | `schema/`, `docs/` | Available | OpenAPI schema and Swagger UI. |
| `POST` | `resources/{key}/imports/preview/` | Available | Upload one multipart `file`, validate it, and create a dry-run job. |
| `GET` | `import-jobs/{id}/` | Available | Read a sanitized, owner-scoped job result. |
| `POST` | `import-jobs/{id}/confirm/` | Available | Revalidate and atomically commit a successful preview. |
| `GET` | `resources/{key}/records/` | Available | Paginated JSON records from configured export fields. |
| `GET` | `resources/{key}/export/` | Available | Bounded, spreadsheet-safe CSV from configured export fields. |

`preview/` accepts UTF-8 CSV in the multipart field `file`. Its headers must exactly
match `IMPORT_FIELDS`. It returns `201` for both successful previews and persisted row
failures; only a `previewed` job is confirmation-eligible. Invalid source structure
returns `400` without storing a job. Confirmation returns `200` on success (including a
safe retry of an already committed job), `409` if a job cannot be committed, and `404`
for an unknown or foreign job.

`records/` accepts `page`, `page_size`, `search`, `ordering`, and `filter.<field>`.
`export/` accepts `search`, `ordering`, and `filter.<field>`; it rejects pagination and
returns `400` when matching records exceed `MAX_EXPORT_ROWS`. Unknown parameters or
fields outside the resource's allowlists return `400`. Search/order/filter controls are
documented in Swagger for each shared endpoint; the final allowed field names come from
the resource configuration returned by `GET resources/{key}/`.
