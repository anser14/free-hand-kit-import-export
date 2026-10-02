import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APIClient

from fk_import_export.models import ImportJob
from tests.settings import FREEHAND_KIT_IMPORT_EXPORT
from tests.test_app.models import Category, Product


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
    assert response.json()["operations"] == ["template", "preview_import"]


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


def _csv_upload(content: bytes, name: str = "products.csv") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, content, content_type="text/csv")


@pytest.mark.django_db
def test_preview_is_dry_run_then_confirmation_commits_once(staff_client: APIClient) -> None:
    Category.objects.create(slug="hardware", name="Hardware")
    response = staff_client.post(
        "/resources/products/imports/preview/",
        {"file": _csv_upload(b"sku,name,price,category\nSKU-001,Keyboard,99.99,hardware\n")},
        format="multipart",
    )

    assert response.status_code == 201
    assert response.json()["status"] == ImportJob.Status.PREVIEWED
    assert response.json()["summary"]["new"] == 1
    assert response.json()["confirmation_eligible"] is True
    assert Product.objects.count() == 0

    job_id = response.json()["id"]
    confirm_response = staff_client.post(f"/import-jobs/{job_id}/confirm/", format="json")

    assert confirm_response.status_code == 200
    assert confirm_response.json()["status"] == ImportJob.Status.COMMITTED
    assert confirm_response.json()["confirmation_eligible"] is False
    assert Product.objects.get(sku="SKU-001").category.slug == "hardware"

    retry_response = staff_client.post(f"/import-jobs/{job_id}/confirm/", format="json")

    assert retry_response.status_code == 200
    assert retry_response.json()["status"] == ImportJob.Status.COMMITTED
    assert Product.objects.count() == 1


@pytest.mark.django_db
def test_invalid_row_creates_failed_job_without_leaking_uploaded_values(
    staff_client: APIClient,
) -> None:
    response = staff_client.post(
        "/resources/products/imports/preview/",
        {
            "file": _csv_upload(
                b"sku,name,price,category\nSKU-SECRET,Keyboard,99.99,missing-category\n"
            )
        },
        format="multipart",
    )

    assert response.status_code == 201
    assert response.json()["status"] == ImportJob.Status.FAILED
    assert response.json()["confirmation_eligible"] is False
    assert response.json()["errors"][0]["code"] == "processing_error"
    assert b"missing-category" not in response.content
    assert Product.objects.count() == 0

    confirm_response = staff_client.post(
        f"/import-jobs/{response.json()['id']}/confirm/", format="json"
    )

    assert confirm_response.status_code == 409
    assert Product.objects.count() == 0


@pytest.mark.django_db
def test_invalid_csv_contract_is_rejected_without_persisting_a_job(staff_client: APIClient) -> None:
    response = staff_client.post(
        "/resources/products/imports/preview/",
        {"file": _csv_upload(b"sku,name,price,unexpected\nSKU-001,Keyboard,99.99,value\n")},
        format="multipart",
    )

    assert response.status_code == 400
    assert "headers do not match" in response.json()["detail"]
    assert ImportJob.objects.count() == 0


@pytest.mark.django_db
def test_import_jobs_are_private_to_the_submitting_staff_user(staff_client: APIClient) -> None:
    Category.objects.create(slug="hardware", name="Hardware")
    preview_response = staff_client.post(
        "/resources/products/imports/preview/",
        {"file": _csv_upload(b"sku,name,price,category\nSKU-001,Keyboard,99.99,hardware\n")},
        format="multipart",
    )
    job_id = preview_response.json()["id"]

    other_staff = get_user_model().objects.create_user(
        username="other-operator",
        password="not-used",
        is_staff=True,
    )
    other_client = APIClient()
    other_client.force_authenticate(user=other_staff)

    assert other_client.get(f"/import-jobs/{job_id}/").status_code == 404
    assert other_client.post(f"/import-jobs/{job_id}/confirm/", format="json").status_code == 404


@pytest.mark.django_db
def test_confirmation_rejects_a_tampered_stored_source(staff_client: APIClient) -> None:
    Category.objects.create(slug="hardware", name="Hardware")
    preview_response = staff_client.post(
        "/resources/products/imports/preview/",
        {"file": _csv_upload(b"sku,name,price,category\nSKU-001,Keyboard,99.99,hardware\n")},
        format="multipart",
    )
    job = ImportJob.objects.get(id=preview_response.json()["id"])
    job.source_file.save(
        "altered.csv",
        ContentFile(b"sku,name,price,category\nSKU-002,Mouse,49.99,hardware\n"),
        save=True,
    )

    confirm_response = staff_client.post(f"/import-jobs/{job.id}/confirm/", format="json")

    assert confirm_response.status_code == 409
    assert confirm_response.json()["status"] == ImportJob.Status.FAILED
    assert confirm_response.json()["errors"] == [{"line": None, "code": "processing_error"}]
    assert Product.objects.count() == 0


@pytest.mark.django_db
def test_preview_enforces_configured_row_limit(staff_client: APIClient) -> None:
    limited_settings = {
        **FREEHAND_KIT_IMPORT_EXPORT,
        "MAX_ROWS": 1,
    }
    with override_settings(FREEHAND_KIT_IMPORT_EXPORT=limited_settings):
        response = staff_client.post(
            "/resources/products/imports/preview/",
            {
                "file": _csv_upload(
                    b"sku,name,price,category\nSKU-001,Keyboard,99.99,hardware\n"
                    b"SKU-002,Mouse,49.99,hardware\n"
                )
            },
            format="multipart",
        )

    assert response.status_code == 400
    assert "row limit" in response.json()["detail"]
    assert ImportJob.objects.count() == 0
