"""Repositorios y unidad de trabajo en memoria."""

from collections.abc import Sequence
from types import TracebackType

from app.core.exceptions import ErrorBaseDatos
from app.infraestructure.interfaces import IAuditoriaRepository, IMaterialRepository, IUnitOfWork
from app.infraestructure.models import Auditoria, Material


class UnitOfWorkFalsa(IUnitOfWork):
    """Cuenta confirmaciones y reversiones; puede simular un fallo de la base de datos.

    Un bloque ``async with`` que termina sin ``commit`` (con o sin excepción) cuenta como
    reversión. ``error_en_commit`` es la excepción que lanza el commit (por ejemplo, un
    ``ErrorIntegridadDatos``); ``fallar_en_commit`` lanza un ``ErrorBaseDatos`` genérico.
    """

    def __init__(
        self,
        fallar_en_commit: bool = False,
        base_disponible: bool = True,
        error_en_commit: ErrorBaseDatos | None = None,
    ) -> None:
        self.fallar_en_commit = fallar_en_commit
        self.base_disponible = base_disponible
        self.error_en_commit = error_en_commit
        self.confirmaciones = 0
        self.reversiones = 0
        self._confirmado = False

    async def __aenter__(self) -> "UnitOfWorkFalsa":
        self._confirmado = False
        return self

    async def __aexit__(
        self, tipo: type[BaseException] | None, exc: BaseException | None, traza: TracebackType | None
    ) -> None:
        if exc is not None or not self._confirmado:
            self.reversiones += 1

    async def commit(self) -> None:
        if self.error_en_commit is not None:
            raise self.error_en_commit
        if self.fallar_en_commit or not self.base_disponible:
            raise ErrorBaseDatos("Fallo simulado de la base de datos")
        self.confirmaciones += 1
        self._confirmado = True

    async def rollback(self) -> None:
        self.reversiones += 1

    async def verificar_conexion(self) -> None:
        if not self.base_disponible:
            raise ErrorBaseDatos("Base de datos no disponible (simulado)")


class AuditoriaRepositoryFalso(IAuditoriaRepository):
    def __init__(self) -> None:
        self.registros: list[Auditoria] = []

    def agregar(self, registro: Auditoria) -> None:
        self.registros.append(registro)


class MaterialRepositoryFalso(IMaterialRepository):
    """Materiales en memoria. No simula el rollback: lo agregado queda en ``materiales``
    aunque la unidad de trabajo falle; para eso, verificar ``uow.confirmaciones``."""

    def __init__(self, materiales: Sequence[Material] = ()) -> None:
        self.materiales: dict[str, Material] = {m.id_material: m for m in materiales}
        self._secuencia = len(self.materiales)

    async def existe_nombre(self, nombre: str) -> bool:
        return any(m.nombre.lower() == nombre.lower() for m in self.materiales.values())

    async def siguiente_numero(self) -> int:
        self._secuencia += 1
        return self._secuencia

    def agregar(self, material: Material) -> None:
        self.materiales[material.id_material] = material
