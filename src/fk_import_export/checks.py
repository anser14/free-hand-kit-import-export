"""Django system checks for Freehand Kit Import Export."""

from django.core.checks import register

from .conf import configuration_issues


@register("fk_import_export")
def freehand_kit_import_export_settings_check(**kwargs: object):  # type: ignore[no-untyped-def]
    """Validate resource declarations during ``manage.py check``."""

    return configuration_issues()
