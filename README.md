# Freehand Kit Import Export: Django REST Framework CSV Import/Export API

`freehand-kit-import-export` gives Django and Django REST Framework projects a secure,
configuration-first API for importing and exporting model data as CSV. Register an
approved model once in Django settings; the package provides discoverable endpoints,
Swagger/OpenAPI documentation, CSV templates, dry-run validation, a durable import queue,
and bounded exports.

> **Status: stable.** Version `1.0.0` is the first stable release. It supports Python
> 3.11–3.13, Django 5.2–6.0, and Django REST Framework 3.17.x.

## Why use this Django import/export package?

Most Django projects need CSV import and export sooner or later: product catalog uploads,
member updates, back-office data fixes, onboarding data, or customer reports. Rebuilding
serializers, CSV parsing, validation, permission checks, pagination, and API documentation
for every model is repetitive and easy to get wrong.

Freehand Kit Import Export lets the host application keep control of its models and access
rules while the package owns the reusable workflow. API callers can use only resources and
fields that the host developer explicitly approves; they cannot submit arbitrary model names
or field lists.

| You configure | The package provides |
| --- | --- |
| Django model, permitted fields, identifiers, relations, permissions, and optional owner/tenant scope | Resource discovery, CSV template, preview, confirmation, job history, records, and export APIs |
| Authentication in your project | Permission checks on every endpoint; the package never creates an authentication system |
| A worker or scheduler | Durable, retry-bounded import processing after an explicit confirmation |
| Private storage and retention policy | Source hashes, sanitized error reports, and safe cleanup commands |

## Supported workflow

1. A developer registers a model as a named resource, for example `products`.
2. An authorized user downloads the exact CSV template or creates a matching UTF-8 CSV.
3. The user uploads it to the **preview** endpoint. No model rows are written yet.
4. The API returns a job with validation results. The user confirms only a successful preview.
5. A background worker revalidates the saved file and atomically writes the model rows.
6. The user polls the job, downloads sanitized errors when needed, lists records, or exports CSV.

Imports are CSV-only in `1.0.0`. XLSX, JSON, and arbitrary model/field submission are not
supported by this package version.

## Install and run your first import

```bash
python -m pip install freehand-kit-import-export
```

1. Add `rest_framework`, `drf_spectacular`, and `fk_import_export` to `INSTALLED_APPS`.
2. Register a resource in `FREEHAND_KIT_IMPORT_EXPORT`.
3. Mount `/api/data/` and the shared Swagger route at `/api/docs/`.
4. Run `python manage.py migrate` and `python manage.py check --tag fk_import_export`.
5. Run `python manage.py process_import_jobs --max-jobs 10` under a worker or scheduler.

The complete copy-and-paste tutorial—including settings, URLs, CSV upload, preview,
confirmation, worker processing, records, exports, errors, and production checklist—is in
[the quickstart guide](docs/quickstart.md).

## Minimal Django configuration

```python
# settings.py
INSTALLED_APPS = [
    # Your Django apps...
    "rest_framework",
    "drf_spectacular",
    "fk_import_export",
]

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

FREEHAND_KIT_IMPORT_EXPORT = {
    "RESOURCES": {
        "products": {
            "MODEL": "inventory.Product",
            "IMPORT_FIELDS": ("sku", "name", "price"),
            "EXPORT_FIELDS": ("sku", "name", "price"),
            "IMPORT_ID_FIELDS": ("sku",),
            "SEARCH_FIELDS": ("sku", "name"),
            "ORDERING_FIELDS": ("sku", "name", "price"),
            "FILTER_FIELDS": (),
            "PERMISSIONS": {
                "READ": "inventory.view_product",
                "EXPORT": "inventory.view_product",
                "IMPORT": "inventory.change_product",
            },
        },
    },
}
```

```python
# urls.py
from django.urls import include, path

urlpatterns = [
    path("api/data/", include("fk_import_export.urls")),
    path("api/", include("fk_import_export.docs_urls")),
]
```

Visit `/api/docs/` after starting the Django project. If your project already exposes a
central drf-spectacular schema—such as one mounted by `fk_auth`—do **not** mount
`fk_import_export.docs_urls` again. The existing `/api/docs/` automatically includes these
endpoints.

## Core features

- **Plug-and-play Django REST Framework endpoints** for approved Django models.
- **CSV import preview and confirmation** so invalid data is never written accidentally.
- **Durable worker queue** with retries, stale-job recovery, atomic commits, and job history.
- **Secure relation handling** with explicit unique lookups; related rows are never silently created.
- **Per-resource Django permissions** and direct owner/tenant scopes.
- **Paginated records API** with allowlisted search, ordering, and filters.
- **Bounded CSV exports** with spreadsheet formula-injection protection.
- **Automatic Swagger/OpenAPI documentation** at `/api/docs/` and `/api/schema/`.
- **Sanitized error reports, lifecycle signals, and retention tools** for operating imports safely.

## Common use cases

- Django admin or operations teams importing product, inventory, pricing, customer, or membership CSV files.
- React, Vue, mobile, and partner clients using a documented Django REST Framework import API.
- SaaS applications that must isolate data by owner or tenant during import and export.
- Back-office systems that need searchable JSON records alongside downloadable CSV reports.

## Security model

The package is intentionally restrictive:

- Only registered resources and explicit fields are exposed.
- Sensitive fields—passwords, staff flags, groups, permissions, and tokens—are denied by default.
- Uploads must be UTF-8 `.csv` files with exact headers and configured byte/row limits.
- Preview and worker execution are transactional; confirming a job is safe to retry.
- Stored errors contain line numbers and categories, never uploaded cell values or raw database exceptions.
- CSV exports are capped and guarded against spreadsheet formula injection.

You must still configure your application's authentication, private media storage,
permissions, tenant rules, backups, and monitoring. Read the [security guide](docs/security.md)
before accepting real customer data.

## Documentation

- **Start here:** [end-to-end quickstart](docs/quickstart.md)
- [Installation and URL setup](docs/installation.md)
- [Resource configuration reference](docs/configuration.md)
- [API endpoint reference](docs/api-reference.md)
- [Worker, retries, and retention operations](docs/operations.md)
- [Custom authorization policies](docs/configuration.md#custom-resource-policy)
- [Lifecycle integration hooks](docs/integration-hooks.md)
- [Production-style Docker demo with a custom user model](examples/production_demo/README.md)
- [Security guidance](docs/security.md)
- [Compatibility and supported versions](docs/compatibility.md)
- [Architecture decision](docs/architecture/ADR-0001-engine-and-safety-boundary.md)

## License

MIT. See [LICENSE](LICENSE).
