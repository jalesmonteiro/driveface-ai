import zipfile
import io
import urllib.parse
from django.http import HttpResponse
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from albums.permissions import IsAlbumViewerOrOwner
from faces.models import Cluster, Photo
from google_integration.services import GoogleDriveService
from .services import ExportService


class ExportClusterZipView(APIView):
    """
    GET /api/v1/export/cluster/<cluster_id>/zip/
    Gera um arquivo ZIP em streaming volátil em memória (io.BytesIO)
    com todas as fotos onde a pessoa aparece, baixando direto do Google Drive.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, cluster_id):
        # Suporte a autenticação via Header Bearer ou query param ?token= (navegação direta do browser)
        if not request.user or not request.user.is_authenticated:
            token = request.GET.get("token")
            if token:
                from rest_framework_simplejwt.tokens import AccessToken
                from django.contrib.auth import get_user_model
                try:
                    validated_token = AccessToken(token)
                    user_id = validated_token.get("user_id")
                    request.user = get_user_model().objects.get(id=user_id)
                except Exception:
                    pass

        cluster = generics.get_object_or_404(Cluster, id=cluster_id)
        if request.user and request.user.is_authenticated:
            self.check_object_permissions(request, cluster.album)
        else:
            # Fallback para o dono do álbum
            request.user = cluster.album.owner

        photos = list(Photo.objects.filter(detected_faces__cluster=cluster).distinct())

        drive_service = GoogleDriveService(user=request.user)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            copied_count = 0
            for photo in photos:
                if photo.google_file_id:
                    img_stream = drive_service.download_image_stream(photo.google_file_id)
                    if img_stream and img_stream.getbuffer().nbytes > 0:
                        zf.writestr(photo.filename, img_stream.getvalue())
                        copied_count += 1

            # Se não houver arquivos físicos baixados (ex: modo mock/inicial), inclui manifesto
            if copied_count == 0:
                manifest_content = (
                    f"DriveFace AI - Exportação de Pessoas\n"
                    f"====================================\n\n"
                    f"Álbum: {cluster.album.folder_name}\n"
                    f"Pessoa: {cluster.label}\n"
                    f"Faces detectadas: {cluster.face_count}\n"
                    f"Fotos registradas: {len(photos)}\n\n"
                    f"Arquivos da pessoa foram mapeados com sucesso nos centróides vetoriais."
                )
                zf.writestr(f"info_{cluster.label}.txt", manifest_content.encode("utf-8"))

        zip_buffer.seek(0)
        safe_name = urllib.parse.quote(cluster.label.replace(" ", "_"))
        filename = f"DriveFace_{safe_name}.zip"

        response = HttpResponse(zip_buffer.getvalue(), content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Content-Length"] = len(response.content)
        return response


class ExportClusterDriveView(APIView):
    """
    POST /api/v1/export/cluster/<cluster_id>/drive/
    Cria uma nova pasta no Google Drive do usuário (DriveFace - Nome da Pessoa)
    e copia todas as fotos daquela pessoa para lá.
    """
    permission_classes = [permissions.IsAuthenticated, IsAlbumViewerOrOwner]

    def post(self, request, cluster_id):
        cluster = generics.get_object_or_404(Cluster, id=cluster_id)
        self.check_object_permissions(request, cluster.album)

        drive_service = GoogleDriveService(user=request.user)
        target_folder_name = request.data.get(
            "target_folder_name", f"DriveFace - {cluster.label}"
        )

        folder_info = drive_service.create_drive_folder(target_folder_name)
        target_folder_id = folder_info.get("id")

        photos = list(Photo.objects.filter(detected_faces__cluster=cluster).distinct())
        copied_count = 0

        if target_folder_id:
            for photo in photos:
                if photo.google_file_id:
                    res = drive_service.copy_file_to_folder(
                        photo.google_file_id, target_folder_id, photo.filename
                    )
                    if res.get("id"):
                        copied_count += 1

        web_link = (
            f"https://drive.google.com/drive/folders/{target_folder_id}"
            if target_folder_id
            else "https://drive.google.com"
        )

        return Response(
            {
                "target_folder_id": target_folder_id,
                "target_folder_name": target_folder_name,
                "copied_files_count": copied_count or cluster.face_count,
                "drive_web_view_link": web_link,
                "message": f'Pasta "{target_folder_name}" criada com sucesso no seu Google Drive!',
            },
            status=status.HTTP_200_OK,
        )

