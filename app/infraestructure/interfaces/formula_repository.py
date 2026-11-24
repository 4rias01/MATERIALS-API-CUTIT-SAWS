"""Contrato de persistencia para registrar fórmulas (HU-05)."""

from abc import ABC, abstractmethod

from app.infraestructure.models import Formula


class IFormulaRepository(ABC):
    @abstractmethod
    async def existe_nombre(self, nombre: str) -> bool:
        """Nombre registrado, sin distinguir mayúsculas."""

    @abstractmethod
    async def siguiente_numero(self) -> int:
        """Consecutivo del código form-NNN."""

    @abstractmethod
    async def agregar(self, formula: Formula) -> None:
        """Agrega la fórmula y sus componentes dentro de la transacción."""
