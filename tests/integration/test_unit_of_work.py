"""Unidad de trabajo: commit, rollback y traducción de fallos de la base de datos."""

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from app.core.exceptions import ErrorBaseDatos, ErrorIntegridadDatos
from app.infraestructure.database import crear_fabrica_sesiones, crear_motor
from app.infraestructure.models import Auditoria
from app.infraestructure.repositories import AuditoriaRepository
from app.infraestructure.unit_of_work import UnitOfWork
from tests.conftest import URL_SIN_BASE_DE_DATOS, configuracion_de_prueba


def un_registro(operacion: str = "PRUEBA") -> Auditoria:
    return Auditoria(trace_id="0123456789abcdef", operacion=operacion, recurso="prueba", recurso_id="1", resultado_http=200)


async def _contar(sesion: AsyncSession) -> int:
    return int(await sesion.scalar(select(func.count()).select_from(Auditoria)) or 0)


async def test_commit_confirma(sesion: AsyncSession, otra_sesion: AsyncSession) -> None:
    async with UnitOfWork(sesion) as uow:
        AuditoriaRepository(sesion).agregar(un_registro())
        await uow.commit()
    assert await _contar(otra_sesion) == 1


async def test_sin_commit_se_revierte(sesion: AsyncSession, otra_sesion: AsyncSession) -> None:
    async with UnitOfWork(sesion):
        sesion.add(un_registro())
        await sesion.flush()
    assert await _contar(otra_sesion) == 0


async def test_cambios_pendientes_sin_commit_se_revierten(sesion: AsyncSession, otra_sesion: AsyncSession) -> None:
    async with UnitOfWork(sesion):
        sesion.add(un_registro())
    assert await _contar(otra_sesion) == 0


async def test_lo_leido_sigue_disponible_despues_del_bloque(sesion: AsyncSession, otra_sesion: AsyncSession) -> None:
    """Una consulta no debe vencer los objetos: el router los usa para armar la respuesta."""
    async with UnitOfWork(otra_sesion) as uow:
        otra_sesion.add(un_registro("LEIDO"))
        await uow.commit()

    async with UnitOfWork(sesion):
        registro = (await sesion.scalars(select(Auditoria))).one()
    assert registro.operacion == "LEIDO"
    assert not sesion.in_transaction()


async def test_una_excepcion_revierte_y_se_propaga_sin_cambios(sesion: AsyncSession, otra_sesion: AsyncSession) -> None:
    with pytest.raises(ValueError, match="regla"):
        async with UnitOfWork(sesion):
            sesion.add(un_registro())
            await sesion.flush()
            raise ValueError("regla de negocio")
    assert await _contar(otra_sesion) == 0
    async with UnitOfWork(sesion) as uow:  # la sesión sigue utilizable
        sesion.add(un_registro())
        await uow.rollback()
        sesion.add(un_registro())
        await uow.commit()
    assert await _contar(otra_sesion) == 1


async def test_violacion_de_restriccion_se_traduce(sesion: AsyncSession) -> None:
    registro = un_registro()
    registro.operacion = None  # type: ignore[assignment]  # NOT NULL
    with pytest.raises(ErrorIntegridadDatos):
        async with UnitOfWork(sesion):
            sesion.add(registro)
            await sesion.flush()


async def test_fallo_en_commit_se_traduce(sesion: AsyncSession) -> None:
    registro = un_registro()
    registro.operacion = None  # type: ignore[assignment]
    with pytest.raises(ErrorIntegridadDatos):
        async with UnitOfWork(sesion) as uow:
            sesion.add(registro)
            await uow.commit()


async def test_timeout_de_sentencia_se_traduce_a_error_de_base_de_datos(url_base_datos: str) -> None:
    motor = crear_motor(configuracion_de_prueba(database_url=url_base_datos, db_timeout_s=0.5))
    try:
        async with crear_fabrica_sesiones(motor)() as sesion:
            with pytest.raises(ErrorBaseDatos):
                async with UnitOfWork(sesion):
                    await sesion.execute(text("SELECT pg_sleep(2)"))
    finally:
        await motor.dispose()


async def test_verificar_conexion(motor: AsyncEngine) -> None:
    async with crear_fabrica_sesiones(motor)() as sesion:
        await UnitOfWork(sesion).verificar_conexion()

    caido = create_async_engine(URL_SIN_BASE_DE_DATOS)
    try:
        async with crear_fabrica_sesiones(caido)() as sesion:
            with pytest.raises(ErrorBaseDatos):
                await UnitOfWork(sesion).verificar_conexion()
    finally:
        await caido.dispose()
