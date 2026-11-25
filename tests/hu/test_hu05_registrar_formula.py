"""HU-05: una o más pruebas por criterio, recorriendo schema, ruta y servicio."""

import logging
from collections.abc import Iterator
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.api.dependencies import obtener_formula_service
from app.business.domain import mensajes
from app.business.domain.mensajes import formatear
from app.business.services.formula_service import FormulaService
from app.core.events import BusEventos, EventoDominio
from app.core.exceptions import ErrorBaseDatos, ErrorIntegridadDatos
from tests.dobles.formulas import FormulaRepositoryFalso
from tests.dobles.repositorios import AuditoriaRepositoryFalso, MaterialRepositoryFalso, UnitOfWorkFalsa
from tests.fabricas import un_material

pytestmark = pytest.mark.hu

VALIDO: dict[str, Any] = {
    "nombre": "Mezcla de corte",
    "aplicacionTecnica": "Corte de acero 1045",
    "componentes": [{"materialId": "mat-001", "cantidad": 2.125}, {"materialId": "mat-002", "cantidad": 3}],
}


@dataclass
class Escenario:
    uow: UnitOfWorkFalsa = field(default_factory=UnitOfWorkFalsa)
    auditoria: AuditoriaRepositoryFalso = field(default_factory=AuditoriaRepositoryFalso)
    formulas: FormulaRepositoryFalso = field(default_factory=FormulaRepositoryFalso)
    materiales: MaterialRepositoryFalso = field(
        default_factory=lambda: MaterialRepositoryFalso(
            [
                un_material(1, nombre="Acero", unidad_medida="kg"),
                un_material(2, nombre="Tornillo", unidad_medida="und"),
            ]
        )
    )
    eventos: list[EventoDominio] = field(default_factory=list)

    def servicio(self) -> FormulaService:
        bus = BusEventos()
        bus.suscribir(self.eventos.append)
        return FormulaService(self.uow, self.auditoria, bus, self.formulas, self.materiales)


@pytest.fixture
def escenario(app: FastAPI) -> Iterator[Escenario]:
    datos = Escenario()
    app.dependency_overrides[obtener_formula_service] = datos.servicio
    yield datos
    app.dependency_overrides.clear()


def _cuerpo(**cambios: Any) -> dict[str, Any]:
    cuerpo = {**deepcopy(VALIDO), **cambios}
    return {k: v for k, v in cuerpo.items() if v is not ...}


async def test_c01_c06_c07_registra_ficha_tecnica_y_auditoria(cliente: httpx.AsyncClient, escenario: Escenario) -> None:
    antes = datetime.now(UTC)
    r = await cliente.post("/formulas", json=_cuerpo())
    assert r.status_code == 201, r.json()
    datos = r.json()
    fecha = datetime.fromisoformat(datos.pop("fechaRegistro"))
    actualizacion = datetime.fromisoformat(datos.pop("fechaUltimaActualizacion"))
    assert antes <= fecha <= datetime.now(UTC)
    assert actualizacion == fecha and fecha.utcoffset().total_seconds() == 0
    assert datos == {
        "formulaId": "form-001",
        "nombre": VALIDO["nombre"],
        "aplicacionTecnica": VALIDO["aplicacionTecnica"],
        "version": 1,
        "estado": "BORRADOR",
        "componentes": [
            {"sku": "MP-00001", "nombre": "Acero", "cantidad": 2.125, "unidadMedida": "kg"},
            {"sku": "MP-00002", "nombre": "Tornillo", "cantidad": 3, "unidadMedida": "und"},
        ],
        "mensaje": "Fórmula 'Mezcla de corte' registrada exitosamente en estado BORRADOR con el código form-001.",
    }
    assert escenario.uow.confirmaciones == 1
    assert [(a.operacion, a.recurso_id, a.resultado_http) for a in escenario.auditoria.registros] == [
        ("REGISTRAR_FORMULA", "form-001", 201)
    ]
    assert [(e.nombre, dict(e.datos)) for e in escenario.eventos] == [("FormulaRegistrada", {"formulaId": "form-001"})]


