# Align initial hand-written index names with Django's generated model-state names.

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("fk_import_export", "0002_importjob_lifecycle_timestamps")]

    operations = [
        migrations.RenameIndex(
            model_name="importjob",
            new_name="fk_import_e_resourc_b89586_idx",
            old_name="fk_import__resourc_4a8098_idx",
        ),
        migrations.RenameIndex(
            model_name="importjob",
            new_name="fk_import_e_created_9f7b64_idx",
            old_name="fk_import__created_9b04df_idx",
        ),
    ]
