"""Persistencia del registro de fórmulas con SQLAlchemy."""

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infraestructure.interfaces.formula_repository import IFormulaRepository
from app.infraestructure.models import SECUENCIA_FORMULA, Formula


class FormulaRepository(IFormulaRepository):
    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def existe_nombre(self, nombre: str) -> bool:
        return bool(await self._sesion.scalar(select(exists().where(func.lower(Formula.nombre) == nombre.lower()))))

    async def siguiente_numero(self) -> int:
        return int((await self._sesion.execute(select(SECUENCIA_FORMULA.next_value()))).scalar_one())

    async def agregar(self, formula: Formula) -> None:
        self._sesion.add(formula)
        await self._sesion.flush()
