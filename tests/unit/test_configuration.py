from django.core.checks import Error
from django.test import override_settings

from fk_import_export.conf import configuration_issues, get_resource


def test_configured_resource_resolves_host_model() -> None:
    resource = get_resource("products")

    assert resource.model_label == "fk_import_export_test_app.Product"
    assert resource.import_id_fields == ("sku",)
    assert resource.relations["category"].lookup_field == "slug"


def test_unknown_model_is_reported_by_system_check() -> None:
    with override_settings(
        FREEHAND_KIT_IMPORT_EXPORT={
            "RESOURCES": {
                "bad": {
                    "MODEL": "missing.Model",
                    "IMPORT_FIELDS": ("name",),
                    "EXPORT_FIELDS": ("name",),
                }
            }
        }
    ):
        issues = configuration_issues()

    assert any(issue.id == "fk_import_export.E010" for issue in issues)


def test_sensitive_field_is_rejected() -> None:
    with override_settings(
        FREEHAND_KIT_IMPORT_EXPORT={
            "RESOURCES": {
                "users": {
                    "MODEL": "auth.User",
                    "IMPORT_FIELDS": ("username", "password"),
                    "EXPORT_FIELDS": ("username",),
                }
            }
        }
    ):
        issues = configuration_issues()

    assert any(isinstance(issue, Error) and issue.id == "fk_import_export.E011" for issue in issues)


def test_import_identifiers_must_be_imported_fields() -> None:
    with override_settings(
        FREEHAND_KIT_IMPORT_EXPORT={
            "RESOURCES": {
                "products": {
                    "MODEL": "fk_import_export_test_app.Product",
                    "IMPORT_FIELDS": ("name",),
                    "EXPORT_FIELDS": ("name",),
                    "IMPORT_ID_FIELDS": ("sku",),
                }
            }
        }
    ):
        issues = configuration_issues()

    assert issues[0].id == "fk_import_export.E001"
