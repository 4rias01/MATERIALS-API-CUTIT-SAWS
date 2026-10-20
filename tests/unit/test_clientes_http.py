"""Clientes de Inventario y Patent Sweep: timeout, circuit breaker, cabeceras y contrato."""

import asyncio
import json
from collections.abc import Callable
from decimal import Decimal

import httpx
import pytest

from app.core.config import Configuracion
from app.core.contexto import establecer_contexto, restablecer_contexto
from app.core.exceptions import ErrorServicioExterno
from app.data_access.clients import CircuitBreaker, EstadoCircuito, InventarioClient, PatentSweepClient
from app.data_access.interfaces import ComponenteEvaluacion, NombreDuplicadoEnInventarioError, SolicitudEvaluacionPatente
from tests.conftest import configuracion_de_prueba

Manejador = Callable[[httpx.Request], httpx.Response]


class Reloj:
    def __init__(self) -> None:
        self.ahora = 0.0

    def __call__(self) -> float:
        return self.ahora


def _http(manejador: Manejador) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(manejador))


def _inventario(manejador: Manejador, config: Configuracion | None = None, circuito: CircuitBreaker | None = None) -> InventarioClient:
    return InventarioClient(_http(manejador), config or configuracion_de_prueba(), circuito or CircuitBreaker("inventario"))


def _solicitud() -> SolicitudEvaluacionPatente:
    return SolicitudEvaluacionPatente(
        formula_id="form-001",
        ticket_evaluacion_id="tck-001",
        nombre="Aleacion",
        aplicacion_tecnica="Corte",
        componentes=[
            ComponenteEvaluacion("mat-001", "Acero", Decimal("2.500"), "kg"),
            ComponenteEvaluacion("mat-002", "Tornillo", Decimal("4"), "und"),
        ],
    )


# ---------------------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------------------


def test_circuit_breaker_se_abre_tras_el_umbral_y_se_recupera() -> None:
    reloj = Reloj()
    circuito = CircuitBreaker("prueba", umbral_fallos=3, tiempo_abierto_s=30, reloj=reloj)
    for _ in range(2):
        assert circuito.permite_llamada()
        circuito.registrar_fallo()
    assert circuito.estado == EstadoCircuito.CERRADO
    circuito.registrar_fallo()
    assert circuito.estado == EstadoCircuito.ABIERTO
    assert not circuito.permite_llamada()

    reloj.ahora = 30
    assert circuito.estado == EstadoCircuito.SEMIABIERTO
    assert circuito.permite_llamada()  # única llamada de prueba
    assert not circuito.permite_llamada()
    circuito.registrar_exito()
    assert circuito.estado == EstadoCircuito.CERRADO


def test_circuit_breaker_semiabierto_vuelve_a_abrirse_si_la_prueba_falla() -> None:
    reloj = Reloj()
    circuito = CircuitBreaker("prueba", umbral_fallos=1, tiempo_abierto_s=10, reloj=reloj)
    circuito.registrar_fallo()
    reloj.ahora = 10
    assert circuito.permite_llamada()
    circuito.registrar_fallo()
    assert circuito.estado == EstadoCircuito.ABIERTO


def test_un_exito_reinicia_el_conteo_de_fallos() -> None:
    circuito = CircuitBreaker("prueba", umbral_fallos=2)
    circuito.registrar_fallo()
    circuito.registrar_exito()
    circuito.registrar_fallo()
    assert circuito.estado == EstadoCircuito.CERRADO


# ---------------------------------------------------------------------------------------
# Inventario
# ---------------------------------------------------------------------------------------


async def test_registrar_materia_prima_devuelve_el_codigo_y_propaga_el_trace_id() -> None:
    recibidas: list[httpx.Request] = []

    def manejador(peticion: httpx.Request) -> httpx.Response:
        recibidas.append(peticion)
        return httpx.Response(201, json={"codigo": "MP-00007"})

    tokens = establecer_contexto("traza-de-prueba-123", "pruebas")
    try:
        sku = await _inventario(manejador).registrar_materia_prima("Acero 1045", "kg")
    finally:
        restablecer_contexto(tokens)

    assert sku == "MP-00007"
    peticion = recibidas[0]
    assert peticion.method == "POST"
    assert str(peticion.url) == "http://inventario.prueba/inventario/materias-primas"
    assert json.loads(peticion.content) == {"nombre": "Acero 1045", "unidadMedida": "kg"}
    assert peticion.headers["X-Trace-Id"] == "traza-de-prueba-123"
    assert peticion.headers["X-Servicio-Origen"] == "materiales-formulas"


async def test_nombre_duplicado_en_inventario() -> None:
    cliente = _inventario(lambda _: httpx.Response(409, json={"mensaje": "Ya existe un artículo con el nombre Acero"}))
    with pytest.raises(NombreDuplicadoEnInventarioError) as error:
        await cliente.registrar_materia_prima("Acero", "kg")
    assert error.value.mensaje_recibido == "Ya existe un artículo con el nombre Acero"


