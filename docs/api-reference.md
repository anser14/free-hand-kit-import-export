# API contract

All paths are relative to the prefix where the host mounts `fk_import_export.urls`.
The foundation endpoints require a staff user while per-resource authorization is
being implemented.

| Method | Path | Status | Purpose |
| --- | --- | --- | --- |
| `GET` | `resources/` | Available | List approved resources only. |
| `GET` | `resources/{key}/` | Available | Show approved fields and relation lookups. |
| `GET` | `resources/{key}/template/` | Available | Download a CSV header template. |
| `GET` | `schema/`, `docs/` | Available | OpenAPI schema and Swagger UI. |
| `POST` | `resources/{key}/imports/preview/` | Planned | Upload and validate without mutation. |
| `POST` | `import-jobs/{id}/confirm/` | Planned | Atomically commit a reviewed import. |
| `GET` | `resources/{key}/export/` | Planned | Export filtered/scoped records as CSV. |

The planned APIs are not mounted yet; their names are a contract draft, not an
implementation claim.