@pytest.mark.parametrize(
    "cambios,mensaje",
    [
        ({"nombre": ...}, mensajes.HU05_C2_1),
        ({"nombre": None}, mensajes.HU05_C2_1),
        ({"nombre": "   "}, mensajes.HU05_C2_1),
        ({"aplicacionTecnica": ...}, mensajes.HU05_C2_2),
        ({"aplicacionTecnica": None}, mensajes.HU05_C2_2),
        ({"aplicacionTecnica": " "}, mensajes.HU05_C2_2),
        ({"componentes": ...}, mensajes.HU05_C2_3),
        ({"componentes": None}, mensajes.HU05_C2_3),
        ({"componentes": []}, mensajes.HU05_C2_3),
        ({"componentes": [{"materialId": "mat-001", "cantidad": 1}]}, mensajes.HU05_C2_3),
        (
            {"componentes": [{"materialId": "mat-001"}, {"materialId": "mat-002", "cantidad": 1}]},
            formatear(mensajes.HU05_C2_4, IDMaterial="mat-001"),
        ),
        ({"nombre": "X" * 81}, mensajes.HU05_C9_1_A),
        ({"nombre": "Mezcla 1"}, mensajes.HU05_C9_1_B),
        ({"nombre": 123}, mensajes.HU05_C9_1_B),
        ({"nombre": "Mezcla!"}, mensajes.HU05_C9_1_B),
        ({"aplicacionTecnica": "A" * 201}, mensajes.HU05_C9_2),
        ({"aplicacionTecnica": "Corte!"}, mensajes.SOLICITUD_INVALIDA),
        ({"aplicacionTecnica": 123}, mensajes.SOLICITUD_INVALIDA),
        ({"componentes": [{"materialId": "mat-001", "cantidad": 1}] * 2}, formatear(mensajes.HU05_C9_3, IDMaterial="mat-001")),
    ],
)
async def test_c02_c09_rechaza_datos_invalidos_sin_guardar(
    cliente: httpx.AsyncClient, escenario: Escenario, cambios: dict[str, Any], mensaje: str
) -> None:
    r = await cliente.post("/formulas", json=_cuerpo(**cambios))
    assert (r.status_code, r.json()["mensaje"]) == (400, mensaje)
    assert escenario.formulas.formulas == {} and escenario.eventos == []
    assert escenario.uow.confirmaciones == 0


@pytest.mark.parametrize(
    "valor,plantilla",
    [
        (None, mensajes.HU05_C2_4),
        (0, mensajes.HU05_C3_1),
        (-1, mensajes.HU05_C3_1),
        (True, mensajes.HU05_C3_1),
        ("abc", mensajes.HU05_C3_1),
        ("NaN", mensajes.HU05_C3_1),
        ("Infinity", mensajes.HU05_C3_1),
        (1000000, mensajes.HU05_C3_2),
        (0.0001, mensajes.HU05_C3_2),
        ("999999.9999", mensajes.HU05_C3_2),
        ("1.00000000000000000000000000001", mensajes.HU05_C3_2),
        ("1e-1000000000000000000", mensajes.HU05_C3_2),
    ],
)
async def test_c02_c03_cantidad_invalida(cliente: httpx.AsyncClient, escenario: Escenario, valor: Any, plantilla: str) -> None:
    cuerpo = _cuerpo()
    cuerpo["componentes"][0]["cantidad"] = valor
    r = await cliente.post("/formulas", json=cuerpo)
    assert (r.status_code, r.json()["mensaje"]) == (400, formatear(plantilla, IDMaterial="mat-001", Cantidad=valor))
    assert escenario.formulas.formulas == {}


@pytest.mark.parametrize("valor", [0.001, 999999.999, "2.0000", "1e-3"])
async def test_c01_c03_limites_de_cantidad_validos(cliente: httpx.AsyncClient, escenario: Escenario, valor: Any) -> None:
    cuerpo = _cuerpo()
    cuerpo["componentes"][0]["cantidad"] = valor
    r = await cliente.post("/formulas", json=cuerpo)
    assert r.status_code == 201, r.json()


@pytest.mark.parametrize("estado,plantilla", [(None, mensajes.HU05_C4_1), ("INACTIVO", mensajes.HU05_C4_2)])
async def test_c04_componentes_no_disponibles(cliente: httpx.AsyncClient, escenario: Escenario, estado: str | None, plantilla: str) -> None:
    for material in escenario.materiales.materiales.values():
        material.estado = estado or "ACTIVO"
    if estado is None:
        escenario.materiales.materiales.clear()
    r = await cliente.post("/formulas", json=_cuerpo())
    assert (r.status_code, r.json()["mensaje"]) == (422, formatear(plantilla, {"Lista de Materiales": "mat-001, mat-002"}))
    assert escenario.formulas.formulas == {} and escenario.eventos == []


async def test_c05_unidad_exige_entero_antes_de_validar_nombre(cliente: httpx.AsyncClient, escenario: Escenario) -> None:
    await cliente.post("/formulas", json=_cuerpo())
    cuerpo = _cuerpo()
    cuerpo["componentes"][1]["cantidad"] = 1.5
    r = await cliente.post("/formulas", json=cuerpo)
    assert (r.status_code, r.json()["mensaje"]) == (422, formatear(mensajes.HU05_C5, NombreMaterial="Tornillo", Cantidad=1.5))
    assert len(escenario.formulas.formulas) == 1


