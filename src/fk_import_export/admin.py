"""Restricted Django Admin observability for import job records."""

from django.contrib import admin

from .models import ImportJob


@admin.register(ImportJob)
class ImportJobAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("id", "resource_key", "status", "submitted_by", "created_at")
    list_filter = ("resource_key", "status")
    search_fields = ("id", "source_name", "source_sha256")
    readonly_fields = (
        "id",
        "resource_key",
        "source_file",
        "source_name",
        "source_sha256",
        "source_size",
        "status",
        "summary",
        "errors",
        "submitted_by",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):  # type: ignore[no-untyped-def]
        return False
