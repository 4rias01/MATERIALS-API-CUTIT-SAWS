"""Implementaciones de los repositorios con SQLAlchemy."""

from app.infraestructure.repositories.auditoria_repository import AuditoriaRepository
from app.infraestructure.repositories.material_repository import MaterialRepository

__all__ = ["AuditoriaRepository", "MaterialRepository"]
