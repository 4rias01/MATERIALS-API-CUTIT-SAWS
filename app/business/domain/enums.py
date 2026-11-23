"""Valores permitidos del dominio (objetos de valor enumerados).

Las restricciones CHECK de la base de datos repiten estos valores
(app/infraestructure/models/material.py).
"""

from enum import StrEnum


class Categoria(StrEnum):
    """Categoría del material (HU-01 c1)."""

    MATERIA_PRIMA = "Materia Prima"
    COMPONENTES = "Componentes"
    LUBRICANTES = "Lubricantes"


class UnidadMedida(StrEnum):
    """Unidad de medida del material (HU-01 c1)."""

    UNIDAD = "und"
    GRAMO = "g"
    KILOGRAMO = "kg"
    MILILITRO = "mL"
    LITRO = "L"
    METRO = "m"


class EstadoMaterial(StrEnum):
    """Estado del material: se registra en ACTIVO (HU-01 c7.3)."""

    ACTIVO = "ACTIVO"
    INACTIVO = "INACTIVO"
