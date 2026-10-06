# Django CSV Import and Export API Quickstart

This guide configures one Django model, previews a CSV upload, confirms it, processes the
job, and exports the resulting data. It is deliberately small so you can copy it into an
existing Django REST Framework project and then extend it safely.

**Time:** about 10 minutes.

**You need:** Python 3.11+, Django 5.2+, Django REST Framework, an authenticated user, and
a model named `inventory.Product` with editable `sku`, `name`, and `price` fields.

## What you will build

At the end, authorized users can use these endpoints:

| Action | Endpoint |
| --- | --- |
| Discover configured models | `GET /api/data/resources/` |
| Download exact CSV headers | `GET /api/data/resources/products/template/` |
| Validate a file without writing rows | `POST /api/data/resources/products/imports/preview/` |
| Queue a successful preview | `POST /api/data/import-jobs/{id}/confirm/` |
| Read job progress and results | `GET /api/data/import-jobs/{id}/` |
| List JSON records | `GET /api/data/resources/products/records/` |
| Download CSV | `GET /api/data/resources/products/export/` |

Swagger UI is available at `GET /api/docs/`.

## 1. Install

```bash
python -m pip install freehand-kit-import-export
```

The package supports UTF-8 `.csv` files. It does not import XLSX files in version `1.0.0`.

## 2. Add applications and API schema settings

In `settings.py`:

```python
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

Keep your existing DRF authentication configuration. The package uses the authenticated
`request.user`; it does not issue login tokens or create users.

## 3. Register a safe model resource

Add this in `settings.py` after the app settings above:

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

How to choose these values:

- `MODEL` is the Django model label: `app_label.ModelName`.
- `IMPORT_FIELDS` are the exact CSV columns a client may send.
- `EXPORT_FIELDS` are the fields an authorized user may receive.
- `IMPORT_ID_FIELDS` choose how rows update existing data. `sku` means the same SKU is
  updated; a new SKU creates a new row.
- `PERMISSIONS` use your normal Django permission codenames. A user needs `IMPORT` to
  preview, confirm, and view their jobs.

Do not include passwords, groups, permissions, owner IDs, tenant IDs, or server-computed
fields in `IMPORT_FIELDS`. For foreign keys, many-to-many fields, tenant scopes, or custom
authorization rules, see [resource configuration](configuration.md).

## 4. Mount URLs and apply migrations

In the host `urls.py`:

```python
from django.urls import include, path

urlpatterns = [
    path("api/data/", include("fk_import_export.urls")),
    path("api/", include("fk_import_export.docs_urls")),
]
```

Then validate and migrate:

```bash
python manage.py check --tag fk_import_export
python manage.py migrate
```

Start your server and open `http://localhost:8000/api/docs/`. Authenticate using the same
method your project uses. If another package already owns `/api/schema/` and `/api/docs/`,
keep that central documentation route and mount only `fk_import_export.urls` at
`/api/data/`.

## 5. Give a user access

Give the user these standard Django permissions for `inventory.Product`:

- `view_product` to discover the resource, list JSON records, and export CSV.
- `change_product` to preview imports, confirm jobs, and read their own job history.

For initial local testing, a Django superuser already has these permissions. In a real
project, grant them through a group rather than making operational users staff or superuser.

## 6. Create or download the CSV template

First, use the template endpoint. It always reflects the live configured field order:

```bash
curl -H "Authorization: Bearer <access-token>" \
  http://localhost:8000/api/data/resources/products/template/ \
  --output products-template.csv
```

For the sample configuration, `products.csv` must be UTF-8 and look exactly like this:

```csv
sku,name,price
SKU-001,Keyboard,99.99
SKU-002,Mouse,49.99
```

The header set must exactly equal `IMPORT_FIELDS`. Extra, missing, duplicate, blank, or
misspelled headers are rejected. The file must end in `.csv`; CSV cell values may contain
commas only when correctly quoted according to normal CSV rules.

## 7. Preview the import — no database rows are written

Use the preview endpoint with a multipart `file` field:

