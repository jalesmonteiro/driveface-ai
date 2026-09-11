from django.contrib import admin
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import include, path
from albums.views import PhotoStreamView
from faces.views import ClusterAvatarView


def index_view(request):
    accept = request.headers.get("Accept", "")
    if "application/json" in accept and "text/html" not in accept:
        return api_root_view(request)
    return dashboard_view(request)


def dashboard_view(request):
    return render(request, "dashboard.html", {"active_page": "dashboard"})


def process_view(request):
    return render(request, "process.html", {"active_page": "process"})


def albums_view(request):
    return render(request, "albums.html", {"active_page": "albums"})


def person_gallery_view(request, album_id, cluster_id):
    return render(
        request,
        "person_gallery.html",
        {
            "active_page": "person",
            "album_id": str(album_id),
            "cluster_id": str(cluster_id),
        },
    )


def shares_view(request):
    return render(request, "shares.html", {"active_page": "shares"})


def api_root_view(request):
    return JsonResponse(
        {
            "name": "DriveFace AI API",
            "version": "v1",
            "status": "online",
            "endpoints": {
                "admin": "/admin/",
                "auth": "/api/v1/auth/",
                "google": "/api/v1/google/",
                "albums": "/api/v1/albums/",
                "faces": "/api/v1/faces/",
                "export": "/api/v1/export/",
            },
        }
    )


urlpatterns = [
    # Páginas Web Dedicadas (Multipage Interface)
    path("", index_view, name="index"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("process/", process_view, name="process"),
    path("albums/", albums_view, name="albums"),
    path(
        "albums/<uuid:album_id>/person/<uuid:cluster_id>/",
        person_gallery_view,
        name="person_gallery",
    ),
    path("shares/", shares_view, name="shares"),

    # APIs RESTful
    path("api/", api_root_view, name="api-root"),
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("authentication.urls")),
    path("api/v1/google/", include("google_integration.urls")),
    path("api/v1/albums/", include("albums.urls")),
    path("api/v1/faces/", include("faces.urls")),
    path("api/v1/export/", include("export.urls")),
    path("api/v1/photos/<uuid:photo_id>/stream/", PhotoStreamView.as_view(), name="photo_stream_root"),
    path("api/v1/clusters/<uuid:cluster_id>/avatar/", ClusterAvatarView.as_view(), name="cluster_avatar_root"),
]

