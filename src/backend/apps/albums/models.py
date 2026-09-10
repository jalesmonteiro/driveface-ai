from typing import TYPE_CHECKING, Any
import secrets
import uuid
from django.conf import settings
from django.db import models


def generate_share_token():
    return f"sh_{secrets.token_hex(12)}"


class Album(models.Model):
    if TYPE_CHECKING:
        shares: models.Manager[Any]
        clusters: models.Manager[Any]
        photos: models.Manager[Any]
        jobs: models.Manager[Any]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_albums",
    )
    google_drive_folder_id = models.CharField(max_length=255)
    folder_name = models.CharField(max_length=255)
    share_token = models.CharField(
        max_length=64,
        unique=True,
        default=generate_share_token,
        db_index=True,
    )
    is_share_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Álbum"
        verbose_name_plural = "Álbuns"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.folder_name} ({self.id})"


class AlbumShare(models.Model):
    class Role(models.TextChoices):
        VIEWER = "VIEWER", "Viewer"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    album = models.ForeignKey(
        Album,
        on_delete=models.CASCADE,
        related_name="shares",
    )
    invited_email = models.EmailField(db_index=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.VIEWER,
    )
    invited_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Compartilhamento de Álbum"
        verbose_name_plural = "Compartilhamentos de Álbuns"
        unique_together = ("album", "invited_email")

    def __str__(self):
        return f"{self.invited_email} -> {self.album.folder_name}"


class Job(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendente"
        PROCESSING = "PROCESSING", "Processando"
        COMPLETED = "COMPLETED", "Concluído"
        FAILED = "FAILED", "Falhou"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    album = models.ForeignKey(
        Album,
        on_delete=models.CASCADE,
        related_name="jobs",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    total_images = models.PositiveIntegerField(default=0)
    processed_images = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Job de Processamento"
        verbose_name_plural = "Jobs de Processamento"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Job {self.id} [{self.status}]"
