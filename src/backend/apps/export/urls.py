from django.urls import path
from .views import ExportClusterZipView, ExportClusterDriveView

urlpatterns = [
    path(
        "clusters/<uuid:cluster_id>/zip/",
        ExportClusterZipView.as_view(),
        name="export_cluster_zip",
    ),
    path(
        "clusters/<uuid:cluster_id>/drive/",
        ExportClusterDriveView.as_view(),
        name="export_cluster_drive",
    ),
]
