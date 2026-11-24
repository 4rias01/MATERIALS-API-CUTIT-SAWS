"""Capa de presentación: traceId, manejador global de excepciones, /health, /metrics y OpenAPI."""

import httpx
import pytest
from fastapi import FastAPI

from app.api.schemas.comun import EsquemaEntrada, mensaje_solicitud_invalida
from app.business.domain import mensajes
from app.core.exceptions import (
    ConflictoError,
    DependenciaNoDisponibleError,
    ErrorInterno,
    NoImplementadoError,
    RecursoNoEncontradoError,
    ReglaDeNegocioError,
    SolicitudInvalidaError,
)
from tests.dobles import ClienteExternoFalso


class CuerpoDePrueba(EsquemaEntrada):
    nombre: str


def _ruta_con_cuerpo(app: FastAPI) -> None:
    async def crear(cuerpo: CuerpoDePrueba) -> None: ...

    app.add_api_route("/prueba-cuerpo", crear, methods=["POST"], status_code=201)


def _ruta_que_lanza(app: FastAPI, ruta: str, error: Exception) -> None:
    async def lanzar() -> None:
        raise error

    app.add_api_route(ruta, lanzar, methods=["GET"])


# ── traceId (Correlation ID) ───────────────────────────────────────────────────


async def test_cada_respuesta_lleva_un_trace_id_nuevo(cliente: httpx.AsyncClient) -> None:
    r1 = await cliente.get("/no-existe")
    r2 = await cliente.get("/no-existe")
    assert len(r1.headers["X-Trace-Id"]) == 32
    assert r1.headers["X-Trace-Id"] != r2.headers["X-Trace-Id"]
    assert r1.json()["traceId"] == r1.headers["X-Trace-Id"]


async def test_reutiliza_el_trace_id_recibido_si_es_valido(cliente: httpx.AsyncClient) -> None:
    r = await cliente.get("/no-existe", headers={"X-Trace-Id": "abc-123-def-456"})
    assert r.headers["X-Trace-Id"] == "abc-123-def-456"
    r = await cliente.get("/no-existe", headers={"X-Trace-Id": "malo\nlinea"})
    assert r.headers["X-Trace-Id"] != "malo\nlinea"


# ── Manejador global de excepciones ────────────────────────────────────────────


@pytest.mark.parametrize(
    ("error", "codigo"),
    [
        (SolicitudInvalidaError("a"), 400),
        (RecursoNoEncontradoError("b"), 404),
        (ConflictoError("c"), 409),
        (ReglaDeNegocioError("d"), 422),
        (ErrorInterno("e"), 500),
        (DependenciaNoDisponibleError("f"), 503),
    ],
)
async def test_cada_error_de_aplicacion_se_traduce_a_su_codigo(app: FastAPI, cliente: httpx.AsyncClient, error: Exception, codigo: int) -> None:
    _ruta_que_lanza(app, "/prueba-error", error)
    r = await cliente.get("/prueba-error")
    assert r.status_code == codigo
    assert r.json() == {"mensaje": str(error), "traceId": r.headers["X-Trace-Id"]}


async def test_no_implementado_responde_501(app: FastAPI, cliente: httpx.AsyncClient) -> None:
    _ruta_que_lanza(app, "/prueba-501", NoImplementadoError("HU-99"))
    r = await cliente.get("/prueba-501")
    assert r.status_code == 501
    assert "HU-99" in r.json()["mensaje"]


async def test_error_no_controlado_responde_500_sin_detalles_internos(app: FastAPI, cliente: httpx.AsyncClient) -> None:
    _ruta_que_lanza(app, "/prueba-500", RuntimeError("detalle interno secreto"))
    r = await cliente.get("/prueba-500")
    assert r.status_code == 500
    assert r.json()["mensaje"] == mensajes.ERROR_INTERNO
    assert "secreto" not in r.text
    assert r.json()["traceId"] == r.headers["X-Trace-Id"]


