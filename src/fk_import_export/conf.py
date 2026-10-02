"""Namespaced configuration and validated resource declarations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from django.apps import apps
from django.conf import settings as django_settings
from django.core.checks import Error
from django.core.exceptions import FieldDoesNotExist, ImproperlyConfigured
from django.db.models import Field, Model

SETTING_NAME = "FREEHAND_KIT_IMPORT_EXPORT"
RESOURCE_KEY_MAX_LENGTH = 80
DEFAULT_MAX_UPLOAD_BYTES = 5 * 1024 * 1024
DEFAULT_MAX_ROWS = 10_000
DEFAULT_MAX_ERROR_ROWS = 100
SENSITIVE_FIELD_NAMES = frozenset(
    {
        "password",
        "is_active",
        "is_staff",
        "is_superuser",
        "groups",
        "user_permissions",
        "last_login",
        "token",
        "tokens",
        "secret",
        "secrets",
    }
)
ALLOWED_RESOURCE_KEYS = frozenset(
    {
        "MODEL",
        "IMPORT_FIELDS",
        "EXPORT_FIELDS",
        "IMPORT_ID_FIELDS",
        "SEARCH_FIELDS",
        "ORDERING_FIELDS",
        "FILTER_FIELDS",
        "RELATIONS",
    }
)
ALLOWED_SETTING_KEYS = frozenset(
    {
        "RESOURCES",
        "MAX_UPLOAD_BYTES",
        "MAX_ROWS",
        "MAX_ERROR_ROWS",
    }
)


class ResourceConfigurationError(ImproperlyConfigured):
    """Raised when code requests an invalid or unregistered resource."""


@dataclass(frozen=True)
class RelationConfig:
    """Explicit lookup contract for a forward Django relation."""

    lookup_field: str
    separator: str = "|"


@dataclass(frozen=True)
class ImportExportSettings:
    """Validated operational limits for synchronous CSV import previews."""

    max_upload_bytes: int
    max_rows: int
    max_error_rows: int


@dataclass(frozen=True)
class ResourceConfig:
    """One host-approved import/export resource."""

    key: str
    model_label: str
    import_fields: tuple[str, ...]
    export_fields: tuple[str, ...]
    import_id_fields: tuple[str, ...]
    search_fields: tuple[str, ...]
    ordering_fields: tuple[str, ...]
    filter_fields: tuple[str, ...]
    relations: dict[str, RelationConfig]

    def model(self) -> type[Model]:
        """Resolve the host model only after Django's registry is ready."""

        try:
            resolved = apps.get_model(self.model_label)
        except (LookupError, ValueError) as exc:
            raise ResourceConfigurationError(
                f"Resource '{self.key}' references unknown model '{self.model_label}'."
            ) from exc
        return resolved


