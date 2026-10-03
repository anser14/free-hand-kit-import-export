# Configuration

The package owns one setting: `FREEHAND_KIT_IMPORT_EXPORT`.

```python
FREEHAND_KIT_IMPORT_EXPORT = {
    "MAX_UPLOAD_BYTES": 5 * 1024 * 1024,
    "MAX_ROWS": 10_000,
    "MAX_ERROR_ROWS": 100,
    "PAGE_SIZE": 100,
    "MAX_PAGE_SIZE": 500,
    "MAX_EXPORT_ROWS": 10_000,
    "PROCESSING_TIMEOUT_SECONDS": 60 * 60,
    "MAX_ATTEMPTS": 3,
    "SOURCE_RETENTION_DAYS": 7,
    "JOB_RETENTION_DAYS": 90,
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
                "category": {"LOOKUP_FIELD": "slug", "SEPARATOR": "|"},
            },
            "PERMISSIONS": {
                "READ": "inventory.view_product",
                "EXPORT": "inventory.view_product",
                "IMPORT": "inventory.change_product",
            },
            "SCOPE": {"MODEL_FIELD": "owner", "USER_ATTRIBUTE": "$self"},
            "POLICY": "inventory.import_policies.ProductMembershipPolicy",
        },
    },
}
```

`MODEL` uses `app_label.ModelName`. Fields must be direct, editable model fields;
nested `__` paths are not allowed. `IMPORT_ID_FIELDS` determine update matching and
must be a subset of `IMPORT_FIELDS`.

For a relationship, declare a stable related-model lookup field. Do not rely on a
display name that is not unique. The package does not auto-create related records.

The optional operational limits above are positive integers. The defaults are 5 MiB,
10,000 data rows, and 100 stored error entries. CSV headers must exactly match the
configured `IMPORT_FIELDS` set; this prevents callers from smuggling extra model fields
into the import engine. Relation names must be declared in import or export fields.

`PROCESSING_TIMEOUT_SECONDS` controls when a worker considers an interrupted
`processing` job stale. `MAX_ATTEMPTS` caps recovery retries; a stale job at the cap is
marked failed with a sanitized processing error. Set both values from realistic worker
timeouts and the maximum execution time of your largest permitted upload.

`SOURCE_RETENTION_DAYS` and `JOB_RETENTION_DAYS` are optional positive integers; both
default to `None`, which disables their respective deletion policy. Source retention
removes only the stored CSV from old committed or failed jobs while preserving the
sanitized audit record. Job retention deletes old committed or failed jobs and any
remaining stored source. Choose periods that satisfy your application's privacy,
support, and legal retention requirements; the package never selects a policy for you.

`PERMISSIONS` declares all requirements for `READ`, `EXPORT`, and `IMPORT`. A value can
be a Django permission codename (`"app_label.codename"`) or a list/tuple of codenames
that must all be held. `$staff` is the safe compatibility default when `PERMISSIONS` is
omitted; production projects should declare explicit codenames. Read controls discovery,
schema, templates, and JSON records; export controls CSV export; import controls preview
and all owner-visible job endpoints.

`SCOPE` is optional for the common direct owner/tenant case. `MODEL_FIELD` identifies one
direct non-many-to-many field on the imported model, while `USER_ATTRIBUTE` is either a
direct field on the configured user model or `$self`. The package filters records and
exports by that value, constrains import identity matching to it, and sets the field
server-side during import. This deliberately does not accept nested paths or arbitrary
callbacks. Use the custom policy hook below for memberships, indirect tenancy, or other
domain-specific rules.

## Custom resource policy

`POLICY` is optional and names a trusted, dotted import path to a zero-argument subclass
of `fk_import_export.policies.ResourcePolicy`. Use it only for host-owned rules that a
direct `SCOPE` cannot express, such as organization membership or a domain-specific
visibility rule. The package validates the import path and subclass during Django system
checks.

```python
from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import ValidationError
from django.db.models import Model, QuerySet

from fk_import_export.policies import ResourcePolicy


class ProductMembershipPolicy(ResourcePolicy):
    def filter_queryset(
        self, *, queryset: QuerySet[Model], user: AbstractBaseUser, operation: str
    ) -> QuerySet[Model]:
        return queryset.filter(organization__members=user)

    def prepare_instance(self, *, instance: Model, user: AbstractBaseUser) -> None:
        if not user.organization_memberships.filter(organization=instance.organization).exists():
            raise ValidationError({"organization": "The current user is not a member."})
```

`filter_queryset` is invoked for `READ`, `EXPORT`, and `IMPORT` operations; for an import
it limits existing-record identity matching. `prepare_instance` runs immediately before
each imported model instance is saved and can attach or validate domain data. It may raise
`ValidationError` to reject the row. Return a queryset for the configured model only.
The policy is composed after a direct `SCOPE` filter and cannot bypass `PERMISSIONS`,
resource field allowlists, CSV validation, or the private job-owner boundary. Keep the
constructor side-effect-free and move slow work out of the request/worker path.

`records/` supports `search`, `ordering`, `page`, `page_size`, and exact
`filter.<field>` parameters only when their fields are explicitly present in
`SEARCH_FIELDS`, `ORDERING_FIELDS`, or `FILTER_FIELDS`. `export/` uses the same search,
ordering, and filter controls but intentionally ignores pagination and is capped by
`MAX_EXPORT_ROWS`. Relationship fields must use `RELATIONS` with a stable lookup field;
many-to-many ordering is intentionally rejected.

Run this after configuration changes:

```bash
python manage.py check --tag fk_import_export
```
