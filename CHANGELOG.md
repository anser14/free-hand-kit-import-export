# Changelog

All notable changes to this package are documented here. The project follows
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-10-02

### Added

- Independent package foundation for declarative Django model import/export.
- Namespaced resource registry, Django system checks, `django-import-export` engine
  boundary, import-job audit model, and Swagger-ready discovery/template APIs.
- CSV-first safety and relationship configuration contract.

### Security

- Explicit resource and field allowlists; denylist for Django credential and privilege
  fields; declared import identifiers; and no automatic related-object creation.
