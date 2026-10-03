"""A representative host routing arrangement with one shared API documentation UI."""

from django.urls import include, path

urlpatterns = [
    path("api/data/", include("fk_import_export.urls")),
    path("api/", include("fk_import_export.docs_urls")),
]
