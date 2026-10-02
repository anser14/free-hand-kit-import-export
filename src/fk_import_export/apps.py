from django.apps import AppConfig


class FKImportExportConfig(AppConfig):
    """Django application configuration for Freehand Kit Import Export."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "fk_import_export"
    label = "fk_import_export"
    verbose_name = "Freehand Kit Import Export"

    def ready(self) -> None:
        # Import Django system checks only after the app registry is ready.
        from . import checks  # noqa: F401
