# Changelog

All notable changes to this package are documented here. The project follows
[Semantic Versioning](https://semver.org/).

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
