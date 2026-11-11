"""Middleware de traceId (patrón Correlation ID).

Para cada petición HTTP:

1. Toma el traceId de la cabecera ``X-Trace-Id`` si otro servicio lo envió con un
   formato válido; si no, genera uno nuevo.
2. Identifica el origen con la cabecera ``X-Servicio-Origen`` o, si no viene, con la IP
   del cliente (no hay autenticación).
3. Los deja en el contexto de la petición (``app.core.contexto``) y en
   ``request.state`` para el manejador global de excepciones.
4. Agrega ``X-Trace-Id`` a la respuesta y registra la petición en el log con su
   duración.

Es un middleware ASGI puro (no ``BaseHTTPMiddleware``) para que el contexto se
comparta con la ruta que atiende la petición.
"""

import logging
import time

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.contexto import establecer_contexto, nuevo_trace_id, restablecer_contexto, trace_id_valido

logger = logging.getLogger("app.peticiones")

CABECERA_TRACE_ID = "X-Trace-Id"
CABECERA_ORIGEN = "X-Servicio-Origen"
_RUTAS_SILENCIOSAS = frozenset({"/metrics", "/health"})
_LONGITUD_ORIGEN = 100


class TraceIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        cabeceras = Headers(scope=scope)
        recibido = cabeceras.get(CABECERA_TRACE_ID)
        trace_id = recibido if trace_id_valido(recibido) else nuevo_trace_id()
        cliente = scope.get("client")
        origen = (cabeceras.get(CABECERA_ORIGEN) or (cliente[0] if cliente else None) or "")[:_LONGITUD_ORIGEN] or None

        estado = scope.setdefault("state", {})
        estado["trace_id"] = trace_id
        estado["origen"] = origen
        tokens = establecer_contexto(trace_id, origen)

        codigo = 500
        inicio = time.perf_counter()

        async def enviar(mensaje: Message) -> None:
            nonlocal codigo
            if mensaje["type"] == "http.response.start":
                codigo = mensaje["status"]
                MutableHeaders(scope=mensaje)[CABECERA_TRACE_ID] = trace_id
            await send(mensaje)

        try:
            await self.app(scope, receive, enviar)
        finally:
            ruta = scope.get("path", "")
            nivel = logging.DEBUG if ruta in _RUTAS_SILENCIOSAS else logging.INFO
            logger.log(
                nivel,
                "%s %s %s",
                scope.get("method"),
                ruta,
                codigo,
                extra={
                    "metodo": scope.get("method"),
                    "ruta": ruta,
                    "estado": codigo,
                    "duracionMs": round((time.perf_counter() - inicio) * 1000, 2),
                },
            )
            restablecer_contexto(tokens)
