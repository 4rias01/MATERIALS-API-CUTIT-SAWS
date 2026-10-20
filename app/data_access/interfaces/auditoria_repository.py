"""Contrato del repositorio de auditoría (patrón Tabla de auditoría)."""

from abc import ABC, abstractmethod

from app.data_access.models import Auditoria


class IAuditoriaRepository(ABC):
    """Pista de auditoría de solo inserción: no hay métodos para modificar ni borrar."""

    @abstractmethod
    def agregar(self, registro: Auditoria) -> None:
        """Agrega el registro a la transacción en curso."""
