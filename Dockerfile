FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dépendances système nécessaires à psycopg2 et à la compilation de paquets Python
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# Utilisateur applicatif sans privilèges : l'application ne tourne jamais en root.
RUN groupadd --system --gid 1000 rose \
    && useradd --system --uid 1000 --gid rose --home-dir /app --shell /usr/sbin/nologin rose

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=rose:rose . .

COPY entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh \
    && mkdir -p /app/media /app/staticfiles \
    && chown -R rose:rose /app/media /app/staticfiles

USER rose

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
# Le nombre de workers se règle par la variable d'environnement WEB_CONCURRENCY (défaut : 3).
ENV WEB_CONCURRENCY=3
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--timeout", "60", "--access-logfile", "-"]
