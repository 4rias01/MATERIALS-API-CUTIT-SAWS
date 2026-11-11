"""Cliente de Inventario: timeout, circuit breaker, cabeceras y contrato."""

import asyncio
import json
from collections.abc import Callable

import httpx
import pytest

from app.core.config import Configuracion
from app.core.contexto import establecer_contexto, restablecer_contexto
from app.core.exceptions import ErrorServicioExterno
from app.infraestructure.clients import CircuitBreaker, EstadoCircuito, InventarioClient
from app.infraestructure.interfaces import NombreDuplicadoEnInventarioError
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


async def test_sin_url_configurada() -> None:
    cliente = _inventario(lambda _: httpx.Response(201), config=configuracion_de_prueba(inventario_url=None))
    with pytest.raises(ErrorServicioExterno) as error:
        await cliente.registrar_materia_prima("Acero", "kg")
    assert error.value.causa == ErrorServicioExterno.SIN_CONFIGURAR
