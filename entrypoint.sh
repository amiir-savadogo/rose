#!/bin/sh
set -e

echo "Attente de la base de données PostgreSQL..."
python << PYEOF
import os
import time
import psycopg2

for _ in range(30):
    try:
        psycopg2.connect(
            dbname=os.environ.get("POSTGRES_DB", "rose"),
            user=os.environ.get("POSTGRES_USER", "rose"),
            password=os.environ.get("POSTGRES_PASSWORD", "rose"),
            host=os.environ.get("POSTGRES_HOST", "db"),
            port=os.environ.get("POSTGRES_PORT", "5432"),
        ).close()
        break
    except psycopg2.OperationalError:
        time.sleep(1)
else:
    raise SystemExit("La base de données n'a pas répondu à temps.")
PYEOF
echo "Base de données disponible."

python manage.py migrate --noinput
python manage.py collectstatic --noinput

python << PYEOF
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

User = get_user_model()
username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")

if User.objects.filter(username=username).exists():
    print(f"Superuser {username} existe déjà, aucune création nécessaire.")
elif not password:
    # Jamais de mot de passe par défaut : un compte administrateur connu de tous serait
    # une porte ouverte sur toute la plateforme.
    print(
        "DJANGO_SUPERUSER_PASSWORD non défini : aucun superutilisateur créé automatiquement. "
        "Créez-le avec : python manage.py createsuperuser"
    )
else:
    try:
        validate_password(password)
    except ValidationError as erreur:
        print("DJANGO_SUPERUSER_PASSWORD refusé (" + " ".join(erreur.messages) + "). Aucun superutilisateur créé.")
    else:
        print(f"Création du superuser {username}...")
        User.objects.create_superuser(
            username=username,
            email=os.environ.get("DJANGO_SUPERUSER_EMAIL", ""),
            password=password,
        )
PYEOF

exec "$@"
