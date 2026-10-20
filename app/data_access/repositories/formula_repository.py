"""Repositorio de fórmulas con SQLAlchemy."""

from sqlalchemy import ColumnElement, Select, exists, func, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.paginacion import Pagina, calcular_desplazamiento
from app.data_access.interfaces.formula_repository import FiltrosBusquedaFormulas, IFormulaRepository
from app.data_access.models import (
    SECUENCIA_FORMULA,
    SECUENCIA_TICKET_EVALUACION,
    ComponenteFormula,
    EvaluacionPatente,
    Formula,
)


def _con_componentes(consulta: Select) -> Select:
    return consulta.options(selectinload(Formula.componentes).selectinload(ComponenteFormula.material))


def _con_evaluaciones(consulta: Select) -> Select:
    return consulta.options(selectinload(Formula.evaluaciones).selectinload(EvaluacionPatente.patentes))


def _escapar_like(texto: str) -> str:
    """Escapa los comodines de LIKE para buscar el texto literal."""
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class FormulaRepository(IFormulaRepository):
    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def obtener_por_id(self, id_formula: str) -> Formula | None:
        consulta = _con_evaluaciones(_con_componentes(select(Formula).where(Formula.id_formula == id_formula)))
        return await self._sesion.scalar(consulta)

    async def existe_nombre(self, nombre: str, excluir_id: str | None = None) -> bool:
        condicion = func.lower(Formula.nombre) == nombre.lower()
        if excluir_id is not None:
            condicion = condicion & (Formula.id_formula != excluir_id)
        return bool(await self._sesion.scalar(select(exists().where(condicion))))

    async def siguiente_numero(self) -> int:
        return int(await self._sesion.scalar(select(SECUENCIA_FORMULA.next_value())))

    async def siguiente_numero_ticket(self) -> int:
        return int(await self._sesion.scalar(select(SECUENCIA_TICKET_EVALUACION.next_value())))

    def agregar(self, formula: Formula) -> None:
        self._sesion.add(formula)

    async def buscar(self, filtros: FiltrosBusquedaFormulas, pagina: int, tamano_pagina: int) -> Pagina[Formula]:
        condiciones = self._condiciones(filtros)
        total = int(
            await self._sesion.scalar(select(func.count()).select_from(Formula).where(*condiciones)) or 0
        )
        consulta = (
            select(Formula)
            .where(*condiciones)
            .order_by(Formula.fecha_actualizacion.desc(), Formula.id_formula)
            .limit(tamano_pagina)
            .offset(calcular_desplazamiento(pagina, tamano_pagina))
        )
        elementos = list((await self._sesion.scalars(consulta)).all())
        return Pagina(elementos, pagina, tamano_pagina, total)

    async def listar_por_estado(self, estado: str, pagina: int, tamano_pagina: int) -> Pagina[Formula]:
        condicion = Formula.estado == estado
        total = int(await self._sesion.scalar(select(func.count()).select_from(Formula).where(condicion)) or 0)
        consulta = _con_componentes(
            select(Formula)
            .where(condicion)
            # Orden numérico del consecutivo: form-999 antes que form-1000.
            .order_by(func.length(Formula.id_formula), Formula.id_formula)
            .limit(tamano_pagina)
            .offset(calcular_desplazamiento(pagina, tamano_pagina))
        )
        elementos = list((await self._sesion.scalars(consulta)).all())
        return Pagina(elementos, pagina, tamano_pagina, total)

    async def obtener_evaluacion_abierta(self, id_formula: str) -> EvaluacionPatente | None:
        consulta = select(EvaluacionPatente).where(
            EvaluacionPatente.id_formula == id_formula,
            EvaluacionPatente.resultado.is_(None),
        )
        return await self._sesion.scalar(consulta)

    @staticmethod
    def _condiciones(filtros: FiltrosBusquedaFormulas) -> list[ColumnElement[bool]]:
        condiciones: list[ColumnElement[bool]] = [true()]
        if filtros.texto:
            patron = f"%{_escapar_like(filtros.texto)}%"
            condiciones.append(
                or_(Formula.id_formula.ilike(patron, escape="\\"), Formula.nombre.ilike(patron, escape="\\"))
            )
        if filtros.estado:
            condiciones.append(Formula.estado == filtros.estado)
        if filtros.registro_desde:
            condiciones.append(Formula.fecha_registro >= filtros.registro_desde)
        if filtros.registro_hasta:
            condiciones.append(Formula.fecha_registro < filtros.registro_hasta)
        if filtros.actualizacion_desde:
            condiciones.append(Formula.fecha_actualizacion >= filtros.actualizacion_desde)
        if filtros.actualizacion_hasta:
            condiciones.append(Formula.fecha_actualizacion < filtros.actualizacion_hasta)
        for id_material in dict.fromkeys(filtros.materiales):  # sin repetidos, en orden
            condiciones.append(
                exists().where(
                    ComponenteFormula.id_formula == Formula.id_formula,
                    ComponenteFormula.id_material == id_material,
                )
            )
        return condiciones
