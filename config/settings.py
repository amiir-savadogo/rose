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
if not DEBUG and (
    SECRET_KEY == _SECRET_KEY_DEV_PAR_DEFAUT
    or SECRET_KEY.startswith("remplacez")
    or len(SECRET_KEY) < 32
):
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY doit être une vraie valeur aléatoire d'au moins 32 caractères "
        "(variable d'environnement) en production — voir .env.example. Le logiciel refuse "
        "de démarrer avec la clé de développement, une valeur d'exemple ou une clé trop "
        "courte hors de DEBUG=True, pour éviter qu'une installation client tourne avec une "
        "clé connue publiquement."
    )

# Hôtes autorisés et origines CSRF de confiance : jamais de joker sur un domaine partagé.
# Sur Render, RENDER_EXTERNAL_HOSTNAME (fourni automatiquement) désigne le service exact.
ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())
CSRF_TRUSTED_ORIGINS = config("DJANGO_CSRF_TRUSTED_ORIGINS", default="", cast=Csv())
_hote_render = config("RENDER_EXTERNAL_HOSTNAME", default="")
if _hote_render:
    ALLOWED_HOSTS = [*ALLOWED_HOSTS, _hote_render]
    CSRF_TRUSTED_ORIGINS = [*CSRF_TRUSTED_ORIGINS, f"https://{_hote_render}"]

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

# --- Sécurité ---------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
# Durée de session : 8 h par défaut (journée de travail), ajustable par institution.
SESSION_COOKIE_AGE = config("DJANGO_SESSION_AGE", default=8 * 3600, cast=int)
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Derrière un reverse proxy / répartiteur de charge qui termine le TLS (Render, nginx...),
# le schéma réel est lu dans X-Forwarded-Proto. À désactiver (DJANGO_BEHIND_PROXY=False)
# si l'application est exposée directement, sans proxy de confiance devant elle.
BEHIND_PROXY = config("DJANGO_BEHIND_PROXY", default=True, cast=bool)
# Nombre de proxys de confiance devant l'application (1 = Render, nginx...). L'adresse IP du
# client est lue dans X-Forwarded-For en comptant depuis la DROITE, car les valeurs de gauche
# sont fournies par le client et donc falsifiables.
TRUSTED_PROXY_COUNT = config("DJANGO_TRUSTED_PROXY_COUNT", default=1, cast=int)
if BEHIND_PROXY:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

if not DEBUG:
    CSRF_COOKIE_SECURE = config("DJANGO_SECURE_COOKIES", default=True, cast=bool)
    SESSION_COOKIE_SECURE = config("DJANGO_SECURE_COOKIES", default=True, cast=bool)
    # Redirection HTTP -> HTTPS et HSTS : à activer dès que le site est servi en HTTPS.
    SECURE_SSL_REDIRECT = config("DJANGO_SSL_REDIRECT", default=False, cast=bool)
    SECURE_HSTS_SECONDS = config("DJANGO_HSTS_SECONDS", default=0, cast=int)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
    # La sonde de santé de la plateforme d'hébergement ne doit pas être redirigée.
    SECURE_REDIRECT_EXEMPT = [r"^healthz/$"]

# --- Fichiers téléversés (preuves, pièces jointes, documents) -----------------------
# Liste blanche d'extensions et taille maximale : voir config/fichiers.py.
# Les fichiers ne sont JAMAIS servis directement par l'application web : ils passent
# par des vues authentifiées (téléchargement en pièce jointe, contrôle de périmètre).
UPLOAD_MAX_BYTES = config("DJANGO_UPLOAD_MAX_MB", default=10, cast=int) * 1024 * 1024
UPLOAD_EXTENSIONS_AUTORISEES = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods", ".odp",
    ".txt", ".csv", ".png", ".jpg", ".jpeg", ".zip",
}

# --- Protection contre le brute-force de la page de connexion --------------------------
LOGIN_MAX_ECHECS_PAR_IDENTIFIANT = config("DJANGO_LOGIN_MAX_ECHECS", default=5, cast=int)
LOGIN_MAX_ECHECS_PAR_IP = config("DJANGO_LOGIN_MAX_ECHECS_IP", default=20, cast=int)
LOGIN_FENETRE_MINUTES = config("DJANGO_LOGIN_FENETRE_MIN", default=15, cast=int)
