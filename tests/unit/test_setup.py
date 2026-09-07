from django.conf import settings
from django.apps import apps


def test_installed_apps():
    """Verifica se todos os apps obrigatórios do DriveFace AI estão registrados."""
    expected_apps = [
        "authentication",
        "google_integration",
        "albums",
        "faces",
        "export",
        "vision_pipeline",
        "rest_framework",
        "rest_framework_simplejwt",
        "corsheaders",
    ]
    for app_name in expected_apps:
        assert apps.is_installed(app_name), f"App {app_name} não está instalado."


def test_custom_user_model():
    """Verifica se o AUTH_USER_MODEL está configurado para authentication.User."""
    assert settings.AUTH_USER_MODEL == "authentication.User"


def test_argon2_hasher_configured():
    """Verifica se Argon2 é o primeiro hasher da lista."""
    assert settings.PASSWORD_HASHERS[0] == "django.contrib.auth.hashers.Argon2PasswordHasher"


def test_mathematical_thresholds():
    """Verifica se os limiares matemáticos R_3, R_4 e R_5 estão definidos."""
    assert settings.FACE_DETECTION_CONFIDENCE_THRESHOLD == 0.80
    assert settings.CLUSTERING_COSINE_EPS == 0.40
    assert settings.IDENTITY_SUGGESTION_THRESHOLD == 0.35
