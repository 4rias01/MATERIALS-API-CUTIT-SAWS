"""Repositorio de materiales con SQLAlchemy."""

from collections.abc import Sequence

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.paginacion import Pagina, calcular_desplazamiento
from app.data_access.interfaces.material_repository import IMaterialRepository
from app.data_access.models import SECUENCIA_MATERIAL, ComponenteFormula, Formula, Material


class MaterialRepository(IMaterialRepository):
    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def obtener_por_id(self, id_material: str) -> Material | None:
        return await self._sesion.get(Material, id_material)

    async def obtener_por_ids(self, ids: Sequence[str]) -> list[Material]:
        if not ids:
            return []
        consulta = select(Material).where(Material.id_material.in_(set(ids)))
        return list((await self._sesion.scalars(consulta)).all())

    async def existe_nombre(self, nombre: str, excluir_id: str | None = None) -> bool:
        condicion = func.lower(Material.nombre) == nombre.lower()
        if excluir_id is not None:
            condicion = condicion & (Material.id_material != excluir_id)
        return bool(await self._sesion.scalar(select(exists().where(condicion))))

    async def siguiente_numero(self) -> int:
        return int(await self._sesion.scalar(select(SECUENCIA_MATERIAL.next_value())))

    def agregar(self, material: Material) -> None:
        self._sesion.add(material)

    async def pertenece_a_formulas_con_estado(self, id_material: str, estados: Sequence[str]) -> bool:
        condicion = (
            (ComponenteFormula.id_material == id_material)
            & (ComponenteFormula.id_formula == Formula.id_formula)
            & Formula.estado.in_(list(estados))
        )
        return bool(await self._sesion.scalar(select(exists().where(condicion))))

    async def listar(self, pagina: int, tamano_pagina: int) -> Pagina[Material]:
        # TODO(HU-02 c3): aplicar los filtros que defina el PO.
        total = int(await self._sesion.scalar(select(func.count()).select_from(Material)) or 0)
        consulta = (
            select(Material)
            # Orden numérico del consecutivo: mat-999 antes que mat-1000.
            .order_by(func.length(Material.id_material), Material.id_material)
            .limit(tamano_pagina)
            .offset(calcular_desplazamiento(pagina, tamano_pagina))
        )
        elementos = list((await self._sesion.scalars(consulta)).all())
        return Pagina(elementos, pagina, tamano_pagina, total)
