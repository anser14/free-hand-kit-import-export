"""Add durable queue state and observable progress to import jobs."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("fk_import_export", "0003_rename_importjob_indexes")]

    operations = [
        migrations.AlterField(
            model_name="importjob",
            name="status",
            field=models.CharField(
                choices=[
                    ("uploaded", "Uploaded"),
                    ("previewed", "Previewed"),
                    ("queued", "Queued"),
                    ("processing", "Processing"),
                    ("committed", "Committed"),
                    ("failed", "Failed"),
                ],
                default="uploaded",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="importjob",
            name="attempt_count",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="importjob",
            name="progress_completed",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="importjob",
            name="progress_total",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="importjob",
            name="queued_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="importjob",
            name="started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="importjob",
            index=models.Index(
                fields=["status", "created_at"],
                name="fk_import_e_status_created_idx",
            ),
        ),
    ]
