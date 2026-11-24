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


class EstadoFormula(StrEnum):
    """Estados definidos en HU-05 c7.2; el registro solo crea BORRADOR."""

    BORRADOR = "BORRADOR"
    EVALUANDO_PATENTE = "EVALUANDO_PATENTE"
    APROBADA = "APROBADA"
    RECHAZADA_POR_INFRACCION = "RECHAZADA_POR_INFRACCION"
    DESCONTINUADA = "DESCONTINUADA"
