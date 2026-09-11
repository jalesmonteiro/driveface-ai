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
        # Usuário convidado autorizado previamente por e-mail
        self.authorized_viewer = User.objects.create_user(
            email="convidado.valido@driveface.ai",
            password="ViewerPassword123!",
            full_name="Convidado Oficial",
        )
        # Novo usuário que acessará pelo link
        self.new_link_visitor = User.objects.create_user(
            email="visitante.link@driveface.ai",
            password="LinkPassword123!",
            full_name="Visitante Via Link",
        )
        # Usuário bloqueado na blacklist
        self.blocked_user = User.objects.create_user(
            email="bloqueado@driveface.ai",
            password="BlockedPassword123!",
            full_name="Usuário Bloqueado",
        )
        # Criação do álbum com compartilhamento ativo
        self.album = Album.objects.create(
            owner=self.owner,
            google_drive_folder_id="drive_folder_formatura_2026",
            folder_name="Formatura Turma 2026",
            is_share_active=True,
        )
        # Convidado por e-mail ativo
        AlbumShare.objects.create(
            album=self.album,
            invited_email=self.authorized_viewer.email,
            invite_type=AlbumShare.InviteType.EMAIL,
            status=AlbumShare.Status.ACTIVE,
            role=AlbumShare.Role.VIEWER,
        )
        # Usuário colocado na blacklist (Bloqueado)
        AlbumShare.objects.create(
            album=self.album,
            invited_email=self.blocked_user.email,
            invite_type=AlbumShare.InviteType.EMAIL,
            status=AlbumShare.Status.BLOCKED,
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
        """Cenário: Convidado autorizado por e-mail acessa o álbum."""
        api_client.force_authenticate(user=self.authorized_viewer)
        response = api_client.get(self.shared_url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["album_id"] == str(self.album.id)
        assert data["user_role"] == "VIEWER"

    def test_link_auto_enrolls_new_user_as_link_invite(self, api_client):
        """Cenário: Acessar pelo link único adiciona automaticamente o usuário como 'Convidado por link'."""
        api_client.force_authenticate(user=self.new_link_visitor)
        response = api_client.get(self.shared_url)

        assert response.status_code == status.HTTP_200_OK
        
        # Verifica se o share foi registrado no banco com invite_type="LINK" e status="ACTIVE"
        share = AlbumShare.objects.filter(album=self.album, invited_email=self.new_link_visitor.email).first()
        assert share is not None
        assert share.invite_type == AlbumShare.InviteType.LINK
        assert share.status == AlbumShare.Status.ACTIVE

    def test_blocked_email_cannot_access_album_even_with_link(self, api_client):
        """Cenário: E-mail presente na blacklist é estritamente bloqueado com 403 Forbidden."""
        api_client.force_authenticate(user=self.blocked_user)
        response = api_client.get(self.shared_url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert data.get("error_code") == "ACL_BLOCKED"
        assert "bloqueado" in data.get("detail", "").lower()

    def test_revoked_or_inactive_share_blocks_viewer(self, api_client):
        """Cenário: Proprietário desativa o compartilhamento do álbum."""
        self.album.is_share_active = False
        self.album.save(update_fields=["is_share_active"])

        api_client.force_authenticate(user=self.authorized_viewer)
        response = api_client.get(self.shared_url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert data.get("error_code") == "SHARE_INACTIVE"

    def test_anonymous_access_returns_401(self, api_client):
        """Cenário: Acesso anônimo ao álbum compartilhado sem autenticação."""
        response = api_client.get(self.shared_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_only_owner_can_manage_shares(self, api_client):
        """Cenário: Apenas o owner pode gerenciar shares do álbum."""
        payload = {"action": "INVITE_EMAIL", "email": "outro.convidado@driveface.ai"}

        # Viewer tenta gerenciar -> 403 Forbidden
        api_client.force_authenticate(user=self.authorized_viewer)
        forbidden_resp = api_client.post(self.shares_manage_url, payload, format="json")
        assert forbidden_resp.status_code == status.HTTP_403_FORBIDDEN

        # Owner gerencia -> 200 OK
        api_client.force_authenticate(user=self.owner)
        success_resp = api_client.post(self.shares_manage_url, payload, format="json")
        assert success_resp.status_code == status.HTTP_200_OK
        data = success_resp.json()
        assert data["owner"]["email"] == self.owner.email
        assert any(s["invited_email"] == "outro.convidado@driveface.ai" for s in data["shares"])

    def test_owner_can_block_email_via_manage_view(self, api_client):
        """Cenário: Owner adiciona um e-mail diretamente à blacklist (status=BLOCKED)."""
        api_client.force_authenticate(user=self.owner)
        payload = {"action": "BLOCK_EMAIL", "email": "spammer@driveface.ai"}
        response = api_client.post(self.shares_manage_url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        blocked_share = AlbumShare.objects.get(album=self.album, invited_email="spammer@driveface.ai")
        assert blocked_share.status == AlbumShare.Status.BLOCKED

    def test_owner_can_toggle_block_and_delete_share(self, api_client):
        """Cenário: Owner alterna status via PATCH e remove acesso via DELETE."""
        api_client.force_authenticate(user=self.owner)
        share = AlbumShare.objects.get(album=self.album, invited_email=self.blocked_user.email)
        item_url = f"/api/v1/albums/{self.album.id}/shares/{share.id}/"

        # 1. Desbloqueia (PATCH)
        patch_resp = api_client.patch(item_url, {"status": "ACTIVE"}, format="json")
        assert patch_resp.status_code == status.HTTP_200_OK
        assert patch_resp.json()["status"] == "ACTIVE"
        share.refresh_from_db()
        assert share.status == AlbumShare.Status.ACTIVE

        # 2. Deleta o registro (DELETE)
        del_resp = api_client.delete(item_url)
        assert del_resp.status_code == status.HTTP_204_NO_CONTENT
        assert not AlbumShare.objects.filter(id=share.id).exists()

    def test_shared_with_me_endpoint(self, api_client):
        """Cenário: Listagem de álbuns compartilhados com o usuário autenticado."""
        api_client.force_authenticate(user=self.authorized_viewer)
        response = api_client.get("/api/v1/albums/shared-with-me/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == str(self.album.id)
        assert data[0]["owner_email"] == self.owner.email
        assert data[0]["user_invite_type"] == "EMAIL"

    def test_album_list_includes_shared_albums_for_invited_user(self, api_client):
        """Cenário: Convidado acessa /api/v1/albums/ e o álbum compartilhado aparece na sua lista."""
        api_client.force_authenticate(user=self.authorized_viewer)

        # 1. Sem filtro -> inclui álbum compartilhado
        res = api_client.get("/api/v1/albums/")
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert len(data) == 1
        assert data[0]["id"] == str(self.album.id)
        assert data[0]["is_owner"] is False
        assert data[0]["owner_email"] == self.owner.email

        # 2. Com only_owned=true -> lista apenas próprios (deve retornar vazio para o convidado)
        res_owned = api_client.get("/api/v1/albums/?only_owned=true")
        assert res_owned.status_code == status.HTTP_200_OK
        assert len(res_owned.json()) == 0

