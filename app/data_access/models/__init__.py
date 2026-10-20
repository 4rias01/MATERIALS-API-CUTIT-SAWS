"""Modelos ORM de SQLAlchemy (tablas del MER).

Importar desde aquí garantiza que todas las tablas queden registradas en
``Base.metadata`` (lo necesitan Alembic y las relaciones entre modelos).
"""

from app.data_access.models.auditoria import Auditoria
from app.data_access.models.base import (
    SECUENCIA_FORMULA,
    SECUENCIA_MATERIAL,
    SECUENCIA_TICKET_EVALUACION,
    Base,
)
from app.data_access.models.evaluacion_patente import EvaluacionPatente, PatenteConflicto
from app.data_access.models.formula import ComponenteFormula, Formula
from app.data_access.models.material import Material

__all__ = [
    "SECUENCIA_FORMULA",
    "SECUENCIA_MATERIAL",
    "SECUENCIA_TICKET_EVALUACION",
    "Auditoria",
    "Base",
    "ComponenteFormula",
    "EvaluacionPatente",
    "Formula",
    "Material",
    "PatenteConflicto",
]
