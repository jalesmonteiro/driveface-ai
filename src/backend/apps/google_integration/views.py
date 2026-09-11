import urllib.parse
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from .models import GoogleToken

User = get_user_model()


class GoogleOAuthInitView(APIView):
    """Gera URL de consentimento OAuth2 do Google ou redireciona o navegador."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        client_id = getattr(settings, "GOOGLE_CLIENT_ID", "")
        redirect_uri = getattr(
            settings,
            "GOOGLE_REDIRECT_URI",
            "http://localhost:8000/api/v1/google/oauth/callback/",
        )

        scopes = [
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/drive.file",
        ]

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "access_type": "offline",
            "prompt": "consent",
        }
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

        if "text/html" in request.headers.get("Accept", ""):
            return redirect(auth_url)

        return Response({"auth_url": auth_url})


class GoogleOAuthCallbackView(APIView):
    """
    Callback do Google OAuth2.
    Troca o code por tokens, obtém nome, email e foto do perfil,
    cadastra/autentica o usuário no banco PostgreSQL e redireciona com tokens JWT.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        code = request.GET.get("code")
        error = request.GET.get("error")

        if error or not code:
            err_msg = error or "no_code_provided"
            return redirect(f"/?auth_error={urllib.parse.quote(err_msg)}")

        # 1. Troca o código pelo access_token no Google
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "code": code,
            "client_id": getattr(settings, "GOOGLE_CLIENT_ID", ""),
            "client_secret": getattr(settings, "GOOGLE_CLIENT_SECRET", ""),
            "redirect_uri": getattr(
                settings,
                "GOOGLE_REDIRECT_URI",
                "http://localhost:8000/api/v1/google/oauth/callback/",
            ),
            "grant_type": "authorization_code",
        }

        try:
            token_res = requests.post(token_url, data=token_data, timeout=10)
            if not token_res.ok:
                return redirect("/?auth_error=google_token_exchange_failed")

            token_json = token_res.json()
            google_access_token = token_json.get("access_token")
            google_refresh_token = token_json.get("refresh_token")

            # 2. Busca informações do perfil do usuário na Google API
            userinfo_res = requests.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {google_access_token}"},
                timeout=10,
            )
            if not userinfo_res.ok:
                return redirect("/?auth_error=google_userinfo_failed")

            userinfo = userinfo_res.json()
            email = userinfo.get("email")
            name = userinfo.get("name", "")
            picture = userinfo.get("picture", "")

            if not email:
                return redirect("/?auth_error=google_email_missing")

            # 3. Cria ou localiza o usuário no banco PostgreSQL
            user, created = User.objects.get_or_create(
                email=email,
                defaults={"full_name": name},
            )
            if not created and name and user.full_name != name:
                user.full_name = name
                user.save(update_fields=["full_name"])

            # 4. Salva ou atualiza os tokens do Google no modelo GoogleToken
            GoogleToken.objects.update_or_create(
                user=user,
                defaults={
                    "encrypted_access_token": google_access_token or "",
                    "encrypted_refresh_token": google_refresh_token or "",
                },
            )

            # 5. Emite os tokens JWT do sistema
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            # 6. Redireciona para o frontend com os dados autenticados
            redirect_params = urllib.parse.urlencode(
                {
                    "auth_success": "true",
                    "token": access_token,
                    "refresh_token": refresh_token,
                    "email": email,
                    "name": name,
                    "picture": picture,
                }
            )
            return redirect(f"/?{redirect_params}")

        except Exception as exc:
            return redirect(f"/?auth_error={urllib.parse.quote(str(exc))}")


