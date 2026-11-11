"""Repositorio de materiales con SQLAlchemy."""

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infraestructure.interfaces.material_repository import IMaterialRepository
from app.infraestructure.models import SECUENCIA_MATERIAL, Material


class MaterialRepository(IMaterialRepository):
    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def existe_nombre(self, nombre: str) -> bool:
        condicion = func.lower(Material.nombre) == nombre.lower()
        return bool(await self._sesion.scalar(select(exists().where(condicion))))

    async def siguiente_numero(self) -> int:
        return int((await self._sesion.execute(select(SECUENCIA_MATERIAL.next_value()))).scalar_one())

    def agregar(self, material: Material) -> None:
        self._sesion.add(material)
