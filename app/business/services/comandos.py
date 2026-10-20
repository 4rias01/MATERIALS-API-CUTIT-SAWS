"""Datos de entrada de los casos de uso.

Los routers convierten los DTO de la capa de presentación en estos objetos, así los
servicios no dependen de FastAPI ni de Pydantic y se pueden invocar desde cualquier
punto de entrada, incluidas las pruebas (patrón Service Layer).
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


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
    """HU-03: PUT /materiales/{id}. ID, SKU y Unidad de medida son de solo lectura."""

    nombre: str
    categoria: str
    densidad: Decimal
    pureza: Decimal


@dataclass(frozen=True, slots=True)
class ComponenteComando:
    """Línea de la tabla de componentes (HU-05 c1, HU-07 c2)."""

    id_material: str
    cantidad: Decimal


@dataclass(frozen=True, slots=True)
class RegistrarFormulaComando:
    """HU-05: POST /formulas."""

    nombre: str
    aplicacion_tecnica: str
    componentes: tuple[ComponenteComando, ...]


@dataclass(frozen=True, slots=True)
class ActualizarFormulaComando:
    """HU-07: PUT /formulas/{id}. El código form-NNN es de solo lectura."""

    nombre: str
    aplicacion_tecnica: str
    componentes: tuple[ComponenteComando, ...]


@dataclass(frozen=True, slots=True)
class ConsultaFormulas:
    """HU-06: filtros de GET /formulas (todos opcionales) y la página pedida."""

    texto: str | None = None
    estado: str | None = None
    registro_desde: date | None = None
    registro_hasta: date | None = None
    actualizacion_desde: date | None = None
    actualizacion_hasta: date | None = None
    materiales: tuple[str, ...] = field(default_factory=tuple)
    pagina: int = 1


@dataclass(frozen=True, slots=True)
class PatenteConflictoDato:
    """Patente en conflicto del dictamen (HU-10 c3.4 y c3.5)."""

    conflicto_id: str
    titulo: str


@dataclass(frozen=True, slots=True)
class RegistrarDictamenComando:
    """HU-10: POST /formulas/{id}/dictamen-patente (callback de Patent Sweep)."""

    ticket_evaluacion_id: str
    resultado: str
    patentes_en_conflicto: tuple[PatenteConflictoDato, ...] = ()
