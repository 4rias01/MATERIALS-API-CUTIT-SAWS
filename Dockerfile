# Imagen de la API Materiales y Fórmulas: FastAPI con Uvicorn en el puerto 8000.
# Al iniciar aplica las migraciones pendientes (Alembic) y arranca la API.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# La API corre con un usuario sin privilegios.
RUN groupadd --system app && useradd --system --gid app --home-dir /app --no-create-home app

# Primero las dependencias: esta capa se reutiliza mientras requirements.txt no cambie.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 755 /usr/local/bin/entrypoint.sh

USER app
EXPOSE 8000

# /health responde 200 si la API alcanza su base de datos (503 si no).
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"]

ENTRYPOINT ["entrypoint.sh"]
