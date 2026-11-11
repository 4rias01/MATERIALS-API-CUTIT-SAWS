"""Repositorio de auditoría con SQLAlchemy."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.infraestructure.interfaces.auditoria_repository import IAuditoriaRepository
from app.infraestructure.models import Auditoria


class AuditoriaRepository(IAuditoriaRepository):
    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    def agregar(self, registro: Auditoria) -> None:
        self._sesion.add(registro)
