"""Minimal Django settings for Freehand Kit Import Export tests."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SECRET_KEY = "test-only-secret-key"
DEBUG = False
USE_TZ = True
ROOT_URLCONF = "fk_import_export.urls"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "rest_framework",
    "drf_spectacular",
    "tests.test_app.apps.ImportExportTestAppConfig",
    "fk_import_export",
]
MIDDLEWARE: list[str] = []
ALLOWED_HOSTS = ["testserver"]
MEDIA_ROOT = BASE_DIR / ".test-media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
REST_FRAMEWORK = {"DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema"}
FREEHAND_KIT_IMPORT_EXPORT = {
    "RESOURCES": {
        "products": {
            "MODEL": "fk_import_export_test_app.Product",
            "IMPORT_FIELDS": ("sku", "name", "price", "category"),
            "EXPORT_FIELDS": ("sku", "name", "price", "category"),
            "IMPORT_ID_FIELDS": ("sku",),
            "SEARCH_FIELDS": ("sku", "name"),
            "ORDERING_FIELDS": ("sku", "name", "price"),
            "FILTER_FIELDS": ("category",),
            "RELATIONS": {"category": {"LOOKUP_FIELD": "slug"}},
        },
    },
}
