"""Registro de fórmulas: exclusivamente HU-05."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import obtener_formula_service
from app.api.schemas.comun import respuestas_error
from app.api.schemas.formulas import FormulaCrearSolicitud, FormulaRegistradaRespuesta
from app.business.services.formula_service import FormulaService

router = APIRouter(prefix="/formulas", tags=["Fórmulas"])
Servicio = Annotated[FormulaService, Depends(obtener_formula_service)]


@router.post(
    "",
    status_code=201,
    response_model=FormulaRegistradaRespuesta,
    summary="Registrar una fórmula (HU-05)",
    description="Registra una fórmula en BORRADOR con al menos dos materiales activos. No modifica existencias.",
    responses=respuestas_error(400, 409, 422, 500),
)
async def registrar_formula(solicitud: FormulaCrearSolicitud, servicio: Servicio) -> FormulaRegistradaRespuesta:
    resultado = await servicio.registrar(solicitud.a_comando())
    return FormulaRegistradaRespuesta.con_mensaje(resultado.datos, resultado.mensaje or "")
