from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Album, AlbumShare, Job
from .permissions import IsAlbumOwner, IsAlbumViewerOrOwner
from .serializers import (
    AlbumSerializer,
    ProcessAlbumSerializer,
    JobStatusSerializer,
    AlbumShareSerializer,
)


class ProcessAlbumView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ProcessAlbumSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        album = Album.objects.create(
            owner=request.user,
            google_drive_folder_id=serializer.validated_data["google_drive_folder_id"],
            folder_name=serializer.validated_data["folder_name"],
        )

        job = Job.objects.create(album=album, status=Job.Status.PENDING)

        # Na Task 2.2 despacharemos a tarefa Celery: process_album_task.delay(str(job.id))

        return Response(
            {
                "job_id": str(job.id),
                "album_id": str(album.id),
                "status": job.status,
                "message": "Processamento facial agendado na fila com sucesso.",
            },
            status=status.HTTP_202_ACCEPTED,
        )


class JobStatusView(generics.RetrieveAPIView):
    queryset = Job.objects.all()
    serializer_class = JobStatusSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"
    lookup_url_kwarg = "job_id"


class AlbumDetailView(generics.RetrieveAPIView):
    queryset = Album.objects.all()
    serializer_class = AlbumSerializer
    permission_classes = [permissions.IsAuthenticated, IsAlbumViewerOrOwner]
    lookup_field = "id"
    lookup_url_kwarg = "album_id"


class AlbumShareManageView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAlbumOwner]

    def post(self, request, album_id):
        album = generics.get_object_or_404(Album, id=album_id)
        self.check_object_permissions(request, album)

        is_active = request.data.get("is_share_active", True)
        emails = request.data.get("invited_emails", [])

        album.is_share_active = is_active
        album.save(update_fields=["is_share_active"])

        for email in emails:
            AlbumShare.objects.get_or_create(
                album=album,
                invited_email=email.strip().lower(),
                defaults={"role": AlbumShare.Role.VIEWER},
            )

        shares = album.shares.all()
        serializer = AlbumShareSerializer(shares, many=True)
        return Response(
            {
                "album_id": str(album.id),
                "share_token": album.share_token,
                "is_share_active": album.is_share_active,
                "whitelist": serializer.data,
            }
        )


class SharedAlbumDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAlbumViewerOrOwner]

    def get(self, request, share_token):
        album = generics.get_object_or_404(Album, share_token=share_token)
        self.check_object_permissions(request, album)

        clusters_data = [
            {
                "cluster_id": str(cluster.id),
                "label": cluster.label,
                "avatar_url": f"/api/v1/clusters/{cluster.id}/avatar/",
                "photo_count": cluster.face_count,
            }
            for cluster in album.clusters.all()
        ]

        role = "OWNER" if request.user == album.owner else "VIEWER"

        return Response(
            {
                "album_id": str(album.id),
                "folder_name": album.folder_name,
                "user_role": role,
                "total_photos": album.photos.count(),
                "total_people": album.clusters.count(),
                "clusters": clusters_data,
            }
        )

