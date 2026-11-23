"""Repositorio en memoria para las pruebas de aceptación de HU-05."""

from app.infraestructure.interfaces import IFormulaRepository
from app.infraestructure.models import Formula


class FormulaRepositoryFalso(IFormulaRepository):
    """No simula rollback; las pruebas de integración comprueban la atomicidad real."""

    def __init__(self) -> None:
        self.formulas: dict[str, Formula] = {}
        self._secuencia = 0

    async def existe_nombre(self, nombre: str) -> bool:
        return any(f.nombre.lower() == nombre.lower() for f in self.formulas.values())

    async def siguiente_numero(self) -> int:
        self._secuencia += 1
        return self._secuencia

    async def agregar(self, formula: Formula) -> None:
        self.formulas[formula.id_formula] = formula
