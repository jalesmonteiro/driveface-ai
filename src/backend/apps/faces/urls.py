from django.urls import path
from .views import ClusterNameView

urlpatterns = [
    path(
        "clusters/<uuid:cluster_id>/name/",
        ClusterNameView.as_view(),
        name="cluster_name",
    ),
]
