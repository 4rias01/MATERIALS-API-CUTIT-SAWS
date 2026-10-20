"""Rutas de la integración con Patent Sweep (HU-09 y HU-10)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.business.services.evaluacion_patente_service import EvaluacionPatenteService
from app.presentation.dependencies import obtener_evaluacion_patente_service
from app.presentation.schemas.comun import respuestas_error
from app.presentation.schemas.evaluacion_patente import DictamenSolicitud, TramiteEvaluacionRespuesta

router = APIRouter(prefix="/formulas", tags=["Evaluación de patentes"])

Servicio = Annotated[EvaluacionPatenteService, Depends(obtener_evaluacion_patente_service)]
IdFormula = Annotated[str, Path(description="Código de la fórmula (form-NNN).", examples=["form-001"])]


@router.post(
    "/{id_formula}/evaluacion-patente",
    status_code=202,
    response_model=TramiteEvaluacionRespuesta,
    summary="Solicitar la evaluación de patente (HU-09)",
    description="Envía la fórmula a Patent Sweep (timeout 5 s), la deja en EVALUANDO_PATENTE y responde 202 con el "
    "ticketEvaluacionId. El dictamen llega después por callback.",
    responses=respuestas_error(404, 409, 422, 500, 503),
)
async def solicitar_evaluacion_patente(id_formula: IdFormula, servicio: Servicio) -> TramiteEvaluacionRespuesta:
    resultado = await servicio.solicitar(id_formula)
    return TramiteEvaluacionRespuesta.desde_tramite(resultado.datos, resultado.mensaje or "")


@router.post(
    "/{id_formula}/dictamen-patente",
    response_model=TramiteEvaluacionRespuesta,
    summary="Registrar el dictamen de patente (HU-10, callback de Patent Sweep)",
    description="Patent Sweep envía el resultado del trámite activo: SIN_INFRACCION aprueba la fórmula e "
    "INFRACCION la rechaza y guarda las patentes en conflicto. Sin autenticación (riesgo documentado en el DAS).",
    responses=respuestas_error(400, 404, 409, 500),
)
async def registrar_dictamen_patente(
    id_formula: IdFormula, solicitud: DictamenSolicitud, servicio: Servicio
) -> TramiteEvaluacionRespuesta:
    resultado = await servicio.registrar_dictamen(id_formula, solicitud.a_comando())
    return TramiteEvaluacionRespuesta.desde_tramite(resultado.datos, resultado.mensaje or "")
