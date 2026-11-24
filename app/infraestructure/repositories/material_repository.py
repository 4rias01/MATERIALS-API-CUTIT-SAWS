"""Repositorio de materiales con SQLAlchemy."""

from sqlalchemy import BigInteger, exists, func, literal, select, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.infraestructure.interfaces.material_repository import FiltrosMaterial, IMaterialRepository
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

    async def obtener(self, identificador: str) -> Material | None:
        return await self._sesion.get(Material, identificador)

    async def listar(self, filtros: FiltrosMaterial, offset: int, limite: int) -> tuple[list[Material], int]:
        condiciones = []
        if filtros.nombre is not None:
            condiciones.append(Material.nombre.icontains(filtros.nombre, autoescape=True))
        for columna, valor in (
            (Material.categoria, filtros.categoria),
            (Material.unidad_medida, filtros.unidad_medida),
            (Material.estado, filtros.estado),
        ):
            if valor is not None:
                condiciones.append(columna == valor)

        # Una sola lectura mantiene el total y la página consistentes incluso con altas concurrentes.
        total = select(func.count().label("cantidad")).select_from(Material).where(*condiciones).subquery()
        orden = (func.length(Material.id_material), Material.id_material)
        desplazamiento = literal(min(offset, 2**63 - 1), type_=BigInteger)
        pagina = select(Material).where(*condiciones).order_by(*orden).offset(desplazamiento).limit(limite).subquery()
        ficha = aliased(Material, pagina)
        consulta = (
            select(total.c.cantidad, ficha)
            .select_from(total)
            .outerjoin(ficha, true())
            .order_by(func.length(ficha.id_material), ficha.id_material)
        )
        filas = (await self._sesion.execute(consulta)).all()
        return [material for _, material in filas if material is not None], filas[0][0]