@pytest.mark.parametrize(
    ("respuesta", "causa"),
    [
        (httpx.Response(500), ErrorServicioExterno.ERROR_INTERNO),
        (httpx.Response(201, json={}), ErrorServicioExterno.RESPUESTA_INESPERADA),
        (httpx.Response(400, json={"mensaje": "x"}), ErrorServicioExterno.RESPUESTA_INESPERADA),
    ],
)
async def test_respuestas_de_error_de_inventario(respuesta: httpx.Response, causa: str) -> None:
    with pytest.raises(ErrorServicioExterno) as error:
        await _inventario(lambda _: respuesta).registrar_materia_prima("Acero", "kg")
    assert error.value.causa == causa


async def test_error_de_conexion() -> None:
    def manejador(peticion: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("conexión rechazada", request=peticion)

    with pytest.raises(ErrorServicioExterno) as error:
        await _inventario(manejador).registrar_materia_prima("Acero", "kg")
    assert error.value.causa == ErrorServicioExterno.CONEXION


async def test_timeout_total_de_la_llamada() -> None:
    async def manejador_lento(peticion: httpx.Request) -> httpx.Response:
        await asyncio.sleep(1)
        return httpx.Response(201, json={"codigo": "MP-00001"})

    config = configuracion_de_prueba(http_timeout_s=0.05)
    cliente = InventarioClient(httpx.AsyncClient(transport=httpx.MockTransport(manejador_lento)), config, CircuitBreaker("inventario"))
    with pytest.raises(ErrorServicioExterno) as error:
        await cliente.registrar_materia_prima("Acero", "kg")
    assert error.value.causa == ErrorServicioExterno.TIMEOUT


async def test_circuito_abierto_rechaza_sin_llamar() -> None:
    llamadas = 0

    def manejador(_: httpx.Request) -> httpx.Response:
        nonlocal llamadas
        llamadas += 1
        return httpx.Response(503)

    cliente = _inventario(manejador, circuito=CircuitBreaker("inventario", umbral_fallos=2))
    for _ in range(2):
        with pytest.raises(ErrorServicioExterno):
            await cliente.registrar_materia_prima("Acero", "kg")
    with pytest.raises(ErrorServicioExterno) as error:
        await cliente.registrar_materia_prima("Acero", "kg")
    assert error.value.causa == ErrorServicioExterno.CIRCUITO_ABIERTO
    assert llamadas == 2
    assert cliente.estado_circuito() == "ABIERTO"


async def test_modificar_nombre_articulo() -> None:
    recibidas: list[httpx.Request] = []

    def manejador(peticion: httpx.Request) -> httpx.Response:
        recibidas.append(peticion)
        return httpx.Response(204)

    await _inventario(manejador).modificar_nombre_articulo("MP-00001", "Nuevo nombre")
    assert recibidas[0].method == "PATCH"
    assert recibidas[0].url.path == "/inventario/articulos/MP-00001"
    assert json.loads(recibidas[0].content) == {"nombre": "Nuevo nombre"}


async def test_sin_url_configurada() -> None:
    cliente = _inventario(lambda _: httpx.Response(201), config=configuracion_de_prueba(inventario_url=None))
    with pytest.raises(ErrorServicioExterno) as error:
        await cliente.registrar_materia_prima("Acero", "kg")
    assert error.value.causa == ErrorServicioExterno.SIN_CONFIGURAR


# ---------------------------------------------------------------------------------------
# Patent Sweep
# ---------------------------------------------------------------------------------------


async def test_solicitud_de_evaluacion_con_el_contrato_de_hu09() -> None:
    recibidas: list[httpx.Request] = []

    def manejador(peticion: httpx.Request) -> httpx.Response:
        recibidas.append(peticion)
        return httpx.Response(202)

    cliente = PatentSweepClient(_http(manejador), configuracion_de_prueba(), CircuitBreaker("patent_sweep"))
    await cliente.solicitar_evaluacion(_solicitud())
    assert str(recibidas[0].url) == "http://patent-sweep.prueba/evaluaciones"
    assert json.loads(recibidas[0].content) == {
        "formulaId": "form-001",
        "ticketEvaluacionId": "tck-001",
        "nombre": "Aleacion",
        "aplicacionTecnica": "Corte",
        "componentes": [
            {"materialId": "mat-001", "nombre": "Acero", "cantidad": 2.5, "unidadMedida": "kg"},
            {"materialId": "mat-002", "nombre": "Tornillo", "cantidad": 4, "unidadMedida": "und"},
        ],
    }


async def test_patent_sweep_debe_responder_202() -> None:
    cliente = PatentSweepClient(_http(lambda _: httpx.Response(200)), configuracion_de_prueba(), CircuitBreaker("patent_sweep"))
    with pytest.raises(ErrorServicioExterno) as error:
        await cliente.solicitar_evaluacion(_solicitud())
    assert error.value.causa == ErrorServicioExterno.RESPUESTA_INESPERADA


async def test_patent_sweep_sin_ruta_configurada() -> None:
    config = configuracion_de_prueba(patent_sweep_ruta_evaluacion=None)
    cliente = PatentSweepClient(_http(lambda _: httpx.Response(202)), config, CircuitBreaker("patent_sweep"))
    with pytest.raises(ErrorServicioExterno) as error:
        await cliente.solicitar_evaluacion(_solicitud())
    assert error.value.causa == ErrorServicioExterno.SIN_CONFIGURAR
