"""Repositorios y restricciones de la base de datos sobre PostgreSQL."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ErrorIntegridadDatos
from app.data_access.interfaces import FiltrosBusquedaFormulas
from app.data_access.models import Auditoria
from app.data_access.repositories import AuditoriaRepository, FormulaRepository, MaterialRepository
from app.data_access.unit_of_work import UnitOfWork
from tests.fabricas import un_material, un_registro_auditoria, una_evaluacion, una_formula


async def _guardar(sesion: AsyncSession, *objetos: object) -> None:
    async with UnitOfWork(sesion) as uow:
        sesion.add_all(objetos)
        await uow.commit()


# ---------------------------------------------------------------------------------------
# Materiales
# ---------------------------------------------------------------------------------------


async def test_material_se_guarda_y_se_consulta(sesion: AsyncSession, otra_sesion: AsyncSession) -> None:
    await _guardar(sesion, un_material(1, nombre="Acero al carbono"))
    material = await MaterialRepository(otra_sesion).obtener_por_id("mat-001")
    assert material is not None
    assert (material.nombre, material.densidad, material.fecha_registro.tzinfo is not None) == (
        "Acero al carbono",
        Decimal("7.85"),
        True,
    )
    assert await MaterialRepository(otra_sesion).obtener_por_id("mat-999") is None


async def test_nombre_unico_sin_distinguir_mayusculas_incluso_con_tildes(sesion: AsyncSession) -> None:
    await _guardar(sesion, un_material(1, nombre="Ácido Cítrico"))
    repositorio = MaterialRepository(sesion)
    assert await repositorio.existe_nombre("ÁCIDO CÍTRICO")
    assert await repositorio.existe_nombre("ácido cítrico")
    assert not await repositorio.existe_nombre("ácido cítrico", excluir_id="mat-001")
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


async def test_secuencia_y_consulta_de_varios(sesion: AsyncSession) -> None:
    repositorio = MaterialRepository(sesion)
    assert [await repositorio.siguiente_numero() for _ in range(3)] == [1, 2, 3]
    await _guardar(sesion, un_material(1), un_material(2))
    encontrados = await repositorio.obtener_por_ids(["mat-002", "mat-001", "mat-404", "mat-001"])
    assert sorted(m.id_material for m in encontrados) == ["mat-001", "mat-002"]


async def test_listado_paginado_en_orden_numerico(sesion: AsyncSession) -> None:
    await _guardar(sesion, un_material(1000), un_material(999), un_material(2))
    pagina = await MaterialRepository(sesion).listar(pagina=1, tamano_pagina=2)
    assert [m.id_material for m in pagina.elementos] == ["mat-002", "mat-999"]
    assert (pagina.total_registros, pagina.total_paginas) == (3, 2)


async def test_material_en_formulas_vigentes(sesion: AsyncSession) -> None:
    acero, cobre, zinc = un_material(1), un_material(2), un_material(3)
    vigente = una_formula(1, [(acero, 1), (cobre, 2)], estado="APROBADA")
    descontinuada = una_formula(2, [(zinc, 1), (cobre, 2)], estado="DESCONTINUADA")
    await _guardar(sesion, acero, cobre, zinc, vigente, descontinuada)
    repositorio = MaterialRepository(sesion)
    vigentes = ["BORRADOR", "EVALUANDO_PATENTE", "APROBADA"]
    assert await repositorio.pertenece_a_formulas_con_estado("mat-001", vigentes)
    assert await repositorio.pertenece_a_formulas_con_estado("mat-002", vigentes)
    assert not await repositorio.pertenece_a_formulas_con_estado("mat-003", vigentes)


# ---------------------------------------------------------------------------------------
# Fórmulas
# ---------------------------------------------------------------------------------------


async def test_formula_con_componentes_y_evaluaciones(sesion: AsyncSession, otra_sesion: AsyncSession) -> None:
    acero, tornillo = un_material(1), un_material(2, unidad_medida="und")
    formula = una_formula(1, [(acero, "2.5"), (tornillo, 4)], estado="RECHAZADA_POR_INFRACCION")
    una_evaluacion(formula, 1, "INFRACCION", [("123456", "Aleación de tungsteno")])
    await _guardar(sesion, acero, tornillo, formula)

    leida = await FormulaRepository(otra_sesion).obtener_por_id("form-001")
    assert leida is not None
    assert [(c.material.sku, c.cantidad) for c in leida.componentes] == [("MP-00001", Decimal("2.500")), ("MP-00002", Decimal("4.000"))]
    assert [(p.conflicto_id, p.titulo) for p in leida.evaluaciones[0].patentes] == [("123456", "Aleación de tungsteno")]


async def test_un_solo_tramite_abierto_por_formula(sesion: AsyncSession) -> None:
    formula = una_formula(1, estado="EVALUANDO_PATENTE")
    una_evaluacion(formula, 1)
    await _guardar(sesion, *[c.material for c in formula.componentes], formula)
    assert (await FormulaRepository(sesion).obtener_evaluacion_abierta("form-001")).ticket_evaluacion_id == "tck-001"

    async with UnitOfWork(sesion) as uow:
        leida = await FormulaRepository(sesion).obtener_por_id("form-001")
        una_evaluacion(leida, 2)
        with pytest.raises(ErrorIntegridadDatos) as error:
            await uow.commit()
    assert error.value.restriccion == "uq_evaluacion_patente_abierta"


async def test_busqueda_de_formulas_con_filtros_orden_y_paginacion(sesion: AsyncSession) -> None:
    base = datetime(2026, 3, 1, tzinfo=UTC)
    acero, cobre, zinc = un_material(1), un_material(2), un_material(3)
    formulas = [
        una_formula(1, [(acero, 1), (cobre, 1)], nombre="Filo Rápido", estado="APROBADA", fecha_registro=base, fecha_actualizacion=base + timedelta(days=3)),
        una_formula(2, [(acero, 1), (zinc, 1)], nombre="Corte 50%_extra", estado="BORRADOR", fecha_registro=base + timedelta(days=1), fecha_actualizacion=base + timedelta(days=5)),
        una_formula(3, [(cobre, 1), (zinc, 1)], nombre="Filo Lento", estado="BORRADOR", fecha_registro=base + timedelta(days=2), fecha_actualizacion=base + timedelta(days=4)),
    ]
    await _guardar(sesion, acero, cobre, zinc, *formulas)
    repositorio = FormulaRepository(sesion)

    async def ids(pagina: int = 1, tamano: int = 10, **filtros: object) -> list[str]:
        resultado = await repositorio.buscar(FiltrosBusquedaFormulas(**filtros), pagina, tamano)  # type: ignore[arg-type]
        return [f.id_formula for f in resultado.elementos]

    assert await ids() == ["form-002", "form-003", "form-001"]  # fecha de actualización descendente
    assert await ids(texto="filo") == ["form-003", "form-001"]
    assert await ids(texto="FORM-00") == ["form-002", "form-003", "form-001"]
    assert await ids(texto="50%_") == ["form-002"]  # comodines de LIKE escapados
    assert await ids(texto="%") == ["form-002"]
    assert await ids(estado="BORRADOR") == ["form-002", "form-003"]
    assert await ids(registro_desde=base + timedelta(days=1), registro_hasta=base + timedelta(days=2)) == ["form-002"]
    assert await ids(actualizacion_hasta=base + timedelta(days=4)) == ["form-001"]
    assert await ids(materiales=["mat-001"]) == ["form-002", "form-001"]
    assert await ids(materiales=["mat-001", "mat-002"]) == ["form-001"]
    assert await ids(pagina=2, tamano=2) == ["form-001"]
    pagina = await repositorio.buscar(FiltrosBusquedaFormulas(), 2, 2)
    assert (pagina.total_registros, pagina.total_paginas) == (3, 2)


async def test_aprobadas_en_orden_numerico_con_componentes(sesion: AsyncSession, otra_sesion: AsyncSession) -> None:
    acero, cobre = un_material(1), un_material(2)
    formulas = [
        una_formula(1000, [(acero, 1), (cobre, 1)], estado="APROBADA"),
        una_formula(7, [(acero, 1), (cobre, 1)], estado="APROBADA"),
        una_formula(8, [(acero, 1), (cobre, 1)], estado="DESCONTINUADA"),
    ]
    await _guardar(sesion, acero, cobre, *formulas)
    pagina = await FormulaRepository(otra_sesion).listar_por_estado("APROBADA", 1, 50)
    assert [f.id_formula for f in pagina.elementos] == ["form-007", "form-1000"]
    assert [c.material.nombre for c in pagina.elementos[0].componentes] == ["Material 1", "Material 2"]
    vacia = await FormulaRepository(otra_sesion).listar_por_estado("APROBADA", 5, 50)
    assert (vacia.elementos, vacia.total_registros, vacia.total_paginas) == ([], 2, 1)


async def test_nombre_de_formula_unico_y_secuencias(sesion: AsyncSession) -> None:
    formula = una_formula(1, nombre="Filo Rápido")
    await _guardar(sesion, *[c.material for c in formula.componentes], formula)
    repositorio = FormulaRepository(sesion)
    assert await repositorio.existe_nombre("FILO RÁPIDO")
    assert not await repositorio.existe_nombre("filo rápido", excluir_id="form-001")
    assert (await repositorio.siguiente_numero(), await repositorio.siguiente_numero_ticket()) == (1, 1)


async def test_cantidad_no_positiva_se_rechaza_en_la_base(sesion: AsyncSession) -> None:
    formula = una_formula(1)
    formula.componentes[0].cantidad = Decimal("-1")
    with pytest.raises(ErrorIntegridadDatos) as error:
        await _guardar(sesion, *[c.material for c in formula.componentes], formula)
    assert error.value.restriccion == "ck_componente_formula_cantidad_positiva"


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
