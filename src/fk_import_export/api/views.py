"""Safe, Swagger-documented discovery endpoints for configured resources."""

from __future__ import annotations

import csv

from django.http import Http404, HttpResponse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from fk_import_export.conf import (
    ResourceConfig,
    ResourceConfigurationError,
    get_resource,
    get_resources,
)

from .serializers import ResourceSchemaSerializer, ResourceSerializer


def _resource_payload(resource: ResourceConfig) -> dict[str, object]:
    return {
        "key": resource.key,
        "model": resource.model_label,
        "import_fields": list(resource.import_fields),
        "export_fields": list(resource.export_fields),
        "import_id_fields": list(resource.import_id_fields),
        "search_fields": list(resource.search_fields),
        "ordering_fields": list(resource.ordering_fields),
        "filter_fields": list(resource.filter_fields),
    }


class ResourceAccessAPIView(APIView):
    """Use staff-only access until per-resource policies are implemented."""

    permission_classes = [permissions.IsAdminUser]

    def get_resource(self, resource_key: str) -> ResourceConfig:
        try:
            return get_resource(resource_key)
        except ResourceConfigurationError as exc:
            raise Http404("Resource not found.") from exc


@extend_schema(
    tags=["Freehand Kit Import Export"],
    responses={200: ResourceSerializer(many=True)},
)
class ResourceListView(ResourceAccessAPIView):
    """List only developer-registered resources; never enumerate installed models."""

    def get(self, request):  # type: ignore[no-untyped-def]
        return Response([_resource_payload(resource) for resource in get_resources().values()])


@extend_schema(
    tags=["Freehand Kit Import Export"],
    responses={
        200: ResourceSchemaSerializer,
        404: OpenApiResponse(description="Unknown or unavailable resource."),
    },
)
class ResourceSchemaView(ResourceAccessAPIView):
    """Expose the configured contract without leaking unrelated model fields."""

    def get(self, request, resource_key: str):  # type: ignore[no-untyped-def]
        resource = self.get_resource(resource_key)
        payload = _resource_payload(resource)
        payload["relationships"] = {
            name: {"lookup_field": relation.lookup_field, "separator": relation.separator}
            for name, relation in resource.relations.items()
        }
        payload["operations"] = ["template"]
        return Response(payload)


@extend_schema(
    tags=["Freehand Kit Import Export"],
    responses={
        200: OpenApiResponse(description="CSV header template for the approved import resource."),
        404: OpenApiResponse(description="Unknown or unavailable resource."),
    },
)
class ResourceTemplateView(ResourceAccessAPIView):
    """Return an import template with only configured and importable headers."""

    def get(self, request, resource_key: str):  # type: ignore[no-untyped-def]
        resource = self.get_resource(resource_key)
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="{resource.key}-import-template.csv"'
        )
        writer = csv.writer(response, lineterminator="\n")
        writer.writerow(resource.import_fields)
        return response
