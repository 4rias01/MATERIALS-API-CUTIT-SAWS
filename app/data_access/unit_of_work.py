"""Unidad de trabajo sobre una sesión de SQLAlchemy (patrón Unit of Work)."""

import logging
from types import TracebackType
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_access.database import ERRORES_BASE_DATOS, traducir_error_base_datos
from app.data_access.interfaces.unit_of_work import IUnitOfWork

logger = logging.getLogger(__name__)


class UnitOfWork(IUnitOfWork):
    """Agrupa las operaciones de una petición en una transacción.

    Comparte la sesión con los repositorios de la misma petición (la inyección de
    dependencias entrega la misma sesión a todos), así que ``commit`` confirma todo lo
    que hicieron. Al salir del bloque ``async with``:

    * con una excepción: se revierte la transacción (y los errores de base de datos se
      traducen a ``ErrorBaseDatos``);
    * con cambios sin ``commit``: se revierten (y queda una advertencia en el log);
    * después de solo leer: se cierra la transacción sin descartar los objetos leídos, que
      siguen disponibles para armar la respuesta (un rollback los marcaría como vencidos y,
      en modo asíncrono, leerlos de nuevo fallaría).
    """

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion
        self._hubo_escrituras = False
        event.listen(sesion.sync_session, "after_flush", self._registrar_escritura)

    def _registrar_escritura(self, *_: Any) -> None:
        self._hubo_escrituras = True

    def _cambios_sin_confirmar(self) -> bool:
        return self._hubo_escrituras or bool(self._sesion.new or self._sesion.dirty or self._sesion.deleted)

    async def __aenter__(self) -> "UnitOfWork":
        return self

    async def __aexit__(
        self,
        tipo: type[BaseException] | None,
        exc: BaseException | None,
        traza: TracebackType | None,
    ) -> None:
        if exc is not None:
            await self._revertir_sin_fallar()
            if isinstance(exc, ERRORES_BASE_DATOS):
                raise traducir_error_base_datos(exc) from exc
            return
        if not self._sesion.in_transaction():
            return
        if self._cambios_sin_confirmar():
            logger.warning("Se revirtió una transacción con cambios sin commit")
            await self._revertir_sin_fallar()
        else:
            await self._confirmar()  # transacción de solo lectura

    async def commit(self) -> None:
        await self._confirmar()

    async def rollback(self) -> None:
        await self._revertir_sin_fallar()

    async def verificar_conexion(self) -> None:
        try:
            await self._sesion.execute(text("SELECT 1"))
        except ERRORES_BASE_DATOS as exc:
            await self._revertir_sin_fallar()
            raise traducir_error_base_datos(exc) from exc
        await self._revertir_sin_fallar()

    async def _confirmar(self) -> None:
        try:
            await self._sesion.commit()
        except ERRORES_BASE_DATOS as exc:
            await self._revertir_sin_fallar()
            raise traducir_error_base_datos(exc) from exc
        self._hubo_escrituras = False

    async def _revertir_sin_fallar(self) -> None:
        """Revierte; si la conexión está caída, el rollback también falla y se ignora."""
        try:
            await self._sesion.rollback()
        except ERRORES_BASE_DATOS:
            logger.debug("No se pudo revertir la transacción (conexión no disponible)", exc_info=True)
        self._hubo_escrituras = False
