import uuid
from django.conf import settings
from django.db import models
from pgvector.django import VectorField
from albums.models import Album


class Identity(models.Model):
    """
    Identidade cadastrada pelo usuário com centróide médio ponderado normalizado.
    Isolamento estrito multi-tenant: WHERE user_id = request.user.id (Regra R_1).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="identities",
    )
    person_name = models.CharField("Nome da Pessoa", max_length=255, db_index=True)
    centroid_embedding = VectorField(dimensions=512)
    total_samples = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Identidade"
        verbose_name_plural = "Identidades"
        unique_together = ("user", "person_name")
        ordering = ["person_name"]

    def __str__(self):
        return f"{self.person_name} (User: {self.user.email})"


class FaceTemplate(models.Model):
    """
    Template biométrico facial (centróide 512-D L2) associado a uma identidade.
    Permite multi-template por pessoa (diferentes poses, iluminação, acessórios, ângulos).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identity = models.ForeignKey(
        Identity,
        on_delete=models.CASCADE,
        related_name="templates",
    )
    centroid_embedding = VectorField(dimensions=512)
    total_samples = models.PositiveIntegerField(default=1)
    notes = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Template Facial"
        verbose_name_plural = "Templates Faciais"
        ordering = ["-total_samples", "-created_at"]

    def __str__(self):
        return f"Template {self.id} ({self.total_samples} faces) - {self.identity.person_name}"


class Photo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    album = models.ForeignKey(
        Album,
        on_delete=models.CASCADE,
        related_name="photos",
    )
    google_file_id = models.CharField(max_length=255, db_index=True)
    filename = models.CharField(max_length=255)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    faces_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Foto"
        verbose_name_plural = "Fotos"
        unique_together = ("album", "google_file_id")

    def __str__(self):
        return f"{self.filename} ({self.google_file_id})"


class Cluster(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    album = models.ForeignKey(
        Album,
        on_delete=models.CASCADE,
        related_name="clusters",
    )
    identity = models.ForeignKey(
        Identity,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clusters",
    )
    label = models.CharField(max_length=255, default="Pessoa Desconhecida")
    avatar_crop_webp = models.TextField(
        "Avatar WebP (Base64)",
        blank=True,
        help_text="Miniatura 160x160 px em Base64 para exibição do avatar na interface.",
    )
    face_count = models.PositiveIntegerField(default=0)
    is_suggested = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cluster de Faces"
        verbose_name_plural = "Clusters de Faces"
        ordering = ["-face_count"]

    def __str__(self):
        return f"{self.label} ({self.face_count} faces)"


class Face(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    photo = models.ForeignKey(
        Photo,
        on_delete=models.CASCADE,
        related_name="detected_faces",
    )
    cluster = models.ForeignKey(
        Cluster,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="faces",
    )
    embedding = VectorField(dimensions=512)
    bbox_xmin = models.FloatField("BBox Xmin (normalizado 0-1)")
    bbox_ymin = models.FloatField("BBox Ymin (normalizado 0-1)")
    bbox_xmax = models.FloatField("BBox Xmax (normalizado 0-1)")
    bbox_ymax = models.FloatField("BBox Ymax (normalizado 0-1)")
    detection_confidence = models.FloatField("Confiança da Detecção")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Face Detectada"
        verbose_name_plural = "Faces Detectadas"

    def __str__(self):
        return f"Face {self.id} em {self.photo.filename} (conf: {self.detection_confidence:.2f})"
