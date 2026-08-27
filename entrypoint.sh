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
django.setup()
from django.contrib.auth import get_user_model

User = get_user_model()
username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")

if not User.objects.filter(username=username).exists():
    print(f"Création du superuser {username}...")
    User.objects.create_superuser(
        username=username,
        email=os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@example.com"),
        password=os.environ.get("DJANGO_SUPERUSER_PASSWORD", "motdepassefort")
    )
else:
    print(f"Superuser {username} existe déjà, aucune création nécessaire.")
PYEOF


exec "$@"
