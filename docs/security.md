# Security

Import/export is privileged data mutation. The stable package must enforce a
resource allowlist, safe fields, authorization, queryset scoping, upload limits,
auditing, and dry-run confirmation.

CSV output intended for spreadsheets requires formula-injection handling. A value
that begins with formula-trigger characters must not be exported naively as a cell.
Raw machine-to-machine CSV and spreadsheet-safe CSV are separate output policies.

Treat uploaded datasets as sensitive. Do not log their contents or expose another
user's import job, error report, or original file.
