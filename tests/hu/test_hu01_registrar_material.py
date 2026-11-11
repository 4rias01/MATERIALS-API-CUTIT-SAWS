"""HU-01 · POST /materiales · prioridad Must · 8 puntos.

Yo como operario de materiales y fórmulas, requiero registrar un material nuevo con sus propiedades,
para poder incluirlo como componente en el diseño de fórmulas.

Una o más pruebas por criterio de aceptación. Recorren la API completa (schema, router,
servicio, manejador de errores) con la base de datos y el cliente de Inventario
reemplazados por dobles (tests/dobles).
"""

import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.api.dependencies import obtener_material_service
from app.business.domain import mensajes
from app.business.domain.mensajes import formatear
from app.business.services.material_service import MaterialService
from app.core.events import BusEventos, EventoDominio
from app.core.exceptions import ErrorIntegridadDatos
from tests.dobles import AuditoriaRepositoryFalso, InventarioClientFalso, MaterialRepositoryFalso, UnitOfWorkFalsa
from tests.fabricas import un_material

pytestmark = pytest.mark.hu

VALIDO: dict[str, Any] = {
    "nombre": "Acero al carbono 1045",
    "categoria": "Materia Prima",
    "unidadMedida": "kg",
    "densidad": 7.85,
    "pureza": 98,
}


@dataclass
class Escenario:
    uow: UnitOfWorkFalsa = field(default_factory=UnitOfWorkFalsa)
    auditoria: AuditoriaRepositoryFalso = field(default_factory=AuditoriaRepositoryFalso)
    materiales: MaterialRepositoryFalso = field(default_factory=MaterialRepositoryFalso)
    inventario: InventarioClientFalso = field(default_factory=InventarioClientFalso)
    eventos: list[EventoDominio] = field(default_factory=list)

    def servicio(self) -> MaterialService:
        bus = BusEventos()
        bus.suscribir(self.eventos.append)
        return MaterialService(self.uow, self.auditoria, bus, self.materiales, self.inventario)


@pytest.fixture
def escenario(app: FastAPI) -> Iterator[Escenario]:
    """Cada prueba ajusta los dobles (p. ej. ``escenario.inventario.caido = True``) antes de llamar."""
    datos = Escenario()
    app.dependency_overrides[obtener_material_service] = datos.servicio
    yield datos
    app.dependency_overrides.clear()


def _cuerpo(**cambios: Any) -> dict[str, Any]:
    """Cuerpo válido con ``cambios``; un valor ``...`` omite el campo."""
    cuerpo = {**VALIDO, **cambios}
    return {k: v for k, v in cuerpo.items() if v is not ...}


def _sin_persistir(escenario: Escenario) -> None:
    """No se guardó el material (la auditoría del rechazo sí se guarda, en su propia transacción)."""
    assert escenario.materiales.materiales == {}
    assert all(a.resultado_http >= 400 for a in escenario.auditoria.registros)
    assert escenario.eventos == []


# ---------------------------------------------------------------------------------------
# Criterio 1: campos y normalización del nombre
# ---------------------------------------------------------------------------------------


async def test_c01_normaliza_los_espacios_del_nombre_antes_de_validar_y_guardar(
    cliente: httpx.AsyncClient, escenario: Escenario
) -> None:
    r = await cliente.post("/materiales", json=_cuerpo(nombre="   Acero   al  carbono 1045  "))
    assert r.status_code == 201
    assert r.json()["nombre"] == "Acero al carbono 1045"
    assert escenario.inventario.altas == [("Acero al carbono 1045", "kg")]
    assert escenario.materiales.materiales["mat-001"].nombre == "Acero al carbono 1045"


