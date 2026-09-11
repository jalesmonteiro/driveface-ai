from django.http import HttpResponse
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
from google_integration.services import GoogleDriveService


class AlbumListView(generics.ListAPIView):
    """Lista todos os álbuns do usuário autenticado no PostgreSQL."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        albums = Album.objects.filter(owner=request.user).order_by("-created_at")
        data = []
        for alb in albums:
            cover_url = ""
            first_cluster = alb.clusters.filter(avatar_crop_webp__isnull=False).exclude(avatar_crop_webp="").first()
            if first_cluster and first_cluster.avatar_crop_webp:
                cover_url = first_cluster.avatar_crop_webp
            else:
                first_photo = alb.photos.first()
                if first_photo:
                    cover_url = f"/api/v1/photos/{first_photo.id}/stream/"

            data.append({
                "id": str(alb.id),
                "folder_name": alb.folder_name,
                "google_drive_folder_id": alb.google_drive_folder_id,
                "total_photos": alb.photos.count(),
                "total_clusters": alb.clusters.count(),
                "cover_url": cover_url,
                "share_token": alb.share_token,
                "is_share_active": alb.is_share_active,
                "created_at": alb.created_at.isoformat(),
            })
        return Response(data)


class PhotoStreamView(APIView):
    """
    GET /api/v1/photos/<photo_id>/stream/
    Transmite em memória volátil a imagem do Google Drive diretamente para o navegador (Zero-Disk).
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, photo_id):
        from faces.models import Photo
        photo = generics.get_object_or_404(Photo, id=photo_id)
        album_owner = photo.album.owner
        drive_service = GoogleDriveService(user=album_owner)
        stream = drive_service.download_image_stream(photo.google_file_id)

        if not stream or stream.getbuffer().nbytes == 0:
            return HttpResponse(status=404)

        return HttpResponse(stream.getvalue(), content_type="image/jpeg")


class ClusterPhotosListView(APIView):
    """
    GET /api/v1/albums/<album_id>/clusters/<cluster_id>/photos/
    Retorna a lista completa de fotos onde essa pessoa/cluster aparece.
    """
    permission_classes = [permissions.IsAuthenticated, IsAlbumViewerOrOwner]

    def get(self, request, album_id, cluster_id):
        from faces.models import Cluster, Photo
        album = generics.get_object_or_404(Album, id=album_id)
        self.check_object_permissions(request, album)
        cluster = generics.get_object_or_404(Cluster, id=cluster_id, album=album)

        photos = list(Photo.objects.filter(detected_faces__cluster=cluster).distinct())
        if not photos:
            photos = list(album.photos.all()[:cluster.face_count])

        photos_data = [
            {
                "id": str(p.id),
                "filename": p.filename,
                "stream_url": f"/api/v1/photos/{p.id}/stream/",
                "google_file_id": p.google_file_id,
                "created_at": p.created_at.isoformat(),
            }
            for p in photos
        ]

        return Response({
            "album_id": str(album.id),
            "album_name": album.folder_name,
            "cluster_id": str(cluster.id),
            "label": cluster.label,
            "face_count": cluster.face_count,
            "photos": photos_data,
        })


class AlbumClustersListView(APIView):
    """
    Lista todos os clusters de faces de um álbum específico.
    Os clusters são criados pelo pipeline Celery (vision_pipeline.process_album_task).
    Esta view é somente leitura — não cria dados falsos.
    """
    permission_classes = [permissions.IsAuthenticated, IsAlbumViewerOrOwner]

    def get(self, request, album_id):
        album = generics.get_object_or_404(Album, id=album_id)
        self.check_object_permissions(request, album)

        from faces.models import Cluster

        photos = album.photos.all()
        clusters = list(album.clusters.all().order_by("-face_count"))

        # Verifica o estado do último job para informar ao frontend
        last_job = album.jobs.order_by("-created_at").first()
        job_status = last_job.status if last_job else None
        job_error = last_job.error_message if last_job else None

        data = []
        for c in clusters:
            avatar = c.avatar_crop_webp
            if not avatar:
                # Tenta obter a primeira foto associada a uma face deste cluster
                first_face = c.faces.select_related("photo").first()
                if first_face and first_face.photo:
                    avatar = f"/api/v1/photos/{first_face.photo.id}/stream/"

            data.append({
                "id": str(c.id),
                "album_id": str(album.id),
                "label": c.label,
                "face_count": c.face_count,
                "is_suggested": c.is_suggested,
                "avatar_webp": avatar or "",
                "created_at": c.created_at.isoformat(),
            })

        return Response({
            "album_id": str(album.id),
            "folder_name": album.folder_name,
            "total_photos": photos.count(),
            "total_people": len(clusters),
            "clusters": data,
            "job_status": job_status,
            "job_error": job_error,
        })



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

        return Response(
            {
                "job_id": str(job.id),
                "album_id": str(album.id),
                "folder_name": album.folder_name,
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


class AlbumDetailView(generics.RetrieveDestroyAPIView):
    queryset = Album.objects.all()
    serializer_class = AlbumSerializer
    lookup_field = "id"
    lookup_url_kwarg = "album_id"

    def get_permissions(self):
        if self.request.method == "DELETE":
            return [permissions.IsAuthenticated(), IsAlbumOwner()]
        return [permissions.IsAuthenticated(), IsAlbumViewerOrOwner()]

    def delete(self, request, album_id):
        album = generics.get_object_or_404(Album, id=album_id)
        self.check_object_permissions(request, album)

        delete_faceids = (
            str(request.data.get("delete_faceids", "")).lower() in ("true", "1")
            or str(request.query_params.get("delete_faceids", "")).lower() in ("true", "1")
            or str(request.data.get("delete_identities", "")).lower() in ("true", "1")
            or str(request.query_params.get("delete_identities", "")).lower() in ("true", "1")
        )

        album_name = album.folder_name

        from faces.models import Identity
        deleted_identities_count = 0
        if delete_faceids:
            linked_identities = Identity.objects.filter(clusters__album=album, user=request.user).distinct()
            deleted_identities_count = linked_identities.count()
            linked_identities.delete()

        # O álbum e suas fotos, faces, clusters e jobs são removidos do banco PostgreSQL.
        # Nenhuma foto no Google Drive é excluída.
        album.delete()

        return Response(
            {
                "success": True,
                "message": f"Álbum '{album_name}' removido do banco de dados com sucesso. Nenhuma foto foi apagada do Google Drive.",
                "deleted_faceids_count": deleted_identities_count,
            },
            status=status.HTTP_200_OK,
        )


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

