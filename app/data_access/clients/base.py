"""Base de los clientes HTTP (patrón Gateway).

Centraliza lo que comparten los clientes de Inventario y Patent Sweep:

* Timeout total de 5 s por llamada (``HTTP_TIMEOUT_S``).
* Circuit Breaker por servicio.
* Propagación del traceId (``X-Trace-Id``) y del nombre de este servicio
  (``X-Servicio-Origen``) para correlacionar logs entre células.
* Métricas de llamadas y duración para Prometheus.

Las respuestas 2xx y 4xx se devuelven al cliente concreto para que las interprete;
los timeouts, errores de conexión y respuestas 5xx se lanzan como ``ErrorServicioExterno``.
"""

import asyncio
import logging
import time
from typing import Any

import httpx

from app.core.contexto import nuevo_trace_id, obtener_trace_id
from app.core.exceptions import ErrorServicioExterno
from app.core.metrics import DURACION_LLAMADAS_EXTERNAS, LLAMADAS_EXTERNAS
from app.data_access.clients.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class ClienteHttpBase:
    def __init__(
        self,
        servicio: str,
        http: httpx.AsyncClient,
        url_base: str | None,
        timeout_s: float,
        circuito: CircuitBreaker,
        nombre_origen: str,
    ) -> None:
        self._servicio = servicio
        self._http = http
        self._url_base = url_base.rstrip("/") if url_base else None
        self._timeout_s = timeout_s
        self._circuito = circuito
        self._nombre_origen = nombre_origen

    def estado_circuito(self) -> str:
        return self._circuito.estado.value

    async def _enviar(self, metodo: str, ruta: str, *, json: Any = None) -> httpx.Response:
        if not self._url_base:
            self._contar("sin_configurar")
            raise ErrorServicioExterno(self._servicio, ErrorServicioExterno.SIN_CONFIGURAR, detalle="URL base no configurada")
        if not self._circuito.permite_llamada():
            self._contar("circuito_abierto")
            raise ErrorServicioExterno(self._servicio, ErrorServicioExterno.CIRCUITO_ABIERTO)

        url = f"{self._url_base}{ruta}"
        cabeceras = {
            "X-Trace-Id": obtener_trace_id() or nuevo_trace_id(),
            "X-Servicio-Origen": self._nombre_origen,
        }
        inicio = time.perf_counter()
        try:
            async with asyncio.timeout(self._timeout_s):
                respuesta = await self._http.request(metodo, url, json=json, headers=cabeceras, timeout=self._timeout_s)
        except (TimeoutError, httpx.TimeoutException) as exc:
            self._fallo("timeout", metodo, url, exc)
            raise ErrorServicioExterno(self._servicio, ErrorServicioExterno.TIMEOUT) from exc
        except httpx.HTTPError as exc:
            self._fallo("conexion", metodo, url, exc)
            raise ErrorServicioExterno(self._servicio, ErrorServicioExterno.CONEXION, detalle=str(exc)) from exc
        except BaseException:
            self._circuito.liberar_prueba()
            raise
        finally:
            DURACION_LLAMADAS_EXTERNAS.labels(servicio=self._servicio).observe(time.perf_counter() - inicio)

        if respuesta.status_code >= 500:
            self._fallo(str(respuesta.status_code), metodo, url)
            raise ErrorServicioExterno(
                self._servicio, ErrorServicioExterno.ERROR_INTERNO, estado_recibido=respuesta.status_code
            )
        self._circuito.registrar_exito()
        self._contar(str(respuesta.status_code))
        return respuesta

    def _fallo(self, resultado: str, metodo: str, url: str, exc: BaseException | None = None) -> None:
        self._circuito.registrar_fallo()
        self._contar(resultado)
        logger.error(
            "Falló la llamada a %s: %s %s (%s)",
            self._servicio,
            metodo,
            url,
            resultado,
            extra={"servicio": self._servicio, "resultado": resultado, "error": repr(exc) if exc else None},
        )

    def _contar(self, resultado: str) -> None:
        LLAMADAS_EXTERNAS.labels(servicio=self._servicio, resultado=resultado).inc()

    def _respuesta_inesperada(self, respuesta: httpx.Response) -> ErrorServicioExterno:
        logger.error(
            "Respuesta inesperada de %s: HTTP %s",
            self._servicio,
            respuesta.status_code,
            extra={"servicio": self._servicio, "cuerpo": respuesta.text[:500]},
        )
        return ErrorServicioExterno(
            self._servicio, ErrorServicioExterno.RESPUESTA_INESPERADA, estado_recibido=respuesta.status_code
        )

    @staticmethod
    def _json(respuesta: httpx.Response) -> dict[str, Any]:
        try:
            datos = respuesta.json()
        except ValueError:
            return {}
        return datos if isinstance(datos, dict) else {}
