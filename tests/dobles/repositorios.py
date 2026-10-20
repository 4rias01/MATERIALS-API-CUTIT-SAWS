"""Repositorios y unidad de trabajo en memoria."""

from collections.abc import Sequence
from types import TracebackType

from app.core.exceptions import ErrorBaseDatos
from app.core.paginacion import Pagina, calcular_desplazamiento
from app.data_access.interfaces import (
    FiltrosBusquedaFormulas,
    IAuditoriaRepository,
    IFormulaRepository,
    IMaterialRepository,
    IUnitOfWork,
)
from app.data_access.models import Auditoria, EvaluacionPatente, Formula, Material


def _orden_consecutivo(identificador: str) -> tuple[int, str]:
    return len(identificador), identificador


class UnitOfWorkFalsa(IUnitOfWork):
    """Cuenta confirmaciones y reversiones; puede simular un fallo de la base de datos.

    Un bloque ``async with`` que termina sin ``commit`` (con o sin excepción) cuenta como
    reversión.
    """

    def __init__(self, fallar_en_commit: bool = False, base_disponible: bool = True) -> None:
        self.fallar_en_commit = fallar_en_commit
        self.base_disponible = base_disponible
        self.confirmaciones = 0
        self.reversiones = 0
        self._confirmado = False

    async def __aenter__(self) -> "UnitOfWorkFalsa":
        self._confirmado = False
        return self

    async def __aexit__(
        self, tipo: type[BaseException] | None, exc: BaseException | None, traza: TracebackType | None
    ) -> None:
        if exc is not None or not self._confirmado:
            self.reversiones += 1

    async def commit(self) -> None:
        if self.fallar_en_commit or not self.base_disponible:
            raise ErrorBaseDatos("Fallo simulado de la base de datos")
        self.confirmaciones += 1
        self._confirmado = True

    async def rollback(self) -> None:
        self.reversiones += 1

    async def verificar_conexion(self) -> None:
        if not self.base_disponible:
            raise ErrorBaseDatos("Base de datos no disponible (simulado)")


class AuditoriaRepositoryFalso(IAuditoriaRepository):
    def __init__(self) -> None:
        self.registros: list[Auditoria] = []

    def agregar(self, registro: Auditoria) -> None:
        self.registros.append(registro)


class MaterialRepositoryFalso(IMaterialRepository):
    def __init__(self, materiales: Sequence[Material] = (), formulas: "FormulaRepositoryFalso | None" = None) -> None:
        self.materiales: dict[str, Material] = {m.id_material: m for m in materiales}
        self._formulas = formulas
        self._secuencia = len(self.materiales)

    async def obtener_por_id(self, id_material: str) -> Material | None:
        return self.materiales.get(id_material)

    async def obtener_por_ids(self, ids: Sequence[str]) -> list[Material]:
        return [self.materiales[i] for i in dict.fromkeys(ids) if i in self.materiales]

    async def existe_nombre(self, nombre: str, excluir_id: str | None = None) -> bool:
        return any(m.nombre.lower() == nombre.lower() and m.id_material != excluir_id for m in self.materiales.values())

    async def siguiente_numero(self) -> int:
        self._secuencia += 1
        return self._secuencia

    def agregar(self, material: Material) -> None:
        self.materiales[material.id_material] = material

    async def pertenece_a_formulas_con_estado(self, id_material: str, estados: Sequence[str]) -> bool:
        if self._formulas is None:
            return False
        return any(
            f.estado in estados and any(c.id_material == id_material for c in f.componentes)
            for f in self._formulas.formulas.values()
        )

    async def listar(self, pagina: int, tamano_pagina: int) -> Pagina[Material]:
        todos = sorted(self.materiales.values(), key=lambda m: _orden_consecutivo(m.id_material))
        inicio = calcular_desplazamiento(pagina, tamano_pagina)
        return Pagina(todos[inicio : inicio + tamano_pagina], pagina, tamano_pagina, len(todos))


class FormulaRepositoryFalso(IFormulaRepository):
    """Fórmulas en memoria. ``buscar`` aplica los mismos filtros que el repositorio real."""

    def __init__(self, formulas: Sequence[Formula] = ()) -> None:
        self.formulas: dict[str, Formula] = {f.id_formula: f for f in formulas}
        self._secuencia = len(self.formulas)
        self._secuencia_ticket = 0

    async def obtener_por_id(self, id_formula: str) -> Formula | None:
        return self.formulas.get(id_formula)

    async def existe_nombre(self, nombre: str, excluir_id: str | None = None) -> bool:
        return any(f.nombre.lower() == nombre.lower() and f.id_formula != excluir_id for f in self.formulas.values())

    async def siguiente_numero(self) -> int:
        self._secuencia += 1
        return self._secuencia

    async def siguiente_numero_ticket(self) -> int:
        self._secuencia_ticket += 1
        return self._secuencia_ticket

    def agregar(self, formula: Formula) -> None:
        self.formulas[formula.id_formula] = formula

    async def buscar(self, filtros: FiltrosBusquedaFormulas, pagina: int, tamano_pagina: int) -> Pagina[Formula]:
        def cumple(f: Formula) -> bool:
            texto = (filtros.texto or "").lower()
            materiales = {c.id_material for c in f.componentes}
            return (
                (not texto or texto in f.id_formula.lower() or texto in f.nombre.lower())
                and (not filtros.estado or f.estado == filtros.estado)
                and (not filtros.registro_desde or f.fecha_registro >= filtros.registro_desde)
                and (not filtros.registro_hasta or f.fecha_registro < filtros.registro_hasta)
                and (not filtros.actualizacion_desde or f.fecha_actualizacion >= filtros.actualizacion_desde)
                and (not filtros.actualizacion_hasta or f.fecha_actualizacion < filtros.actualizacion_hasta)
                and set(filtros.materiales) <= materiales
            )

        encontradas = sorted(
            (f for f in self.formulas.values() if cumple(f)),
            key=lambda f: (-f.fecha_actualizacion.timestamp(), f.id_formula),
        )
        inicio = calcular_desplazamiento(pagina, tamano_pagina)
        return Pagina(encontradas[inicio : inicio + tamano_pagina], pagina, tamano_pagina, len(encontradas))

    async def listar_por_estado(self, estado: str, pagina: int, tamano_pagina: int) -> Pagina[Formula]:
        encontradas = sorted(
            (f for f in self.formulas.values() if f.estado == estado), key=lambda f: _orden_consecutivo(f.id_formula)
        )
        inicio = calcular_desplazamiento(pagina, tamano_pagina)
        return Pagina(encontradas[inicio : inicio + tamano_pagina], pagina, tamano_pagina, len(encontradas))

    async def obtener_evaluacion_abierta(self, id_formula: str) -> EvaluacionPatente | None:
        formula = self.formulas.get(id_formula)
        if formula is None:
            return None
        return next((e for e in formula.evaluaciones if e.resultado is None), None)
