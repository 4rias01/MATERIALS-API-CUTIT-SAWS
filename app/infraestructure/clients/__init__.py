"""Clientes HTTP (httpx) de las APIs de otras células (patrón Gateway).

Cada cliente nuevo hereda de ``ClienteHttpBase`` y de su interfaz en
``app/infraestructure/interfaces``.
"""

from app.infraestructure.clients.base import ClienteHttpBase
from app.infraestructure.clients.circuit_breaker import CircuitBreaker, EstadoCircuito
from app.infraestructure.clients.inventario_client import InventarioClient

__all__ = ["CircuitBreaker", "ClienteHttpBase", "EstadoCircuito", "InventarioClient"]
