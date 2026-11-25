"""Repositorio de materiales y restricciones de la tabla material sobre PostgreSQL."""

from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ErrorIntegridadDatos
from app.infraestructure.interfaces.material_repository import FiltrosMaterial
from app.infraestructure.models import Material
from app.infraestructure.repositories import MaterialRepository
from app.infraestructure.unit_of_work import UnitOfWork
from tests.fabricas import un_material


async def _guardar(sesion: AsyncSession, *materiales: Material) -> None:
    async with UnitOfWork(sesion) as uow:
        for material in materiales:
            await MaterialRepository(sesion).agregar(material)
        await uow.commit()


async def test_material_se_guarda_con_el_repositorio(sesion: AsyncSession, otra_sesion: AsyncSession) -> None:
    await _guardar(sesion, un_material(1, nombre="Acero al carbono"))
    material = await otra_sesion.get(Material, "mat-001")
    assert material is not None
    assert (material.nombre, material.sku, material.estado, material.densidad) == (
        "Acero al carbono",
        "MP-00001",
        "ACTIVO",
        Decimal("7.85"),
    )
    assert material.fecha_registro.tzinfo is not None


async def test_nombre_unico_sin_distinguir_mayusculas_incluso_con_tildes(sesion: AsyncSession) -> None:
    await _guardar(sesion, un_material(1, nombre="Ácido Cítrico"))
    repositorio = MaterialRepository(sesion)
    assert await repositorio.existe_nombre("ÁCIDO CÍTRICO")
    assert await repositorio.existe_nombre("ácido cítrico")
    assert not await repositorio.existe_nombre("Acido Citrico")
    assert not await repositorio.existe_nombre("ácido cítrico", excluir_id="mat-001")


async def test_lectura_para_actualizar_reserva_la_fila_hasta_el_commit(sesion: AsyncSession, otra_sesion: AsyncSession) -> None:
    await _guardar(sesion, un_material(1))
    filas_disponibles = select(Material.id_material).with_for_update(skip_locked=True)
    async with UnitOfWork(sesion) as uow:
        assert await MaterialRepository(sesion).obtener_por_id("mat-001", para_actualizar=True) is not None
        assert await otra_sesion.scalar(filas_disponibles) is None
        await uow.commit()
    assert await otra_sesion.scalar(filas_disponibles) == "mat-001"


async def test_el_indice_unico_impide_nombres_repetidos(sesion: AsyncSession) -> None:
    await _guardar(sesion, un_material(1, nombre="Acero"))
    with pytest.raises(ErrorIntegridadDatos) as error:
        await _guardar(sesion, un_material(2, nombre="ACERO"))
    assert error.value.restriccion == "uq_material_nombre_lower"


async def test_el_sku_es_unico(sesion: AsyncSession) -> None:
    await _guardar(sesion, un_material(1, nombre="Acero"))
    repetido = un_material(2, nombre="Cobre")
    repetido.sku = "MP-00001"
    with pytest.raises(ErrorIntegridadDatos) as error:
        await _guardar(sesion, repetido)
    assert error.value.restriccion == "uq_material_sku"


@pytest.mark.parametrize(
    ("cambios", "restriccion"),
    [
        ({"categoria": "Otra"}, "ck_material_categoria"),
        ({"unidad_medida": "lb"}, "ck_material_unidad_medida"),
        ({"densidad": Decimal("0")}, "ck_material_densidad_positiva"),
        ({"pureza": Decimal("101")}, "ck_material_pureza_rango"),
        ({"estado": "BORRADO"}, "ck_material_estado"),
    ],
)
async def test_restricciones_check_del_material(sesion: AsyncSession, cambios: dict[str, object], restriccion: str) -> None:
    material = un_material(1)
    for campo, valor in cambios.items():
        setattr(material, campo, valor)
    with pytest.raises(ErrorIntegridadDatos) as error:
        await _guardar(sesion, material)
    assert error.value.restriccion == restriccion


async def test_secuencia_del_id(sesion: AsyncSession) -> None:
    repositorio = MaterialRepository(sesion)
    assert [await repositorio.siguiente_numero() for _ in range(3)] == [1, 2, 3]


async def test_consulta_materiales_con_paginacion_y_busqueda_literal(sesion: AsyncSession) -> None:
    await _guardar(sesion, un_material(1000, nombre="Acero fino"), un_material(999, nombre="ACERO A"))
    repo = MaterialRepository(sesion)
    filtros = FiltrosMaterial(nombre="cEr", categoria="Materia Prima", unidad_medida="kg", estado="ACTIVO")
    pagina, total = await repo.listar_pagina(filtros, 1, 1)
    assert total == 2 and [m.id_material for m in pagina] == ["mat-1000"]
    assert await repo.obtener_por_id("mat-1000") is pagina[0]
    assert await repo.listar_pagina(filtros, 2, 1) == ([], 2)
    assert await repo.listar_pagina(FiltrosMaterial(nombre="%"), 0, 10) == ([], 0)
