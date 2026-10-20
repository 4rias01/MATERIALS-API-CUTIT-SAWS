"""Punto de entrada de la API (``uvicorn app.main:app``).

Crea la aplicación FastAPI y, en el arranque (lifespan), los recursos compartidos que
viven mientras corre el proceso (patrones Object Pool e inyección con instancias
compartidas):

* El motor de SQLAlchemy con su pool de conexiones y la fábrica de sesiones.
* Un único ``httpx.AsyncClient`` (reutiliza conexiones) y los clientes de Inventario y
  Patent Sweep, cada uno con su circuit breaker.
* El bus de eventos de dominio con sus suscriptores (log y métricas).

También registra el middleware de traceId, el manejador global de excepciones, los
routers, las métricas (/metrics) y la documentación OpenAPI (/docs).
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.core.config import Configuracion, obtener_configuracion
from app.core.events import BusEventos, registrar_evento_en_log
from app.core.logging import configurar_logging
from app.core.metrics import configurar_metricas, contar_evento
from app.core.openapi import DESCRIPCION, ETIQUETAS, ajustar_openapi
from app.data_access.clients import CircuitBreaker, InventarioClient, PatentSweepClient
from app.data_access.clients.inventario_client import SERVICIO as SERVICIO_INVENTARIO
from app.data_access.clients.patent_sweep_client import SERVICIO as SERVICIO_PATENT_SWEEP
from app.data_access.database import crear_fabrica_sesiones, crear_motor
from app.presentation.exception_handlers import registrar_manejadores
from app.presentation.middleware import TraceIdMiddleware
from app.presentation.routers import evaluacion_patente, formulas, health, materiales

logger = logging.getLogger("app")


def crear_bus_eventos() -> BusEventos:
    bus = BusEventos()
    bus.suscribir(registrar_evento_en_log)
    bus.suscribir(contar_evento)
    return bus


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
    config: Configuracion = app.state.config
    motor = crear_motor(config)
    http = httpx.AsyncClient(
        timeout=httpx.Timeout(config.http_timeout_s),
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )
    app.state.motor = motor
    app.state.fabrica_sesiones = crear_fabrica_sesiones(motor)
    app.state.cliente_http = http
    app.state.cliente_inventario = InventarioClient(
        http, config, CircuitBreaker(SERVICIO_INVENTARIO, config.cb_umbral_fallos, config.cb_tiempo_abierto_s)
    )
    app.state.cliente_patent_sweep = PatentSweepClient(
        http, config, CircuitBreaker(SERVICIO_PATENT_SWEEP, config.cb_umbral_fallos, config.cb_tiempo_abierto_s)
    )
    app.state.bus_eventos = crear_bus_eventos()
    logger.info(
        "API iniciada",
        extra={"version": config.app_version, "entorno": config.entorno, "inventarioUrl": config.inventario_url,
               "patentSweepUrl": config.patent_sweep_url},
    )
    try:
        yield
    finally:
        await http.aclose()
        await motor.dispose()
        logger.info("API detenida")


def crear_app(config: Configuracion | None = None) -> FastAPI:
    config = config or obtener_configuracion()
    configurar_logging(config.log_nivel)

    app = FastAPI(
        title=config.app_nombre,
        version=config.app_version,
        description=DESCRIPCION,
        openapi_tags=ETIQUETAS,
        lifespan=ciclo_de_vida,
        docs_url="/docs" if config.docs_habilitada else None,
        redoc_url="/redoc" if config.docs_habilitada else None,
        openapi_url="/openapi.json" if config.docs_habilitada else None,
    )
    app.state.config = config

    app.add_middleware(TraceIdMiddleware)
    registrar_manejadores(app)

    app.include_router(health.router)
    app.include_router(materiales.router)
    app.include_router(formulas.router)
    app.include_router(evaluacion_patente.router)

    configurar_metricas(app)
    ajustar_openapi(app)
    return app


app = crear_app()
