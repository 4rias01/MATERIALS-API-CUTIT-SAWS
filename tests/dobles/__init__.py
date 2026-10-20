"""Dobles de prueba (patrón Test Double) de las interfaces de la capa de acceso a datos.

Permiten probar los servicios sin base de datos ni APIs externas::

    uow = UnitOfWorkFalsa()
    materiales = MaterialRepositoryFalso()
    inventario = InventarioClientFalso(sku="MP-00001")
    servicio = MaterialService(uow, AuditoriaRepositoryFalso(), BusEventos(), materiales, inventario)

Los repositorios guardan en memoria y no simulan el rollback: para probar una
reversión, verificar ``uow.confirmaciones`` y ``uow.reversiones``.
"""

from tests.dobles.clientes import InventarioClientFalso, PatentSweepClientFalso
from tests.dobles.repositorios import (
    AuditoriaRepositoryFalso,
    FormulaRepositoryFalso,
    MaterialRepositoryFalso,
    UnitOfWorkFalsa,
)

__all__ = [
    "AuditoriaRepositoryFalso",
    "FormulaRepositoryFalso",
    "InventarioClientFalso",
    "MaterialRepositoryFalso",
    "PatentSweepClientFalso",
    "UnitOfWorkFalsa",
]
