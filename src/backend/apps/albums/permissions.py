from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied


class IsAlbumOwner(permissions.BasePermission):
    """Permite acesso total apenas se request.user for o proprietário do álbum."""

    def has_object_permission(self, request, view, obj):
        owner = getattr(obj, "owner", None)
        if owner is None and hasattr(obj, "album"):
            owner = obj.album.owner
        return bool(request.user and request.user.is_authenticated and owner == request.user)


class IsAlbumViewerOrOwner(permissions.BasePermission):
    """
    Permite acesso se request.user for proprietário ou se request.user.email
    estiver na whitelist de AlbumShare com status ativo (Regra R_6).
    Se o e-mail estiver explicitamente bloqueado (Blacklist), nega acesso.
    """

    message = "O e-mail autenticado não possui autorização para visualizar este álbum. Solicite acesso ao proprietário."
    code = "ACL_FORBIDDEN"

    def has_object_permission(self, request, view, obj):
        album = obj if hasattr(obj, "shares") else getattr(obj, "album", None)
        if not album:
            return False

        if not request.user or not request.user.is_authenticated:
            return False

        if request.user == album.owner:
            return True

        if not album.is_share_active:
            self.message = "O compartilhamento deste álbum está temporariamente desativado pelo proprietário."
            return False

        user_share = album.shares.filter(invited_email__iexact=request.user.email).first()
        if not user_share:
            return False

        if user_share.status == "BLOCKED":
            self.message = "Seu acesso a este álbum foi bloqueado pelo proprietário."
            return False

        return user_share.status == "ACTIVE"
