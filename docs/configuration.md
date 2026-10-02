# Configuration

The package owns one setting: `FREEHAND_KIT_IMPORT_EXPORT`.

```python
FREEHAND_KIT_IMPORT_EXPORT = {
    "MAX_UPLOAD_BYTES": 5 * 1024 * 1024,
    "MAX_ROWS": 10_000,
    "MAX_ERROR_ROWS": 100,
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

Run this after configuration changes:

```bash
python manage.py check --tag fk_import_export
```
