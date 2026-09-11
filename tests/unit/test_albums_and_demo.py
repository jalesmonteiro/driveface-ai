import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from albums.models import Album
from faces.models import Cluster, Identity, Photo

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
