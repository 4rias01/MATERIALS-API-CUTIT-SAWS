"""Paginación con LIMIT/OFFSET en la base de datos (patrón Pagination)."""

import math
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


def calcular_desplazamiento(pagina: int, tamano_pagina: int) -> int:
    """OFFSET de la página ``pagina`` (la primera es la 1)."""
    return (pagina - 1) * tamano_pagina


@dataclass(frozen=True, slots=True)
class Pagina(Generic[T]):
    """Una página de resultados y los totales de la consulta completa."""

    elementos: list[T]
    pagina: int
    tamano_pagina: int
    total_registros: int

    @property
    def total_paginas(self) -> int:
        """Cantidad de páginas; 0 si no hay registros."""
        return math.ceil(self.total_registros / self.tamano_pagina) if self.total_registros else 0

    @property
    def esta_vacia(self) -> bool:
        return not self.elementos
