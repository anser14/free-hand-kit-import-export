"""Safe, Swagger-documented discovery endpoints for configured resources."""

from __future__ import annotations

import csv
from uuid import UUID

from django.contrib.auth.models import AbstractBaseUser
from django.http import Http404, HttpResponse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from fk_import_export.conf import (
    ResourceConfig,
    ResourceConfigurationError,
    get_resource,
    get_resources,
    get_runtime_settings,
)
from fk_import_export.services import (
    ImportJobNotFound,
    ImportJobStateError,
    ImportPayloadError,
    confirm_import,
    get_owned_job,
    preview_import,
)

from .serializers import (
    ImportJobSerializer,
    ImportPreviewSerializer,
    ResourceSchemaSerializer,
    ResourceSerializer,
)


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

    @staticmethod
    def get_submitting_user(request) -> AbstractBaseUser:  # type: ignore[no-untyped-def]
        user = request.user
        if not isinstance(user, AbstractBaseUser):
            raise Http404("Resource not found.")
        return user

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
        payload["operations"] = ["template", "preview_import"]
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


@extend_schema(
    tags=["Freehand Kit Import Export"],
    request=ImportPreviewSerializer,
    responses={
        201: ImportJobSerializer,
        400: OpenApiResponse(description="Invalid CSV source or resource contract."),
        404: OpenApiResponse(description="Unknown or unavailable resource."),
    },
)
class ImportPreviewView(ResourceAccessAPIView):
    """Store and dry-run an approved CSV without changing host model rows."""

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, resource_key: str):  # type: ignore[no-untyped-def]
        resource = self.get_resource(resource_key)
        serializer = ImportPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            job = preview_import(
                resource=resource,
                upload=serializer.validated_data["file"],
                submitted_by=self.get_submitting_user(request),
                limits=get_runtime_settings(),
            )
        except ImportPayloadError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ImportJobSerializer(job).data, status=status.HTTP_201_CREATED)


class ImportJobAccessAPIView(ResourceAccessAPIView):
    """Owner-scoped job lookup shared by detail and confirm endpoints."""

    def get_job(self, request, job_id: UUID):  # type: ignore[no-untyped-def]
        try:
            return get_owned_job(job_id=job_id, submitted_by=self.get_submitting_user(request))
        except ImportJobNotFound as exc:
            raise Http404("Import job not found.") from exc


@extend_schema(
    tags=["Freehand Kit Import Export"],
    responses={404: OpenApiResponse(description="Unknown or unavailable import job.")},
)
class ImportJobDetailView(ImportJobAccessAPIView):
    """Return a sanitized import job visible only to its submitting user."""

    def get(self, request, job_id: UUID):  # type: ignore[no-untyped-def]
        return Response(ImportJobSerializer(self.get_job(request, job_id)).data)


@extend_schema(
    tags=["Freehand Kit Import Export"],
    request=None,
    responses={
        200: ImportJobSerializer,
        404: OpenApiResponse(description="Unknown or unavailable import job."),
        409: OpenApiResponse(description="Job cannot be confirmed in its current state."),
    },
)
class ImportConfirmView(ImportJobAccessAPIView):
    """Revalidate and atomically commit a previously successful preview."""

    def post(self, request, job_id: UUID):  # type: ignore[no-untyped-def]
        try:
            result = confirm_import(
                job_id=job_id,
                submitted_by=self.get_submitting_user(request),
                limits=get_runtime_settings(),
            )
        except ImportJobNotFound as exc:
            raise Http404("Import job not found.") from exc
        except ImportJobStateError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        response_status = status.HTTP_200_OK if result.committed else status.HTTP_409_CONFLICT
        return Response(ImportJobSerializer(result.job).data, status=response_status)
