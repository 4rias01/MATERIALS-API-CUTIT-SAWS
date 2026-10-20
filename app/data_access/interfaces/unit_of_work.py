"""Contrato de la unidad de trabajo."""

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self


class IUnitOfWork(ABC):
    """Transacción de una operación de negocio (patrón Unit of Work).

    Uso en un servicio::

        async with self._uow:
            ...  # cambios con los repositorios
            await self._uow.commit()

    Sin ``commit``, los cambios se revierten al salir del bloque; lo que solo se leyó
    sigue disponible después del bloque (para armar la respuesta). Si la base de datos
    falla o tarda más de 5 s, se revierte y se lanza ``app.core.exceptions.ErrorBaseDatos``.
    """

    @abstractmethod
    async def __aenter__(self) -> Self: ...

    @abstractmethod
    async def __aexit__(
        self,
        tipo: type[BaseException] | None,
        exc: BaseException | None,
        traza: TracebackType | None,
    ) -> None: ...

    @abstractmethod
    async def commit(self) -> None:
        """Confirma la transacción (lanza ErrorBaseDatos si falla)."""

    @abstractmethod
    async def rollback(self) -> None:
        """Revierte la transacción en curso."""

    @abstractmethod
    async def verificar_conexion(self) -> None:
        """Ejecuta una consulta mínima (lanza ErrorBaseDatos si la base no responde)."""
