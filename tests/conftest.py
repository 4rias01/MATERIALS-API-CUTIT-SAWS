"""Configuración común de las pruebas.

* Pruebas unitarias (tests/unit): no necesitan base de datos ni APIs externas.
* Pruebas de integración (tests/integration): usan PostgreSQL. La URL se toma de
  ``TEST_DATABASE_URL``; si la base no responde, se omiten.
* Criterios de aceptación (tests/hu): uno por criterio del backlog, pendientes de implementar.
"""

import os
from collections.abc import AsyncIterator

os.environ.setdefault("ENTORNO", "pruebas")
os.environ.setdefault("LOG_NIVEL", "WARNING")

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402

from app.core.config import Configuracion  # noqa: E402
from app.main import crear_app  # noqa: E402

# Base de datos inexistente: la conexión se rechaza de inmediato (puerto 9).
URL_SIN_BASE_DE_DATOS = "postgresql+asyncpg://nadie:nadie@127.0.0.1:9/ninguna"
URL_BD_PRUEBAS = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://materiales:materiales@127.0.0.1:5432/materiales_formulas_test"
)


def configuracion_de_prueba(**valores: object) -> Configuracion:
    """Configuración aislada: no lee el archivo .env del desarrollador."""
    base: dict[str, object] = {
        "entorno": "pruebas",
        "log_nivel": "WARNING",
        "database_url": URL_SIN_BASE_DE_DATOS,
        "db_timeout_s": 2.0,
        "inventario_url": "http://inventario.prueba",
        "patent_sweep_url": "http://patent-sweep.prueba",
        "patent_sweep_ruta_evaluacion": "/evaluaciones",
    }
    base.update(valores)
    return Configuracion(_env_file=None, **base)  # type: ignore[call-arg]


@pytest.fixture
def config() -> Configuracion:
    return configuracion_de_prueba()


@pytest.fixture
async def app(config: Configuracion) -> AsyncIterator[FastAPI]:
    """Aplicación con su ciclo de vida (motor, clientes HTTP y bus de eventos) iniciado."""
    aplicacion = crear_app(config)
    async with aplicacion.router.lifespan_context(aplicacion):
        yield aplicacion


@pytest.fixture
async def cliente(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    """Cliente HTTP que llama a la API en memoria (sin servidor)."""
    transporte = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transporte, base_url="http://pruebas") as c:
        yield c
