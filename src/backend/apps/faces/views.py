from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from albums.permissions import IsAlbumOwner
from .models import Cluster, Face, Identity, Photo
from .serializers import ClusterSerializer, IdentitySerializer


class ClusterNameView(APIView):
    """
    POST /api/v1/faces/clusters/{cluster_id}/name/
    Atribui nome a um cluster e cria/atualiza a identidade biométrica (FaceID) no banco de dados.
    Restrito ao proprietário do álbum.
    """
    permission_classes = [permissions.IsAuthenticated, IsAlbumOwner]

    def post(self, request, cluster_id):
        cluster = generics.get_object_or_404(Cluster, id=cluster_id)
        self.check_object_permissions(request, cluster.album)

        person_name = request.data.get("person_name")
        if not person_name or not str(person_name).strip():
            return Response(
                {"error": "person_name é obrigatório"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        clean_name = str(person_name).strip()

        # 1. Calcula o centróide biométrico 512-D a partir das faces detectadas neste cluster
        import numpy as np
        faces = [f for f in cluster.faces.exclude(embedding__isnull=True) if f.embedding is not None and len(f.embedding) == 512]
        centroid = None
        if faces:
            embs = np.array([f.embedding for f in faces], dtype=np.float32)
            centroid = np.mean(embs, axis=0)
            norm = np.linalg.norm(centroid)
            if norm > 0:
                centroid = centroid / norm

        # 2. Localiza ou cria a Identity (FaceID biométrica) do usuário
        identity = Identity.objects.filter(user=request.user, person_name__iexact=clean_name).first()
        if identity:
            if centroid is not None:
                old_c = np.array(identity.centroid_embedding, dtype=np.float32)
                if identity.total_samples > 0 and np.linalg.norm(old_c) > 0:
                    # Média ponderada entre amostras já acumuladas e as novas amostras
                    combined = (old_c * identity.total_samples + centroid * len(faces)) / (identity.total_samples + len(faces))
                else:
                    combined = centroid
                norm = np.linalg.norm(combined)
                if norm > 0:
                    combined = combined / norm
                identity.centroid_embedding = combined.tolist()
                identity.total_samples += len(faces)
            identity.person_name = clean_name
            identity.save(update_fields=["person_name", "centroid_embedding", "total_samples", "updated_at"])
        else:
            centroid_list = centroid.tolist() if centroid is not None else [0.0] * 512
            identity = Identity.objects.create(
                user=request.user,
                person_name=clean_name,
                centroid_embedding=centroid_list,
                total_samples=len(faces) or 1,
            )

        # 3. Verifica se já existe outro cluster no mesmo álbum com o mesmo nome (Merge Automático)
        existing_cluster = (
            Cluster.objects.filter(album=cluster.album, label__iexact=clean_name)
            .exclude(id=cluster.id)
            .first()
        )

        if existing_cluster:
            # Transfere todas as faces do cluster atual para o cluster existente
            source_cluster_id = str(cluster.id)
            cluster.faces.all().update(cluster=existing_cluster)

            # Atualiza o avatar caso o existente esteja vazio
            if not existing_cluster.avatar_crop_webp and cluster.avatar_crop_webp:
                existing_cluster.avatar_crop_webp = cluster.avatar_crop_webp

            existing_cluster.face_count = existing_cluster.faces.count()

            # Recalcula o centróide biométrico L2 unificado com todas as faces combinadas
            all_faces = [f for f in existing_cluster.faces.exclude(embedding__isnull=True) if f.embedding is not None and len(f.embedding) == 512]
            if all_faces:
                embs = np.array([f.embedding for f in all_faces], dtype=np.float32)
                unified_c = np.mean(embs, axis=0)
                norm_u = np.linalg.norm(unified_c)
                if norm_u > 0:
                    unified_c = unified_c / norm_u
                identity.centroid_embedding = unified_c.tolist()
                identity.total_samples = max(identity.total_samples, len(all_faces))
                identity.save(update_fields=["centroid_embedding", "total_samples", "updated_at"])

            existing_cluster.identity = identity
            existing_cluster.label = clean_name
            existing_cluster.is_suggested = False
            existing_cluster.save(update_fields=["label", "identity", "face_count", "avatar_crop_webp", "is_suggested"])

            # Exclui o cluster de origem que agora está vazio
            cluster.delete()

            return Response(
                {
                    "cluster_id": str(existing_cluster.id),
                    "person_name": existing_cluster.label,
                    "identity_id": str(identity.id),
                    "merged": True,
                    "source_cluster_id": source_cluster_id,
                    "target_cluster_id": str(existing_cluster.id),
                    "face_count": existing_cluster.face_count,
                    "total_samples": identity.total_samples,
                    "message": f"Grupos mesclados com sucesso! Todas as fotos foram unificadas em '{clean_name}'.",
                },
                status=status.HTTP_200_OK,
            )

        # 4. Caso contrário, atualiza normalmente este cluster
        cluster.label = clean_name
        cluster.identity = identity
        cluster.is_suggested = False
        cluster.save(update_fields=["label", "identity", "is_suggested"])

        return Response(
            {
                "cluster_id": str(cluster.id),
                "person_name": cluster.label,
                "identity_id": str(identity.id),
                "merged": False,
                "centroid_updated": True,
                "face_count": cluster.face_count,
                "total_samples": identity.total_samples,
            },
            status=status.HTTP_200_OK,
        )


class ClusterAvatarView(APIView):
    """
    GET /api/v1/faces/clusters/<cluster_id>/avatar/
    Retorna o recorte facial (crop 160x160 px) da pessoa específica deste cluster.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, cluster_id):
        import base64
        import io
        import logging
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None
        from django.http import HttpResponse
        from google_integration.services import GoogleDriveService

        logger = logging.getLogger(__name__)
        cluster = generics.get_object_or_404(Cluster, id=cluster_id)

        # 1. Se já está em cache como Base64 (data:image/...), responde diretamente
        if cluster.avatar_crop_webp and cluster.avatar_crop_webp.startswith("data:image"):
            try:
                header, b64_data = cluster.avatar_crop_webp.split(",", 1)
                content_type = header.split(";")[0].split(":")[1]
                image_data = base64.b64decode(b64_data)
                response = HttpResponse(image_data, content_type=content_type)
                response["Cache-Control"] = "public, max-age=86400"
                return response
            except Exception as e:
                logger.warning(f"Falha ao decodificar avatar base64: {e}")

        # 2. Localiza a melhor face deste cluster
        face = cluster.faces.select_related("photo", "photo__album__owner").order_by("-detection_confidence").first()
        if not face or not face.photo:
            return HttpResponse(status=404)

        photo = face.photo
        owner = photo.album.owner
        drive_service = GoogleDriveService(user=owner)
        stream = drive_service.download_image_stream(photo.google_file_id)
        if not stream or stream.getbuffer().nbytes == 0:
            return HttpResponse(status=404)

        try:
            img = Image.open(stream).convert("RGB")
            w, h = img.size

            # Coordenadas da face normalizadas (0.0 a 1.0)
            x1 = int(face.bbox_xmin * w)
            y1 = int(face.bbox_ymin * h)
            x2 = int(face.bbox_xmax * w)
            y2 = int(face.bbox_ymax * h)

            bw = max(1, x2 - x1)
            bh = max(1, y2 - y1)

            # Margem de 35% ao redor do rosto para um enquadramento natural de retrato
            pad_x = int(bw * 0.35)
            pad_y = int(bh * 0.35)

            crop_x1 = max(0, x1 - pad_x)
            crop_y1 = max(0, y1 - pad_y)
            crop_x2 = min(w, x2 + pad_x)
            crop_y2 = min(h, y2 + pad_y)

            face_img = img.crop((crop_x1, crop_y1, crop_x2, crop_y2))
            face_thumb = face_img.resize((160, 160), Image.Resampling.LANCZOS)

            out_buf = io.BytesIO()
            face_thumb.save(out_buf, format="WEBP", quality=85)
            out_bytes = out_buf.getvalue()

            # Salva no banco de dados para que as próximas chamadas sejam instantâneas
            b64_str = f"data:image/webp;base64,{base64.b64encode(out_bytes).decode('utf-8')}"
            cluster.avatar_crop_webp = b64_str
            cluster.save(update_fields=["avatar_crop_webp"])

            response = HttpResponse(out_bytes, content_type="image/webp")
            response["Cache-Control"] = "public, max-age=86400"
            return response
        except Exception as exc:
            logger.error(f"Erro ao gerar recorte facial do cluster {cluster.id}: {exc}")
            return HttpResponse(status=500)
