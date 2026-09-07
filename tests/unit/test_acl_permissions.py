import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from albums.models import Album, AlbumShare

User = get_user_model()


@pytest.mark.django_db
class TestACLPermissions:
    def setup_method(self):
        # Usuário proprietário do álbum
        self.owner = User.objects.create_user(
            email="organizador@driveface.ai",
            password="OwnerPassword123!",
            full_name="Organizador do Evento",
        )
        # Usuário convidado autorizado na whitelist
        self.authorized_viewer = User.objects.create_user(
            email="convidado.valido@driveface.ai",
            password="ViewerPassword123!",
            full_name="Convidado Oficial",
        )
        # Usuário intruso não cadastrado na whitelist
        self.intruder = User.objects.create_user(
            email="estranho@driveface.ai",
            password="IntruderPassword123!",
            full_name="Invasor Não Convidado",
        )
        # Criação do álbum com compartilhamento ativo
        self.album = Album.objects.create(
            owner=self.owner,
            google_drive_folder_id="drive_folder_formatura_2026",
            folder_name="Formatura Turma 2026",
            is_share_active=True,
        )
        # Adiciona o convidado autorizado na whitelist
        AlbumShare.objects.create(
            album=self.album,
            invited_email=self.authorized_viewer.email,
            role=AlbumShare.Role.VIEWER,
        )

        self.shared_url = f"/api/v1/albums/shared/{self.album.share_token}/"
        self.shares_manage_url = f"/api/v1/albums/{self.album.id}/shares/"

    def test_owner_can_access_shared_album(self, api_client):
        """Cenário: Proprietário acessa o álbum compartilhado."""
        api_client.force_authenticate(user=self.owner)
        response = api_client.get(self.shared_url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["album_id"] == str(self.album.id)
        assert data["user_role"] == "OWNER"
        assert data["folder_name"] == "Formatura Turma 2026"

    def test_authorized_viewer_can_access_shared_album(self, api_client):
        """Cenário: Convidado autorizado na whitelist acessa o álbum."""
        api_client.force_authenticate(user=self.authorized_viewer)
        response = api_client.get(self.shared_url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["album_id"] == str(self.album.id)
        assert data["user_role"] == "VIEWER"

    def test_unauthorized_email_is_blocked_with_403_forbidden(self, api_client):
        """Cenário R_6: E-mail não presente na whitelist é estritamente bloqueado com 403."""
        api_client.force_authenticate(user=self.intruder)
        response = api_client.get(self.shared_url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert data.get("error_code") == "ACL_FORBIDDEN"
        assert "não possui autorização" in data.get("detail", "")

    def test_revoked_or_inactive_share_blocks_viewer(self, api_client):
        """Cenário: Proprietário desativa o link de compartilhamento."""
        self.album.is_share_active = False
        self.album.save(update_fields=["is_share_active"])

        api_client.force_authenticate(user=self.authorized_viewer)
        response = api_client.get(self.shared_url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_anonymous_access_returns_401(self, api_client):
        """Cenário: Acesso anônimo ao álbum compartilhado sem autenticação."""
        response = api_client.get(self.shared_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_only_owner_can_manage_shares(self, api_client):
        """Cenário: Apenas o owner pode adicionar e-mails à whitelist."""
        payload = {
            "is_share_active": True,
            "invited_emails": ["novo.convidado@driveface.ai"],
        }

        # Viewer autorizado tenta gerenciar shares -> deve ser bloqueado
        api_client.force_authenticate(user=self.authorized_viewer)
        forbidden_response = api_client.post(self.shares_manage_url, payload, format="json")
        assert forbidden_response.status_code == status.HTTP_403_FORBIDDEN

        # Owner gerencia shares -> permitido
        api_client.force_authenticate(user=self.owner)
        success_response = api_client.post(self.shares_manage_url, payload, format="json")
        assert success_response.status_code == status.HTTP_200_OK
        data = success_response.json()
        assert len(data["whitelist"]) == 2
