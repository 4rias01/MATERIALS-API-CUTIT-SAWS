"""Contrato del repositorio de materiales (patrón Repository)."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.core.paginacion import Pagina
from app.data_access.models import Material


class IMaterialRepository(ABC):
    """Acceso a la tabla material. Los cambios se confirman con la unidad de trabajo."""

    @abstractmethod
    async def obtener_por_id(self, id_material: str) -> Material | None:
        """Material con ese ID, en cualquier estado (HU-02 c2), o None."""

    @abstractmethod
    async def obtener_por_ids(self, ids: Sequence[str]) -> list[Material]:
        """Los materiales que existen entre ``ids``, en una sola consulta (HU-05 c4, HU-07 c4)."""

    @abstractmethod
    async def existe_nombre(self, nombre: str, excluir_id: str | None = None) -> bool:
        """Si otro material ya usa ``nombre`` sin distinguir mayúsculas (HU-01 c3, HU-03 c3).

        ``excluir_id`` deja por fuera al propio material cuando se modifica.
        """

    @abstractmethod
    async def siguiente_numero(self) -> int:
        """Siguiente número de la secuencia del ID mat-NNN."""

    @abstractmethod
    def agregar(self, material: Material) -> None:
        """Agrega un material nuevo a la transacción en curso."""

    @abstractmethod
    async def pertenece_a_formulas_con_estado(self, id_material: str, estados: Sequence[str]) -> bool:
        """Si el material es componente de alguna fórmula en uno de ``estados`` (HU-04 c5)."""

    @abstractmethod
    async def listar(self, pagina: int, tamano_pagina: int) -> Pagina[Material]:
        """Listado paginado de materiales ordenado por ID (GET /materiales, HU-02 c3).

        TODO(HU-02 c3): agregar los filtros cuando el PO los defina (el backlog solo da
        el ejemplo ``densidad=abc``).
        """
