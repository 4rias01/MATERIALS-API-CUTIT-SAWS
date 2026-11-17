"""Valores permitidos del dominio (objetos de valor enumerados).

Las restricciones CHECK de la base de datos repiten estos valores
(app/infraestructure/models/material.py).
"""

from enum import StrEnum


class Categoria(StrEnum):
    """Categoría del material."""

    MATERIA_PRIMA = "Materia Prima"
    COMPONENTES = "Componentes"
    LUBRICANTES = "Lubricantes"


class UnidadMedida(StrEnum):
    """Unidad de medida del material."""

    UNIDAD = "und"
    GRAMO = "g"
    KILOGRAMO = "kg"
    MILILITRO = "mL"
    LITRO = "L"
    METRO = "m"
