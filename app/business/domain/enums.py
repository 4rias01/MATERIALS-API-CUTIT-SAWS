"""Valores permitidos del dominio (objetos de valor enumerados).

Las restricciones CHECK de la base de datos repiten estos valores
(app/data_access/models). La prueba tests/unit/test_modelos_vs_dominio.py verifica
que ambas listas coincidan.
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
    """Estado del material: INACTIVO es el borrado lógico (HU-04)."""

    ACTIVO = "ACTIVO"
    INACTIVO = "INACTIVO"


class EstadoFormula(StrEnum):
    """Estados del ciclo de vida de la fórmula (HU-05 c7.2)."""

    BORRADOR = "BORRADOR"
    EVALUANDO_PATENTE = "EVALUANDO_PATENTE"
    APROBADA = "APROBADA"
    RECHAZADA_POR_INFRACCION = "RECHAZADA_POR_INFRACCION"
    DESCONTINUADA = "DESCONTINUADA"


class ResultadoDictamen(StrEnum):
    """Resultado del dictamen de Patent Sweep (HU-10 c3.2)."""

    SIN_INFRACCION = "SIN_INFRACCION"
    INFRACCION = "INFRACCION"
