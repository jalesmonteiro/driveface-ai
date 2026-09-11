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
        user_email = (request.user.email or "").strip().lower()
        only_owned = request.query_params.get("only_owned") in ("true", "1")
        from django.db.models import Q

        if only_owned:
            albums = Album.objects.filter(owner=request.user).order_by("-created_at")
        else:
            albums = Album.objects.filter(
                Q(owner=request.user) |
                Q(
                    shares__invited_email__iexact=user_email,
                    shares__status=AlbumShare.Status.ACTIVE,
                    is_share_active=True,
                )
            ).distinct().order_by("-created_at")

        data = []
        for alb in albums:
            cover_url = ""
            first_cluster = alb.clusters.exclude(label__in=["Outras", "Não Identificado", "nao identificado"]).order_by("-face_count").first()
            if not first_cluster:
                first_cluster = alb.clusters.first()
            if first_cluster:
                if first_cluster.avatar_crop_webp and first_cluster.avatar_crop_webp.startswith("data:image"):
                    cover_url = first_cluster.avatar_crop_webp
                else:
                    cover_url = f"/api/v1/faces/clusters/{first_cluster.id}/avatar/"
            else:
                first_photo = alb.photos.first()
                if first_photo:
                    cover_url = f"/api/v1/photos/{first_photo.id}/stream/"

            is_owner = (alb.owner == request.user)
            owner_name = getattr(alb.owner, "full_name", None) or alb.owner.email

            data.append({
                "id": str(alb.id),
                "folder_name": alb.folder_name,
                "google_drive_folder_id": alb.google_drive_folder_id,
                "total_photos": alb.photos.count(),
                "total_clusters": alb.clusters.count(),
                "cover_url": cover_url,
                "share_token": alb.share_token,
                "is_share_active": alb.is_share_active,
                "is_owner": is_owner,
                "owner_name": owner_name,
                "owner_email": alb.owner.email,
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

        avatar = cluster.avatar_crop_webp
        if not avatar or not avatar.startswith("data:image"):
            avatar = f"/api/v1/faces/clusters/{cluster.id}/avatar/"

        return Response({
            "album_id": str(album.id),
            "album_name": album.folder_name,
            "cluster_id": str(cluster.id),
            "label": cluster.label,
            "face_count": cluster.face_count,
            "avatar_webp": avatar,
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
        raw_clusters = list(album.clusters.all().order_by("-face_count"))

        # Pessoas e clusters ordenados por -face_count, e "Outras" / "Não Identificado" SEMPRE por último
        normal_clusters = []
        other_clusters = []
        for c in raw_clusters:
            clean_lbl = c.label.strip().lower()
            if clean_lbl in ("outras", "outros", "não identificado", "nao identificado"):
                if c.label != "Outras":
                    c.label = "Outras"
                    c.save(update_fields=["label"])
                other_clusters.append(c)
            else:
                normal_clusters.append(c)

        clusters = normal_clusters + other_clusters

        # Verifica o estado do último job para informar ao frontend
        last_job = album.jobs.order_by("-created_at").first()
        job_status = last_job.status if last_job else None
        job_error = last_job.error_message if last_job else None

        job_info = None
        if last_job:
            progress_pct = 0.0
            if last_job.total_images > 0:
                progress_pct = round((last_job.processed_images / last_job.total_images) * 100.0, 1)
            elif last_job.status == Job.Status.COMPLETED:
                progress_pct = 100.0

            job_info = {
                "id": str(last_job.id),
                "status": last_job.status,
                "total_images": last_job.total_images,
                "processed_images": last_job.processed_images,
                "progress_percentage": progress_pct,
                "error_message": last_job.error_message,
                "created_at": last_job.created_at.isoformat() if last_job.created_at else None,
                "started_at": last_job.started_at.isoformat() if last_job.started_at else None,
                "finished_at": last_job.finished_at.isoformat() if last_job.finished_at else None,
            }

        data = []
        for c in clusters:
            avatar = c.avatar_crop_webp
            if not avatar or not avatar.startswith("data:image"):
                # Recorte dinâmico da face específica da pessoa
                avatar = f"/api/v1/faces/clusters/{c.id}/avatar/"

            data.append({
                "id": str(c.id),
                "album_id": str(album.id),
                "label": c.label,
                "face_count": c.face_count,
                "is_suggested": c.is_suggested,
                "avatar_webp": avatar,
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
            "job": job_info,
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

        # Dispara a tarefa Celery de processamento assíncrono
        from vision_pipeline.tasks import process_album_task
        try:
            process_album_task.delay(str(job.id))
        except Exception as e:
            import logging, threading
            logging.getLogger(__name__).warning(f"Celery delay falhou ({e}), executando em background thread...")
            threading.Thread(target=process_album_task, args=(str(job.id),), daemon=True).start()

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


class AlbumReprocessView(APIView):
    """
    POST /api/v1/albums/<album_id>/reprocess/
    Reinicia ou dispara o processamento facial do álbum.
    """
    permission_classes = [permissions.IsAuthenticated, IsAlbumOwner]

    def post(self, request, album_id):
        album = generics.get_object_or_404(Album, id=album_id)
        self.check_object_permissions(request, album)

        from vision_pipeline.tasks import process_album_task

        # Se já existe um job PENDING ou PROCESSING, tenta acionar e retorna
        running_job = album.jobs.filter(status__in=[Job.Status.PENDING, Job.Status.PROCESSING]).first()
        if running_job:
            try:
                process_album_task.delay(str(running_job.id))
            except Exception as e:
                import logging, threading
                logging.getLogger(__name__).warning(f"Celery delay falhou ({e}), executando em thread...")
                threading.Thread(target=process_album_task, args=(str(running_job.id),), daemon=True).start()

            return Response(
                {
                    "job_id": str(running_job.id),
                    "album_id": str(album.id),
                    "folder_name": album.folder_name,
                    "status": running_job.status,
                    "message": "Processamento em andamento retomado com sucesso.",
                },
                status=status.HTTP_200_OK,
            )

        job = Job.objects.create(album=album, status=Job.Status.PENDING)
        try:
            process_album_task.delay(str(job.id))
        except Exception as e:
            import logging, threading
            logging.getLogger(__name__).warning(f"Celery delay falhou ({e}), executando em background thread...")
            threading.Thread(target=process_album_task, args=(str(job.id),), daemon=True).start()

        return Response(
            {
                "job_id": str(job.id),
                "album_id": str(album.id),
                "folder_name": album.folder_name,
                "status": job.status,
                "message": "Processamento facial reiniciado com sucesso.",
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
    """
    GET /api/v1/albums/<album_id>/shares/
    Retorna link seguro do álbum, status e lista completa de acessos (Proprietário, Convidados e Bloqueados).

    POST /api/v1/albums/<album_id>/shares/
    Permite:
    - Convidar e-mail (action='INVITE_EMAIL' ou invited_emails=[...])
    - Bloquear e-mail na blacklist (action='BLOCK_EMAIL')
    - Alternar is_share_active (true/false)
    """
    permission_classes = [permissions.IsAuthenticated, IsAlbumOwner]

    def get(self, request, album_id):
        album = generics.get_object_or_404(Album, id=album_id)
        self.check_object_permissions(request, album)

        host = request.build_absolute_uri('/')[:-1]
        share_url = f"{host}/share/{album.share_token}/"

        # Item 1: Proprietário
        owner_name = getattr(album.owner, "full_name", None) or album.owner.email
        access_list = [
            {
                "id": "owner",
                "email": album.owner.email,
                "name": owner_name,
                "type": "PROPRIETARIO",
                "type_label": "Proprietário",
                "status": "ACTIVE",
                "status_label": "Ativo",
                "invited_at": album.created_at.isoformat(),
                "can_modify": False,
            }
        ]

        shares = album.shares.all().order_by("-invited_at")
        for s in shares:
            access_list.append({
                "id": str(s.id),
                "email": s.invited_email,
                "name": s.invited_email,
                "type": s.invite_type,
                "type_label": s.get_invite_type_display(),
                "status": s.status,
                "status_label": s.get_status_display(),
                "invited_at": s.invited_at.isoformat(),
                "can_modify": True,
            })

        serialized_shares = AlbumShareSerializer(shares, many=True).data

        return Response({
            "album_id": str(album.id),
            "folder_name": album.folder_name,
            "share_token": album.share_token,
            "share_url": share_url,
            "is_share_active": album.is_share_active,
            "owner": {
                "id": str(album.owner.id),
                "email": album.owner.email,
                "name": owner_name,
                "type": "OWNER",
                "type_display": "Proprietário",
            },
            "shares": serialized_shares,
            "total_accesses": len(access_list),
            "access_list": access_list,
            "whitelist": serialized_shares,
        })

    def post(self, request, album_id):
        album = generics.get_object_or_404(Album, id=album_id)
        self.check_object_permissions(request, album)

        # 1. Atualiza status de ativação do link se fornecido
        if "is_share_active" in request.data:
            val = str(request.data["is_share_active"]).lower() in ("true", "1")
            album.is_share_active = val
            album.save(update_fields=["is_share_active"])

        action = request.data.get("action")
        email = (request.data.get("email") or "").strip().lower()

        # 2. Convidar por e-mail
        if action == "INVITE_EMAIL" and email:
            if email == album.owner.email.lower():
                return Response({"error": "O proprietário já possui acesso total a este álbum."}, status=status.HTTP_400_BAD_REQUEST)
            share, _ = AlbumShare.objects.get_or_create(
                album=album,
                invited_email=email,
                defaults={"invite_type": AlbumShare.InviteType.EMAIL, "status": AlbumShare.Status.ACTIVE}
            )
            share.invite_type = AlbumShare.InviteType.EMAIL
            share.status = AlbumShare.Status.ACTIVE
            share.save(update_fields=["invite_type", "status", "updated_at"])

        # 3. Bloquear e-mail (adicionar na Blacklist)
        elif action == "BLOCK_EMAIL" and email:
            if email == album.owner.email.lower():
                return Response({"error": "Não é possível bloquear o proprietário do álbum."}, status=status.HTTP_400_BAD_REQUEST)
            share, _ = AlbumShare.objects.get_or_create(
                album=album,
                invited_email=email,
                defaults={"invite_type": AlbumShare.InviteType.EMAIL, "status": AlbumShare.Status.BLOCKED}
            )
            share.status = AlbumShare.Status.BLOCKED
            share.save(update_fields=["status", "updated_at"])

        # 4. Suporte legado a invited_emails: [...]
        legacy_emails = request.data.get("invited_emails", [])
        if legacy_emails:
            for em in legacy_emails:
                clean_em = em.strip().lower()
                if clean_em and clean_em != album.owner.email.lower():
                    AlbumShare.objects.get_or_create(
                        album=album,
                        invited_email=clean_em,
                        defaults={"role": AlbumShare.Role.VIEWER, "invite_type": AlbumShare.InviteType.EMAIL, "status": AlbumShare.Status.ACTIVE},
                    )

        return self.get(request, album_id)


class AlbumShareItemView(APIView):
    """
    PATCH /api/v1/albums/<album_id>/shares/<share_id>/ -> Alternar status (ACTIVE / BLOCKED)
    DELETE /api/v1/albums/<album_id>/shares/<share_id>/ -> Remover da lista
    """
    permission_classes = [permissions.IsAuthenticated, IsAlbumOwner]

    def patch(self, request, album_id, share_id):
        album = generics.get_object_or_404(Album, id=album_id)
        self.check_object_permissions(request, album)
        share = generics.get_object_or_404(AlbumShare, id=share_id, album=album)

        new_status = request.data.get("status")
        if new_status in (AlbumShare.Status.ACTIVE, AlbumShare.Status.BLOCKED):
            share.status = new_status
            share.save(update_fields=["status", "updated_at"])
            return Response({
                "id": str(share.id),
                "email": share.invited_email,
                "status": share.status,
                "status_display": share.get_status_display(),
                "message": f"Status de '{share.invited_email}' alterado para {share.get_status_display()}.",
            })
        return Response({"error": "Status inválido"}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, album_id, share_id):
        album = generics.get_object_or_404(Album, id=album_id)
        self.check_object_permissions(request, album)
        share = generics.get_object_or_404(AlbumShare, id=share_id, album=album)
        share.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SharedWithMeAlbumsListView(APIView):
    """
    GET /api/v1/albums/shared-with-me/
    Retorna a lista de álbuns onde o usuário autenticado foi convidado (status=ACTIVE e is_share_active=True).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_email = (request.user.email or "").strip().lower()
        shares = AlbumShare.objects.filter(
            invited_email__iexact=user_email,
            status=AlbumShare.Status.ACTIVE,
            album__is_share_active=True,
        ).select_related("album", "album__owner").order_by("-invited_at")

        data = []
        for s in shares:
            alb = s.album
            cover_url = ""
            first_cluster = alb.clusters.exclude(label__in=["Outras", "Não Identificado", "nao identificado"]).order_by("-face_count").first()
            if not first_cluster:
                first_cluster = alb.clusters.first()
            if first_cluster:
                if first_cluster.avatar_crop_webp and first_cluster.avatar_crop_webp.startswith("data:image"):
                    cover_url = first_cluster.avatar_crop_webp
                else:
                    cover_url = f"/api/v1/faces/clusters/{first_cluster.id}/avatar/"
            else:
                first_photo = alb.photos.first()
                if first_photo:
                    cover_url = f"/api/v1/photos/{first_photo.id}/stream/"

            owner_name = getattr(alb.owner, "full_name", None) or alb.owner.email

            data.append({
                "id": str(alb.id),
                "folder_name": alb.folder_name,
                "owner_email": alb.owner.email,
                "owner_name": owner_name,
                "cover_url": cover_url,
                "total_photos": alb.photos.count(),
                "total_clusters": alb.clusters.count(),
                "invite_type": s.invite_type,
                "invite_type_display": s.get_invite_type_display(),
                "user_invite_type": s.invite_type,
                "user_invite_type_display": s.get_invite_type_display(),
                "shared_at": s.invited_at.isoformat(),
            })

        return Response(data)


class SharedAlbumDetailView(APIView):
    """
    GET /api/v1/albums/shared/<share_token>/
    Acessa o álbum compartilhado via link único.
    Adiciona o usuário autenticado automaticamente à whitelist (invite_type=LINK) se não estiver bloqueado.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, share_token):
        album = generics.get_object_or_404(Album, share_token=share_token)

        if not album.is_share_active and request.user != album.owner:
            return Response(
                {"error_code": "SHARE_INACTIVE", "detail": "O compartilhamento deste álbum está temporariamente desativado pelo proprietário."},
                status=status.HTTP_403_FORBIDDEN,
            )

        user_email = (request.user.email or "").strip().lower()

        # Verifica bloqueio prévio (Blacklist)
        existing_share = album.shares.filter(invited_email__iexact=user_email).first()
        if existing_share and existing_share.status == AlbumShare.Status.BLOCKED:
            return Response(
                {"error_code": "ACL_BLOCKED", "detail": "Seu acesso a este álbum foi bloqueado pelo proprietário."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Se não for o proprietário e ainda não estiver na lista de compartilhamento:
        # Adiciona automaticamente à whitelist como "Convidado por link"
        if request.user != album.owner and not existing_share:
            existing_share = AlbumShare.objects.create(
                album=album,
                invited_email=user_email,
                invite_type=AlbumShare.InviteType.LINK,
                status=AlbumShare.Status.ACTIVE,
            )

        clusters_data = [
            {
                "cluster_id": str(cluster.id),
                "label": cluster.label,
                "avatar_url": cluster.avatar_crop_webp if (cluster.avatar_crop_webp and cluster.avatar_crop_webp.startswith("data:")) else f"/api/v1/faces/clusters/{cluster.id}/avatar/",
                "photo_count": cluster.face_count,
            }
            for cluster in album.clusters.exclude(label__in=["Outras", "Não Identificado"]).order_by("-face_count")
        ]

        role = "OWNER" if request.user == album.owner else "VIEWER"

        return Response(
            {
                "album_id": str(album.id),
                "folder_name": album.folder_name,
                "user_role": role,
                "total_photos": album.photos.count(),
                "total_people": len(clusters_data),
                "clusters": clusters_data,
                "invite_type": existing_share.invite_type if existing_share else "OWNER",
                "invite_type_display": existing_share.get_invite_type_display() if existing_share else "Proprietário",
            }
        )

