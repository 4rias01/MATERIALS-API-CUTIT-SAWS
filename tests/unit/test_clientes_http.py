"""Clientes HTTP: base (timeout, circuit breaker, cabeceras y métricas) y cliente de Inventario."""

import asyncio
import json
from collections.abc import Callable

import httpx
import pytest

from app.core.config import Configuracion
from app.core.contexto import establecer_contexto, restablecer_contexto
from app.core.exceptions import ErrorServicioExterno
from app.infraestructure.clients import CircuitBreaker, ClienteHttpBase, EstadoCircuito, InventarioClient
from app.infraestructure.interfaces import IClienteExterno, IInventarioClient, NombreDuplicadoEnInventarioError
from tests.conftest import configuracion_de_prueba


class Reloj:
    def __init__(self) -> None:
        self.ahora = 0.0

    def __call__(self) -> float:
        return self.ahora


class ClienteDePrueba(ClienteHttpBase):
    """Cliente concreto mínimo: una operación que devuelve el campo ``valor``."""

    async def consultar(self) -> str:
        respuesta = await self._enviar("POST", "/recurso", json={"dato": 1})
        if respuesta.status_code != 200:
            raise self._respuesta_inesperada(respuesta)
        valor = self._json(respuesta).get("valor")
        if not isinstance(valor, str):
            raise self._respuesta_inesperada(respuesta)
        return valor


def _cliente(
    manejador: Callable[[httpx.Request], object],
    url_base: str | None = "http://otra.celula/",
    timeout_s: float = 5.0,
    circuito: CircuitBreaker | None = None,
) -> ClienteDePrueba:
    return ClienteDePrueba(
        servicio="prueba",
        http=httpx.AsyncClient(transport=httpx.MockTransport(manejador)),  # type: ignore[arg-type]
        url_base=url_base,
        timeout_s=timeout_s,
        circuito=circuito or CircuitBreaker("prueba"),
        nombre_origen="materiales-formulas",
    )


# ── Circuit breaker ────────────────────────────────────────────────────────────


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


def test_liberar_prueba_permite_otra_llamada_de_prueba() -> None:
    reloj = Reloj()
    circuito = CircuitBreaker("prueba", umbral_fallos=1, tiempo_abierto_s=1, reloj=reloj)
    circuito.registrar_fallo()
    reloj.ahora = 1
    assert circuito.permite_llamada()
    circuito.liberar_prueba()  # la llamada se canceló sin resultado
    assert circuito.permite_llamada()


# ── Cliente HTTP base ──────────────────────────────────────────────────────────


def test_el_cliente_base_cumple_la_interfaz_de_cliente_externo() -> None:
    cliente = _cliente(lambda _: httpx.Response(200))
    assert isinstance(cliente, IClienteExterno)
    assert cliente.estado_circuito() == "CERRADO"


async def test_envia_la_peticion_y_propaga_el_trace_id_y_el_origen() -> None:
    recibidas: list[httpx.Request] = []

    def manejador(peticion: httpx.Request) -> httpx.Response:
        recibidas.append(peticion)
        return httpx.Response(200, json={"valor": "ok"})

    tokens = establecer_contexto("traza-de-prueba-123", "pruebas")
    try:
        valor = await _cliente(manejador).consultar()
    finally:
        restablecer_contexto(tokens)

    assert valor == "ok"
    peticion = recibidas[0]
    assert (peticion.method, str(peticion.url), peticion.content) == ("POST", "http://otra.celula/recurso", b'{"dato":1}')
    assert peticion.headers["X-Trace-Id"] == "traza-de-prueba-123"
    assert peticion.headers["X-Servicio-Origen"] == "materiales-formulas"


@pytest.mark.parametrize(
    ("respuesta", "causa"),
    [
        (httpx.Response(500), ErrorServicioExterno.ERROR_INTERNO),
        (httpx.Response(200, json={}), ErrorServicioExterno.RESPUESTA_INESPERADA),
        (httpx.Response(200, json=[1, 2]), ErrorServicioExterno.RESPUESTA_INESPERADA),
        (httpx.Response(200, text="no es json"), ErrorServicioExterno.RESPUESTA_INESPERADA),
        (httpx.Response(400, json={"mensaje": "x"}), ErrorServicioExterno.RESPUESTA_INESPERADA),
    ],
)
async def test_respuestas_de_error(respuesta: httpx.Response, causa: str) -> None:
    with pytest.raises(ErrorServicioExterno) as error:
        await _cliente(lambda _: respuesta).consultar()
    assert error.value.causa == causa


