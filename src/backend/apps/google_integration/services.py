"""Serviços de integração com o Google Drive API v3."""
import io
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class GoogleDriveService:
    """Cliente para operações de leitura, streaming e cópia de imagens do Google Drive v3."""

    def __init__(self, user=None, access_token=None):
        self.user = user
        self.access_token = access_token
        if user and not access_token:
            token_obj = getattr(user, "google_token", None)
            if token_obj:
                self.access_token = token_obj.encrypted_access_token

    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
        }

    def _refresh_token_if_needed(self):
        if not self.user:
            return False
        token_obj = getattr(self.user, "google_token", None)
        if not token_obj or not token_obj.encrypted_refresh_token:
            return False
        refresh_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": getattr(settings, "GOOGLE_CLIENT_ID", ""),
            "client_secret": getattr(settings, "GOOGLE_CLIENT_SECRET", ""),
            "refresh_token": token_obj.encrypted_refresh_token,
            "grant_type": "refresh_token",
        }
        try:
            res = requests.post(refresh_url, data=data, timeout=10)
            if res.ok:
                new_token = res.json().get("access_token")
                if new_token:
                    token_obj.encrypted_access_token = new_token
                    token_obj.save(update_fields=["encrypted_access_token"])
                    self.access_token = new_token
                    return True
        except Exception as exc:
            logger.error(f"Erro ao renovar token Google: {exc}")
        return False

    def _request(self, method, url, **kwargs):
        headers = kwargs.pop("headers", {})
        headers.update(self._get_headers())
        res = requests.request(method, url, headers=headers, **kwargs)
        if res.status_code == 401 and self._refresh_token_if_needed():
            headers["Authorization"] = f"Bearer {self.access_token}"
            res = requests.request(method, url, headers=headers, **kwargs)
        return res

    def list_images(self, folder_id: str):
        """Lista arquivos de imagem de uma pasta do Google Drive."""
        if not self.access_token:
            return []

        q = f"'{folder_id}' in parents and mimeType contains 'image/' and trashed = false"
        params = {
            "q": q,
            "pageSize": 100,
            "fields": "files(id, name, mimeType, thumbnailLink, webViewLink, webContentLink, imageMediaMetadata)",
            "orderBy": "name",
        }
        res = self._request("GET", "https://www.googleapis.com/drive/v3/files", params=params, timeout=15)
        if res.ok:
            return res.json().get("files", [])
        logger.error(f"Falha ao listar imagens da pasta {folder_id}: {res.status_code} {res.text}")
        return []

    def download_image_stream(self, file_id: str) -> io.BytesIO:
        """Download em memória volátil de arquivo do Google Drive."""
        stream = io.BytesIO()
        if not self.access_token:
            return stream

        url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
        res = self._request("GET", url, stream=True, timeout=30)
        if res.ok:
            for chunk in res.iter_content(chunk_size=65536):
                if chunk:
                    stream.write(chunk)
            stream.seek(0)
        else:
            logger.error(f"Falha ao baixar arquivo {file_id} do Drive: {res.status_code}")
        return stream

    def create_drive_folder(self, folder_name: str, parent_id: str = None) -> dict:
        """Cria uma nova pasta no Google Drive do usuário."""
        if not self.access_token:
            return {}

        metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            metadata["parents"] = [parent_id]

        res = self._request("POST", "https://www.googleapis.com/drive/v3/files", json=metadata, timeout=15)
        if res.ok:
            return res.json()
        logger.error(f"Falha ao criar pasta {folder_name}: {res.status_code} {res.text}")
        return {}

    def copy_file_to_folder(self, file_id: str, target_folder_id: str, new_name: str = None) -> dict:
        """Copia um arquivo no Google Drive para uma pasta de destino."""
        if not self.access_token:
            return {}

        metadata = {
            "parents": [target_folder_id],
        }
        if new_name:
            metadata["name"] = new_name

        url = f"https://www.googleapis.com/drive/v3/files/{file_id}/copy"
        res = self._request("POST", url, json=metadata, timeout=15)
        if res.ok:
            return res.json()
        logger.error(f"Falha ao copiar arquivo {file_id}: {res.status_code} {res.text}")
        return {}

    def get_or_create_thumbnails_folder(self) -> str:
        """Localiza ou cria a pasta DriveFace_Miniaturas no Drive do usuário."""
        if not self.access_token:
            return ""

        q = "name = 'DriveFace_Miniaturas' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        res = self._request("GET", "https://www.googleapis.com/drive/v3/files", params={"q": q}, timeout=10)
        if res.ok:
            files = res.json().get("files", [])
            if files:
                return files[0]["id"]

        new_folder = self.create_drive_folder("DriveFace_Miniaturas")
        return new_folder.get("id", "")

