# Freehand Kit Import Export

`freehand-kit-import-export` is a declarative, CSV-first import/export package for
Django REST Framework. A host developer registers approved model resources in one
settings dictionary, mounts one URL, and receives documented discovery, schema,
CSV-template, preview, and confirm APIs. The package uses `django-import-export` as
its data engine.

> **Status: pre-release.** Version `0.3.0` implements bounded, synchronous,
> two-phase CSV import plus configured records and spreadsheet-safe CSV export. It is
> not published and is not yet a stable production release: queryset/tenant scoping,
> configurable per-resource permissions, background jobs, and retention operations
> remain to be implemented.

## Design promise

Host developers should not need to write a `ModelResource`, CSV parser, serializer,
view, pagination class, search backend, ordering backend, or Swagger annotation for
every model. They configure an approved resource; the package owns the reusable API
workflow.

API callers never submit arbitrary Django model labels or field names. They select a
developer-approved resource key such as `products`.

## Quick start

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

Run `python manage.py migrate`, then visit `/api/data/docs/`. Staff users can download
the template, submit `POST /api/data/resources/products/imports/preview/` as multipart
form data with a `file` field, review the returned job, and explicitly call
`POST /api/data/import-jobs/{id}/confirm/`. A preview is dry-run only; confirmation
revalidates the stored source and applies it atomically.

Staff users can also use `GET /api/data/resources/products/records/` for paginated JSON
and `GET /api/data/resources/products/export/` for bounded CSV. Both accept only
developer-configured `search`, `ordering`, and `filter.<field>` controls. CSV export
cells that could be interpreted as spreadsheet formulae are prefixed safely.

## Safety boundary

- Only explicitly registered resources are discoverable.
- Sensitive fields such as passwords, staff flags, groups, permissions, and tokens are
  denied by default.
- Import identifiers and relationship lookups must be explicit.
- Related objects are never auto-created by default.
- Uploads are UTF-8 CSV only, with exact configured headers, size/row limits, and no
  blank rows. Persisted errors contain line numbers and codes—not uploaded cell values.
- Preview and confirmation use transactions; confirmation is retry-safe after success.
- CSV exports are capped and spreadsheet-formula-safe. Queryset scoping and configurable
  authorization are still mandatory before the first stable release.

## Documentation

- [Architecture decision](docs/architecture/ADR-0001-engine-and-safety-boundary.md)
- [Installation](docs/installation.md)
- [Configuration](docs/configuration.md)
- [API contract](docs/api-reference.md)
- [Security](docs/security.md)

## License

MIT. See [LICENSE](LICENSE).
