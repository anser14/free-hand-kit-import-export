"""Record when a retained audit job has had its private CSV source removed."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("fk_import_export", "0004_importjob_queue_lifecycle")]

    operations = [
        migrations.AddField(
            model_name="importjob",
            name="source_deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