async def test_ruta_inexistente_y_metodo_no_permitido(cliente: httpx.AsyncClient) -> None:
    r = await cliente.get("/no-existe")
    assert (r.status_code, r.json()["mensaje"]) == (404, mensajes.RUTA_NO_ENCONTRADA)
    r = await cliente.put("/health")
    assert (r.status_code, r.json()["mensaje"]) == (405, mensajes.METODO_NO_PERMITIDO)


async def test_validacion_usa_el_mensaje_de_la_ruta(app: FastAPI, cliente: httpx.AsyncClient) -> None:
    async def con_parametro(numero: int) -> None: ...

    app.add_api_route("/prueba-validacion/{numero}", con_parametro, methods=["GET"], openapi_extra=mensaje_solicitud_invalida("Mensaje de la ruta"))
    r = await cliente.get("/prueba-validacion/no-es-un-numero")
    assert (r.status_code, r.json()["mensaje"]) == (400, "Mensaje de la ruta")


async def test_validacion_sin_mensaje_propio_usa_el_generico(app: FastAPI, cliente: httpx.AsyncClient) -> None:
    _ruta_con_cuerpo(app)
    r = await cliente.post("/prueba-cuerpo", content=b"{no es json", headers={"Content-Type": "application/json"})
    assert (r.status_code, r.json()["mensaje"]) == (400, mensajes.SOLICITUD_INVALIDA)


async def test_rechaza_campos_no_permitidos(app: FastAPI, cliente: httpx.AsyncClient) -> None:
    _ruta_con_cuerpo(app)
    r = await cliente.post("/prueba-cuerpo", json={"nombre": "Acero", "sku": "MP-00001"})
    assert (r.status_code, r.json()["mensaje"]) == (400, mensajes.SOLICITUD_INVALIDA)
    assert (await cliente.post("/prueba-cuerpo", json={"nombre": "Acero"})).status_code == 201


# ── /health y /metrics ─────────────────────────────────────────────────────────


async def test_health_responde_503_si_la_base_de_datos_no_responde(cliente: httpx.AsyncClient) -> None:
    r = await cliente.get("/health")
    assert r.status_code == 503
    assert r.json() == {"estado": "DEGRADADO", "version": "0.1.0", "baseDatos": "ERROR", "circuitos": {"inventario": "CERRADO"}}


async def test_health_muestra_el_circuito_de_cada_cliente_externo(app: FastAPI, cliente: httpx.AsyncClient) -> None:
    app.state.clientes_externos = {"inventario": ClienteExternoFalso("ABIERTO")}
    r = await cliente.get("/health")
    assert r.json()["circuitos"] == {"inventario": "ABIERTO"}


async def test_metrics_expone_las_metricas_para_prometheus(cliente: httpx.AsyncClient) -> None:
    await cliente.get("/no-existe")
    r = await cliente.get("/metrics")
    assert r.status_code == 200
    assert "http_requests_total" in r.text
    assert "materiales_formulas_eventos_negocio_total" in r.text


# ── Contrato OpenAPI ───────────────────────────────────────────────────────────

RUTAS = {
    ("get", "/health"): "200",
    ("post", "/materiales"): "201",
    ("post", "/formulas"): "201",
    ("get", "/materiales"): "200",
    ("get", "/materiales/buscar"): "200",
    ("get", "/materiales/{id_material}"): "200",
    ("put", "/materiales/{id_material}"): "200",
    ("delete", "/materiales/{id_material}"): "204",
}


async def test_el_contrato_publica_las_rutas_implementadas(app: FastAPI) -> None:
    esquema = app.openapi()
    publicadas = {(m, p) for p, operaciones in esquema["paths"].items() for m in operaciones}
    assert publicadas == set(RUTAS)
    for (metodo, ruta), exito in RUTAS.items():
        assert exito in esquema["paths"][ruta][metodo]["responses"], (metodo, ruta)


async def test_los_errores_de_validacion_se_documentan_como_400(app: FastAPI) -> None:
    esquema = app.openapi()
    assert "HTTPValidationError" not in esquema["components"]["schemas"]
    assert "422" not in esquema["paths"]["/materiales"]["post"]["responses"]
    assert app.openapi() is esquema  # se genera una sola vez
