"""Unidad de trabajo y auditoría en memoria.

Los repositorios propios de cada recurso se simulan en cada prueba con
``AsyncMock(spec=IMaterialRepository)`` (el equivalente al ``@Mock`` de Mockito).
"""

from types import TracebackType

from app.core.exceptions import ErrorBaseDatos
from app.infraestructure.interfaces import IAuditoriaRepository, IUnitOfWork
from app.infraestructure.models import Auditoria


class UnitOfWorkFalsa(IUnitOfWork):
    """Cuenta las confirmaciones (commit) sin tocar ninguna base de datos.

    ``fallar_en_commit`` simula una base de datos que falla al confirmar y
    ``base_disponible=False`` una base que no responde (para /health).
    """

    def __init__(self, fallar_en_commit: bool = False, base_disponible: bool = True) -> None:
        self.fallar_en_commit = fallar_en_commit
        self.base_disponible = base_disponible
        self.confirmaciones = 0

    async def __aenter__(self) -> "UnitOfWorkFalsa":
        return self

    async def __aexit__(self, tipo: type[BaseException] | None, exc: BaseException | None, traza: TracebackType | None) -> None:
        return None

    async def commit(self) -> None:
        if self.fallar_en_commit or not self.base_disponible:
            raise ErrorBaseDatos("Fallo simulado de la base de datos")
        self.confirmaciones += 1

    async def rollback(self) -> None:
        return None

    async def verificar_conexion(self) -> None:
        if not self.base_disponible:
            raise ErrorBaseDatos("Base de datos no disponible (simulado)")


class AuditoriaRepositoryFalso(IAuditoriaRepository):
    """Guarda en una lista los registros de auditoría que agrega el servicio."""

    def __init__(self) -> None:
        self.registros: list[Auditoria] = []

    def agregar(self, registro: Auditoria) -> None:
        self.registros.append(registro)
