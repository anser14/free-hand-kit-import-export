# Generated manually for the package's initial durable job-audit model.

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="ImportJob",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("resource_key", models.CharField(max_length=80)),
                ("source_file", models.FileField(blank=True, upload_to="fk-import-export/%Y/%m/%d/")),
                ("source_name", models.CharField(max_length=255)),
                ("source_sha256", models.CharField(max_length=64)),
                ("source_size", models.PositiveBigIntegerField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("uploaded", "Uploaded"),
                            ("previewed", "Previewed"),
                            ("committed", "Committed"),
                            ("failed", "Failed"),
                        ],
                        default="uploaded",
                        max_length=16,
                    ),
                ),
                ("summary", models.JSONField(blank=True, default=dict)),
                ("errors", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "submitted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="fk_import_export_jobs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.AddIndex(
            model_name="importjob",
            index=models.Index(fields=["resource_key", "status"], name="fk_import__resourc_4a8098_idx"),
        ),
        migrations.AddIndex(
            model_name="importjob",
            index=models.Index(fields=["created_at"], name="fk_import__created_9b04df_idx"),
        ),
    ]
