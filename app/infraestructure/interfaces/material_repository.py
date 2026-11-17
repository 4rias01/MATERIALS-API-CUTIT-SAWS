"""Contrato del repositorio de materiales (patrón Repository)."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.infraestructure.models import Material


class IMaterialRepository(ABC):
    """Acceso a la tabla material. Los cambios se confirman con la unidad de trabajo."""

    @abstractmethod
    async def obtener_por_id(self, id_material: int) -> Material | None:
        """El material con ese id, o None si no existe."""

    @abstractmethod
    async def listar(self) -> Sequence[Material]:
        """Todos los materiales, ordenados por id."""

    @abstractmethod
    async def buscar_por_nombre(self, fragmento: str) -> Sequence[Material]:
        """Materiales cuyo nombre contiene ``fragmento`` sin distinguir mayúsculas."""

    @abstractmethod
    async def existe_nombre(self, nombre: str, excluir_id: int | None = None) -> bool:
        """Si otro material (distinto de ``excluir_id``) ya usa ``nombre`` sin distinguir mayúsculas."""

    @abstractmethod
    async def agregar(self, material: Material) -> None:
        """Agrega un material nuevo a la transacción en curso y le asigna su id
        (la base de datos lo genera). Lanza ErrorBaseDatos si viola una restricción."""

    @abstractmethod
    async def eliminar(self, material: Material) -> None:
        """Marca el material para borrarlo en la transacción en curso."""
