"""Contratos que usan los servicios: la lógica de negocio no depende de SQL ni de HTTP.

Las implementaciones están en ``repositories`` y ``clients``; se entregan a los
servicios por inyección de dependencias (app/api/dependencies.py) y en las pruebas se
reemplazan por dobles (tests/dobles).
"""

from app.infraestructure.interfaces.auditoria_repository import IAuditoriaRepository
from app.infraestructure.interfaces.inventario_client import IInventarioClient, NombreDuplicadoEnInventarioError
from app.infraestructure.interfaces.material_repository import IMaterialRepository
from app.infraestructure.interfaces.unit_of_work import IUnitOfWork

__all__ = [
    "IAuditoriaRepository",
    "IInventarioClient",
    "IMaterialRepository",
    "IUnitOfWork",
    "NombreDuplicadoEnInventarioError",
]
