"""Environment-driven settings for the Dockerized custom-user demonstration."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-demo-secret-change-me")
DEBUG = env_bool("DJANGO_DEBUG")
ALLOWED_HOSTS = [host for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost").split(",") if host]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "accounts",
    "inventory",
    "fk_import_export",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"

if os.getenv("POSTGRES_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "freehand_demo"),
            "USER": os.getenv("POSTGRES_USER", "freehand_demo"),
            "PASSWORD": os.environ["POSTGRES_PASSWORD"],
            "HOST": os.environ["POSTGRES_HOST"],
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "demo.sqlite3",
        }
    }

AUTH_USER_MODEL = "accounts.User"
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
MEDIA_ROOT = BASE_DIR / "private-media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
REST_FRAMEWORK = {"DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema"}

FREEHAND_KIT_IMPORT_EXPORT = {
    "MAX_UPLOAD_BYTES": 5 * 1024 * 1024,
    "MAX_ROWS": 10_000,
    "MAX_EXPORT_ROWS": 10_000,
    "SOURCE_RETENTION_DAYS": 7,
    "JOB_RETENTION_DAYS": 90,
    "RESOURCES": {
        "products": {
            "MODEL": "inventory.Product",
            "IMPORT_FIELDS": ("sku", "name", "price", "category", "tags"),
            "EXPORT_FIELDS": ("sku", "name", "price", "category", "tags"),
            "IMPORT_ID_FIELDS": ("sku",),
            "SEARCH_FIELDS": ("sku", "name"),
            "ORDERING_FIELDS": ("sku", "name", "price"),
            "FILTER_FIELDS": ("category", "tags"),
            "RELATIONS": {
                "category": {"LOOKUP_FIELD": "slug"},
                "tags": {"LOOKUP_FIELD": "slug", "SEPARATOR": "|"},
            },
            "PERMISSIONS": {
                "READ": "inventory.view_product",
                "EXPORT": "inventory.view_product",
                "IMPORT": "inventory.change_product",
            },
            "SCOPE": {"MODEL_FIELD": "owner", "USER_ATTRIBUTE": "$self"},
        }
    },
}
