"""Repositorio de materiales con SQLAlchemy.

Todas las consultas usan parámetros enlazados (nunca texto concatenado), así que los
valores del cliente no pueden alterar el SQL (OWASP A03: inyección).
"""

from collections.abc import Sequence

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infraestructure.interfaces.material_repository import IMaterialRepository
from app.infraestructure.models import Material


def _escapar_like(texto: str) -> str:
    """Escapa los comodines de LIKE para que el fragmento se busque literalmente."""
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class MaterialRepository(IMaterialRepository):
    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def obtener_por_id(self, id_material: int) -> Material | None:
        return await self._sesion.get(Material, id_material)

    async def listar(self) -> Sequence[Material]:
        return (await self._sesion.scalars(select(Material).order_by(Material.id_material))).all()

    async def buscar_por_nombre(self, fragmento: str) -> Sequence[Material]:
        consulta = (
            select(Material)
            .where(Material.nombre.ilike(f"%{_escapar_like(fragmento)}%", escape="\\"))
            .order_by(Material.id_material)
        )
        return (await self._sesion.scalars(consulta)).all()

    async def existe_nombre(self, nombre: str, excluir_id: int | None = None) -> bool:
        condicion = func.lower(Material.nombre) == nombre.lower()
        if excluir_id is not None:
            condicion = condicion & (Material.id_material != excluir_id)
        return bool(await self._sesion.scalar(select(exists().where(condicion))))

    async def agregar(self, material: Material) -> None:
        self._sesion.add(material)
        await self._sesion.flush()  # INSERT dentro de la transacción: la base asigna el id

    async def eliminar(self, material: Material) -> None:
        await self._sesion.delete(material)
