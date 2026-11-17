"""Contrato común de los clientes de las APIs de otras células."""

from abc import ABC, abstractmethod


class IClienteExterno(ABC):
    """Cliente de la API de otra célula (request-reply síncrono, timeout 5 s).

    Cada cliente concreto (p. ej. Inventario o Patent Sweep) define su propio contrato
    heredando de esta interfaz y agrega sus operaciones. Los fallos de comunicación (sin
    respuesta, error interno, más de 5 s o circuito abierto) se lanzan como
    ``app.core.exceptions.ErrorServicioExterno``.
    """

    @abstractmethod
    def estado_circuito(self) -> str:
        """Estado del circuit breaker: CERRADO, ABIERTO o SEMIABIERTO (se muestra en /health)."""
