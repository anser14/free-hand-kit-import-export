"""Stable mount point for Freehand Kit Import Export APIs and OpenAPI routes."""

from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from .api.views import (
    ImportConfirmView,
    ImportJobDetailView,
    ImportPreviewView,
    ResourceListView,
    ResourceSchemaView,
    ResourceTemplateView,
)

app_name = "fk_import_export"

urlpatterns = [
    path("resources/", ResourceListView.as_view(), name="resource-list"),
    path("resources/<str:resource_key>/", ResourceSchemaView.as_view(), name="resource-schema"),
    path(
        "resources/<str:resource_key>/template/",
        ResourceTemplateView.as_view(),
        name="resource-template",
    ),
    path(
        "resources/<str:resource_key>/imports/preview/",
        ImportPreviewView.as_view(),
        name="import-preview",
    ),
    path("import-jobs/<uuid:job_id>/", ImportJobDetailView.as_view(), name="import-job-detail"),
    path(
        "import-jobs/<uuid:job_id>/confirm/",
        ImportConfirmView.as_view(),
        name="import-confirm",
    ),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "docs/",
        SpectacularSwaggerView.as_view(url_name="fk_import_export:schema"),
        name="swagger-ui",
    ),
]
