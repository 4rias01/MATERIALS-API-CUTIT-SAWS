#!/bin/sh
# Aplica las migraciones pendientes y arranca la API.
# Reintenta las migraciones mientras PostgreSQL termina de iniciar (por ejemplo, después de
# reiniciar la EC2, cuando Docker levanta los contenedores sin esperar a la base de datos).
set -e

intentos=${MIGRACION_INTENTOS:-10}
espera=${MIGRACION_ESPERA_S:-3}
n=1
until alembic upgrade head; do
    if [ "$n" -ge "$intentos" ]; then
        echo "No se pudieron aplicar las migraciones después de $intentos intentos" >&2
        exit 1
    fi
    echo "La base de datos aún no responde (intento $n de $intentos); nuevo intento en ${espera}s" >&2
    n=$((n + 1))
    sleep "$espera"
done

# Un solo proceso: las métricas de Prometheus viven en la memoria del proceso.
# El log de acceso lo escribe el middleware de traceId (en JSON), no Uvicorn.
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log
