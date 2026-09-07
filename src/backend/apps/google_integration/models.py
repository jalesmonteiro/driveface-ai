import uuid
from django.conf import settings
from django.db import models


class GoogleToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="google_token",
    )
    encrypted_access_token = models.TextField("Access Token Criptografado")
    encrypted_refresh_token = models.TextField(
        "Refresh Token Criptografado", blank=True, null=True
    )
    token_expiry = models.DateTimeField("Expiração do Token", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Token Google"
        verbose_name_plural = "Tokens Google"

    def __str__(self):
        return f"GoogleToken({self.user.email})"