async def test_error_de_conexion() -> None:
    def manejador(peticion: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("conexión rechazada", request=peticion)

    with pytest.raises(ErrorServicioExterno) as error:
        await _cliente(manejador).consultar()
    assert error.value.causa == ErrorServicioExterno.CONEXION


async def test_timeout_total_de_la_llamada() -> None:
    async def manejador_lento(peticion: httpx.Request) -> httpx.Response:
        await asyncio.sleep(1)
        return httpx.Response(200, json={"valor": "tarde"})

    with pytest.raises(ErrorServicioExterno) as error:
        await _cliente(manejador_lento, timeout_s=0.05).consultar()
    assert error.value.causa == ErrorServicioExterno.TIMEOUT


async def test_una_llamada_cancelada_libera_la_prueba_del_circuito() -> None:
    def manejador(_: httpx.Request) -> httpx.Response:
        raise asyncio.CancelledError

    reloj = Reloj()
    circuito = CircuitBreaker("prueba", umbral_fallos=1, tiempo_abierto_s=1, reloj=reloj)
    circuito.registrar_fallo()
    reloj.ahora = 1
    with pytest.raises(asyncio.CancelledError):
        await _cliente(manejador, circuito=circuito).consultar()
    assert circuito.permite_llamada()


async def test_circuito_abierto_rechaza_sin_llamar() -> None:
    llamadas = 0

    def manejador(_: httpx.Request) -> httpx.Response:
        nonlocal llamadas
        llamadas += 1
        return httpx.Response(503)

    cliente = _cliente(manejador, circuito=CircuitBreaker("prueba", umbral_fallos=2))
    for _ in range(2):
        with pytest.raises(ErrorServicioExterno):
            await cliente.consultar()
    with pytest.raises(ErrorServicioExterno) as error:
        await cliente.consultar()
    assert error.value.causa == ErrorServicioExterno.CIRCUITO_ABIERTO
    assert llamadas == 2
    assert cliente.estado_circuito() == "ABIERTO"


async def test_sin_url_configurada() -> None:
    with pytest.raises(ErrorServicioExterno) as error:
        await _cliente(lambda _: httpx.Response(200), url_base=None).consultar()
    assert error.value.causa == ErrorServicioExterno.SIN_CONFIGURAR


# ── Cliente de Inventario (HU-01 c4 y c5) ──────────────────────────────────────


def _inventario(manejador: Callable[[httpx.Request], object], config: Configuracion | None = None) -> InventarioClient:
    return InventarioClient(
        httpx.AsyncClient(transport=httpx.MockTransport(manejador)),  # type: ignore[arg-type]
        config or configuracion_de_prueba(),
        CircuitBreaker("inventario"),
    )


async def test_registrar_materia_prima_devuelve_el_codigo_de_articulo() -> None:
    recibidas: list[httpx.Request] = []

    def manejador(peticion: httpx.Request) -> httpx.Response:
        recibidas.append(peticion)
        return httpx.Response(201, json={"codigo": "MP-00007"})

    cliente = _inventario(manejador)
    assert isinstance(cliente, IInventarioClient)
    assert await cliente.registrar_materia_prima("Acero 1045", "kg") == "MP-00007"
    peticion = recibidas[0]
    assert (peticion.method, str(peticion.url)) == ("POST", "http://inventario.prueba/inventario/materias-primas")
    assert json.loads(peticion.content) == {"nombre": "Acero 1045", "unidadMedida": "kg"}


async def test_nombre_duplicado_en_inventario() -> None:
    cliente = _inventario(lambda _: httpx.Response(409, json={"mensaje": "Ya existe un artículo con el nombre Acero"}))
    with pytest.raises(NombreDuplicadoEnInventarioError) as error:
        await cliente.registrar_materia_prima("Acero", "kg")
    assert error.value.mensaje_recibido == "Ya existe un artículo con el nombre Acero"


@pytest.mark.parametrize(
    "respuesta",
    [httpx.Response(201, json={}), httpx.Response(201, json={"codigo": 7}), httpx.Response(400, json={"mensaje": "x"})],
)
async def test_respuestas_inesperadas_de_inventario(respuesta: httpx.Response) -> None:
    with pytest.raises(ErrorServicioExterno) as error:
        await _inventario(lambda _: respuesta).registrar_materia_prima("Acero", "kg")
    assert error.value.causa == ErrorServicioExterno.RESPUESTA_INESPERADA


async def test_inventario_sin_url_configurada() -> None:
    cliente = _inventario(lambda _: httpx.Response(201), configuracion_de_prueba(inventario_url=None))
    with pytest.raises(ErrorServicioExterno) as error:
        await cliente.registrar_materia_prima("Acero", "kg")
    assert error.value.causa == ErrorServicioExterno.SIN_CONFIGURAR


@pytest.mark.parametrize("codigo_http", [200, 204])
async def test_actualizar_articulo_envia_solo_el_nombre_al_sku_indicado(codigo_http: int) -> None:
    def confirmar(peticion: httpx.Request) -> httpx.Response:
        assert peticion.method == "PATCH"
        assert peticion.url.path == "/inventario/articulos/MP-00007"
        assert json.loads(peticion.content) == {"nombre": "Acero 1045"}
        return httpx.Response(codigo_http)

    await _inventario(confirmar).actualizar_articulo("MP-00007", "Acero 1045")


async def test_actualizar_articulo_reconoce_rechazo_por_duplicado() -> None:
    cliente = _inventario(lambda _: httpx.Response(409))
    with pytest.raises(NombreDuplicadoEnInventarioError):
        await cliente.actualizar_articulo("MP-00007", "Acero")
