"""Eventos de dominio (patrón Observer).

Los servicios publican un evento cuando una operación de negocio termina con éxito
(después del commit). Los suscriptores reaccionan sin que el negocio dependa de
ellos: hoy uno escribe el evento en el log y otro incrementa una métrica de
Prometheus. Un suscriptor que falla nunca interrumpe la operación de negocio.
"""

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.core.contexto import obtener_trace_id

logger = logging.getLogger("app.eventos")


@dataclass(frozen=True, slots=True)
class EventoDominio:
    """Hecho de negocio ocurrido, por ejemplo ``MaterialRegistrado``."""

    nombre: str
    datos: Mapping[str, Any] = field(default_factory=dict)
    fecha: datetime = field(default_factory=lambda: datetime.now(UTC))
    trace_id: str | None = field(default_factory=obtener_trace_id)


Suscriptor = Callable[[EventoDominio], None]


class BusEventos:
    """Publica eventos de dominio a sus suscriptores (todos o los de un evento concreto)."""

    def __init__(self) -> None:
        self._generales: list[Suscriptor] = []
        self._por_evento: dict[str, list[Suscriptor]] = {}

    def suscribir(self, suscriptor: Suscriptor, evento: str | None = None) -> None:
        """Registra un suscriptor para todos los eventos o solo para ``evento``."""
        if evento is None:
            self._generales.append(suscriptor)
        else:
            self._por_evento.setdefault(evento, []).append(suscriptor)

    def publicar(self, evento: EventoDominio) -> None:
        """Entrega el evento a cada suscriptor; los errores se registran y no se propagan."""
        for suscriptor in [*self._generales, *self._por_evento.get(evento.nombre, [])]:
            try:
                suscriptor(evento)
            except Exception:
                logger.exception("Falló un suscriptor del evento %s", evento.nombre)


def registrar_evento_en_log(evento: EventoDominio) -> None:
    """Suscriptor que deja la huella del evento en el log estructurado."""
    logger.info(
        "Evento de dominio %s",
        evento.nombre,
        extra={"evento": evento.nombre, "datos": dict(evento.datos), "trace_id": evento.trace_id},
    )
