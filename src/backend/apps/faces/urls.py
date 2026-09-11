from django.urls import path
from .views import ClusterAvatarView, ClusterNameView

urlpatterns = [
    path(
        "clusters/<uuid:cluster_id>/name/",
        ClusterNameView.as_view(),
        name="cluster_name",
    ),
    path(
        "clusters/<uuid:cluster_id>/avatar/",
        ClusterAvatarView.as_view(),
        name="cluster_avatar",
    ),
]
