from decimal import Decimal

import pytest

from fk_import_export.conf import get_resource
from fk_import_export.registry import resource_class
from tests.test_app.models import Category, Product


@pytest.mark.django_db
def test_resource_engine_uses_configured_relation_lookup() -> None:
    category = Category.objects.create(slug="hardware", name="Hardware")
    Product.objects.create(sku="S-1", name="Sensor", price=Decimal("19.99"), category=category)

    resource = resource_class(get_resource("products"))()
    dataset = resource.export(Product.objects.all())

    assert dataset.headers == ["sku", "name", "price", "category"]
    assert dataset.dict[0]["category"] == "hardware"
