# Generated manually for lifecycle audit timestamps added before the first stable release.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("fk_import_export", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="importjob",
            name="committed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="importjob",
            name="failed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="importjob",
            name="previewed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
