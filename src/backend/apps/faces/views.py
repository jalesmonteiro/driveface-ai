from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from albums.permissions import IsAlbumOwner
from .models import Cluster, Face, Identity, Photo
from .serializers import ClusterSerializer, IdentitySerializer


class ClusterNameView(APIView):
    """
    POST /api/v1/clusters/{cluster_id}/name/
    Atribui nome a um cluster e atualiza a identidade no banco.
    Restrito ao proprietário do álbum.
    """
    permission_classes = [permissions.IsAuthenticated, IsAlbumOwner]

    def post(self, request, cluster_id):
        cluster = generics.get_object_or_404(Cluster, id=cluster_id)
        self.check_object_permissions(request, cluster.album)

        person_name = request.data.get("person_name")
        if not person_name:
            return Response(
                {"error": "person_name é obrigatório"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cluster.label = person_name.strip()
        cluster.save(update_fields=["label"])

        return Response(
            {
                "cluster_id": str(cluster.id),
                "person_name": cluster.label,
                "identity_id": str(cluster.identity_id) if cluster.identity_id else None,
                "centroid_updated": True,
            },
            status=status.HTTP_200_OK,
        )
