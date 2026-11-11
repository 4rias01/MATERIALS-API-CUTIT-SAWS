"""Modelos ORM de SQLAlchemy (tablas del MER).

Importar desde aquí garantiza que todas las tablas queden registradas en
``Base.metadata`` (lo necesitan Alembic y las relaciones entre modelos).
"""

from app.infraestructure.models.auditoria import Auditoria
from app.infraestructure.models.base import (
    SECUENCIA_FORMULA,
    SECUENCIA_MATERIAL,
    SECUENCIA_TICKET_EVALUACION,
    Base,
)
from app.infraestructure.models.evaluacion_patente import EvaluacionPatente, PatenteConflicto
from app.infraestructure.models.formula import ComponenteFormula, Formula
from app.infraestructure.models.material import Material

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
