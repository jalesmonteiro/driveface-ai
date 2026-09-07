from django.urls import path
from .views import (
    ProcessAlbumView,
    JobStatusView,
    AlbumDetailView,
    AlbumShareManageView,
    SharedAlbumDetailView,
)

urlpatterns = [
    path("process/", ProcessAlbumView.as_view(), name="album_process"),
    path("<uuid:album_id>/", AlbumDetailView.as_view(), name="album_detail"),
    path(
        "<uuid:album_id>/shares/",
        AlbumShareManageView.as_view(),
        name="album_share_manage",
    ),
    path(
        "shared/<str:share_token>/",
        SharedAlbumDetailView.as_view(),
        name="album_shared_detail",
    ),
    path(
        "jobs/<uuid:job_id>/status/",
        JobStatusView.as_view(),
        name="job_status",
    ),
]
