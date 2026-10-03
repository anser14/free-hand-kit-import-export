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


def test_non_positive_operational_limit_is_reported_by_system_check() -> None:
    with override_settings(
        FREEHAND_KIT_IMPORT_EXPORT={
            "MAX_ROWS": 0,
            "RESOURCES": {},
        }
    ):
        issues = configuration_issues()

    assert issues[0].id == "fk_import_export.E001"


def test_retention_period_must_be_positive_or_disabled() -> None:
    with override_settings(
        FREEHAND_KIT_IMPORT_EXPORT={
            "SOURCE_RETENTION_DAYS": 0,
            "RESOURCES": {},
        }
    ):
        issues = configuration_issues()

    assert issues[0].id == "fk_import_export.E001"


def test_relation_fields_require_an_explicit_lookup_configuration() -> None:
    with override_settings(
        FREEHAND_KIT_IMPORT_EXPORT={
            "RESOURCES": {
                "products": {
                    "MODEL": "fk_import_export_test_app.Product",
                    "IMPORT_FIELDS": ("sku", "name", "price", "category"),
                    "EXPORT_FIELDS": ("sku", "name", "price", "category"),
                    "IMPORT_ID_FIELDS": ("sku",),
                }
            }
        }
    ):
        issues = configuration_issues()

    assert any(issue.id == "fk_import_export.E018" for issue in issues)


def test_many_to_many_fields_cannot_be_ordered() -> None:
    with override_settings(
        FREEHAND_KIT_IMPORT_EXPORT={
            "RESOURCES": {
                "products": {
                    "MODEL": "fk_import_export_test_app.Product",
                    "EXPORT_FIELDS": ("sku", "tags"),
                    "ORDERING_FIELDS": ("tags",),
                    "RELATIONS": {"tags": {"LOOKUP_FIELD": "slug"}},
                }
            }
        }
    ):
        issues = configuration_issues()

    assert any(issue.id == "fk_import_export.E019" for issue in issues)


def test_scope_requires_a_real_direct_user_field() -> None:
    with override_settings(
        FREEHAND_KIT_IMPORT_EXPORT={
            "RESOURCES": {
                "products": {
                    "MODEL": "fk_import_export_test_app.Product",
                    "EXPORT_FIELDS": ("sku",),
                    "SCOPE": {
                        "MODEL_FIELD": "owner",
                        "USER_ATTRIBUTE": "missing_user_attribute",
                    },
                }
            }
        }
    ):
        issues = configuration_issues()

    assert any(issue.id == "fk_import_export.E022" for issue in issues)


def test_scope_field_cannot_be_client_imported() -> None:
    with override_settings(
        FREEHAND_KIT_IMPORT_EXPORT={
            "RESOURCES": {
                "products": {
                    "MODEL": "fk_import_export_test_app.Product",
                    "IMPORT_FIELDS": ("sku", "owner"),
                    "EXPORT_FIELDS": ("sku",),
                    "IMPORT_ID_FIELDS": ("sku",),
                    "RELATIONS": {"owner": {"LOOKUP_FIELD": "username"}},
                    "SCOPE": {"MODEL_FIELD": "owner", "USER_ATTRIBUTE": "$self"},
                }
            }
        }
    ):
        issues = configuration_issues()

    assert any(issue.id == "fk_import_export.E024" for issue in issues)


def test_policy_must_import_a_resource_policy_subclass() -> None:
    with override_settings(
        FREEHAND_KIT_IMPORT_EXPORT={
            "RESOURCES": {
                "products": {
                    "MODEL": "fk_import_export_test_app.Product",
                    "EXPORT_FIELDS": ("sku",),
                    "POLICY": "tests.test_app.policies.NotAPolicy",
                }
            }
        }
    ):
        issues = configuration_issues()

    assert any(issue.id == "fk_import_export.E023" for issue in issues)
