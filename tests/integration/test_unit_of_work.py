"""Unidad de trabajo: commit, rollback y traducción de fallos de la base de datos."""

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from app.core.exceptions import ErrorBaseDatos, ErrorIntegridadDatos
from app.data_access.database import crear_fabrica_sesiones, crear_motor
from app.data_access.models import Material
from app.data_access.repositories import FormulaRepository, MaterialRepository
from app.data_access.unit_of_work import UnitOfWork
from tests.conftest import URL_SIN_BASE_DE_DATOS, configuracion_de_prueba
from tests.fabricas import un_material, una_evaluacion, una_formula


async def _contar(sesion: AsyncSession) -> int:
    return int(await sesion.scalar(select(func.count()).select_from(Material)) or 0)


async def test_commit_confirma(sesion: AsyncSession, otra_sesion: AsyncSession) -> None:
    async with UnitOfWork(sesion) as uow:
        sesion.add(un_material(1))
        await uow.commit()
    assert await _contar(otra_sesion) == 1


async def test_sin_commit_se_revierte(sesion: AsyncSession, otra_sesion: AsyncSession) -> None:
    async with UnitOfWork(sesion):
        sesion.add(un_material(1))
        await sesion.flush()
    assert await _contar(otra_sesion) == 0


async def test_cambios_pendientes_sin_commit_se_revierten(sesion: AsyncSession, otra_sesion: AsyncSession) -> None:
    async with UnitOfWork(sesion):
        sesion.add(un_material(1))
    assert await _contar(otra_sesion) == 0


async def test_lo_leido_sigue_disponible_despues_del_bloque(sesion: AsyncSession, otra_sesion: AsyncSession) -> None:
    """Una consulta no debe vencer los objetos: el router los usa para armar la respuesta."""
    formula = una_formula(1, estado="RECHAZADA_POR_INFRACCION")
    una_evaluacion(formula, 1, "INFRACCION", [("123456", "Patente")])
    await _registrar(otra_sesion, *[c.material for c in formula.componentes], formula)

    async with UnitOfWork(sesion):
        leida = await FormulaRepository(sesion).obtener_por_id("form-001")
        material = await MaterialRepository(sesion).obtener_por_id("mat-011")
    assert leida is not None and material is not None
    assert (leida.nombre, material.sku) == ("Formula 1", "MP-00011")
    assert [c.material.nombre for c in leida.componentes] == ["Material 11", "Material 12"]
    assert leida.evaluaciones[0].patentes[0].titulo == "Patente"
    assert not sesion.in_transaction()


async def test_una_excepcion_revierte_y_se_propaga_sin_cambios(sesion: AsyncSession, otra_sesion: AsyncSession) -> None:
    with pytest.raises(ValueError, match="regla"):
        async with UnitOfWork(sesion):
            sesion.add(un_material(1))
            await sesion.flush()
            raise ValueError("regla de negocio")
    assert await _contar(otra_sesion) == 0
    # La sesión sigue utilizable después de la reversión.
    async with UnitOfWork(sesion) as uow:
        sesion.add(un_material(2))
        await uow.commit()
    assert await _contar(otra_sesion) == 1


async def test_violacion_de_restriccion_en_el_bloque(sesion: AsyncSession) -> None:
    await _registrar(sesion, un_material(1, nombre="Acero"))
    with pytest.raises(ErrorIntegridadDatos) as error:
        async with UnitOfWork(sesion):
            sesion.add(un_material(2, nombre="acero"))
            await sesion.flush()
    assert error.value.restriccion == "uq_material_nombre_lower"


async def _registrar(sesion: AsyncSession, *objetos: object) -> None:
    async with UnitOfWork(sesion) as uow:
        sesion.add_all(objetos)
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
