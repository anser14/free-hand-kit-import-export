"""OpenAPI serializers for the resource-discovery foundation endpoints."""

from __future__ import annotations

from rest_framework import serializers

from fk_import_export.models import ImportJob


class ResourceSerializer(serializers.Serializer[dict[str, object]]):
    key = serializers.CharField()
    model = serializers.CharField()
    import_fields = serializers.ListField(child=serializers.CharField())
    export_fields = serializers.ListField(child=serializers.CharField())
    import_id_fields = serializers.ListField(child=serializers.CharField())
    search_fields = serializers.ListField(child=serializers.CharField())
    ordering_fields = serializers.ListField(child=serializers.CharField())
    filter_fields = serializers.ListField(child=serializers.CharField())


class ResourceSchemaSerializer(ResourceSerializer):
    relationships = serializers.DictField(child=serializers.DictField())
    operations = serializers.ListField(child=serializers.CharField())


class ImportPreviewSerializer(serializers.Serializer[dict[str, object]]):
    """Multipart request body for a CSV preview."""

    file = serializers.FileField(allow_empty_file=False, write_only=True)


class ImportJobSerializer(serializers.ModelSerializer[ImportJob]):
    """Sanitized, owner-visible import job state."""

    confirmation_eligible = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()

    class Meta:
        model = ImportJob
        fields = (
            "id",
            "resource_key",
            "source_name",
            "source_size",
            "status",
            "summary",
            "errors",
            "progress",
            "attempt_count",
            "confirmation_eligible",
            "created_at",
            "updated_at",
            "previewed_at",
            "queued_at",
            "started_at",
            "committed_at",
            "failed_at",
        )
        read_only_fields = fields

    def get_confirmation_eligible(self, job: ImportJob) -> bool:
        return job.status == ImportJob.Status.PREVIEWED

    def get_progress(self, job: ImportJob) -> dict[str, int]:
        total = job.progress_total
        completed = min(job.progress_completed, total)
        percent = 0 if total == 0 else (completed * 100) // total
        return {"total_rows": total, "completed_rows": completed, "percent": percent}


class ImportJobPageSerializer(serializers.Serializer[dict[str, object]]):
    """OpenAPI contract for the authenticated caller's paginated import history."""

    count = serializers.IntegerField(min_value=0)
    page = serializers.IntegerField(min_value=1)
    page_size = serializers.IntegerField(min_value=1)
    total_pages = serializers.IntegerField(min_value=0)
    results = ImportJobSerializer(many=True)


class RecordPageSerializer(serializers.Serializer[dict[str, object]]):
    """OpenAPI contract for a page of dynamically configured export records."""

    count = serializers.IntegerField(min_value=0)
    page = serializers.IntegerField(min_value=1)
    page_size = serializers.IntegerField(min_value=1)
    total_pages = serializers.IntegerField(min_value=0)
    results = serializers.ListField(child=serializers.DictField())
