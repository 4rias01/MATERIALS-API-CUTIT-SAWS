"""Clientes HTTP (httpx) de las APIs de Inventario y Patent Sweep (patrón Gateway)."""

from app.infraestructure.clients.circuit_breaker import CircuitBreaker, EstadoCircuito
from app.infraestructure.clients.inventario_client import InventarioClient
from app.infraestructure.clients.patent_sweep_client import PatentSweepClient

__all__ = ["CircuitBreaker", "EstadoCircuito", "InventarioClient", "PatentSweepClient"]