```bash
curl --request POST \
  --header "Authorization: Bearer <access-token>" \
  --form "file=@products.csv;type=text/csv" \
  http://localhost:8000/api/data/resources/products/imports/preview/
```

A successful preview returns `201 Created` and a payload similar to:

```json
{
  "id": "8f1a1f7e-8f7a-4d1c-9e2f-000000000000",
  "resource_key": "products",
  "status": "previewed",
  "confirmation_eligible": true,
  "progress": {"total_rows": 2, "completed_rows": 0, "percent": 0}
}
```

Copy the `id` as `JOB_ID`. A preview is a dry run: it validates the file and persists a
private audit job, but it does not create or update product rows.

If individual rows have validation errors, the API still returns a stored job with
`"status": "failed"` and sanitized errors. Correct the CSV and preview it again. If the
file itself is structurally invalid—for example, it has the wrong header—the API returns
`400` and creates no job.

## 8. Run the worker and confirm the preview

Keep a worker running under your process supervisor, container, or scheduler:

```bash
python manage.py process_import_jobs --max-jobs 10
```

When the preview response says `confirmation_eligible: true`, queue it:

```bash
curl --request POST \
  --header "Authorization: Bearer <access-token>" \
  http://localhost:8000/api/data/import-jobs/<JOB_ID>/confirm/
```

The API returns `202 Accepted` while processing is queued or underway. The worker reloads
and hashes the saved file again, rechecks the CSV contract, and writes all affected rows in
one database transaction. Sending the same confirmation request again is safe.

For local experimentation without a long-running process, run the worker after confirming:

```bash
python manage.py process_import_jobs --max-jobs 1
```

## 9. Check results and download errors

Poll the job until `status` is `committed` or `failed`:

```bash
curl -H "Authorization: Bearer <access-token>" \
  http://localhost:8000/api/data/import-jobs/<JOB_ID>/
```

For a failed job, download only the sanitized error metadata:

```bash
curl -H "Authorization: Bearer <access-token>" \
  http://localhost:8000/api/data/import-jobs/<JOB_ID>/errors/ \
  --output import-errors.csv
```

The report contains line numbers, error categories, and field names. It deliberately does
not include uploaded cell values or raw database exceptions. Each user can see only their
own jobs, and only while they retain the configured import permission.

## 10. List and export data

Use the records endpoint for a paginated JSON response:

```bash
curl -H "Authorization: Bearer <access-token>" \
  "http://localhost:8000/api/data/resources/products/records/?search=Keyboard&ordering=sku"
```

Export all matching approved fields as CSV:

```bash
curl -H "Authorization: Bearer <access-token>" \
  "http://localhost:8000/api/data/resources/products/export/?ordering=sku" \
  --output products-export.csv
```

Search, ordering, and `filter.<field>` values work only for fields allowlisted in the
resource configuration. Exports reject oversized result sets instead of silently producing
an unbounded download. Values that could become spreadsheet formulas are escaped safely.

## 11. Operate it safely in production

Before accepting real uploads:

1. Store uploaded source files in private, non-public Django storage.
2. Set `MAX_UPLOAD_BYTES`, `MAX_ROWS`, `MAX_EXPORT_ROWS`, timeout, retry, and retention
   values appropriate for your data.
3. Run the worker as a supervised process and monitor failed jobs.
4. Test every custom relation, permission, scope, and policy with real user roles.
5. Run retention cleanup as a dry run before enabling deletion:

   ```bash
   python manage.py purge_import_jobs --batch-size 100
   python manage.py purge_import_jobs --batch-size 100 --apply
   ```

Read [operations](operations.md), [security](security.md), and
[configuration](configuration.md) before production rollout.

## Next steps

- Add [relations, scopes, and custom policies](configuration.md) for real-world models.
- Review every endpoint and response in the [API reference](api-reference.md).
- Connect [lifecycle hooks](integration-hooks.md) for notifications or audit integrations.
- Run the [Dockerized custom-user demo](../examples/production_demo/README.md) for a
  PostgreSQL and worker example.
