"""Migración 0003: las filas del CRUD básico (0002) no se pierden al crear la tabla de HU-01.

Prueba síncrona: los comandos de Alembic abren su propio ciclo de eventos (migrations/env.py).
Al terminar deja la base en la última versión y el respaldo vacío.
"""

import asyncio
from typing import Any

from alembic import command
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.integration.conftest import configuracion_alembic

FILA_DEL_CRUD = (
    "INSERT INTO material (nombre, categoria, unidad_medida, densidad, pureza) VALUES ('Acero del CRUD', 'Materia Prima', 'kg', 7.85, 98)"
)


def _sql(url: str, sentencia: str) -> list[tuple[Any, ...]]:
    async def ejecutar() -> list[tuple[Any, ...]]:
        motor = create_async_engine(url)
        try:
            async with motor.begin() as conexion:
                resultado = await conexion.execute(text(sentencia))
                return [tuple(fila) for fila in resultado] if resultado.returns_rows else []
        finally:
            await motor.dispose()

    return asyncio.run(ejecutar())


def test_0003_conserva_las_filas_del_crud_en_el_respaldo(url_base_datos: str) -> None:
    config = configuracion_alembic(url_base_datos)
    command.downgrade(config, "0002")
    try:
        _sql(url_base_datos, FILA_DEL_CRUD)

        command.upgrade(config, "head")
        assert _sql(url_base_datos, "SELECT nombre FROM material_crud_respaldo") == [("Acero del CRUD",)]
        assert _sql(url_base_datos, "SELECT count(*) FROM material") == [(0,)]

        # El downgrade devuelve las filas a la tabla del CRUD.
        command.downgrade(config, "0002")
        assert _sql(url_base_datos, "SELECT nombre FROM material") == [("Acero del CRUD",)]
    finally:
        command.upgrade(config, "head")
        _sql(url_base_datos, "DELETE FROM material_crud_respaldo")


def test_0003_funciona_si_la_tabla_del_crud_no_existe(url_base_datos: str) -> None:
    """Caso de la EC2: alembic_version en 0002 pero la tabla material se borró a mano."""
    config = configuracion_alembic(url_base_datos)
    command.downgrade(config, "0002")
    try:
        _sql(url_base_datos, "DROP TABLE material")

        command.upgrade(config, "head")
        assert _sql(url_base_datos, "SELECT count(*) FROM material") == [(0,)]
        assert _sql(url_base_datos, "SELECT to_regclass('material_crud_respaldo') IS NULL") == [(True,)]

        # Sin respaldo, el downgrade deja la tabla del CRUD vacía (esquema de 0002).
        command.downgrade(config, "0002")
        assert _sql(url_base_datos, "SELECT count(*) FROM material") == [(0,)]
    finally:
        command.upgrade(config, "head")
