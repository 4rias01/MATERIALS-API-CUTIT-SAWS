"""Cliente HTTP (httpx) de la API de Inventario (patrón Gateway)."""

from app.infraestructure.clients.circuit_breaker import CircuitBreaker, EstadoCircuito
from app.infraestructure.clients.inventario_client import InventarioClient

__all__ = ["CircuitBreaker", "EstadoCircuito", "InventarioClient"]
