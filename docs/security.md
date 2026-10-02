# Security

Import/export is privileged data mutation. This pre-release implementation enforces a
resource allowlist, direct safe fields, staff access, owner-scoped jobs, upload limits,
auditing, dry-run preview, source hashing, and atomic confirmation. It deliberately
does not trust a client-supplied model label, field list, or stored preview alone.

The CSV parser accepts UTF-8 only, requires exact configured headers, rejects duplicate
headers, NUL bytes, blank rows, malformed rows, and files over configured limits. API
error records contain line numbers, error categories, and validation field names; they
never include uploaded cell values or raw database exception text.

Source files can contain sensitive data. Use a private storage backend, deny direct
media access, encrypt storage where appropriate, and define a retention/deletion job.
The package cannot make an application's selected Django storage private by itself.

CSV output intended for spreadsheets requires formula-injection handling. A value
that begins with formula-trigger characters must not be exported naively as a cell.
Raw machine-to-machine CSV and spreadsheet-safe CSV are separate output policies.

Treat uploaded datasets as sensitive. Do not log their contents or expose another
user's import job, error report, or original file.

Before a stable release, add tenant/queryset scoping and a configurable per-resource
permission policy. The current staff-only baseline is intentionally conservative but
not a substitute for an application's domain authorization rules.
