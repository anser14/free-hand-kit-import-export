# Freehand Kit Import Export

`freehand-kit-import-export` is a declarative, CSV-first import/export package for
Django REST Framework. A host developer registers approved model resources in one
settings dictionary, mounts one URL, and receives documented discovery, schema,
CSV-template, preview, and confirm APIs. The package uses `django-import-export` as
its data engine.

> **Status: pre-release.** Version `0.5.0` implements bounded, queued CSV import,
> configured records, spreadsheet-safe CSV export, direct tenant/owner scopes, permission
> policies, progress state, and sanitized error reports. It is not published and is not
> yet a stable production release: retention operations and application-specific complex
> authorization policies remain.

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
            "PERMISSIONS": {
                "READ": "inventory.view_product",
                "EXPORT": "inventory.view_product",
                "IMPORT": "inventory.change_product",
            },
            "SCOPE": {"MODEL_FIELD": "owner", "USER_ATTRIBUTE": "$self"},
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
returns `202 Accepted` after adding the job to the durable database queue. Run a worker
under your process supervisor or scheduler:

```bash
python manage.py process_import_jobs --max-jobs 10
```

The worker revalidates the stored source and atomically applies the import. Poll
`GET /api/data/import-jobs/{id}/` for queue state and progress, or download its
sanitized failure metadata from `GET /api/data/import-jobs/{id}/errors/`.

Authorized users can also use `GET /api/data/resources/products/records/` for paginated
JSON and `GET /api/data/resources/products/export/` for bounded CSV. Both accept only
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
- Preview and worker execution use transactions; queue confirmation is retry-safe and
  worker retries are bounded.
- CSV exports are capped and spreadsheet-formula-safe. Scope and permission policies are
  declared in settings; model-specific complex authorization may still need a future hook.

## Documentation

- [Architecture decision](docs/architecture/ADR-0001-engine-and-safety-boundary.md)
- [Installation](docs/installation.md)
- [Configuration](docs/configuration.md)
- [API contract](docs/api-reference.md)
- [Security](docs/security.md)

## License

MIT. See [LICENSE](LICENSE).
