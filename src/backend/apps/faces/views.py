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
