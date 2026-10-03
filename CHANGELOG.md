# Changelog

All notable changes to this package are documented here. The project follows
[Semantic Versioning](https://semver.org/).

## [0.9.2] - 2026-10-03

### Changed

- The Docker consumer demo runs migrations in one short-lived service. Web and worker
  now wait for that migration to complete successfully, preventing concurrent startup
  migration attempts.

## [0.9.1] - 2026-10-03

### Fixed

- Apply server-controlled owner/tenant scopes before model validation, so a scoped
  resource whose model requires that field can successfully complete preview and import.
- Exclude local SQLite state and private demonstration upload storage from Docker build
  contexts.

### Added

- A Dockerized custom-user consumer demo with PostgreSQL, a separate import worker,
  private storage, relational data, and an end-to-end operator guide.

## [0.9.0] - 2026-10-03

### Added

- Owner-private, import-permission-filtered `GET import-jobs/` history with bounded
  pagination and resource/status filters.

## [0.8.0] - 2026-10-03

### Added

- Optional, typed host `ResourcePolicy` classes for indirect tenancy, memberships, and
  other domain-specific queryset and import-instance rules.

### Security

- Policy classes must be an explicitly configured, zero-argument subclass of the public
  `ResourcePolicy` base class. They compose with—not replace—resource permissions,
  field allowlists, and direct scopes.

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
