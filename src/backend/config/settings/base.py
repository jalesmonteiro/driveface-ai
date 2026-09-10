import os
import sys
from datetime import timedelta
from pathlib import Path
import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# BASE_DIR aponta para src/backend
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# PROJECT_ROOT aponta para a raiz do repositório
PROJECT_ROOT = BASE_DIR.parent.parent
APPS_DIR = BASE_DIR / "apps"

for _path in (str(BASE_DIR), str(APPS_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_SECRET_KEY=(str, "insecure-default-change-me-in-production"),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    DATABASE_URL=(
        str,
        "postgres://driveface_admin:driveface_secure_pass@localhost:5432/driveface_db",
    ),
    REDIS_HOST=(str, "localhost"),
    REDIS_PORT=(int, 6379),
    CELERY_BROKER_URL=(str, "redis://localhost:6379/0"),
    CELERY_RESULT_BACKEND=(str, "redis://localhost:6379/1"),
    GOOGLE_CLIENT_ID=(str, ""),
    GOOGLE_CLIENT_SECRET=(str, ""),
    GOOGLE_REDIRECT_URI=(
        str,
        "http://localhost:8000/api/v1/google/oauth/callback/",
    ),
    DEVICE=(str, "cpu"),
    FACE_DETECTION_MODEL=(str, "buffalo_l"),
    FACE_DETECTION_CONFIDENCE_THRESHOLD=(float, 0.80),
    CLUSTERING_COSINE_EPS=(float, 0.40),
    IDENTITY_SUGGESTION_THRESHOLD=(float, 0.35),
)

# Ler .env se existir na raiz do projeto
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
]

LOCAL_APPS = [
    "authentication.apps.AuthenticationConfig",
    "google_integration.apps.GoogleIntegrationConfig",
    "albums.apps.AlbumsConfig",
    "faces.apps.FacesConfig",
    "export.apps.ExportConfig",
    "vision_pipeline.apps.VisionPipelineConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database via dj-database-url / django-environ
DATABASES = {
    "default": env.db("DATABASE_URL", default="postgres://driveface_admin:driveface_secure_pass@localhost:5432/driveface_db")
}

# Custom User Model
AUTH_USER_MODEL = "authentication.User"

# Hashing de senhas com Argon2id prioritário
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
    "EXCEPTION_HANDLER": "config.exceptions.custom_exception_handler",
}

# SimpleJWT
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Celery Configuration
CELERY_BROKER_URL = env("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# Google Drive OAuth2
GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = env("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = env("GOOGLE_REDIRECT_URI")

# Mathematical & Deep Learning Thresholds (R_3, R_4, R_5)
DEVICE = env("DEVICE")
FACE_DETECTION_MODEL = env("FACE_DETECTION_MODEL")
FACE_DETECTION_CONFIDENCE_THRESHOLD = env("FACE_DETECTION_CONFIDENCE_THRESHOLD")
CLUSTERING_COSINE_EPS = env("CLUSTERING_COSINE_EPS")
IDENTITY_SUGGESTION_THRESHOLD = env("IDENTITY_SUGGESTION_THRESHOLD")
