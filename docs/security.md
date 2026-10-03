# Security

Import/export is privileged data mutation. This pre-release implementation enforces a
resource allowlist, direct safe fields, staff access, owner-scoped jobs, upload limits,
auditing, dry-run preview, source hashing, a durable worker queue, atomic execution,
declarative permissions, and optional direct owner/tenant scope. It deliberately
does not trust a client-supplied model label, field list, or stored preview alone.

The CSV parser accepts UTF-8 only, requires exact configured headers, rejects duplicate
headers, NUL bytes, blank rows, malformed rows, and files over configured limits. API
error records contain line numbers, error categories, and validation field names; they
never include uploaded cell values or raw database exception text. The downloadable error
report applies the same contract and is owner-scoped.

Source files can contain sensitive data. Use a private storage backend, deny direct
media access, and encrypt storage where appropriate. Configure
`SOURCE_RETENTION_DAYS` and/or `JOB_RETENTION_DAYS`, review `purge_import_jobs` in
dry-run mode, then schedule it with `--apply`. It considers only terminal jobs and
cannot make an application's selected Django storage private by itself.

CSV output intended for spreadsheets requires formula-injection handling. A value
that begins with formula-trigger characters must not be exported naively as a cell.
The current CSV endpoint prefixes values beginning with `=`, `+`, `-`, or `@` (including
after whitespace) with an apostrophe. The endpoint is therefore spreadsheet-safe by
default; a future raw machine-to-machine policy must remain opt-in and explicit.

Treat uploaded datasets as sensitive. Do not log their contents or expose another
user's import job, error report, or original file.

Validate every application's tenant/queryset and permission configuration in its own
deployment. For membership graphs, indirect tenancy, or other domain rules, use a tested
host `ResourcePolicy` class. A policy is trusted application code: keep its constructor
side-effect-free, return only the configured model queryset, validate every imported
instance, and test it with real users and worker execution. The package still enforces
resource permissions, direct scopes, field allowlists, and private job ownership around
that extension point.
