"""Contratos que usan los servicios: la lógica de negocio no depende de SQL ni de HTTP.

Las implementaciones están en ``repositories`` y ``clients``; se entregan a los
servicios por inyección de dependencias (app/presentation/dependencies.py) y en las
pruebas se reemplazan por dobles (tests/dobles).
"""

from app.data_access.interfaces.auditoria_repository import IAuditoriaRepository
from app.data_access.interfaces.formula_repository import FiltrosBusquedaFormulas, IFormulaRepository
from app.data_access.interfaces.inventario_client import IInventarioClient, NombreDuplicadoEnInventarioError
from app.data_access.interfaces.material_repository import IMaterialRepository
from app.data_access.interfaces.patent_sweep_client import (
    ComponenteEvaluacion,
    IPatentSweepClient,
    SolicitudEvaluacionPatente,
)
from app.data_access.interfaces.unit_of_work import IUnitOfWork

__all__ = [
    "ComponenteEvaluacion",
    "FiltrosBusquedaFormulas",
    "IAuditoriaRepository",
    "IFormulaRepository",
    "IInventarioClient",
    "IMaterialRepository",
    "IPatentSweepClient",
    "IUnitOfWork",
    "NombreDuplicadoEnInventarioError",
    "SolicitudEvaluacionPatente",
]
