import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

User = get_user_model()


@pytest.mark.django_db
class TestAuthentication:
    register_url = "/api/v1/auth/register/"
    token_url = "/api/v1/auth/token/"
    refresh_url = "/api/v1/auth/token/refresh/"
    me_url = "/api/v1/auth/me/"

    def test_user_registration_success(self, api_client):
        """Valida cadastro de usuário com sucesso e hashing Argon2id."""
        payload = {
            "email": "jales@driveface.ai",
            "password": "StrongPassword123!#",
            "full_name": "Jales Monteiro",
        }
        response = api_client.post(self.register_url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == "jales@driveface.ai"
        assert data["full_name"] == "Jales Monteiro"
        assert "id" in data
        assert "password" not in data

        user = User.objects.get(email="jales@driveface.ai")
        assert user.check_password("StrongPassword123!#")
        assert user.password.startswith("argon2"), "A senha deve ser criptografada com Argon2id"

    def test_user_registration_duplicate_email(self, api_client):
        """Valida que o sistema rejeita e-mails duplicados."""
        User.objects.create_user(
            email="duplicado@driveface.ai",
            password="Password123!",
            full_name="Usuario Um",
        )
        payload = {
            "email": "duplicado@driveface.ai",
            "password": "AnotherPassword456!",
            "full_name": "Usuario Dois",
        }
        response = api_client.post(self.register_url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.json()

    def test_jwt_token_obtain_and_refresh(self, api_client):
        """Valida emissão e rotação de tokens JWT (access e refresh)."""
        user = User.objects.create_user(
            email="token_test@driveface.ai",
            password="SecurePassword999!",
            full_name="Token User",
        )

        # Obtenção do par de tokens
        payload = {
            "email": "token_test@driveface.ai",
            "password": "SecurePassword999!",
        }
        response = api_client.post(self.token_url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access" in data
        assert "refresh" in data

        access_token = data["access"]
        refresh_token = data["refresh"]

        # Rotação de token
        refresh_response = api_client.post(
            self.refresh_url, {"refresh": refresh_token}, format="json"
        )
        assert refresh_response.status_code == status.HTTP_200_OK
        assert "access" in refresh_response.json()

        # Acesso a endpoint autenticado com Bearer token
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        me_response = api_client.get(self.me_url)
        assert me_response.status_code == status.HTTP_200_OK
        assert me_response.json()["email"] == user.email

    def test_unauthorized_access(self, api_client):
        """Valida retorno 401 Unauthorized para requisições sem token válido."""
        response = api_client.get(self.me_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
