"""Safe, Swagger-documented discovery endpoints for configured resources."""

from __future__ import annotations

import csv
from uuid import UUID

from django.contrib.auth.models import AbstractBaseUser
from django.http import Http404, HttpResponse
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, OpenApiTypes, extend_schema
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
from fk_import_export.querying import (
    ExportLimitError,
    ResourceQueryError,
    csv_export,
    record_page,
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
    RecordPageSerializer,
    ResourceSchemaSerializer,
    ResourceSerializer,
)

RESOURCE_QUERY_PARAMETERS = [
    OpenApiParameter(
        name="search",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description="Search across the resource's configured SEARCH_FIELDS.",
    ),
    OpenApiParameter(
        name="ordering",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description=(
            "Comma-separated configured ORDERING_FIELDS; prefix a field with - for descending."
        ),
    ),
    OpenApiParameter(
        name="filter.<field>",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description="Exact-match filter for a configured FILTER_FIELDS entry.",
    ),
]


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
        payload["operations"] = ["template", "preview_import", "records", "export"]
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
    parameters=[
        *RESOURCE_QUERY_PARAMETERS,
        OpenApiParameter(
            name="page",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="One-based page number.",
        ),
        OpenApiParameter(
            name="page_size",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Records per page, bounded by MAX_PAGE_SIZE.",
        ),
    ],
    responses={
        200: RecordPageSerializer,
        400: OpenApiResponse(description="Invalid or disallowed query parameter."),
        404: OpenApiResponse(description="Unknown or unavailable resource."),
    },
)
class ResourceRecordsView(ResourceAccessAPIView):
    """Return a page of safe record representations for an approved resource."""

    def get(self, request, resource_key: str):  # type: ignore[no-untyped-def]
        try:
            result = record_page(
                self.get_resource(resource_key),
                request.query_params,
                get_runtime_settings(),
            )
        except ResourceQueryError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "count": result.count,
                "page": result.page,
                "page_size": result.page_size,
                "total_pages": result.total_pages,
                "results": result.results,
            }
        )


@extend_schema(
    tags=["Freehand Kit Import Export"],
    parameters=RESOURCE_QUERY_PARAMETERS,
    responses={
        200: OpenApiResponse(description="Spreadsheet-safe CSV export."),
        400: OpenApiResponse(description="Invalid query parameter or export limit exceeded."),
        404: OpenApiResponse(description="Unknown or unavailable resource."),
    },
)
class ResourceExportView(ResourceAccessAPIView):
    """Return a bounded CSV export using the same safe query controls as records."""

    def get(self, request, resource_key: str):  # type: ignore[no-untyped-def]
        resource = self.get_resource(resource_key)
        try:
            export = csv_export(resource, request.query_params, get_runtime_settings())
        except (ExportLimitError, ResourceQueryError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{resource.key}-export.csv"'
        writer = csv.writer(response, lineterminator="\n")
        writer.writerow(export.headers)
        writer.writerows(export.rows)
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


def _safe_error_report_cell(value: object) -> str:
    """Defend the CSV report even if an operator edited job JSON manually."""

    text = str(value)
    if text.lstrip().startswith(("=", "+", "-", "@")):
        return f"'{text}"
    return text


@extend_schema(
    tags=["Freehand Kit Import Export"],
    responses={
        200: OpenApiResponse(description="Sanitized CSV sample of this job's row-level errors."),
        404: OpenApiResponse(description="Unknown or unavailable import job."),
    },
)
class ImportJobErrorsView(ImportJobAccessAPIView):
    """Download only sanitized error metadata for an owner-visible import job."""

    def get(self, request, job_id: UUID):  # type: ignore[no-untyped-def]
        job = self.get_job(request, job_id)
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="import-job-{job.id}-errors.csv"'
        response["X-Freehand-Errors-Truncated"] = str(
            bool(job.summary.get("errors_truncated", False))
        ).lower()
        writer = csv.writer(response, lineterminator="\n")
        writer.writerow(("line", "code", "fields"))
        for raw_error in job.errors:
            if not isinstance(raw_error, dict):
                continue
            raw_line = raw_error.get("line")
            line = raw_line if isinstance(raw_line, int) and raw_line > 0 else ""
            raw_code = raw_error.get("code")
            code = (
                raw_code
                if isinstance(raw_code, str)
                and raw_code in {"validation_error", "processing_error", "dataset_error"}
                else "processing_error"
            )
            raw_fields = raw_error.get("fields", [])
            fields = (
                "|".join(
                    field for field in raw_fields if isinstance(field, str) and field.isidentifier()
                )
                if isinstance(raw_fields, list)
                else ""
            )
            writer.writerow(
                (
                    _safe_error_report_cell(line),
                    _safe_error_report_cell(code),
                    _safe_error_report_cell(fields),
                )
            )
        return response


@extend_schema(
    tags=["Freehand Kit Import Export"],
    request=None,
    responses={
        200: ImportJobSerializer,
        202: ImportJobSerializer,
        404: OpenApiResponse(description="Unknown or unavailable import job."),
        409: OpenApiResponse(description="Job cannot be confirmed in its current state."),
    },
)
class ImportConfirmView(ImportJobAccessAPIView):
    """Atomically enqueue a previously successful preview for worker execution."""

    def post(self, request, job_id: UUID):  # type: ignore[no-untyped-def]
        try:
            result = confirm_import(
                job_id=job_id,
                submitted_by=self.get_submitting_user(request),
            )
        except ImportJobNotFound as exc:
            raise Http404("Import job not found.") from exc
        except ImportJobStateError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        response_status = (
            status.HTTP_200_OK
            if result.job.status == result.job.Status.COMMITTED
            else status.HTTP_202_ACCEPTED
        )
        return Response(ImportJobSerializer(result.job).data, status=response_status)
