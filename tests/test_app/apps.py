from django.apps import AppConfig


class ImportExportTestAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tests.test_app"
    label = "fk_import_export_test_app"
