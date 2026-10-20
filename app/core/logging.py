"""Logging estructurado en JSON con traceId (táctica de analizabilidad).

Cada línea de log es un objeto JSON con la fecha en UTC, el nivel, el logger, el
mensaje, el traceId y el origen de la petición en curso. Los datos adicionales se
pasan con ``extra``::

    logger.info("Material registrado", extra={"materialId": "mat-001", "sku": "MP-00001"})
"""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from app.core.contexto import obtener_origen, obtener_trace_id

# Atributos que trae todo LogRecord; el resto se considera dato adicional (extra).
_ATRIBUTOS_ESTANDAR = frozenset(vars(logging.makeLogRecord({})).keys()) | {"message", "asctime", "taskName", "color_message"}


class FormateadorJson(logging.Formatter):
    """Convierte cada registro en una línea JSON."""

    def format(self, record: logging.LogRecord) -> str:
        datos: dict[str, Any] = {
            "fecha": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "nivel": record.levelname,
            "logger": record.name,
            "mensaje": record.getMessage(),
            "traceId": getattr(record, "trace_id", None) or obtener_trace_id(),
            "origen": getattr(record, "origen", None) or obtener_origen(),
        }
        for clave, valor in vars(record).items():
            if clave not in _ATRIBUTOS_ESTANDAR and clave not in ("trace_id", "origen") and not clave.startswith("_"):
                datos[clave] = valor
        if record.exc_info:
            datos["excepcion"] = self.formatException(record.exc_info)
        return json.dumps(datos, ensure_ascii=False, default=str)


class _ManejadorConsola(logging.StreamHandler):
    """Manejador propio: se reconoce para no duplicarlo si la configuración se repite."""


class _SinErrorAsgiDuplicado(logging.Filter):
    """Evita el segundo registro de un error no controlado.

    El manejador global de excepciones ya lo registra con su traceId; Uvicorn lo
    vuelve a registrar como "Exception in ASGI application".
    """

    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage() != "Exception in ASGI application"


def configurar_logging(nivel: str = "INFO") -> None:
    """Envía todos los logs (incluidos los de Uvicorn) a la salida estándar en JSON."""
    raiz = logging.getLogger()
    for manejador in list(raiz.handlers):
        if isinstance(manejador, _ManejadorConsola):
            raiz.removeHandler(manejador)
    manejador = _ManejadorConsola(sys.stdout)
    manejador.setFormatter(FormateadorJson())
    raiz.addHandler(manejador)
    raiz.setLevel(nivel)

    for nombre in ("uvicorn", "uvicorn.error"):
        registrador = logging.getLogger(nombre)
        registrador.handlers.clear()
        registrador.propagate = True
    error_uvicorn = logging.getLogger("uvicorn.error")
    if not any(isinstance(f, _SinErrorAsgiDuplicado) for f in error_uvicorn.filters):
        error_uvicorn.addFilter(_SinErrorAsgiDuplicado())
    # El middleware de traceId registra cada petición; el log de acceso de Uvicorn sobra.
    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