@pytest.mark.parametrize(
    "cambios",
    [
        {"nombre": "Ácido cítrico"},
        {"nombre": "Aceite Ñandú"},
        {"nombre": "Lámina 3/4 (tipo #2), cal. 1.5-A"},
        {"nombre": "Fe3"},
        {"nombre": "x" * 100},
        {"categoria": "Componentes", "unidadMedida": "und"},
        {"categoria": "Lubricantes", "unidadMedida": "mL"},
        {"unidadMedida": "g"},
        {"unidadMedida": "L"},
        {"unidadMedida": "m"},
        {"densidad": 1000},
        {"densidad": "7.850"},  # los ceros a la derecha del decimal no cuentan
        {"densidad": 0.5},
        {"pureza": 100},
        {"pureza": 9.5},
        {"pureza": 0},
    ],
)
async def test_c01_acepta_los_valores_permitidos(cliente: httpx.AsyncClient, escenario: Escenario, cambios: dict[str, Any]) -> None:
    r = await cliente.post("/materiales", json=_cuerpo(**cambios))
    assert r.status_code == 201, r.json()


# ---------------------------------------------------------------------------------------
# Criterio 2: 400 con el mensaje de la causa, sin persistir
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("cambios", "mensaje"),
    [
        # 2.1 Nombre obligatorio
        ({"nombre": ...}, mensajes.HU01_C2_1),
        ({"nombre": None}, mensajes.HU01_C2_1),
        ({"nombre": "    "}, mensajes.HU01_C2_1),
        # 2.2 Nombre: longitud o caracteres
        ({"nombre": "Ac"}, mensajes.HU01_C2_2_A),
        ({"nombre": "  A    "}, mensajes.HU01_C2_2_A),  # se cuenta después de normalizar
        ({"nombre": "x" * 101}, mensajes.HU01_C2_2_A),
        ({"nombre": "Acero@1045"}, mensajes.HU01_C2_2_B),
        ({"nombre": "Acero_1045"}, mensajes.HU01_C2_2_B),
        ({"nombre": 1045}, mensajes.HU01_C2_2_B),
        # 2.3 Categoría
        ({"categoria": ...}, mensajes.HU01_C2_3_A),
        ({"categoria": None}, mensajes.HU01_C2_3_A),
        ({"categoria": "Metales"}, formatear(mensajes.HU01_C2_3_B, valor="Metales")),
        ({"categoria": "materia prima"}, formatear(mensajes.HU01_C2_3_B, valor="materia prima")),
        # 2.4 Unidad de medida
        ({"unidadMedida": ...}, mensajes.HU01_C2_4_A),
        ({"unidadMedida": "lb"}, formatear(mensajes.HU01_C2_4_B, valor="lb")),
        ({"unidadMedida": "KG"}, formatear(mensajes.HU01_C2_4_B, valor="KG")),
        # 2.5 Densidad
        ({"densidad": ...}, mensajes.HU01_C2_5_A),
        ({"densidad": None}, mensajes.HU01_C2_5_A),
        ({"densidad": 0}, mensajes.HU01_C2_5_B),
        ({"densidad": -1}, mensajes.HU01_C2_5_B),
        ({"densidad": 10000}, mensajes.HU01_C2_5_B),
        ({"densidad": 7.856}, mensajes.HU01_C2_5_B),
        ({"densidad": "abc"}, mensajes.HU01_C2_5_B),
        ({"densidad": True}, mensajes.HU01_C2_5_B),
        # 2.6 Pureza
        ({"pureza": ...}, mensajes.HU01_C2_6_A),
        ({"pureza": 101}, mensajes.HU01_C2_6_B),
        ({"pureza": -1}, mensajes.HU01_C2_6_B),
        ({"pureza": 99.5}, mensajes.HU01_C2_6_B),
        ({"pureza": "abc"}, mensajes.HU01_C2_6_B),
    ],
)
async def test_c02_responde_400_con_el_mensaje_de_la_causa(
    cliente: httpx.AsyncClient, escenario: Escenario, cambios: dict[str, Any], mensaje: str
) -> None:
    r = await cliente.post("/materiales", json=_cuerpo(**cambios))
    assert (r.status_code, r.json()["mensaje"]) == (400, mensaje)
    assert r.json()["traceId"] == r.headers["X-Trace-Id"]
    assert escenario.inventario.altas == []
    _sin_persistir(escenario)


