"""Especificaciones, estados de la fórmula (patrón State) y catálogo de mensajes."""

import re
from decimal import Decimal

import pytest

from app.business.domain import mensajes
from app.business.domain.enums import EstadoFormula, ResultadoDictamen, UnidadMedida
from app.business.domain.errores import TransicionNoPermitidaError
from app.business.domain.formula_states import ESTADOS_VIGENTES, estado_formula
from app.business.domain.specifications import CantidadEnteraSiUnidad, MaterialActivo, MinimoMaterialesDistintos
from app.business.domain.value_objects import Cantidad
from tests.fabricas import un_material

E = EstadoFormula

# ---------------------------------------------------------------------------------------
# Especificaciones
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("ids", "cumple"),
    [
        (["mat-001", "mat-002"], True),
        (["mat-001", "mat-001"], False),
        (["mat-001"], False),
        ([], False),
        (["mat-001", "mat-001", "mat-002"], True),
    ],
)
def test_minimo_dos_materiales_distintos(ids: list[str], cumple: bool) -> None:
    assert MinimoMaterialesDistintos(2).es_satisfecha_por(ids) is cumple


@pytest.mark.parametrize(
    ("cantidad", "unidad", "cumple"),
    [("3", UnidadMedida.UNIDAD, True), ("3.5", UnidadMedida.UNIDAD, False), ("3.5", UnidadMedida.KILOGRAMO, True), ("3.5", "und", False)],
)
def test_cantidad_entera_si_la_unidad_es_und(cantidad: str, unidad: UnidadMedida | str, cumple: bool) -> None:
    assert CantidadEnteraSiUnidad().es_satisfecha_por((Cantidad(Decimal(cantidad)), unidad)) is cumple


def test_material_activo() -> None:
    assert MaterialActivo().es_satisfecha_por(un_material(estado="ACTIVO"))
    assert not MaterialActivo().es_satisfecha_por(un_material(estado="INACTIVO"))


def test_las_especificaciones_se_combinan() -> None:
    minimo_dos = MinimoMaterialesDistintos(2)
    minimo_tres = MinimoMaterialesDistintos(3)
    ids = ["mat-001", "mat-002"]
    assert (minimo_dos & ~minimo_tres).es_satisfecha_por(ids)
    assert (minimo_tres | minimo_dos).es_satisfecha_por(ids)
    assert not (minimo_dos & minimo_tres).es_satisfecha_por(ids)


# ---------------------------------------------------------------------------------------
# Estados de la fórmula
# ---------------------------------------------------------------------------------------

# (estado, admite_modificacion, admite_descontinuacion, admite_solicitud_evaluacion, admite_dictamen, vigente)
TABLA_ESTADOS = [
    (E.BORRADOR, True, True, True, False, True),
    (E.EVALUANDO_PATENTE, False, False, False, True, True),
    (E.APROBADA, False, True, False, False, True),
    (E.RECHAZADA_POR_INFRACCION, True, True, False, False, False),
    (E.DESCONTINUADA, False, False, False, False, False),
]


@pytest.mark.parametrize(("estado", "modificar", "descontinuar", "evaluar", "dictamen", "vigente"), TABLA_ESTADOS)
def test_acciones_permitidas_por_estado(
    estado: EstadoFormula, modificar: bool, descontinuar: bool, evaluar: bool, dictamen: bool, vigente: bool
) -> None:
    objeto = estado_formula(estado)
    assert objeto.admite_modificacion() is modificar  # HU-07 c1 y c6
    assert objeto.admite_descontinuacion() is descontinuar  # HU-08 c2 y c5
    assert objeto.admite_solicitud_evaluacion() is evaluar  # HU-09 c1 y c4
    assert objeto.admite_dictamen() is dictamen  # HU-10 c6
    assert objeto.es_vigente() is vigente  # HU-04 c5


@pytest.mark.parametrize("estado", [fila[0] for fila in TABLA_ESTADOS])
def test_cada_transicion_coincide_con_su_consulta(estado: EstadoFormula) -> None:
    objeto = estado_formula(estado)
    acciones = [
        (objeto.admite_modificacion(), objeto.modificar, E.BORRADOR),
        (objeto.admite_descontinuacion(), objeto.descontinuar, E.DESCONTINUADA),
        (objeto.admite_solicitud_evaluacion(), objeto.solicitar_evaluacion, E.EVALUANDO_PATENTE),
    ]
    for permitida, transicion, destino in acciones:
        if permitida:
            assert transicion().nombre == destino
        else:
            with pytest.raises(TransicionNoPermitidaError) as error:
                transicion()
            assert error.value.estado_actual == estado.value


def test_dictamen_aprueba_o_rechaza() -> None:
    evaluando = estado_formula("EVALUANDO_PATENTE")
    assert evaluando.registrar_dictamen(ResultadoDictamen.SIN_INFRACCION).nombre == E.APROBADA
    assert evaluando.registrar_dictamen(ResultadoDictamen.INFRACCION).nombre == E.RECHAZADA_POR_INFRACCION
    with pytest.raises(TransicionNoPermitidaError):
        estado_formula(E.BORRADOR).registrar_dictamen(ResultadoDictamen.SIN_INFRACCION)


def test_estados_vigentes_para_inhabilitar_materiales() -> None:
    assert set(ESTADOS_VIGENTES) == {E.BORRADOR, E.EVALUANDO_PATENTE, E.APROBADA}


def test_estado_desconocido() -> None:
    with pytest.raises(ValueError):
        estado_formula("INEXISTENTE")


# ---------------------------------------------------------------------------------------
# Catálogo de mensajes
# ---------------------------------------------------------------------------------------


def _constantes() -> dict[str, str]:
    return {k: v for k, v in vars(mensajes).items() if re.fullmatch(r"HU\d{2}_C\w+", k)}


def test_el_catalogo_tiene_los_96_mensajes_del_backlog() -> None:
    constantes = _constantes()
    assert len(constantes) == 96
    assert {k[:4] for k in constantes} == {f"HU{n:02d}" for n in range(1, 12)}
    assert all(isinstance(v, str) and v.strip() == v and v for v in constantes.values())


def test_formatear_reemplaza_los_marcadores() -> None:
    assert mensajes.formatear(mensajes.HU01_C7, Nombre="Acero", SKU="MP-00001") == (
        "Material 'Acero' registrado exitosamente con el SKU MP-00001."
    )
    assert mensajes.formatear(mensajes.HU05_C6_2, {"Nombre": "F1", "form-NNN": "form-001"}).endswith("form-001.")
    assert mensajes.formatear(mensajes.HU07_C8) == mensajes.HU07_C8


def test_formatear_avisa_si_falta_un_valor() -> None:
    with pytest.raises(KeyError):
        mensajes.formatear(mensajes.HU01_C7, Nombre="Acero")


def test_marcadores() -> None:
    assert mensajes.marcadores(mensajes.HU05_C4_1) == ["Lista de Materiales"]
    assert mensajes.marcadores(mensajes.HU02_C5) == ["traceId"]
