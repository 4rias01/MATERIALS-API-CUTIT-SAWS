"""Contrato del repositorio de fórmulas (patrón Repository).

La fórmula es la raíz del agregado: sus componentes y sus evaluaciones de patente
(con las patentes en conflicto) se guardan a través de ella.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime

from app.core.paginacion import Pagina
from app.data_access.models import EvaluacionPatente, Formula


@dataclass(frozen=True, slots=True)
class FiltrosBusquedaFormulas:
    """Filtros de GET /formulas (HU-06 c1); todos son opcionales y se combinan con Y.

    Los rangos de fechas son [desde, hasta): el servicio convierte las fechas
    DD/MM/AAAA del usuario en instantes con zona horaria.
    """

    texto: str | None = None  # coincidencia parcial en código o nombre, sin distinguir mayúsculas
    estado: str | None = None
    registro_desde: datetime | None = None
    registro_hasta: datetime | None = None
    actualizacion_desde: datetime | None = None
    actualizacion_hasta: datetime | None = None
    materiales: Sequence[str] = field(default_factory=tuple)  # la fórmula contiene todos


class IFormulaRepository(ABC):
    """Acceso a las tablas formula, componente_formula, evaluacion_patente y patente_conflicto."""

    @abstractmethod
    async def obtener_por_id(self, id_formula: str) -> Formula | None:
        """Fórmula con sus componentes (y el material de cada uno) y sus evaluaciones
        (con las patentes en conflicto), o None (HU-06 c3 y c4)."""

    @abstractmethod
    async def existe_nombre(self, nombre: str, excluir_id: str | None = None) -> bool:
        """Si otra fórmula ya usa ``nombre`` sin distinguir mayúsculas (HU-05 c6.1)."""

    @abstractmethod
    async def siguiente_numero(self) -> int:
        """Siguiente número de la secuencia del código form-NNN."""

    @abstractmethod
    async def siguiente_numero_ticket(self) -> int:
        """Siguiente número de la secuencia del ticketEvaluacionId tck-NNN."""

    @abstractmethod
    def agregar(self, formula: Formula) -> None:
        """Agrega una fórmula nueva (con sus componentes) a la transacción en curso."""

    @abstractmethod
    async def buscar(self, filtros: FiltrosBusquedaFormulas, pagina: int, tamano_pagina: int) -> Pagina[Formula]:
        """Fórmulas que cumplen los filtros, de la más reciente a la más antigua por fecha
        de última actualización (HU-06 c2). No carga los componentes."""

    @abstractmethod
    async def listar_por_estado(self, estado: str, pagina: int, tamano_pagina: int) -> Pagina[Formula]:
        """Fórmulas en ``estado`` ordenadas por código ascendente, con sus componentes y el
        material de cada uno (HU-11 c2 y c3)."""

    @abstractmethod
    async def obtener_evaluacion_abierta(self, id_formula: str) -> EvaluacionPatente | None:
        """Trámite de evaluación sin dictamen de la fórmula, o None (HU-10 c6)."""
