"""Dobles de prueba (patrón Test Double) de las interfaces de la capa de acceso a datos."""

from tests.dobles.clientes import ClienteExternoFalso, InventarioClientFalso
from tests.dobles.repositorios import AuditoriaRepositoryFalso, UnitOfWorkFalsa

__all__ = ["AuditoriaRepositoryFalso", "ClienteExternoFalso", "InventarioClientFalso", "UnitOfWorkFalsa"]
