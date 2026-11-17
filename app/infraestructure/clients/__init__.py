"""Clientes HTTP (httpx) de las APIs de otras células (patrón Gateway).

Cada cliente nuevo hereda de ``ClienteHttpBase`` y de su interfaz en
``app/infraestructure/interfaces``.
"""

from app.infraestructure.clients.base import ClienteHttpBase
from app.infraestructure.clients.circuit_breaker import CircuitBreaker, EstadoCircuito

__all__ = ["CircuitBreaker", "ClienteHttpBase", "EstadoCircuito"]
