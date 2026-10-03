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

Mount `fk_import_export.urls` beneath a host-chosen prefix. Every endpoint requires
authentication and the configured resource policy; resources without explicit
`PERMISSIONS` use the safe `$staff` compatibility policy:

```python
from django.urls import include, path

urlpatterns = [
    path("api/data/", include("fk_import_export.urls")),
]
```

Apply the package migration before accepting imports:

```bash
python manage.py migrate
python manage.py check --tag fk_import_export
```

`ImportJob.source_file` contains submitted CSV data. Configure a private Django media
storage backend and an explicit retention policy before allowing real data uploads.
