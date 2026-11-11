"""Contrato del repositorio de materiales (patrón Repository)."""

from abc import ABC, abstractmethod

from app.infraestructure.models import Material


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
