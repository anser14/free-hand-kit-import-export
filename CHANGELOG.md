# Changelog

All notable changes to this package are documented here. The project follows
[Semantic Versioning](https://semver.org/).

## [0.7.0] - 2026-10-03

### Added

- Transaction-safe Django lifecycle signals for previewed, queued, committed, and failed
  import jobs.

### Changed

- Corrected the package runtime version to match distribution metadata.

## [0.6.0] - 2026-10-03

### Added

- Opt-in retention settings and a bounded `purge_import_jobs` management command.
- Source-deletion audit timestamps on retained terminal import-job records.

### Security

- Retention processing considers only committed and failed jobs, defaults to dry-run,
  and requires `--apply` before any source object or job record is removed.

## [0.5.0] - 2026-10-03

### Added

- Per-resource Django permission policies for read, export, and import operations.
- Direct owner/tenant scope configuration applied to records, exports, import matching,
  and worker commits.

### Security

- Resource discovery now returns only resources whose declared read policy permits the
  caller. Scoped imports attach the declared owner/tenant value server-side.

## [0.4.0] - 2026-10-02

### Added

- Durable database-backed import queue states, attempts, timestamps, and progress counters.
- Bundled `process_import_jobs` Django management command with stale-job recovery and a
  bounded retry budget.
- Owner-scoped, sanitized CSV error-report download endpoint.

### Changed

- Confirmation now returns `202 Accepted` after queuing a successful preview; a worker
  atomically commits the import and records terminal state.

## [0.3.0] - 2026-10-02

### Added

- Paginated configured-record APIs and bounded CSV export APIs.
- Allowlisted search, ordering, exact filtering, relationship lookup filtering, and
  spreadsheet-formula-safe CSV cell serialization.
- Explicit relation requirements and validation that disallows many-to-many ordering.

## [0.2.0] - 2026-10-02

### Added

- CSV preview, owner-scoped import-job detail, and explicit confirmation endpoints.
- Bounded UTF-8 CSV validation, exact header contracts, row and upload-size limits,
  stored-source hashing, dry-run preview, atomic confirmation, and retry-safe commits.
- Lifecycle timestamps and sanitized, capped import error summaries.

### Security

- Previewed jobs are private to the submitting staff user; an unknown or foreign job
  returns `404`.
- Confirmation rechecks the stored source hash and CSV contract before mutation.

## [0.1.0] - 2026-10-02

### Added

- Independent package foundation for declarative Django model import/export.
- Namespaced resource registry, Django system checks, `django-import-export` engine
  boundary, import-job audit model, and Swagger-ready discovery/template APIs.
- CSV-first safety and relationship configuration contract.

### Security

- Explicit resource and field allowlists; denylist for Django credential and privilege
  fields; declared import identifiers; and no automatic related-object creation.