def _field_tuple(value: Any, *, key: str, setting_key: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or not all(
        isinstance(item, str) and item and "__" not in item for item in value
    ):
        raise ResourceConfigurationError(
            f"Resource '{key}' {setting_key} must be a list or tuple of direct field names."
        )
    return tuple(value)


def _relation_config(value: Any, *, key: str) -> dict[str, RelationConfig]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ResourceConfigurationError(f"Resource '{key}' RELATIONS must be a mapping.")

    result: dict[str, RelationConfig] = {}
    for field_name, raw_relation in value.items():
        if not isinstance(field_name, str) or not field_name or "__" in field_name:
            raise ResourceConfigurationError(
                f"Resource '{key}' RELATIONS keys must be direct field names."
            )
        if not isinstance(raw_relation, Mapping):
            raise ResourceConfigurationError(
                f"Resource '{key}' relation '{field_name}' must be a mapping."
            )
        lookup_field = raw_relation.get("LOOKUP_FIELD")
        separator = raw_relation.get("SEPARATOR", "|")
        if not isinstance(lookup_field, str) or not lookup_field or "__" in lookup_field:
            raise ResourceConfigurationError(
                f"Resource '{key}' relation '{field_name}' requires a direct LOOKUP_FIELD."
            )
        if not isinstance(separator, str) or not separator:
            raise ResourceConfigurationError(
                f"Resource '{key}' relation '{field_name}' SEPARATOR must be a non-empty string."
            )
        result[field_name] = RelationConfig(lookup_field=lookup_field, separator=separator)
    return result


def _resource_config(key: str, raw_resource: Any) -> ResourceConfig:
    if (
        not isinstance(key, str)
        or not key
        or len(key) > RESOURCE_KEY_MAX_LENGTH
        or not key.isidentifier()
    ):
        raise ResourceConfigurationError(
            "Resource keys must be Python-identifier-like strings of at most "
            f"{RESOURCE_KEY_MAX_LENGTH} characters."
        )
    if not isinstance(raw_resource, Mapping):
        raise ResourceConfigurationError(f"Resource '{key}' must be a mapping.")

    unexpected = set(raw_resource) - ALLOWED_RESOURCE_KEYS
    if unexpected:
        raise ResourceConfigurationError(
            f"Resource '{key}' has unsupported setting(s): "
            f"{', '.join(sorted(map(str, unexpected)))}."
        )

    model_label = raw_resource.get("MODEL")
    if not isinstance(model_label, str) or model_label.count(".") != 1:
        raise ResourceConfigurationError(
            f"Resource '{key}' MODEL must use the 'app_label.ModelName' format."
        )

    import_fields = _field_tuple(
        raw_resource.get("IMPORT_FIELDS", ()), key=key, setting_key="IMPORT_FIELDS"
    )
    export_fields = _field_tuple(
        raw_resource.get("EXPORT_FIELDS", ()), key=key, setting_key="EXPORT_FIELDS"
    )
    if not import_fields and not export_fields:
        raise ResourceConfigurationError(
            f"Resource '{key}' must declare at least one import or export field."
        )

    import_id_fields = _field_tuple(
        raw_resource.get("IMPORT_ID_FIELDS", ()), key=key, setting_key="IMPORT_ID_FIELDS"
    )
    if not set(import_id_fields).issubset(import_fields):
        raise ResourceConfigurationError(
            f"Resource '{key}' IMPORT_ID_FIELDS must be included in IMPORT_FIELDS."
        )

    relations = _relation_config(raw_resource.get("RELATIONS"), key=key)
    declared_fields = set(import_fields) | set(export_fields)
    undeclared_relations = set(relations) - declared_fields
    if undeclared_relations:
        raise ResourceConfigurationError(
            f"Resource '{key}' RELATIONS must be included in IMPORT_FIELDS or EXPORT_FIELDS: "
            f"{', '.join(sorted(undeclared_relations))}."
        )

    return ResourceConfig(
        key=key,
        model_label=model_label,
        import_fields=import_fields,
        export_fields=export_fields,
        import_id_fields=import_id_fields,
        search_fields=_field_tuple(
            raw_resource.get("SEARCH_FIELDS", ()), key=key, setting_key="SEARCH_FIELDS"
        ),
        ordering_fields=_field_tuple(
            raw_resource.get("ORDERING_FIELDS", ()), key=key, setting_key="ORDERING_FIELDS"
        ),
        filter_fields=_field_tuple(
            raw_resource.get("FILTER_FIELDS", ()), key=key, setting_key="FILTER_FIELDS"
        ),
        relations=relations,
    )


def _settings_mapping() -> Mapping[str, Any]:
    """Return and validate the package's namespaced setting mapping."""

    raw_settings = getattr(django_settings, SETTING_NAME, {})
    if not isinstance(raw_settings, Mapping):
        raise ResourceConfigurationError(f"{SETTING_NAME} must be a mapping.")
    unexpected = set(raw_settings) - ALLOWED_SETTING_KEYS
    if unexpected:
        raise ResourceConfigurationError(
            f"{SETTING_NAME} has unsupported setting(s): {', '.join(sorted(map(str, unexpected)))}."
        )
    return raw_settings


def _positive_int(value: Any, *, setting_key: str, default: int) -> int:
    if value is None:
        return default
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ResourceConfigurationError(
            f"{SETTING_NAME}['{setting_key}'] must be a positive integer."
        )
    return value


def get_runtime_settings() -> ImportExportSettings:
    """Return validated operational limits for this package instance."""

    raw_settings = _settings_mapping()
    return ImportExportSettings(
        max_upload_bytes=_positive_int(
            raw_settings.get("MAX_UPLOAD_BYTES"),
            setting_key="MAX_UPLOAD_BYTES",
            default=DEFAULT_MAX_UPLOAD_BYTES,
        ),
        max_rows=_positive_int(
            raw_settings.get("MAX_ROWS"), setting_key="MAX_ROWS", default=DEFAULT_MAX_ROWS
        ),
        max_error_rows=_positive_int(
            raw_settings.get("MAX_ERROR_ROWS"),
            setting_key="MAX_ERROR_ROWS",
            default=DEFAULT_MAX_ERROR_ROWS,
        ),
    )


def get_resources() -> dict[str, ResourceConfig]:
    """Return validated resource declarations from the host settings module."""

    raw_settings = _settings_mapping()
    raw_resources = raw_settings.get("RESOURCES", {})
    if not isinstance(raw_resources, Mapping):
        raise ResourceConfigurationError(f"{SETTING_NAME}['RESOURCES'] must be a mapping.")
    return {key: _resource_config(key, raw_resource) for key, raw_resource in raw_resources.items()}


def get_resource(key: str) -> ResourceConfig:
    """Return one registered resource or raise a configuration-safe error."""

    try:
        return get_resources()[key]
    except KeyError as exc:
        raise ResourceConfigurationError(f"Resource '{key}' is not registered.") from exc


def _validate_model_fields(resource: ResourceConfig) -> list[Error]:
    issues: list[Error] = []
    model = resource.model()
    field_sets = {
        "IMPORT_FIELDS": resource.import_fields,
        "EXPORT_FIELDS": resource.export_fields,
        "IMPORT_ID_FIELDS": resource.import_id_fields,
        "SEARCH_FIELDS": resource.search_fields,
        "ORDERING_FIELDS": resource.ordering_fields,
        "FILTER_FIELDS": resource.filter_fields,
    }
    for setting_key, field_names in field_sets.items():
        for field_name in field_names:
            if field_name in SENSITIVE_FIELD_NAMES:
                issues.append(
                    Error(
                        f"Resource '{resource.key}' exposes prohibited field '{field_name}'.",
                        id="fk_import_export.E011",
                    )
                )
                continue
            try:
                field = model._meta.get_field(field_name)
            except FieldDoesNotExist:
                issues.append(
                    Error(
                        f"Resource '{resource.key}' {setting_key} references missing field "
                        f"'{field_name}' on {resource.model_label}.",
                        id="fk_import_export.E012",
                    )
                )
                continue
            if not isinstance(field, Field):
                issues.append(
                    Error(
                        f"Resource '{resource.key}' {setting_key} must reference a concrete model "
                        f"field, not reverse relation '{field_name}'.",
                        id="fk_import_export.E017",
                    )
                )
                continue
            if field.primary_key or not field.editable and setting_key == "IMPORT_FIELDS":
                issues.append(
                    Error(
                        f"Resource '{resource.key}' cannot import into '{field_name}'.",
                        id="fk_import_export.E013",
                    )
                )

    for relation_name, relation in resource.relations.items():
        try:
            field = model._meta.get_field(relation_name)
        except FieldDoesNotExist:
            issues.append(
                Error(
                    f"Resource '{resource.key}' relation '{relation_name}' does not exist.",
                    id="fk_import_export.E014",
                )
            )
            continue
        if not field.is_relation or field.auto_created:
            issues.append(
                Error(
                    f"Resource '{resource.key}' relation "
                    f"'{relation_name}' must be a forward relation.",
                    id="fk_import_export.E015",
                )
            )
            continue
        related_model = field.related_model
        if related_model is None:
            issues.append(
                Error(
                    f"Resource '{resource.key}' relation '{relation_name}' has no related model.",
                    id="fk_import_export.E016",
                )
            )
            continue
        try:
            related_model._meta.get_field(relation.lookup_field)
        except FieldDoesNotExist:
            issues.append(
                Error(
                    f"Resource '{resource.key}' relation '{relation_name}' lookup field "
                    f"'{relation.lookup_field}' does not exist.",
                    id="fk_import_export.E016",
                )
            )
    return issues


def configuration_issues() -> list[Error]:
    """Return Django system-check errors for unsafe resource declarations."""

    try:
        get_runtime_settings()
        resources = get_resources()
    except ResourceConfigurationError as exc:
        return [Error(str(exc), id="fk_import_export.E001")]

    issues: list[Error] = []
    if not apps.ready:
        return issues
    for resource in resources.values():
        try:
            issues.extend(_validate_model_fields(resource))
        except ResourceConfigurationError as exc:
            issues.append(Error(str(exc), id="fk_import_export.E010"))
        except LookupError:
            issues.append(
                Error(
                    f"Resource '{resource.key}' references unknown model '{resource.model_label}'.",
                    id="fk_import_export.E010",
                )
            )
    return issues
