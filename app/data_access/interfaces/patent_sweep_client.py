"""Contrato del cliente de la API de Patent Sweep (célula 2)."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


def numero_json(valor: Decimal) -> int | float:
    """Número para JSON: entero si no tiene decimales (2 en vez de 2.0)."""
    return int(valor) if valor == valor.to_integral_value() else float(valor)


@dataclass(frozen=True, slots=True)
class ComponenteEvaluacion:
    material_id: str
    nombre: str
    cantidad: Decimal
    unidad_medida: str


@dataclass(frozen=True, slots=True)
class SolicitudEvaluacionPatente:
    """Cuerpo de la solicitud de evaluación (HU-09 c2)."""

    formula_id: str
    ticket_evaluacion_id: str
    nombre: str
    aplicacion_tecnica: str
    componentes: Sequence[ComponenteEvaluacion]

    def a_json(self) -> dict[str, Any]:
        return {
            "formulaId": self.formula_id,
            "ticketEvaluacionId": self.ticket_evaluacion_id,
            "nombre": self.nombre,
            "aplicacionTecnica": self.aplicacion_tecnica,
            "componentes": [
                {
                    "materialId": c.material_id,
                    "nombre": c.nombre,
                    "cantidad": numero_json(c.cantidad),
                    "unidadMedida": c.unidad_medida,
                }
                for c in self.componentes
            ],
        }


class IPatentSweepClient(ABC):
    """Operaciones que este módulo pide a Patent Sweep (request-reply asíncrono con callback).

    Los fallos de comunicación (sin respuesta, error interno, más de 5 s o circuito
    abierto) se lanzan como ``app.core.exceptions.ErrorServicioExterno``.
    """

    @abstractmethod
    async def solicitar_evaluacion(self, solicitud: SolicitudEvaluacionPatente) -> None:
        """Envía la solicitud; Patent Sweep la acepta con 202 y después envía el dictamen
        a POST /formulas/{id}/dictamen-patente (HU-09 c3)."""

    @abstractmethod
    def estado_circuito(self) -> str:
        """Estado del circuit breaker: CERRADO, ABIERTO o SEMIABIERTO."""
