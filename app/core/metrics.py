"""Métricas de la aplicación para Prometheus (patrón Application Metrics).

``configurar_metricas`` instrumenta todas las rutas (cantidad de peticiones por ruta,
método y código; latencia; tamaño) y publica ``GET /metrics``. Además se definen
métricas propias del módulo, que se ven en el tablero de Grafana
(monitoring/grafana/dashboards/materiales-api.json).
"""

from fastapi import FastAPI
from prometheus_client import Counter, Gauge, Histogram
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.events import EventoDominio

EVENTOS_NEGOCIO = Counter(
    "materiales_formulas_eventos_negocio_total",
    "Eventos de dominio publicados (operaciones de negocio exitosas).",
    ["evento"],
)
LLAMADAS_EXTERNAS = Counter(
    "materiales_formulas_llamadas_externas_total",
    "Llamadas a las APIs de otras células por resultado.",
    ["servicio", "resultado"],
)
DURACION_LLAMADAS_EXTERNAS = Histogram(
    "materiales_formulas_llamadas_externas_duracion_segundos",
    "Duración de las llamadas a las APIs de otras células.",
    ["servicio"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0),
)
CIRCUITO_ABIERTO = Gauge(
    "materiales_formulas_circuito_abierto",
    "1 si el circuit breaker del cliente está abierto; 0 si está cerrado o semiabierto.",
    ["servicio"],
)


def contar_evento(evento: EventoDominio) -> None:
    """Suscriptor del bus de eventos que cuenta cada evento de dominio."""
    EVENTOS_NEGOCIO.labels(evento=evento.nombre).inc()


def configurar_metricas(app: FastAPI) -> None:
    """Instrumenta la API y expone /metrics (excluido de la documentación OpenAPI)."""
    Instrumentator(
        should_group_status_codes=False,
        excluded_handlers=["/metrics", "/health"],
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
