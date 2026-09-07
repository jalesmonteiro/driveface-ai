"""Serviços de integração com o Google Drive API v3."""
import io
import logging

logger = logging.getLogger(__name__)


class GoogleDriveService:
    """Cliente para operações de leitura e streaming de imagens do Google Drive."""

    def __init__(self, credentials=None):
        self.credentials = credentials

    def list_images(self, folder_id: str):
        """Lista imagens de uma pasta do Google Drive."""
        return []

    def download_image_stream(self, file_id: str) -> io.BytesIO:
        """Download em memória volátil de arquivo do Google Drive."""
        return io.BytesIO()