async def test_c02_reporta_el_primer_campo_en_el_orden_del_criterio_1(cliente: httpx.AsyncClient, escenario: Escenario) -> None:
    r = await cliente.post("/materiales", json={"categoria": "Otra", "densidad": -1})
    assert r.json()["mensaje"] == mensajes.HU01_C2_1


async def test_c02_rechaza_campos_de_solo_lectura(cliente: httpx.AsyncClient, escenario: Escenario) -> None:
    r = await cliente.post("/materiales", json=_cuerpo(sku="MP-00001"))
    assert r.status_code == 400
    assert escenario.inventario.altas == []


# ---------------------------------------------------------------------------------------
# Criterio 3: nombre repetido en el catálogo
# ---------------------------------------------------------------------------------------


async def test_c03_responde_409_si_el_nombre_ya_existe_sin_distinguir_mayusculas(
    cliente: httpx.AsyncClient, escenario: Escenario
) -> None:
    escenario.materiales.agregar(un_material(1, nombre="Ácido Cítrico"))
    r = await cliente.post("/materiales", json=_cuerpo(nombre="  ÁCIDO   cítrico "))
    assert r.status_code == 409
    assert r.json()["mensaje"] == formatear(mensajes.HU01_C3, Nombre="ÁCIDO cítrico")
    assert escenario.inventario.altas == []  # no se llega a Inventario
    assert list(escenario.materiales.materiales) == ["mat-001"]
    assert [(a.operacion, a.resultado_http) for a in escenario.auditoria.registros] == [("REGISTRAR_MATERIAL", 409)]


async def test_c03_registro_simultaneo_del_mismo_nombre_responde_409(cliente: httpx.AsyncClient, escenario: Escenario) -> None:
    """Otra petición guarda el mismo nombre entre la verificación y el commit: el índice
    único de la base de datos lo rechaza y se responde igual que en c3."""
    escenario.uow.error_en_commit = ErrorIntegridadDatos("duplicado", "uq_material_nombre_lower")
    r = await cliente.post("/materiales", json=_cuerpo())
    assert (r.status_code, r.json()["mensaje"]) == (409, formatear(mensajes.HU01_C3, Nombre=VALIDO["nombre"]))
    assert escenario.uow.confirmaciones == 0


# ---------------------------------------------------------------------------------------
# Criterio 4: alta de la materia prima en Inventario
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("categoria", ["Materia Prima", "Componentes", "Lubricantes"])
async def test_c04_envia_nombre_y_unidad_a_inventario_sin_importar_la_categoria(
    cliente: httpx.AsyncClient, escenario: Escenario, categoria: str
) -> None:
    r = await cliente.post("/materiales", json=_cuerpo(categoria=categoria, unidadMedida="mL"))
    assert r.status_code == 201
    assert escenario.inventario.altas == [("Acero al carbono 1045", "mL")]


# ---------------------------------------------------------------------------------------
# Criterio 5: Inventario ya tiene un artículo con ese nombre
# ---------------------------------------------------------------------------------------


async def test_c05_responde_409_si_inventario_rechaza_el_nombre(cliente: httpx.AsyncClient, escenario: Escenario) -> None:
    escenario.inventario.nombre_duplicado = True
    r = await cliente.post("/materiales", json=_cuerpo())
    assert r.status_code == 409
    assert r.json()["mensaje"] == formatear(mensajes.HU01_C5, Nombre="Acero al carbono 1045")
    _sin_persistir(escenario)


# ---------------------------------------------------------------------------------------
# Criterio 6: Inventario no responde, falla o tarda más de 5 s
# ---------------------------------------------------------------------------------------


async def test_c06_responde_503_con_trace_id_y_lo_registra_en_el_log(
    cliente: httpx.AsyncClient, escenario: Escenario, caplog: pytest.LogCaptureFixture
) -> None:
    escenario.inventario.caido = True
    with caplog.at_level(logging.ERROR):
        r = await cliente.post("/materiales", json=_cuerpo())
    assert r.status_code == 503
    trace_id = r.headers["X-Trace-Id"]
    assert r.json() == {"mensaje": mensajes.HU01_C6, "traceId": trace_id}
    assert any(rec.levelno == logging.ERROR and getattr(rec, "trace_id", None) == trace_id for rec in caplog.records)
    _sin_persistir(escenario)
    assert [a.resultado_http for a in escenario.auditoria.registros] == [503]


