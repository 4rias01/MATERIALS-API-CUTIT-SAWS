"""Repositorios y restricciones de la base de datos sobre PostgreSQL."""

from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ErrorIntegridadDatos
from app.infraestructure.interfaces.material_repository import FiltrosMaterial
from app.infraestructure.models import Auditoria, Material
from app.infraestructure.repositories import AuditoriaRepository, MaterialRepository
from app.infraestructure.unit_of_work import UnitOfWork
from tests.fabricas import un_material, un_registro_auditoria


async def _guardar(sesion: AsyncSession, *objetos: object) -> None:
    async with UnitOfWork(sesion) as uow:
        sesion.add_all(objetos)
        await uow.commit()


# ---------------------------------------------------------------------------------------
# Materiales
# ---------------------------------------------------------------------------------------


async def test_material_se_guarda_con_el_repositorio(sesion: AsyncSession, otra_sesion: AsyncSession) -> None:
    async with UnitOfWork(sesion) as uow:
        MaterialRepository(sesion).agregar(un_material(1, nombre="Acero al carbono"))
        await uow.commit()
    material = await otra_sesion.get(Material, "mat-001")
    assert material is not None
    assert (material.nombre, material.densidad, material.fecha_registro.tzinfo is not None) == (
        "Acero al carbono",
        Decimal("7.85"),
        True,
    )


async def test_nombre_unico_sin_distinguir_mayusculas_incluso_con_tildes(sesion: AsyncSession) -> None:
    await _guardar(sesion, un_material(1, nombre="Ácido Cítrico"))
    repositorio = MaterialRepository(sesion)
    assert await repositorio.existe_nombre("ÁCIDO CÍTRICO")
    assert await repositorio.existe_nombre("ácido cítrico")
    assert not await repositorio.existe_nombre("Acido Citrico")


async def test_el_indice_unico_impide_nombres_repetidos(sesion: AsyncSession) -> None:
    await _guardar(sesion, un_material(1, nombre="Acero"))
    with pytest.raises(ErrorIntegridadDatos) as error:
        await _guardar(sesion, un_material(2, nombre="ACERO"))
    assert error.value.restriccion == "uq_material_nombre_lower"


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


# ---------------------------------------------------------------------------------------
# Auditoría
# ---------------------------------------------------------------------------------------


async def test_auditoria_de_solo_insercion(sesion: AsyncSession, otra_sesion: AsyncSession) -> None:
    async with UnitOfWork(sesion) as uow:
        AuditoriaRepository(sesion).agregar(un_registro_auditoria("REGISTRAR_MATERIAL", 201))
        await uow.commit()
    registro = (await otra_sesion.scalars(select(Auditoria))).one()
    assert (registro.operacion, registro.resultado_http, registro.detalle) == ("REGISTRAR_MATERIAL", 201, {"clave": "valor"})
    assert await otra_sesion.scalar(select(func.count()).select_from(Auditoria)) == 1


async def test_consulta_materiales_con_paginacion_y_busqueda_literal(sesion: AsyncSession) -> None:
    await _guardar(sesion, un_material(1000, nombre="Acero fino"), un_material(999, nombre="ACERO A"))
    repo = MaterialRepository(sesion)
    filtros = FiltrosMaterial(nombre="cEr", categoria="Materia Prima", unidad_medida="kg", estado="ACTIVO")
    pagina, total = await repo.listar(filtros, 1, 1)
    assert total == 2 and [m.id_material for m in pagina] == ["mat-1000"]
    assert await repo.obtener("mat-1000") is pagina[0]
    assert await repo.listar(filtros, 2, 1) == ([], 2)
    assert await repo.listar(FiltrosMaterial(nombre="%"), 0, 10) == ([], 0)
