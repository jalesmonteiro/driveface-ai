from django.urls import path
from .views import (
    AlbumListView,
    ProcessAlbumView,
    JobStatusView,
    AlbumDetailView,
    AlbumClustersListView,
    ClusterPhotosListView,
    PhotoStreamView,
    AlbumShareManageView,
    SharedAlbumDetailView,
    AlbumReprocessView,
)

urlpatterns = [
    path("", AlbumListView.as_view(), name="album_list"),
    path("process/", ProcessAlbumView.as_view(), name="album_process"),
    path("<uuid:album_id>/", AlbumDetailView.as_view(), name="album_detail"),
    path("<uuid:album_id>/reprocess/", AlbumReprocessView.as_view(), name="album_reprocess"),
    path("<uuid:album_id>/clusters/", AlbumClustersListView.as_view(), name="album_clusters"),
    path(
        "<uuid:album_id>/clusters/<uuid:cluster_id>/photos/",
        ClusterPhotosListView.as_view(),
        name="cluster_photos",
    ),
    path(
        "photos/<uuid:photo_id>/stream/",
        PhotoStreamView.as_view(),
        name="photo_stream",
    ),
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
