"""Manejador global de excepciones (patrón Global Exception Handler).

Punto único donde cada resultado se traduce al código HTTP y al cuerpo
``{"mensaje": ..., "traceId": ...}``. Se registra en ``app/main.py``.

* ``ErrorAplicacion`` (400, 404, 409, 422, 500, 501, 503): mensaje del backlog.
* ``RequestValidationError``: 400 con el mensaje del backlog que produjo el DTO; si no
  hay, el mensaje de la ruta (``openapi_extra``) o el genérico.
* ``HTTPException`` de Starlette (ruta inexistente, método no permitido).
* Cualquier otra excepción: 500 con el mensaje genérico. Nunca se exponen detalles
  internos al cliente; el detalle completo queda en el log con el mismo traceId.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.business.domain import mensajes
from app.core.contexto import nuevo_trace_id, obtener_trace_id
from app.core.exceptions import ErrorAplicacion, NoImplementadoError
from app.presentation.middleware import CABECERA_TRACE_ID
from app.presentation.schemas.comun import CLAVE_MENSAJE_SOLICITUD_INVALIDA, TIPO_ERROR_NEGOCIO, ErrorRespuesta

logger = logging.getLogger("app.errores")


def _trace_id(request: Request) -> str:
    return getattr(request.state, "trace_id", None) or obtener_trace_id() or nuevo_trace_id()


def respuesta_error(request: Request, codigo: int, mensaje: str, cabeceras: dict[str, str] | None = None) -> JSONResponse:
    """Respuesta JSON de error con el traceId en el cuerpo y en la cabecera."""
    trace_id = _trace_id(request)
    cuerpo = ErrorRespuesta(mensaje=mensaje, trace_id=trace_id).model_dump(mode="json", by_alias=True)
    return JSONResponse(status_code=codigo, content=cuerpo, headers={**(cabeceras or {}), CABECERA_TRACE_ID: trace_id})


async def manejar_error_aplicacion(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ErrorAplicacion)
    datos = {"estado": exc.codigo_http, "error": type(exc).__name__, "trace_id": _trace_id(request)}
    if isinstance(exc, NoImplementadoError):
        logger.warning(exc.mensaje, extra=datos)
    elif exc.codigo_http >= 500:
        # exc_info incluye la causa encadenada (p. ej. el ErrorBaseDatos original).
        logger.error(exc.mensaje, exc_info=exc, extra=datos)
    else:
        logger.info(exc.mensaje, extra=datos)
    return respuesta_error(request, exc.codigo_http, exc.mensaje)


async def manejar_error_validacion(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    errores = exc.errors()
    if errores and errores[0].get("type") == TIPO_ERROR_NEGOCIO:
        mensaje = str(errores[0]["msg"])
    else:
        ruta = request.scope.get("route")
        extra = getattr(ruta, "openapi_extra", None) or {}
        mensaje = extra.get(CLAVE_MENSAJE_SOLICITUD_INVALIDA) or mensajes.SOLICITUD_INVALIDA
    logger.info(
        "Solicitud rechazada: %s",
        mensaje,
        extra={
            "estado": 400,
            "errores": [{"tipo": e.get("type"), "ubicacion": list(e.get("loc", ()))} for e in errores[:10]],
            "trace_id": _trace_id(request),
        },
    )
    return respuesta_error(request, 400, mensaje)


async def manejar_error_http(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    mensaje = {404: mensajes.RUTA_NO_ENCONTRADA, 405: mensajes.METODO_NO_PERMITIDO}.get(exc.status_code)
    if mensaje is None:
        mensaje = exc.detail if isinstance(exc.detail, str) else mensajes.SOLICITUD_INVALIDA
    return respuesta_error(request, exc.status_code, mensaje, cabeceras=dict(exc.headers or {}))


async def manejar_error_no_controlado(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Error no controlado: %s", type(exc).__name__, exc_info=exc, extra={"estado": 500, "trace_id": _trace_id(request)})
    return respuesta_error(request, 500, mensajes.ERROR_INTERNO)


def registrar_manejadores(app: FastAPI) -> None:
    app.add_exception_handler(ErrorAplicacion, manejar_error_aplicacion)
    app.add_exception_handler(RequestValidationError, manejar_error_validacion)
    app.add_exception_handler(StarletteHTTPException, manejar_error_http)
    app.add_exception_handler(Exception, manejar_error_no_controlado)
