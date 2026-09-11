import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from albums.models import Album
from faces.models import Cluster, Face, Identity, Photo

User = get_user_model()


@pytest.mark.django_db
class TestDemoLoginAndAlbums:
    demo_login_url = "/api/v1/auth/demo-login/"
    albums_url = "/api/v1/albums/"

    def test_demo_login_issues_valid_jwt_and_accesses_albums(self, api_client):
        """Valida que o demo login emite tokens válidos e permite acessar a API de álbuns."""
        # 1. Requisição para o login demo
        response = api_client.post(self.demo_login_url)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access" in data
        assert "refresh" in data
        assert data["user"]["email"] == "alexandre.google@driveface.ai"

        # 2. Acesso à API de álbuns com o token retornado
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {data['access']}")
        albums_res = api_client.get(self.albums_url)
        assert albums_res.status_code == status.HTTP_200_OK
        assert isinstance(albums_res.json(), list)

    def test_album_list_includes_cover_url(self, api_client):
        """Valida que a listagem de álbuns inclui campo cover_url."""
        user = User.objects.create_user(
            email="owner@driveface.ai",
            password="StrongPassword123!",
            full_name="Album Owner",
        )
        album = Album.objects.create(
            owner=user,
            google_drive_folder_id="drive_f1",
            folder_name="Viagem Praia 2026",
        )
        Photo.objects.create(
            album=album,
            google_file_id="photo_1",
            filename="foto1.jpg",
        )

        api_client.force_authenticate(user=user)
        res = api_client.get(self.albums_url)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert len(data) == 1
        assert data[0]["folder_name"] == "Viagem Praia 2026"
        assert "cover_url" in data[0]
        assert "api/v1/photos/" in data[0]["cover_url"]

    def test_delete_album_without_deleting_faceids(self, api_client):
        """Valida exclusão do álbum mantendo as FaceIDs cadastradas intactas."""
        user = User.objects.create_user(
            email="owner_del1@driveface.ai",
            password="StrongPassword123!",
            full_name="Owner Del",
        )
        album = Album.objects.create(
            owner=user,
            google_drive_folder_id="drive_del_1",
            folder_name="Evento Corporativo",
        )
        identity = Identity.objects.create(
            user=user,
            person_name="Carlos Executivo",
            centroid_embedding=[0.1] * 512,
            total_samples=1,
        )
        Cluster.objects.create(
            album=album,
            identity=identity,
            label="Carlos Executivo",
            face_count=5,
        )

        api_client.force_authenticate(user=user)
        del_res = api_client.delete(f"/api/v1/albums/{album.id}/?delete_faceids=false")
        assert del_res.status_code == status.HTTP_200_OK
        assert not Album.objects.filter(id=album.id).exists()
        # Identity DEVE continuar existindo no banco
        assert Identity.objects.filter(id=identity.id).exists()

    def test_delete_album_with_deleting_faceids(self, api_client):
        """Valida exclusão do álbum removendo também as FaceIDs vinculadas se solicitado."""
        user = User.objects.create_user(
            email="owner_del2@driveface.ai",
            password="StrongPassword123!",
            full_name="Owner Del 2",
        )
        album = Album.objects.create(
            owner=user,
            google_drive_folder_id="drive_del_2",
            folder_name="Festa de Fim de Ano",
        )
        identity = Identity.objects.create(
            user=user,
            person_name="Mariana Convidada",
            centroid_embedding=[0.2] * 512,
            total_samples=1,
        )
        Cluster.objects.create(
            album=album,
            identity=identity,
            label="Mariana Convidada",
            face_count=3,
        )

        api_client.force_authenticate(user=user)
        del_res = api_client.delete(f"/api/v1/albums/{album.id}/?delete_faceids=true")
        assert del_res.status_code == status.HTTP_200_OK
        assert not Album.objects.filter(id=album.id).exists()
        # Identity DEVE ter sido removida conforme solicitado pelo usuário
        assert not Identity.objects.filter(id=identity.id).exists()

    def test_cluster_avatar_endpoint_cached(self, api_client):
        """Valida que o endpoint de avatar retorna imagem em bytes a partir de base64 em cache."""
        import base64
        import io
        from PIL import Image

        user = User.objects.create_user(
            email="avatar_user@driveface.ai",
            password="StrongPassword123!",
            full_name="Avatar User",
        )
        album = Album.objects.create(
            owner=user,
            google_drive_folder_id="drive_av_1",
            folder_name="Álbum Avatar",
        )

        # Gera uma imagem 160x160 válida em memória
        img = Image.new("RGB", (160, 160), color="blue")
        buf = io.BytesIO()
        img.save(buf, format="WEBP")
        b64_str = f"data:image/webp;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"

        cluster = Cluster.objects.create(
            album=album,
            label="Pessoa Teste",
            face_count=1,
            avatar_crop_webp=b64_str,
        )

        res = api_client.get(f"/api/v1/faces/clusters/{cluster.id}/avatar/")
        assert res.status_code == status.HTTP_200_OK
        assert res["Content-Type"] == "image/webp"
        assert len(res.content) > 0

    def test_cluster_avatar_endpoint_dynamic_crop(self, api_client, monkeypatch):
        """Valida que o endpoint recorta dinamicamente o rosto específico a partir da foto."""
        import io
        from PIL import Image

        user = User.objects.create_user(
            email="dynamic_crop@driveface.ai",
            password="StrongPassword123!",
            full_name="Crop User",
        )
        album = Album.objects.create(
            owner=user,
            google_drive_folder_id="drive_crop_1",
            folder_name="Álbum Crop",
        )
        photo = Photo.objects.create(
            album=album,
            google_file_id="photo_group_1",
            filename="foto_grupo.jpg",
            width=1000,
            height=1000,
        )
        cluster = Cluster.objects.create(
            album=album,
            label="Rosto Recortado",
            face_count=1,
            avatar_crop_webp="",
        )
        # Face em um canto específico da foto (ex: centro 40% a 60%)
        Face.objects.create(
            photo=photo,
            cluster=cluster,
            embedding=[0.0] * 512,
            bbox_xmin=0.4,
            bbox_ymin=0.4,
            bbox_xmax=0.6,
            bbox_ymax=0.6,
            detection_confidence=0.95,
        )

        # Mock do download da imagem do Google Drive
        def mock_download_stream(self, file_id):
            img = Image.new("RGB", (1000, 1000), color="red")
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            buf.seek(0)
            return buf

        from google_integration.services import GoogleDriveService
        monkeypatch.setattr(GoogleDriveService, "download_image_stream", mock_download_stream)

        res = api_client.get(f"/api/v1/faces/clusters/{cluster.id}/avatar/")
        assert res.status_code == status.HTTP_200_OK
        assert res["Content-Type"] == "image/webp"

        # Verifica que o avatar recortado foi salvo em cache no banco
        cluster.refresh_from_db()
        assert cluster.avatar_crop_webp.startswith("data:image/webp;base64,")

    def test_album_clusters_returns_job_progress(self, api_client):
        """Valida que a rota /api/v1/albums/<id>/clusters/ retorna o objeto de job com métricas de progresso."""
        from albums.models import Job

        user = User.objects.create_user(
            email="progress_tester@driveface.ai",
            password="StrongPassword123!",
            full_name="Progress Tester",
        )
        album = Album.objects.create(
            owner=user,
            google_drive_folder_id="drive_prog_1",
            folder_name="Álbum com Progresso",
        )
        job = Job.objects.create(
            album=album,
            status=Job.Status.PROCESSING,
            total_images=50,
            processed_images=25,
        )

        api_client.force_authenticate(user=user)
        res = api_client.get(f"/api/v1/albums/{album.id}/clusters/")
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert "job" in data
        assert data["job"]["status"] == "PROCESSING"
        assert data["job"]["total_images"] == 50
        assert data["job"]["processed_images"] == 25
        assert data["job"]["progress_percentage"] == 50.0

    def test_album_reprocess_endpoint(self, api_client, monkeypatch):
        """Valida que o endpoint /api/v1/albums/<id>/reprocess/ dispara o job na fila."""
        user = User.objects.create_user(
            email="reprocess_tester@driveface.ai",
            password="StrongPassword123!",
            full_name="Reprocess Tester",
        )
        album = Album.objects.create(
            owner=user,
            google_drive_folder_id="drive_reproc_1",
            folder_name="Álbum Reprocess",
        )

        # Mock Celery delay
        mock_called = []
        from vision_pipeline.tasks import process_album_task
        monkeypatch.setattr(process_album_task, "delay", lambda job_id: mock_called.append(job_id))

        api_client.force_authenticate(user=user)
        res = api_client.post(f"/api/v1/albums/{album.id}/reprocess/")
        assert res.status_code == status.HTTP_202_ACCEPTED
        data = res.json()
        assert data["status"] == "PENDING"
        assert len(mock_called) == 1


