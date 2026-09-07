from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("authentication.urls")),
    path("api/v1/google/", include("google_integration.urls")),
    path("api/v1/albums/", include("albums.urls")),
    path("api/v1/faces/", include("faces.urls")),
    path("api/v1/export/", include("export.urls")),
]
