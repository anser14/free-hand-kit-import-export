# Generated manually for the package test application's many-to-many coverage.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("fk_import_export_test_app", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="Tag",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("slug", models.SlugField(unique=True)),
                ("name", models.CharField(max_length=100)),
            ],
        ),
        migrations.AddField(
            model_name="product",
            name="tags",
            field=models.ManyToManyField(blank=True, to="fk_import_export_test_app.tag"),
        ),
    ]
