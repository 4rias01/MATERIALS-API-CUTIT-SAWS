"""Datos de entrada de los casos de uso.

Los routers convierten los DTO de la capa de presentación en estos objetos, así los
servicios no dependen de FastAPI ni de Pydantic y se pueden invocar desde cualquier
punto de entrada, incluidas las pruebas (patrón Service Layer).
"""

from dataclasses import dataclass
from decimal import Decimal

from app.business.domain.formulas import AplicacionTecnica, ComponenteFormula, NombreFormula, validar_componentes


@dataclass(frozen=True, slots=True)
class RegistrarMaterialComando:
    """HU-01: POST /materiales."""

    nombre: str
    categoria: str
    unidad_medida: str
    densidad: Decimal
    pureza: Decimal

@dataclass(frozen=True, slots=True)
class ActualizarMaterialComando:
    """HU-03: PUT /materiales/{id}. Unidad de medida es de solo lectura, no va aquí."""

    nombre: str
    categoria: str
    densidad: Decimal
    pureza: Decimal


@dataclass(frozen=True, slots=True)
class DatosMaterial:
    """Campos editables de un material (PUT /materiales/{id}, CRUD básico)."""

    nombre: str
    categoria: str
    unidad_medida: str
    densidad: Decimal
    pureza: Decimal


@dataclass(frozen=True, slots=True)
class RegistrarFormulaComando:
    """HU-05: POST /formulas. Valida también las llamadas ajenas a la API."""

    nombre: str
    aplicacion_tecnica: str
    componentes: tuple[ComponenteFormula, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "nombre", NombreFormula.crear(self.nombre).valor)
        AplicacionTecnica(self.aplicacion_tecnica)
        validar_componentes(self.componentes)
