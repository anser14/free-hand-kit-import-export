# Installation

```bash
python -m pip install freehand-kit-import-export
```

For future XLSX support, install the optional extra:

```bash
python -m pip install "freehand-kit-import-export[xlsx]"
```

Add the app and supporting DRF/OpenAPI packages to the host project:

```python
INSTALLED_APPS = [
    # Host applications...
    "rest_framework",
    "drf_spectacular",
    "fk_import_export",
]
```

Mount import/export APIs beneath a host-chosen prefix and mount the package's shared
OpenAPI routes beneath the API root. Every endpoint requires authentication and the
configured resource policy; resources without explicit `PERMISSIONS` use the safe
`$staff` compatibility policy:

```python
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

Apply the package migration before accepting imports:

```bash
python manage.py migrate
python manage.py check --tag fk_import_export
```

`ImportJob.source_file` contains submitted CSV data. Configure a private Django media
storage backend and an explicit retention policy before allowing real data uploads.
