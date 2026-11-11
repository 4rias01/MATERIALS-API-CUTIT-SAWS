"""Datos de entrada de los casos de uso.

Los routers convierten los DTO de la capa de presentación en estos objetos, así los
servicios no dependen de FastAPI ni de Pydantic y se pueden invocar desde cualquier
punto de entrada, incluidas las pruebas (patrón Service Layer).
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class RegistrarMaterialComando:
    """HU-01: POST /materiales."""

    nombre: str
    categoria: str
    unidad_medida: str
    densidad: Decimal
    pureza: Decimal
