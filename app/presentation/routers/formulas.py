"""Rutas del recurso /formulas (HU-05 a HU-08 y HU-11)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.business.domain import mensajes
from app.business.domain.value_objects import PATRON_ID_FORMULA
from app.business.services.formula_service import FormulaService
from app.presentation.dependencies import obtener_formula_service
from app.presentation.schemas.comun import mensaje_solicitud_invalida, respuestas_error
from app.presentation.schemas.formulas import (
    FiltrosFormulasConsulta,
    FormulaActualizarSolicitud,
    FormulaCrearSolicitud,
    FormulaEstadoRespuesta,
    FormulaRespuesta,
    FormulasAprobadasRespuesta,
    FormulasPaginaRespuesta,
    PaginacionAprobadasConsulta,
)

router = APIRouter(prefix="/formulas", tags=["Fórmulas"])

Servicio = Annotated[FormulaService, Depends(obtener_formula_service)]
IdFormula = Annotated[str, Path(description="Código de la fórmula (form-NNN).", examples=["form-001"])]


@router.post(
    "",
    status_code=201,
    response_model=FormulaRespuesta,
    response_model_exclude_none=True,
    summary="Registrar una fórmula (HU-05)",
    description="Crea la fórmula en estado BORRADOR, versión 1, con mínimo 2 materiales activos diferentes.",
    responses=respuestas_error(400, 409, 422, 500),
)
async def registrar_formula(solicitud: FormulaCrearSolicitud, servicio: Servicio) -> FormulaRespuesta:
    resultado = await servicio.registrar(solicitud.a_comando())
    return FormulaRespuesta.desde_modelo(resultado.datos, resultado.mensaje)


@router.get(
    "",
    response_model=FormulasPaginaRespuesta,
    response_model_exclude_none=True,
    summary="Consultar fórmulas (HU-06)",
    description="Búsqueda y filtros combinables; de la más reciente a la más antigua, en páginas de 10.",
    responses=respuestas_error(400, 500),
)
async def listar_formulas(
    filtros: Annotated[FiltrosFormulasConsulta, Query()], servicio: Servicio
) -> FormulasPaginaRespuesta:
    resultado = await servicio.listar(filtros.a_consulta())
    return FormulasPaginaRespuesta.desde_pagina(resultado.datos, resultado.mensaje)


# Debe declararse antes de /{id_formula} para que "aprobadas" no se tome como un código.
@router.get(
    "/aprobadas",
    response_model=FormulasAprobadasRespuesta,
    response_model_exclude_none=True,
    summary="Consultar las fórmulas aprobadas (HU-11)",
    description="Consulta de solo lectura para Patent Sweep: fórmulas en estado APROBADA con su composición, "
    "ordenadas por formulaId.",
    responses=respuestas_error(400, 500),
)
async def listar_formulas_aprobadas(
    parametros: Annotated[PaginacionAprobadasConsulta, Query()], servicio: Servicio
) -> FormulasAprobadasRespuesta:
    resultado = await servicio.listar_aprobadas(parametros.pagina, parametros.tamano_pagina)
    return FormulasAprobadasRespuesta.desde_pagina(resultado.datos, resultado.mensaje)


@router.get(
    "/{id_formula}",
    response_model=FormulaRespuesta,
    response_model_exclude_none=True,
    summary="Consultar el detalle de una fórmula (HU-06)",
    description="Ficha técnica con sus componentes; si está RECHAZADA_POR_INFRACCION incluye las patentes en conflicto.",
    responses=respuestas_error(404, 500),
)
async def consultar_formula(id_formula: IdFormula, servicio: Servicio) -> FormulaRespuesta:
    resultado = await servicio.consultar(id_formula)
    return FormulaRespuesta.desde_modelo(resultado.datos)


@router.put(
    "/{id_formula}",
    response_model=FormulaRespuesta,
    response_model_exclude_none=True,
    summary="Modificar una fórmula (HU-07)",
    description="Solo en BORRADOR o RECHAZADA_POR_INFRACCION; incrementa la versión y deja la fórmula en BORRADOR.",
    responses=respuestas_error(400, 404, 409, 422, 500),
)
async def actualizar_formula(
    id_formula: IdFormula, solicitud: FormulaActualizarSolicitud, servicio: Servicio
) -> FormulaRespuesta:
    resultado = await servicio.actualizar(id_formula, solicitud.a_comando())
    return FormulaRespuesta.desde_modelo(resultado.datos, resultado.mensaje)


@router.patch(
    "/{id_formula}/descontinuar",
    response_model=FormulaEstadoRespuesta,
    summary="Descontinuar una fórmula (HU-08)",
    responses=respuestas_error(400, 404, 409, 500),
    openapi_extra=mensaje_solicitud_invalida(mensajes.HU08_C3),
)
async def descontinuar_formula(
    id_formula: Annotated[str, Path(pattern=PATRON_ID_FORMULA, description="Código de la fórmula (form-NNN).", examples=["form-001"])],
    servicio: Servicio,
) -> FormulaEstadoRespuesta:
    # TODO(HU-08 c3): rechazar también parámetros o cuerpo no permitidos.
    resultado = await servicio.descontinuar(id_formula)
    return FormulaEstadoRespuesta.desde_modelo(resultado.datos, resultado.mensaje or "")
