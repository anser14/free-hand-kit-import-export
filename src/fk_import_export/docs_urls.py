"""Optional central OpenAPI routes for a host's shared ``/api/`` prefix.

Mount this module only when the host does not already expose a central schema and
Swagger UI (for example, through ``fk_auth.urls``). drf-spectacular generates one
schema across the host URL configuration, so that UI documents the import/export
endpoints as well as every other installed DRF package.
"""

from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

app_name = "fk_import_export_docs"

urlpatterns = [
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "docs/",
        SpectacularSwaggerView.as_view(url_name="fk_import_export_docs:schema"),
        name="swagger-ui",
    ),
]
