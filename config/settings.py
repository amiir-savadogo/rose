"""
Configuration Django du projet Rose.

Toutes les valeurs sensibles ou dépendantes de l'environnement (secret key,
base de données, debug...) sont lues depuis des variables d'environnement,
définies via le fichier .env et injectées par docker-compose. Cela permet de
déployer la même image chez chaque institution cliente en changeant
uniquement le fichier .env.
"""
from pathlib import Path

from decouple import Csv, config
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = config("DJANGO_DEBUG", default=False, cast=bool)

_SECRET_KEY_DEV_PAR_DEFAUT = "dev-secret-key-a-changer-en-production"
SECRET_KEY = config("DJANGO_SECRET_KEY", default=_SECRET_KEY_DEV_PAR_DEFAUT)
if not DEBUG and SECRET_KEY == _SECRET_KEY_DEV_PAR_DEFAUT:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY doit être défini (variable d'environnement) en production — "
        "voir .env.example. Le logiciel refuse de démarrer avec la clé de développement "
        "par défaut hors de DEBUG=True, pour éviter qu'une installation client tourne "
        "avec une clé connue publiquement."
    )
ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Tiers
    "rest_framework",
    # Applications métier Rose
    "apps.accounts",
    "apps.risks",
    "apps.incidents",
    "apps.obligations",
    "apps.controles",
    "apps.comite",
    "apps.bibliotheque",
    "apps.audit",
    "apps.dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Rend l'utilisateur courant disponible pour le journal d'audit
    "apps.audit.middleware.CurrentUserMiddleware",
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
                "apps.accounts.context_processors.permissions_front",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("POSTGRES_DB", default="rose"),
        "USER": config("POSTGRES_USER", default="rose"),
        "PASSWORD": config("POSTGRES_PASSWORD", default="rose"),
        "HOST": config("POSTGRES_HOST", default="db"),
        "PORT": config("POSTGRES_PORT", default="5432"),
    }
}

AUTH_USER_MODEL = "accounts.User"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard:accueil"
LOGOUT_REDIRECT_URL = "login"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Ouagadougou"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

# Sécurité de base recommandée en production (activée automatiquement si DEBUG=False)
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    CSRF_COOKIE_SECURE = config("DJANGO_SECURE_COOKIES", default=True, cast=bool)
    SESSION_COOKIE_SECURE = config("DJANGO_SECURE_COOKIES", default=True, cast=bool)
