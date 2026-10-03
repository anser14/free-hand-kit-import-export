"""Audit record foundation for the two-phase import workflow."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class ImportJob(models.Model):
    """Stored source metadata and lifecycle audit for one approved CSV import."""

    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        PREVIEWED = "previewed", "Previewed"
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        COMMITTED = "committed", "Committed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resource_key = models.CharField(max_length=80)
    source_file = models.FileField(upload_to="fk-import-export/%Y/%m/%d/", blank=True)
    source_name = models.CharField(max_length=255)
    source_sha256 = models.CharField(max_length=64)
    source_size = models.PositiveBigIntegerField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.UPLOADED)
    summary = models.JSONField(default=dict, blank=True)
    errors = models.JSONField(default=list, blank=True)
    progress_total = models.PositiveIntegerField(default=0)
    progress_completed = models.PositiveIntegerField(default=0)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="fk_import_export_jobs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    previewed_at = models.DateTimeField(null=True, blank=True)
    queued_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    committed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    source_deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("resource_key", "status")),
            models.Index(fields=("created_at",)),
            models.Index(fields=("status", "created_at"), name="fk_import_e_status_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.resource_key}: {self.id} ({self.status})"
