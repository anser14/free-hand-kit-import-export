# Production-style consumer demo

This is a runnable Django consumer project for `freehand-kit-import-export`. It uses a
custom `accounts.User` model, PostgreSQL, a separate durable-import worker, private
media storage, and a relational `inventory.Product` resource. It is intentionally a
demo: adapt the host/domain, secret management, TLS termination, backups, observability,
and storage backend to the target deployment.

The package is installed from the wheel built from this repository. It is not imported
from the repository checkout at runtime, which verifies the normal consumer installation
path.

## Start it

From the repository root:

```bash
cp examples/production_demo/.env.example examples/production_demo/.env
# Edit .env and replace DJANGO_SECRET_KEY and POSTGRES_PASSWORD.
docker compose --env-file examples/production_demo/.env \
  -f examples/production_demo/compose.yaml up --build
```

In PowerShell, use this copy command instead:

```powershell
Copy-Item examples/production_demo/.env.example examples/production_demo/.env
```

The one-shot `migrate` service applies database migrations exactly once. Docker Compose
starts `web` and `worker` only after that succeeds, avoiding a migration race at startup.
The `worker` service polls the database-backed job queue every five seconds. Web and
worker share a private Docker volume for uploaded CSV sources; no media URL is configured
or exposed.

Create an initial administrator in another terminal:

```bash
docker compose --env-file examples/production_demo/.env \
  -f examples/production_demo/compose.yaml exec web python manage.py createsuperuser
```

Sign in at `http://localhost:8000/admin/`. Create the categories and tags referenced by
an import there. A superuser has the resource permissions already. For a non-superuser,
grant `inventory | product | Can view product` for listing/export and `Can change product`
for preview/confirmation, through Django admin or a group.

## API workflow

Visit `http://localhost:8000/api/data/docs/` after signing into admin in the same browser.
The generated Swagger UI exposes the discovery, template, records, export, preview, job,
error-report, and confirmation endpoints.

The configured CSV contract is:

```csv
sku,name,price,category,tags
SKU-001,Example notebook,15.50,stationery,featured|sale
```

- `category` is looked up by `Category.slug`.
- `tags` is a `|`-separated set of `Tag.slug` values.
- Products are identified by `sku`, but only inside the authenticated user's owner scope.
- The package assigns `Product.owner` server-side; the client must not send it.

Use `GET /api/data/resources/products/template/` to obtain the exact header row. Submit a
multipart `file` to `POST /api/data/resources/products/imports/preview/`; no product is
written at this stage. When the response reports a `previewed` job, submit
`POST /api/data/import-jobs/{id}/confirm/`. Confirmation returns `202`; the separate
worker then commits or safely fails the job. Poll `GET /api/data/import-jobs/{id}/` or
use the owner-private paginated `GET /api/data/import-jobs/` history endpoint.

`GET /api/data/resources/products/records/` and
`GET /api/data/resources/products/export/` are limited to the caller's products. They
support the resource's approved search, ordering, and filter controls only.

## Operations

Inspect container state and worker output:

```bash
docker compose --env-file examples/production_demo/.env \
  -f examples/production_demo/compose.yaml ps
docker compose --env-file examples/production_demo/.env \
  -f examples/production_demo/compose.yaml logs --follow worker
docker compose --env-file examples/production_demo/.env \
  -f examples/production_demo/compose.yaml logs migrate
```

The demo retains source CSV files for seven days and terminal job audit records for
90 days. First review cleanup without deleting anything, then apply it only after the
output is understood:

```bash
docker compose --env-file examples/production_demo/.env \
  -f examples/production_demo/compose.yaml exec worker python manage.py purge_import_jobs
docker compose --env-file examples/production_demo/.env \
  -f examples/production_demo/compose.yaml exec worker python manage.py purge_import_jobs --apply
```

To stop the local demo while retaining PostgreSQL and private uploaded sources:

```bash
docker compose --env-file examples/production_demo/.env \
  -f examples/production_demo/compose.yaml down
```

Removing volumes deletes the demo database and all uploaded source files. Only do that
when the local data is no longer needed:

```bash
docker compose --env-file examples/production_demo/.env \
  -f examples/production_demo/compose.yaml down --volumes
```