async def test_c06_codigo_de_inventario_con_formato_invalido_responde_503(cliente: httpx.AsyncClient, escenario: Escenario) -> None:
    escenario.inventario.sku = "ART-1"
    r = await cliente.post("/materiales", json=_cuerpo())
    assert (r.status_code, r.json()["mensaje"]) == (503, mensajes.HU01_C6)
    _sin_persistir(escenario)


# ---------------------------------------------------------------------------------------
# Criterio 7: 201 con el material creado
# ---------------------------------------------------------------------------------------


async def test_c07_responde_201_con_el_material_creado(cliente: httpx.AsyncClient, escenario: Escenario) -> None:
    escenario.inventario.sku = "MP-00042"
    antes = datetime.now(UTC)
    r = await cliente.post("/materiales", json=_cuerpo(categoria="Lubricantes"))
    assert r.status_code == 201
    datos = r.json()
    fecha_registro = datetime.fromisoformat(datos.pop("fechaRegistro"))
    fecha_actualizacion = datetime.fromisoformat(datos.pop("fechaUltimaActualizacion"))
    assert datos == {
        "materialId": "mat-001",  # 7.1
        "sku": "MP-00042",  # 7.2
        "nombre": "Acero al carbono 1045",
        "categoria": "Lubricantes",
        "unidadMedida": "kg",
        "densidad": 7.85,
        "pureza": 98,
        "estado": "ACTIVO",  # 7.3
        "mensaje": "Material 'Acero al carbono 1045' registrado exitosamente con el SKU MP-00042.",
    }
    assert antes - timedelta(seconds=1) <= fecha_registro <= datetime.now(UTC)  # 7.4
    assert fecha_actualizacion == fecha_registro  # 7.5
    assert escenario.uow.confirmaciones == 1
    assert [(a.operacion, a.recurso_id, a.resultado_http, a.detalle) for a in escenario.auditoria.registros] == [
        ("REGISTRAR_MATERIAL", "mat-001", 201, {"sku": "MP-00042"})
    ]
    assert [(e.nombre, dict(e.datos)) for e in escenario.eventos] == [
        ("MaterialRegistrado", {"materialId": "mat-001", "sku": "MP-00042"})
    ]


async def test_c07_el_id_es_secuencial(cliente: httpx.AsyncClient, escenario: Escenario) -> None:
    r1 = await cliente.post("/materiales", json=_cuerpo(nombre="Material uno"))
    escenario.inventario.sku = "MP-00002"
    r2 = await cliente.post("/materiales", json=_cuerpo(nombre="Material dos"))
    assert (r1.json()["materialId"], r2.json()["materialId"]) == ("mat-001", "mat-002")


# ---------------------------------------------------------------------------------------
# Criterio 8: fallo de la base de datos al guardar
# ---------------------------------------------------------------------------------------


async def test_c08_responde_500_revierte_y_registra_el_sku_en_el_log(
    cliente: httpx.AsyncClient, escenario: Escenario, caplog: pytest.LogCaptureFixture
) -> None:
    escenario.uow.fallar_en_commit = True
    escenario.inventario.sku = "MP-00077"
    with caplog.at_level(logging.ERROR):
        r = await cliente.post("/materiales", json=_cuerpo())
    assert r.status_code == 500
    trace_id = r.headers["X-Trace-Id"]
    assert r.json() == {"mensaje": mensajes.HU01_C8, "traceId": trace_id}
    assert escenario.uow.confirmaciones == 0
    assert escenario.uow.reversiones >= 1
    assert escenario.eventos == []
    registros_sku = [rec for rec in caplog.records if getattr(rec, "sku", None) == "MP-00077"]
    assert registros_sku and registros_sku[0].levelno == logging.ERROR
    assert any(getattr(rec, "trace_id", None) == trace_id for rec in caplog.records)
