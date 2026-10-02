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

Mount `fk_import_export.urls` beneath a host-chosen prefix. The first foundation
endpoints are staff-only while the per-resource policy adapter is completed.
