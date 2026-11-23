"""Modelos ORM de SQLAlchemy (tablas del MER).

Importar desde aquí garantiza que todas las tablas queden registradas en
``Base.metadata`` (lo necesita Alembic). Cada tabla nueva se agrega a este archivo.
"""

from app.infraestructure.models.auditoria import Auditoria
from app.infraestructure.models.base import SECUENCIA_MATERIAL, Base
from app.infraestructure.models.material import Material

__all__ = ["SECUENCIA_MATERIAL", "Auditoria", "Base", "Material"]
