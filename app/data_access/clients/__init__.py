"""Clientes HTTP (httpx) de las APIs de Inventario y Patent Sweep (patrón Gateway)."""

from app.data_access.clients.circuit_breaker import CircuitBreaker, EstadoCircuito
from app.data_access.clients.inventario_client import InventarioClient
from app.data_access.clients.patent_sweep_client import PatentSweepClient

__all__ = ["CircuitBreaker", "EstadoCircuito", "InventarioClient", "PatentSweepClient"]
