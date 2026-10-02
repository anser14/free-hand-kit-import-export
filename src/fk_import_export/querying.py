"""Safe, configuration-bound querying and serialization for resource read APIs."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from math import ceil

from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db.models import Field, Model, Q, QuerySet
from django.http import QueryDict

from .conf import ImportExportSettings, ResourceConfig
from .registry import resource_class


class ResourceQueryError(ValueError):
    """Raised for an invalid, unapproved, or malformed resource query parameter."""


class ExportLimitError(ValueError):
    """Raised when a caller requests more records than the configured export bound."""


@dataclass(frozen=True)
class RecordPage:
    """One page of safe, resource-defined record representations."""

    count: int
    page: int
    page_size: int
    total_pages: int
    results: list[dict[str, object]]


@dataclass(frozen=True)
class CSVExport:
    """Bounded CSV export data ready for a transport adapter."""

    headers: list[str]
    rows: list[list[str]]


def _model_field(resource: ResourceConfig, field_name: str) -> Field[object, object]:
    try:
        field = resource.model()._meta.get_field(field_name)
    except FieldDoesNotExist as exc:
        raise ResourceQueryError(f"Configured field '{field_name}' is unavailable.") from exc
    if not isinstance(field, Field):
        raise ResourceQueryError(f"Configured field '{field_name}' is not a concrete model field.")
    return field


def _lookup(resource: ResourceConfig, field_name: str) -> str:
    field = _model_field(resource, field_name)
    if not field.is_relation:
        return field_name
    relation = resource.relations.get(field_name)
    if relation is None:
        raise ResourceQueryError(
            f"Relation '{field_name}' requires an explicit RELATIONS lookup configuration."
        )
    return f"{field_name}__{relation.lookup_field}"


def _positive_parameter(query_params: QueryDict, name: str, default: int, maximum: int) -> int:
    raw_value = query_params.get(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ResourceQueryError(f"'{name}' must be a positive integer.") from exc
    if value < 1 or value > maximum:
        raise ResourceQueryError(f"'{name}' must be between 1 and {maximum}.")
    return value


def _validate_query_parameters(query_params: QueryDict) -> None:
    permitted = {"search", "ordering", "page", "page_size"}
    for key, values in query_params.lists():
        if key not in permitted and not key.startswith("filter."):
            raise ResourceQueryError(f"Unsupported query parameter '{key}'.")
        if len(values) != 1:
            raise ResourceQueryError(f"Query parameter '{key}' may only be supplied once.")


def _optimized_queryset(resource: ResourceConfig) -> QuerySet[Model]:
    queryset = resource.model()._default_manager.all()
    select_related_fields: list[str] = []
    prefetch_related_fields: list[str] = []
    for relation_name in resource.relations:
        field = _model_field(resource, relation_name)
        if field.many_to_many:
            prefetch_related_fields.append(relation_name)
        else:
            select_related_fields.append(relation_name)
    if select_related_fields:
        queryset = queryset.select_related(*select_related_fields)
    if prefetch_related_fields:
        queryset = queryset.prefetch_related(*prefetch_related_fields)
    return queryset


def _filtered_queryset(resource: ResourceConfig, query_params: QueryDict) -> QuerySet[Model]:
    _validate_query_parameters(query_params)
    queryset = _optimized_queryset(resource)
    requires_distinct = False

    for key, values in query_params.lists():
        if not key.startswith("filter."):
            continue
        field_name = key.removeprefix("filter.")
        if field_name not in resource.filter_fields:
            raise ResourceQueryError(
                f"Filtering by '{field_name}' is not allowed for this resource."
            )
        lookup = _lookup(resource, field_name)
        field = _model_field(resource, field_name)
        try:
            queryset = queryset.filter(**{lookup: values[0]})
        except (TypeError, ValidationError) as exc:
            raise ResourceQueryError(f"Filter value for '{field_name}' is invalid.") from exc
        requires_distinct = requires_distinct or bool(field.many_to_many)

    search_value = query_params.get("search")
    if search_value:
        if not resource.search_fields:
            raise ResourceQueryError("Search is not configured for this resource.")
        query = Q()
        for field_name in resource.search_fields:
            query |= Q(**{f"{_lookup(resource, field_name)}__icontains": search_value})
            requires_distinct = requires_distinct or bool(
                _model_field(resource, field_name).many_to_many
            )
        queryset = queryset.filter(query)

    if requires_distinct:
        queryset = queryset.distinct()
    return queryset


def _ordered_queryset(resource: ResourceConfig, query_params: QueryDict) -> QuerySet[Model]:
    queryset = _filtered_queryset(resource, query_params)
    raw_ordering = query_params.get("ordering")
    if not raw_ordering:
        return queryset.order_by(resource.model()._meta.pk.name)

    ordering: list[str] = []
    for raw_field_name in raw_ordering.split(","):
        field_name = raw_field_name.strip()
        descending = field_name.startswith("-")
        configured_name = field_name.removeprefix("-")
        if not configured_name or configured_name not in resource.ordering_fields:
            raise ResourceQueryError(
                f"Ordering by '{field_name}' is not allowed for this resource."
            )
        field = _model_field(resource, configured_name)
        if field.many_to_many:
            raise ResourceQueryError("Ordering by many-to-many fields is not supported.")
        lookup = _lookup(resource, configured_name)
        ordering.append(f"-{lookup}" if descending else lookup)

    primary_key = resource.model()._meta.pk.name
    if primary_key not in {term.removeprefix("-") for term in ordering}:
        ordering.append(primary_key)
    return queryset.order_by(*ordering)


def _export_rows(
    resource: ResourceConfig, records: Iterable[Model]
) -> tuple[list[str], list[list[str]]]:
    if not resource.export_fields:
        raise ResourceQueryError(f"Resource '{resource.key}' does not expose export fields.")
    engine = resource_class(resource)()
    headers = [str(header) for header in engine.get_export_headers(resource.export_fields)]
    rows: list[list[str]] = []
    for record in records:
        values = engine.export_resource(record, selected_fields=resource.export_fields)
        if len(values) != len(headers):
            raise ResourceQueryError("Configured export resource returned an invalid row shape.")
        rows.append(values)
    return headers, rows


def record_page(
    resource: ResourceConfig,
    query_params: QueryDict,
    limits: ImportExportSettings,
) -> RecordPage:
    """Apply approved query controls and return one deterministic record page."""

    page = _positive_parameter(query_params, "page", default=1, maximum=2_147_483_647)
    page_size = _positive_parameter(
        query_params,
        "page_size",
        default=limits.page_size,
        maximum=limits.max_page_size,
    )
    queryset = _ordered_queryset(resource, query_params)
    count = queryset.count()
    records = list(queryset[(page - 1) * page_size : page * page_size])
    headers, rows = _export_rows(resource, records)
    return RecordPage(
        count=count,
        page=page,
        page_size=page_size,
        total_pages=ceil(count / page_size) if count else 0,
        results=[dict(zip(headers, row, strict=True)) for row in rows],
    )


def _spreadsheet_safe_cell(value: object) -> str:
    cell = "" if value is None else str(value)
    if cell.lstrip().startswith(("=", "+", "-", "@")):
        return f"'{cell}"
    return cell


def csv_export(
    resource: ResourceConfig,
    query_params: QueryDict,
    limits: ImportExportSettings,
) -> CSVExport:
    """Apply approved query controls and return a spreadsheet-safe, bounded CSV export."""

    if "page" in query_params or "page_size" in query_params:
        raise ResourceQueryError("Pagination parameters are not supported for CSV export.")
    queryset = _ordered_queryset(resource, query_params)
    records = list(queryset[: limits.max_export_rows + 1])
    if len(records) > limits.max_export_rows:
        raise ExportLimitError(
            f"Export exceeds the configured limit of {limits.max_export_rows} records."
        )
    headers, rows = _export_rows(resource, records)
    return CSVExport(
        headers=headers,
        rows=[[_spreadsheet_safe_cell(value) for value in row] for row in rows],
    )
