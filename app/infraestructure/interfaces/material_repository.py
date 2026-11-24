"""Contrato del repositorio de materiales (patrón Repository)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.infraestructure.models import Material


@dataclass(frozen=True, slots=True)
class FiltrosMaterial:
    nombre: str | None = None
    categoria: str | None = None
    unidad_medida: str | None = None
    estado: str | None = None


class IMaterialRepository(ABC):
    """Acceso a la tabla material. Los cambios se confirman con la unidad de trabajo."""

    @abstractmethod
    async def existe_nombre(self, nombre: str) -> bool:
        """Si otro material ya usa ``nombre`` sin distinguir mayúsculas (HU-01 c3)."""

    @abstractmethod
    async def siguiente_numero(self) -> int:
        """Siguiente número de la secuencia del ID mat-NNN (HU-01 c7.1)."""

    @abstractmethod
    def agregar(self, material: Material) -> None:
        """Agrega un material nuevo a la transacción en curso."""

    @abstractmethod
    async def obtener(self, identificador: str) -> Material | None:
        """Busca una ficha por su ID, en cualquier estado."""

    @abstractmethod
    async def listar(self, filtros: FiltrosMaterial, offset: int, limite: int) -> tuple[list[Material], int]:
        """Devuelve la página ordenada y el total de coincidencias antes de paginar."""
