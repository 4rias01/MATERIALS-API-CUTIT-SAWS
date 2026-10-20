"""Piezas comunes de los servicios (patrones Service Layer y Transaction Script).

Cada método público de un servicio es un caso de uso: un procedimiento con un solo
punto donde se confirma o se revierte la transacción. El decorador
``operacion_de_negocio`` le agrega el manejo uniforme de fallos:

* ``ErrorBaseDatos`` (fallo de conexión, de persistencia o timeout > 5 s): la unidad de
  trabajo ya revirtió; se responde ``ErrorInterno`` (500 con traceId) con el mensaje
  del backlog para ese caso de uso.
* ``ErrorServicioExterno`` (Inventario o Patent Sweep no responde, falla o tarda > 5 s):
  se responde ``DependenciaNoDisponibleError`` (503) con el mensaje del caso de uso.
* Cualquier otro ``ErrorAplicacion`` (400, 404, 409, 422, 503): se registra en la tabla
  de auditoría en una transacción propia y se propaga.

El registro de auditoría de un caso exitoso lo agrega el propio método con
``self._auditar(...)`` antes del commit, para que quede en la misma transacción.
"""

import functools
import inspect
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from app.core.contexto import nuevo_trace_id, obtener_origen, obtener_trace_id
from app.core.events import BusEventos, EventoDominio
from app.core.exceptions import (
    DependenciaNoDisponibleError,
    ErrorAplicacion,
    ErrorBaseDatos,
    ErrorInterno,
    ErrorServicioExterno,
    NoImplementadoError,
)
from app.data_access.interfaces import IAuditoriaRepository, IUnitOfWork
from app.data_access.models import Auditoria

logger = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")

_LONGITUD_RECURSO_ID = 10
_LONGITUD_ORIGEN = 100


@dataclass(frozen=True, slots=True)
class Resultado(Generic[T]):
    """Lo que devuelve un caso de uso: los datos y, si el backlog lo define, el mensaje."""

    datos: T
    mensaje: str | None = None


def ahora() -> datetime:
    """Fecha y hora del servidor en UTC (fechas de registro y de última actualización)."""
    return datetime.now(UTC)


class ServicioBase:
    """Base de los servicios: unidad de trabajo, auditoría y eventos de dominio."""

    def __init__(self, uow: IUnitOfWork, auditoria: IAuditoriaRepository, eventos: BusEventos) -> None:
        self._uow = uow
        self._auditoria = auditoria
        self._eventos = eventos

    def _auditar(
        self,
        operacion: str,
        recurso: str,
        recurso_id: str | None,
        resultado_http: int,
        detalle: dict[str, Any] | None = None,
    ) -> None:
        """Agrega el registro de auditoría a la transacción en curso (llamar antes del commit)."""
        detalle = dict(detalle or {})
        if recurso_id is not None and len(recurso_id) > _LONGITUD_RECURSO_ID:
            detalle["recursoIdRecibido"] = recurso_id
            recurso_id = None
        origen = obtener_origen()
        self._auditoria.agregar(
            Auditoria(
                fecha_hora=ahora(),
                trace_id=obtener_trace_id() or nuevo_trace_id(),
                operacion=operacion,
                recurso=recurso,
                recurso_id=recurso_id,
                resultado_http=resultado_http,
                origen=origen[:_LONGITUD_ORIGEN] if origen else None,
                detalle=detalle or None,
            )
        )

    async def _auditar_fallo(self, operacion: str, recurso: str, recurso_id: str | None, error: ErrorAplicacion) -> None:
        """Registra un rechazo o fallo en su propia transacción. Si la base de datos no está
        disponible, queda solo en el log: la auditoría nunca oculta el error original."""
        try:
            async with self._uow:
                self._auditar(operacion, recurso, recurso_id, error.codigo_http, {"mensaje": error.mensaje})
                await self._uow.commit()
        except Exception:
            logger.warning(
                "No se pudo registrar en la auditoría el fallo de %s",
                operacion,
                exc_info=True,
                extra={"operacion": operacion, "recursoId": recurso_id},
            )

    def _publicar(self, evento: str, **datos: Any) -> None:
        """Publica un evento de dominio (llamar después del commit)."""
        self._eventos.publicar(EventoDominio(evento, datos))


def operacion_de_negocio(
    nombre: str,
    recurso: str,
    *,
    mensaje_error_bd: str,
    mensaje_servicio_externo: str | None = None,
    auditar: bool = True,
    parametro_id: str | None = None,
) -> Callable[[Callable[..., Awaitable[R]]], Callable[..., Awaitable[R]]]:
    """Decora un caso de uso de un servicio que hereda de ``ServicioBase``.

    :param nombre: operación que queda en la auditoría, p. ej. ``"REGISTRAR_MATERIAL"``.
    :param recurso: recurso afectado, p. ej. ``"material"``.
    :param mensaje_error_bd: mensaje del backlog para el 500 por fallo de base de datos.
    :param mensaje_servicio_externo: mensaje del backlog para el 503 si falla una API externa.
    :param auditar: False en las consultas (solo se auditan las escrituras).
    :param parametro_id: nombre del parámetro con el ID del recurso (para la auditoría).
    """

    def decorador(metodo: Callable[..., Awaitable[R]]) -> Callable[..., Awaitable[R]]:
        firma = inspect.signature(metodo)

        @functools.wraps(metodo)
        async def envoltura(self: ServicioBase, *args: Any, **kwargs: Any) -> R:
            try:
                return await metodo(self, *args, **kwargs)
            except NoImplementadoError:
                raise
            except ErrorBaseDatos as exc:
                raise ErrorInterno(_con_trace_id(mensaje_error_bd)) from exc
            except ErrorServicioExterno as exc:
                if mensaje_servicio_externo is None:
                    raise
                error = DependenciaNoDisponibleError(_con_trace_id(mensaje_servicio_externo))
                if auditar:
                    await self._auditar_fallo(nombre, recurso, _id_recurso(firma, parametro_id, self, args, kwargs), error)
                raise error from exc
            except ErrorAplicacion as exc:
                if auditar:
                    await self._auditar_fallo(nombre, recurso, _id_recurso(firma, parametro_id, self, args, kwargs), exc)
                raise

        return envoltura

    return decorador


def _con_trace_id(mensaje: str) -> str:
    """Reemplaza el marcador [traceId] de los mensajes que lo incluyen (por ejemplo HU02_C5)."""
    if "[traceId]" not in mensaje:
        return mensaje
    return mensaje.replace("[traceId]", obtener_trace_id() or nuevo_trace_id())


def _id_recurso(
    firma: inspect.Signature, parametro: str | None, servicio: object, args: tuple[Any, ...], kwargs: dict[str, Any]
) -> str | None:
    if parametro is None:
        return None
    valor = firma.bind_partial(servicio, *args, **kwargs).arguments.get(parametro)
    return str(valor) if valor is not None else None
