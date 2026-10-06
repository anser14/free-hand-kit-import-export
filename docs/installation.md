# Install Freehand Kit Import Export in Django

Use this package when you want a reusable, secure CSV import and export API for approved
Django models. It works with Django REST Framework; it does not authenticate users or run
background jobs for you.

## Requirements

- Python 3.11, 3.12, or 3.13
- Django 5.2 through 6.0
- Django REST Framework 3.17.x
- A Django authentication setup; users must have the resource permissions you configure

`1.0.0` accepts **UTF-8 CSV files only**. Do not install an XLSX dependency expecting
XLSX import support.

## 1. Install the package

```bash
python -m pip install freehand-kit-import-export
```

## 2. Add installed apps and OpenAPI configuration

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
```

## 3. Configure at least one resource

Add `FREEHAND_KIT_IMPORT_EXPORT` to `settings.py`. A resource is the public name for one
model and its allowed CSV/API fields. Start with the smallest safe field set; never include
passwords, permissions, ownership, or other server-controlled values in `IMPORT_FIELDS`.

```python
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

See the [configuration guide](configuration.md) before adding relationships, scopes, or a
custom policy.

## 4. Mount the API and Swagger UI

Mount import/export APIs beneath a host-chosen prefix and the package's shared OpenAPI
routes beneath the API root. Every endpoint requires authentication and the configured
resource permission. Resources without explicit `PERMISSIONS` use the safe `$staff`
compatibility policy:

```python
# urls.py
from django.urls import include, path

urlpatterns = [
    path("api/data/", include("fk_import_export.urls")),
    path("api/", include("fk_import_export.docs_urls")),
]
```

This exposes the unified schema at `/api/schema/` and Swagger UI at `/api/docs/`. If a
host already mounts `fk_auth.urls` or its own central drf-spectacular schema at `/api/`,
omit `fk_import_export.docs_urls`: the existing `/api/docs/` view automatically documents
these import/export routes too. Do not expose two documentation views at the same path.

## 5. Migrate, validate, and run a worker

Apply the package migration and validate settings before accepting imports:

```bash
python manage.py migrate
python manage.py check --tag fk_import_export
```

Then run the durable worker under a supervisor, container, or scheduler:

```bash
python manage.py process_import_jobs --max-jobs 10
```

For a complete CSV upload, preview, confirmation, and export walkthrough, continue to
the [end-to-end quickstart](quickstart.md).

## Before production

`ImportJob.source_file` contains submitted CSV data. Configure private Django storage,
an explicit retention policy, backups, and monitoring before allowing real data uploads.
Review the [security guide](security.md) and [operations guide](operations.md).
