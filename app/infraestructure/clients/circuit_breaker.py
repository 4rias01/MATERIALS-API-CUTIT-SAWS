"""Circuit Breaker para las llamadas a otras APIs (táctica de tolerancia a fallos).

* CERRADO: las llamadas pasan. Cada fallo (timeout, conexión, error 5xx) suma; al
  llegar a ``umbral_fallos`` fallos seguidos, el circuito se abre.
* ABIERTO: las llamadas se rechazan de inmediato, sin esperar los 5 s del timeout, y el
  servicio responde 503. Pasado ``tiempo_abierto_s``, pasa a SEMIABIERTO.
* SEMIABIERTO: se deja pasar una sola llamada de prueba. Si funciona, se cierra; si
  falla, se vuelve a abrir.

Un éxito (incluida una respuesta 4xx, que prueba que el servicio está arriba) reinicia
el conteo. Hay una instancia por servicio externo, compartida por todas las peticiones.
"""

import logging
import time
from collections.abc import Callable
from enum import StrEnum

from app.core.metrics import CIRCUITO_ABIERTO

logger = logging.getLogger(__name__)


class EstadoCircuito(StrEnum):
    CERRADO = "CERRADO"
    ABIERTO = "ABIERTO"
    SEMIABIERTO = "SEMIABIERTO"


class CircuitBreaker:
    def __init__(
        self,
        servicio: str,
        umbral_fallos: int = 5,
        tiempo_abierto_s: float = 30.0,
        reloj: Callable[[], float] = time.monotonic,
    ) -> None:
        self.servicio = servicio
        self._umbral = umbral_fallos
        self._tiempo_abierto = tiempo_abierto_s
        self._reloj = reloj
        self._estado = EstadoCircuito.CERRADO
        self._fallos_seguidos = 0
        self._abierto_desde = 0.0
        self._prueba_en_curso = False
        CIRCUITO_ABIERTO.labels(servicio=servicio).set(0)

    @property
    def estado(self) -> EstadoCircuito:
        if self._estado == EstadoCircuito.ABIERTO and self._reloj() - self._abierto_desde >= self._tiempo_abierto:
            self._cambiar_a(EstadoCircuito.SEMIABIERTO)
        return self._estado

    def permite_llamada(self) -> bool:
        """Indica si la llamada puede hacerse. En SEMIABIERTO reserva la única llamada de prueba."""
        estado = self.estado
        if estado == EstadoCircuito.CERRADO:
            return True
        if estado == EstadoCircuito.SEMIABIERTO and not self._prueba_en_curso:
            self._prueba_en_curso = True
            return True
        return False

    def registrar_exito(self) -> None:
        self._prueba_en_curso = False
        self._fallos_seguidos = 0
        if self._estado != EstadoCircuito.CERRADO:
            self._cambiar_a(EstadoCircuito.CERRADO)

    def registrar_fallo(self) -> None:
        self._prueba_en_curso = False
        self._fallos_seguidos += 1
        if self._estado == EstadoCircuito.SEMIABIERTO or self._fallos_seguidos >= self._umbral:
            self._abierto_desde = self._reloj()
            self._cambiar_a(EstadoCircuito.ABIERTO)

    def liberar_prueba(self) -> None:
        """Libera la llamada de prueba si se canceló sin resultado."""
        self._prueba_en_curso = False

    def _cambiar_a(self, nuevo: EstadoCircuito) -> None:
        if nuevo != self._estado:
            logger.warning(
                "Circuit breaker de %s: %s -> %s",
                self.servicio,
                self._estado.value,
                nuevo.value,
                extra={"servicio": self.servicio, "estadoCircuito": nuevo.value},
            )
        self._estado = nuevo
        CIRCUITO_ABIERTO.labels(servicio=self.servicio).set(1 if nuevo == EstadoCircuito.ABIERTO else 0)
