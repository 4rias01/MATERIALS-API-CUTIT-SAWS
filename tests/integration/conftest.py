"""Base de datos de las pruebas de integración.

Usa ``TEST_DATABASE_URL`` (por defecto, la base materiales_formulas_test en localhost).
Al iniciar la sesión aplica las migraciones desde cero; antes de cada prueba vacía las
tablas y reinicia las secuencias. Si la base no responde, las pruebas se omiten.
"""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from app.data_access.database import crear_fabrica_sesiones
from tests.conftest import URL_BD_PRUEBAS

RAIZ = Path(__file__).resolve().parents[2]
TABLAS = "auditoria, patente_conflicto, evaluacion_patente, componente_formula, formula, material"
SECUENCIAS = ("seq_material", "seq_formula", "seq_ticket_evaluacion")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if Path(str(item.fspath)).is_relative_to(Path(__file__).parent):
            item.add_marker(pytest.mark.integracion)


def configuracion_alembic(url: str = URL_BD_PRUEBAS) -> Config:
    config = Config(str(RAIZ / "alembic.ini"))
    config.set_main_option("script_location", str(RAIZ / "migrations"))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return config


def _base_disponible(url: str) -> bool:
    async def probar() -> bool:
        motor = create_async_engine(url, connect_args={"timeout": 3})
        try:
            async with motor.connect() as conexion:
                await conexion.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
        finally:
            await motor.dispose()

    return asyncio.run(probar())


@pytest.fixture(scope="session")
def url_base_datos() -> str:
    if not _base_disponible(URL_BD_PRUEBAS):
        pytest.skip("PostgreSQL no disponible: defina TEST_DATABASE_URL para correr las pruebas de integración")
    config = configuracion_alembic()
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    return URL_BD_PRUEBAS


@pytest.fixture
async def motor(url_base_datos: str) -> AsyncIterator[AsyncEngine]:
    motor = create_async_engine(url_base_datos)
    async with motor.begin() as conexion:
        await conexion.execute(text(f"TRUNCATE {TABLAS} RESTART IDENTITY CASCADE"))
        for secuencia in SECUENCIAS:
            await conexion.execute(text(f"ALTER SEQUENCE {secuencia} RESTART WITH 1"))
    yield motor
    await motor.dispose()


@pytest.fixture
async def sesion(motor: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with crear_fabrica_sesiones(motor)() as s:
        yield s


@pytest.fixture
async def otra_sesion(motor: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Segunda sesión para comprobar lo que quedó confirmado en la base de datos."""
    async with crear_fabrica_sesiones(motor)() as s:
        yield s
