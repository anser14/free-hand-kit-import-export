from decimal import Decimal

import pytest
from django.test import override_settings
from tablib import Dataset

from fk_import_export.conf import get_resource
from fk_import_export.registry import resource_class
from tests.test_app.models import Category, Product, Tag


@pytest.mark.django_db
def test_resource_engine_uses_configured_relation_lookup() -> None:
    category = Category.objects.create(slug="hardware", name="Hardware")
    Product.objects.create(sku="S-1", name="Sensor", price=Decimal("19.99"), category=category)

    resource = resource_class(get_resource("products"))()
    dataset = resource.export(Product.objects.all())

    assert dataset.headers == ["sku", "name", "price", "category"]
    assert dataset.dict[0]["category"] == "hardware"


@pytest.mark.django_db
def test_resource_engine_imports_many_to_many_values_by_explicit_lookup() -> None:
    category = Category.objects.create(slug="hardware", name="Hardware")
    Tag.objects.create(slug="wireless", name="Wireless")
    Tag.objects.create(slug="compact", name="Compact")
    resource_settings = {
        "RESOURCES": {
            "tagged_products": {
                "MODEL": "fk_import_export_test_app.Product",
                "IMPORT_FIELDS": ("sku", "name", "price", "category", "tags"),
                "EXPORT_FIELDS": ("sku", "name", "price", "category", "tags"),
                "IMPORT_ID_FIELDS": ("sku",),
                "RELATIONS": {
                    "category": {"LOOKUP_FIELD": "slug"},
                    "tags": {"LOOKUP_FIELD": "slug", "SEPARATOR": "|"},
                },
            }
        }
    }
    with override_settings(FREEHAND_KIT_IMPORT_EXPORT=resource_settings):
        resource = resource_class(get_resource("tagged_products"))()
        dataset = Dataset(headers=["sku", "name", "price", "category", "tags"])
        dataset.append(["S-2", "Keyboard", "99.99", "hardware", "wireless|compact"])
        result = resource.import_data(
            dataset,
            dry_run=False,
            use_transactions=True,
            rollback_on_validation_errors=True,
        )

    product = Product.objects.get(sku="S-2")

    assert result.has_errors() is False
    assert result.has_validation_errors() is False
    assert product.category == category
    assert set(product.tags.values_list("slug", flat=True)) == {"wireless", "compact"}
