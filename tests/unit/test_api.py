"""Capa de presentación: traceId, manejador global de excepciones, /health, /metrics y OpenAPI."""

import httpx
import pytest
from fastapi import FastAPI

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


def _ruta_que_lanza(app: FastAPI, ruta: str, error: Exception) -> None:
    async def lanzar() -> None:
        raise error

    app.add_api_route(ruta, lanzar, methods=["GET"])


# ---------------------------------------------------------------------------------------
# traceId (Correlation ID)
# ---------------------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------------------
# Manejador global de excepciones
# ---------------------------------------------------------------------------------------


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
async def test_cada_error_de_aplicacion_se_traduce_a_su_codigo(
    app: FastAPI, cliente: httpx.AsyncClient, error: Exception, codigo: int
) -> None:
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


async def test_validacion_usa_el_mensaje_de_la_ruta(cliente: httpx.AsyncClient) -> None:
    r = await cliente.delete("/materiales/no-es-un-id")
    assert (r.status_code, r.json()["mensaje"]) == (400, mensajes.HU04_C3)
    r = await cliente.patch("/formulas/123/descontinuar")
    assert (r.status_code, r.json()["mensaje"]) == (400, mensajes.HU08_C3)


async def test_validacion_sin_mensaje_propio_usa_el_generico(cliente: httpx.AsyncClient) -> None:
    r = await cliente.post("/materiales", content=b"{no es json", headers={"Content-Type": "application/json"})
    assert (r.status_code, r.json()["mensaje"]) == (400, mensajes.SOLICITUD_INVALIDA)


async def test_rechaza_campos_no_permitidos(cliente: httpx.AsyncClient) -> None:
    cuerpo = {"nombre": "Acero", "categoria": "Materia Prima", "densidad": 7.8, "pureza": 98, "sku": "MP-00001"}
    r = await cliente.put("/materiales/mat-001", json=cuerpo)
    assert r.status_code == 400


# ---------------------------------------------------------------------------------------
# /health y /metrics
# ---------------------------------------------------------------------------------------


async def test_health_responde_503_si_la_base_de_datos_no_responde(cliente: httpx.AsyncClient) -> None:
    r = await cliente.get("/health")
    assert r.status_code == 503
    assert r.json() == {
        "estado": "DEGRADADO",
        "version": "0.1.0",
        "baseDatos": "ERROR",
        "circuitos": {"inventario": "CERRADO", "patentSweep": "CERRADO"},
    }


async def test_metrics_expone_las_metricas_para_prometheus(cliente: httpx.AsyncClient) -> None:
    await cliente.get("/no-existe")
    r = await cliente.get("/metrics")
    assert r.status_code == 200
    assert "http_requests_total" in r.text
    assert "materiales_formulas_circuito_abierto" in r.text


# ---------------------------------------------------------------------------------------
# Contrato OpenAPI
# ---------------------------------------------------------------------------------------

RUTAS = {
    ("post", "/materiales"): "201",
    ("get", "/materiales"): "200",
    ("get", "/materiales/{id_material}"): "200",
    ("put", "/materiales/{id_material}"): "200",
    ("delete", "/materiales/{id_material}"): "200",
    ("post", "/formulas"): "201",
    ("get", "/formulas"): "200",
    ("get", "/formulas/aprobadas"): "200",
    ("get", "/formulas/{id_formula}"): "200",
    ("put", "/formulas/{id_formula}"): "200",
    ("patch", "/formulas/{id_formula}/descontinuar"): "200",
    ("post", "/formulas/{id_formula}/evaluacion-patente"): "202",
    ("post", "/formulas/{id_formula}/dictamen-patente"): "200",
    ("get", "/health"): "200",
}


async def test_el_contrato_publica_todas_las_rutas_del_das(app: FastAPI) -> None:
    esquema = app.openapi()
    publicadas = {(m, p) for p, operaciones in esquema["paths"].items() for m in operaciones}
    assert publicadas == set(RUTAS)
    for (metodo, ruta), exito in RUTAS.items():
        assert exito in esquema["paths"][ruta][metodo]["responses"], (metodo, ruta)


async def test_los_errores_de_validacion_se_documentan_como_400(app: FastAPI) -> None:
    esquema = app.openapi()
    assert "HTTPValidationError" not in esquema["components"]["schemas"]
    assert "422" not in esquema["paths"]["/materiales"]["post"]["responses"]
    assert "422" in esquema["paths"]["/formulas"]["post"]["responses"]  # regla de negocio (HU-05 c4)
