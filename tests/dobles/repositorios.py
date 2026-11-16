"""Unidad de trabajo y auditoría en memoria.

Los repositorios propios de cada recurso se simulan en cada prueba con
``AsyncMock(spec=IMaterialRepository)`` (el equivalente al ``@Mock`` de Mockito).
"""

from types import TracebackType

from app.infraestructure.interfaces import IAuditoriaRepository, IUnitOfWork
from app.infraestructure.models import Auditoria


class UnitOfWorkFalsa(IUnitOfWork):
    """Cuenta las confirmaciones (commit) sin tocar ninguna base de datos."""

    def __init__(self) -> None:
        self.confirmaciones = 0

    async def __aenter__(self) -> "UnitOfWorkFalsa":
        return self

    async def __aexit__(self, tipo: type[BaseException] | None, exc: BaseException | None, traza: TracebackType | None) -> None:
        return None

    async def commit(self) -> None:
        self.confirmaciones += 1

    async def rollback(self) -> None:
        return None

    async def verificar_conexion(self) -> None:
        return None


class AuditoriaRepositoryFalso(IAuditoriaRepository):
    """Guarda en una lista los registros de auditoría que agrega el servicio."""

    def __init__(self) -> None:
        self.registros: list[Auditoria] = []

    def agregar(self, registro: Auditoria) -> None:
        self.registros.append(registro)
