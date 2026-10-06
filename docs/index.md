# Freehand Kit Import Export documentation

This package is a CSV-first, API-first integration layer over
`django-import-export`. Host applications define an explicit resource registry;
they retain ownership of Django models, permissions, storage, and business rules.

## New to the package?

Start with the [end-to-end quickstart](quickstart.md). It takes a Django model from
configuration through preview, confirmation, worker processing, records, and CSV export.
Use the [installation guide](installation.md) when adding the package to an existing
project, and the [configuration guide](configuration.md) when your model has relations,
permissions, or tenancy rules.

## Guides

- [Architecture decision](architecture/ADR-0001-engine-and-safety-boundary.md)
- [End-to-end quickstart](quickstart.md)
- [Installation](installation.md)
- [Configuration](configuration.md)
- [API reference](api-reference.md)
- [Integration hooks](integration-hooks.md)
- [Security](security.md)
- [Operations](operations.md)
- [Testing](testing.md)
- [Compatibility](compatibility.md)
