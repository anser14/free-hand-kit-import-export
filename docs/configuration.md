# Configuration

The package owns one setting: `FREEHAND_KIT_IMPORT_EXPORT`.

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

Run this after configuration changes:

```bash
python manage.py check --tag fk_import_export
```
