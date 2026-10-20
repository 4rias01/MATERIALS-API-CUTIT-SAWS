"""DTO de la integración con Patent Sweep (HU-09 y HU-10)."""

from typing import Any, Self

from pydantic import Field

from app.business.domain.enums import EstadoFormula, ResultadoDictamen
from app.business.domain.value_objects import PATRON_TICKET_EVALUACION
from app.business.services.comandos import PatenteConflictoDato, RegistrarDictamenComando
from app.presentation.schemas.comun import EsquemaEntrada, EsquemaSalida


class PatenteConflictoSolicitud(EsquemaEntrada):
    """Elemento de ``patentesEnConflicto`` (HU-10 c3.4 y c3.5)."""

    conflicto_id: str = Field(pattern=r"^\d{6}$", description="6 dígitos numéricos.", examples=["123456"])
    titulo: str = Field(min_length=1, max_length=60, examples=["Aleación de tungsteno para filos"])


class DictamenSolicitud(EsquemaEntrada):
    """Cuerpo del callback POST /formulas/{id}/dictamen-patente (HU-10 c3).

    TODO(HU-10 c4):
    * ``mensajes_error``: ("ticketEvaluacionId", "*") → ``HU10_C4_1``; ("resultado", "*") →
      ``HU10_C4_2``; ("patentesEnConflicto", "too_long") → ``HU10_C4_6``; errores dentro de un
      elemento (loc ``("patentesEnConflicto", i, ...)``) → ``HU10_C4_5`` (sobrescribir
      ``mensaje_para_error``).
    * ``@model_validator(mode="after")``: INFRACCION con arreglo vacío → ``HU10_C4_3``;
      SIN_INFRACCION con elementos → ``HU10_C4_4``.
    * El backlog no define mensaje si falta ``patentesEnConflicto`` (ver README).
    """

    ticket_evaluacion_id: str = Field(pattern=PATRON_TICKET_EVALUACION, examples=["tck-001"])
    resultado: ResultadoDictamen
    patentes_en_conflicto: list[PatenteConflictoSolicitud] = Field(
        max_length=50,
        description="Vacío si el resultado es SIN_INFRACCION; de 1 a 50 elementos si es INFRACCION.",
    )

    def a_comando(self) -> RegistrarDictamenComando:
        return RegistrarDictamenComando(
            ticket_evaluacion_id=self.ticket_evaluacion_id,
            resultado=self.resultado.value,
            patentes_en_conflicto=tuple(PatenteConflictoDato(p.conflicto_id, p.titulo) for p in self.patentes_en_conflicto),
        )


class TramiteEvaluacionRespuesta(EsquemaSalida):
    """Respuesta de la solicitud de evaluación (HU-09 c1: 202) y del dictamen (HU-10 c1 y c2: 200)."""

    formula_id: str = Field(examples=["form-001"])
    ticket_evaluacion_id: str = Field(examples=["tck-001"])
    estado: EstadoFormula
    mensaje: str = Field(examples=["Solicitud enviada al departamento de patentes exitosamente. Ticket asignado: tck-001"])

    @classmethod
    def desde_tramite(cls, tramite: Any, mensaje: str) -> Self:
        """``tramite`` es el TramiteEvaluacion que devuelve EvaluacionPatenteService."""
        return cls(
            formula_id=tramite.formula_id,
            ticket_evaluacion_id=tramite.ticket_evaluacion_id,
            estado=tramite.estado,
            mensaje=mensaje,
        )