async def test_c06_nombre_unico_sin_distinguir_mayusculas(cliente: httpx.AsyncClient, escenario: Escenario) -> None:
    assert (await cliente.post("/formulas", json=_cuerpo())).status_code == 201
    r = await cliente.post("/formulas", json=_cuerpo(nombre="MEZCLA DE CORTE"))
    assert (r.status_code, r.json()["mensaje"]) == (409, formatear(mensajes.HU05_C6_1, NombreIngresado="MEZCLA DE CORTE"))
    assert len(escenario.formulas.formulas) == 1


async def test_c07_codigo_secuencial(cliente: httpx.AsyncClient, escenario: Escenario) -> None:
    r1 = await cliente.post("/formulas", json=_cuerpo(nombre="Fórmula uno"))
    r2 = await cliente.post("/formulas", json=_cuerpo(nombre="Fórmula dos"))
    assert (r1.json()["formulaId"], r2.json()["formulaId"]) == ("form-001", "form-002")


@pytest.mark.parametrize("unidad", ["und", "g", "kg", "mL", "L", "m"])
async def test_c01_unidad_se_toma_del_catalogo(cliente: httpx.AsyncClient, escenario: Escenario, unidad: str) -> None:
    escenario.materiales.materiales["mat-001"].unidad_medida = unidad
    cuerpo = _cuerpo(nombre="Á" * 80, aplicacionTecnica="A" * 200)
    cuerpo["componentes"][0]["cantidad"] = 1
    r = await cliente.post("/formulas", json=cuerpo)
    assert r.status_code == 201, r.json()
    assert r.json()["componentes"][0]["unidadMedida"] == unidad


@pytest.mark.parametrize(
    "error,codigo,plantilla",
    [
        (ErrorBaseDatos("conexión"), 500, mensajes.HU05_C8),
        (ErrorBaseDatos("timeout > 5 s"), 500, mensajes.HU05_C8),
        (ErrorIntegridadDatos("nombre duplicado", "uq_formula_nombre_lower"), 409, mensajes.HU05_C6_1),
        (ErrorIntegridadDatos("otra restricción", "otra"), 500, mensajes.HU05_C8),
    ],
)
async def test_c06_c08_fallo_en_commit_no_publica_eventos(
    cliente: httpx.AsyncClient,
    escenario: Escenario,
    caplog: pytest.LogCaptureFixture,
    error: ErrorBaseDatos,
    codigo: int,
    plantilla: str,
) -> None:
    escenario.uow.error_en_commit = error
    with caplog.at_level(logging.ERROR):
        r = await cliente.post("/formulas", json=_cuerpo())
    assert (r.status_code, r.json()["mensaje"]) == (codigo, formatear(plantilla, NombreIngresado=VALIDO["nombre"]))
    assert escenario.uow.confirmaciones == 0 and escenario.uow.reversiones >= 1
    assert escenario.eventos == []
    assert r.json()["traceId"] == r.headers["X-Trace-Id"]
    if codigo == 500:
        assert any(getattr(rec, "trace_id", None) == r.json()["traceId"] for rec in caplog.records)


@pytest.mark.parametrize("campo", ["unidadMedida", "estado", "formulaId", "version", "fechaRegistro", "fechaUltimaActualizacion"])
async def test_c07_c09_campos_de_solo_lectura(cliente: httpx.AsyncClient, escenario: Escenario, campo: str) -> None:
    cuerpo = _cuerpo()
    if campo == "unidadMedida":
        cuerpo["componentes"][0][campo] = "kg"
    else:
        cuerpo[campo] = "valor"
    r = await cliente.post("/formulas", json=cuerpo)
    assert r.status_code == 400
    if campo == "unidadMedida":
        assert r.json()["mensaje"] == mensajes.HU05_C9_4
    assert escenario.formulas.formulas == {}


@pytest.mark.parametrize("material_id", ["mat-1", "otro", "", 1, None])
async def test_c01_id_material_invalido(cliente: httpx.AsyncClient, escenario: Escenario, material_id: Any) -> None:
    cuerpo = _cuerpo()
    cuerpo["componentes"][0]["materialId"] = material_id
    assert (await cliente.post("/formulas", json=cuerpo)).status_code == 400
    assert escenario.formulas.formulas == {}


async def test_solo_hu05_publicada_en_openapi(cliente: httpx.AsyncClient, escenario: Escenario) -> None:
    esquema = (await cliente.get("/openapi.json")).json()
    rutas = {p: v for p, v in esquema["paths"].items() if p.startswith("/formulas")}
    assert set(rutas) == {"/formulas"} and set(rutas["/formulas"]) == {"post"}
    assert set(rutas["/formulas"]["post"]["responses"]) == {"201", "400", "409", "422", "500"}
