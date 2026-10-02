from fk_import_export.checks import freehand_kit_import_export_settings_check


def test_registered_system_check_returns_no_issues_for_valid_configuration() -> None:
    assert freehand_kit_import_export_settings_check() == []
