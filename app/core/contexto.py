"""Contexto de la petición en curso (patrón Correlation ID).

El middleware de traceId guarda aquí el identificador de la petición y el servicio
de origen. Cualquier capa puede leerlos sin recibirlos por parámetro: el logging los
agrega a cada línea, la auditoría los persiste y los clientes HTTP los propagan a
Inventario y a Patent Sweep.
"""

import re
import uuid
from contextvars import ContextVar, Token

_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)
_origen: ContextVar[str | None] = ContextVar("origen", default=None)

# Un traceId recibido de otro servicio solo se reutiliza si tiene un formato seguro
# (evita inyectar texto arbitrario en los logs).
_PATRON_TRACE_ID = re.compile(r"^[A-Za-z0-9\-]{8,64}$")


def nuevo_trace_id() -> str:
    """Genera un identificador único de 32 caracteres hexadecimales."""
    return uuid.uuid4().hex


def trace_id_valido(valor: str | None) -> bool:
    """Indica si un traceId recibido en una cabecera puede reutilizarse."""
    return bool(valor) and _PATRON_TRACE_ID.fullmatch(valor) is not None


def obtener_trace_id() -> str | None:
    """traceId de la petición en curso (None fuera de una petición)."""
    return _trace_id.get()


def obtener_origen() -> str | None:
    """Servicio o cliente que originó la petición en curso."""
    return _origen.get()


def establecer_contexto(trace_id: str, origen: str | None) -> tuple[Token, Token]:
    """Fija el contexto de la petición y devuelve los tokens para restablecerlo."""
    return _trace_id.set(trace_id), _origen.set(origen)


def restablecer_contexto(tokens: tuple[Token, Token]) -> None:
    """Restaura el contexto anterior al terminar la petición."""
    token_trace, token_origen = tokens
    _trace_id.reset(token_trace)
    _origen.reset(token_origen)
