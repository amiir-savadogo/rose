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

exec "$@"
