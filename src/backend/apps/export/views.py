from django.http import HttpResponse
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from albums.permissions import IsAlbumViewerOrOwner
from faces.models import Cluster


class ExportClusterZipView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAlbumViewerOrOwner]

    def get(self, request, cluster_id):
        return HttpResponse(
            b"ZIP_PLACEHOLDER",
            content_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="DriveFace_Cluster_{cluster_id}.zip"'},
        )


class ExportClusterDriveView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAlbumViewerOrOwner]

    def post(self, request, cluster_id):
        target_folder = request.data.get("target_folder_name", "DriveFace Export")
        return Response(
            {
                "target_folder_id": "placeholder_folder_id",
                "copied_files_count": 0,
                "drive_web_view_link": "https://drive.google.com",
            },
            status=status.HTTP_200_OK,
        )
