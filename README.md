# Freehand Kit Import Export

`freehand-kit-import-export` is a declarative, CSV-first import/export package for
Django REST Framework. A host developer registers approved model resources in one
settings dictionary, mounts one URL, and receives documented discovery, schema, and
CSV-template APIs. The package uses `django-import-export` as its data engine.

> **Status: pre-release foundation.** Version `0.1.0` establishes the package,
> registry, validation contract, engine boundary, job model, and Swagger-ready API
> surface. It is not yet published and must not be used as a production data-mutation
> service until the preview/confirm import workflow reaches its release gate.

## Design promise

Host developers should not need to write a `ModelResource`, CSV parser, serializer,
view, pagination class, search backend, ordering backend, or Swagger annotation for
every model. They configure an approved resource; the package owns the reusable API
workflow.

API callers never submit arbitrary Django model labels or field names. They select a
developer-approved resource key such as `products`.

## Planned developer experience

```python
FREEHAND_KIT_IMPORT_EXPORT = {
    "RESOURCES": {
        "products": {
            "MODEL": "inventory.Product",
            "IMPORT_FIELDS": ("sku", "name", "price", "category"),
            "EXPORT_FIELDS": ("sku", "name", "price", "category"),
            "IMPORT_ID_FIELDS": ("sku",),
            "SEARCH_FIELDS": ("sku", "name"),
            "ORDERING_FIELDS": ("sku", "name", "price"),
            "FILTER_FIELDS": ("category",),
            "RELATIONS": {
                "category": {"LOOKUP_FIELD": "slug"},
            },
        },
    },
}
```

```python
from django.urls import include, path

urlpatterns = [
    path("api/data/", include("fk_import_export.urls")),
]
```

The foundation exposes its OpenAPI schema and a CSV template at a host-chosen prefix.
The full import preview, confirmation, export, filter, search, ordering, pagination,
and asynchronous-job endpoints are the next gated implementation increment.

## Safety boundary

- Only explicitly registered resources are discoverable.
- Sensitive fields such as passwords, staff flags, groups, permissions, and tokens are
  denied by default.
- Import identifiers and relationship lookups must be explicit.
- Related objects are never auto-created by default.
- CSV upload limits, transaction semantics, permissions, job auditing, idempotency,
  and spreadsheet-formula-safe export are mandatory before the first stable release.

## Documentation

- [Architecture decision](docs/architecture/ADR-0001-engine-and-safety-boundary.md)
- [Installation](docs/installation.md)
- [Configuration](docs/configuration.md)
- [API contract](docs/api-reference.md)
- [Security](docs/security.md)

## License

MIT. See [LICENSE](LICENSE).
