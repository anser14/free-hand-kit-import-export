import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


@pytest.fixture
def staff_client() -> APIClient:
    user = get_user_model().objects.create_user(
        username="operator",
        password="not-used",
        is_staff=True,
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_staff_can_discover_only_registered_resources(staff_client: APIClient) -> None:
    response = staff_client.get("/resources/")

    assert response.status_code == 200
    assert response.json()[0]["key"] == "products"
    assert response.json()[0]["import_fields"] == ["sku", "name", "price", "category"]


@pytest.mark.django_db
def test_staff_can_download_csv_template(staff_client: APIClient) -> None:
    response = staff_client.get("/resources/products/template/")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/csv")
    assert response.content == b"sku,name,price,category\n"


@pytest.mark.django_db
def test_staff_can_read_the_configured_resource_schema(staff_client: APIClient) -> None:
    response = staff_client.get("/resources/products/")

    assert response.status_code == 200
    assert response.json()["relationships"] == {
        "category": {"lookup_field": "slug", "separator": "|"}
    }
    assert response.json()["operations"] == ["template"]


@pytest.mark.django_db
def test_unknown_resource_is_not_disclosed(staff_client: APIClient) -> None:
    response = staff_client.get("/resources/not_registered/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_non_staff_cannot_enumerate_resources() -> None:
    user = get_user_model().objects.create_user(username="member", password="not-used")
    client = APIClient()
    client.force_authenticate(user=user)

    assert client.get("/resources/").status_code == 403
