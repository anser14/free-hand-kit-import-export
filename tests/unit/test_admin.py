from django.contrib import admin
from django.test import RequestFactory

from fk_import_export.admin import ImportJobAdmin
from fk_import_export.models import ImportJob


def test_import_job_admin_is_read_only_for_manual_creation() -> None:
    admin_instance = admin.site._registry[ImportJob]

    assert isinstance(admin_instance, ImportJobAdmin)
    assert admin_instance.has_add_permission(RequestFactory().get("/")) is False
    assert "source_sha256" in admin_instance.search_fields