class GoogleDriveFoldersView(APIView):
    """
    Lista pastas do Google Drive do usuário autenticado para seleção no Picker modal.
    Suporta abas 'my_drive', 'recent', 'shared', 'starred' e busca por nome ou URL.
    """
    permission_classes = [permissions.IsAuthenticated]

    def _refresh_access_token(self, google_token):
        if not google_token.encrypted_refresh_token:
            return None
        refresh_url = "https://oauth2.googleapis.com/token"
        refresh_data = {
            "client_id": getattr(settings, "GOOGLE_CLIENT_ID", ""),
            "client_secret": getattr(settings, "GOOGLE_CLIENT_SECRET", ""),
            "refresh_token": google_token.encrypted_refresh_token,
            "grant_type": "refresh_token",
        }
        try:
            res = requests.post(refresh_url, data=refresh_data, timeout=10)
            if res.ok:
                new_token = res.json().get("access_token")
                if new_token:
                    google_token.encrypted_access_token = new_token
                    google_token.save(update_fields=["encrypted_access_token"])
                    return new_token
        except Exception:
            pass
        return None

    def get(self, request):
        user = request.user
        google_token = getattr(user, "google_token", None)

        parent_id = request.query_params.get("parent", "root")
        tab = request.query_params.get("tab", "my_drive")
        search = request.query_params.get("search", "").strip()

        # Se for usuário mock ou não tiver token do Google, retorna pastas de demonstração
        if not google_token or not google_token.encrypted_access_token:
            mock_folders = [
                {"id": "demo_folder_1", "name": "Formatura Turma 2026", "modifiedTime": "2026-09-08T15:30:00Z", "shared": False},
                {"id": "demo_folder_2", "name": "Aniversário Beatriz 15 Anos", "modifiedTime": "2026-09-05T18:00:00Z", "shared": False},
                {"id": "demo_folder_3", "name": "Viagem Fernando de Noronha", "modifiedTime": "2026-08-20T12:00:00Z", "shared": True},
                {"id": "demo_folder_4", "name": "Casamento Mariana e Lucas", "modifiedTime": "2026-08-10T10:15:00Z", "shared": True},
            ]
            if search:
                mock_folders = [f for f in mock_folders if search.lower() in f["name"].lower()]
            return Response({
                "source": "demo",
                "parent": parent_id,
                "folders": mock_folders,
            })

        import re
        url_match = re.search(r"folders/([a-zA-Z0-9_-]+)", search)
        direct_folder_id = url_match.group(1) if url_match else None

        access_token = google_token.encrypted_access_token

        def query_drive_api(token):
            headers = {"Authorization": f"Bearer {token}"}
            
            if direct_folder_id:
                direct_url = f"https://www.googleapis.com/drive/v3/files/{direct_folder_id}?fields=id,name,mimeType,modifiedTime,shared"
                return requests.get(direct_url, headers=headers, timeout=10)

            q_parts = [
                "mimeType = 'application/vnd.google-apps.folder'",
                "trashed = false",
            ]

            if tab == "shared":
                q_parts.append("sharedWithMe = true")
            elif tab == "starred":
                q_parts.append("starred = true")
            elif tab == "recent":
                pass
            else:
                q_parts.append(f"'{parent_id}' in parents")

            if search and not direct_folder_id:
                safe_search = search.replace("'", "\\'")
                q_parts.append(f"name contains '{safe_search}'")

            params = {
                "q": " and ".join(q_parts),
                "pageSize": 50,
                "fields": "files(id, name, mimeType, modifiedTime, shared, iconLink, webViewLink)",
            }
            if tab == "recent":
                params["orderBy"] = "viewedByMeTime desc, modifiedTime desc"
            else:
                params["orderBy"] = "folder, name"

            return requests.get(
                "https://www.googleapis.com/drive/v3/files",
                headers=headers,
                params=params,
                timeout=10,
            )

        res = query_drive_api(access_token)

        if res.status_code == 401:
            new_token = self._refresh_access_token(google_token)
            if new_token:
                res = query_drive_api(new_token)

        if not res.ok:
            return Response(
                {"error": "Falha ao consultar o Google Drive", "details": res.text},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        data = res.json()
        if direct_folder_id:
            folders = [data] if data.get("mimeType") == "application/vnd.google-apps.folder" else []
        else:
            folders = data.get("files", [])

        parent_info = None
        if parent_id and parent_id != "root":
            try:
                parent_res = requests.get(
                    f"https://www.googleapis.com/drive/v3/files/{parent_id}?fields=id,name,parents",
                    headers={"Authorization": f"Bearer {google_token.encrypted_access_token}"},
                    timeout=5,
                )
                if parent_res.ok:
                    parent_info = parent_res.json()
            except Exception:
                pass

        return Response({
            "source": "google_drive",
            "parent": parent_id,
            "parent_info": parent_info,
            "folders": folders,
        })

