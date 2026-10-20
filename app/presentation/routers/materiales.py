"""Rutas del recurso /materiales (HU-01 a HU-04)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.business.domain import mensajes
from app.business.domain.value_objects import PATRON_ID_MATERIAL
from app.business.services.material_service import MaterialService
from app.presentation.dependencies import obtener_material_service
from app.presentation.schemas.comun import mensaje_solicitud_invalida, respuestas_error
from app.presentation.schemas.materiales import (
    ListadoMaterialesConsulta,
    MaterialActualizarSolicitud,
    MaterialCrearSolicitud,
    MaterialEstadoRespuesta,
    MaterialesPaginaRespuesta,
    MaterialFichaRespuesta,
    MaterialRespuesta,
)

router = APIRouter(prefix="/materiales", tags=["Materiales"])

Servicio = Annotated[MaterialService, Depends(obtener_material_service)]
IdMaterial = Annotated[str, Path(description="ID del material (mat-NNN).", examples=["mat-001"])]


@router.post(
    "",
    status_code=201,
    response_model=MaterialRespuesta,
    response_model_exclude_none=True,
    summary="Registrar un material (HU-01)",
    description="Registra el material como materia prima en Inventario, que asigna el SKU, y lo guarda en estado ACTIVO.",
    responses=respuestas_error(400, 409, 500, 503),
)
async def registrar_material(solicitud: MaterialCrearSolicitud, servicio: Servicio) -> MaterialRespuesta:
    resultado = await servicio.registrar(solicitud.a_comando())
    return MaterialRespuesta.desde_modelo(resultado.datos, resultado.mensaje)


@router.get(
    "",
    response_model=MaterialesPaginaRespuesta,
    response_model_exclude_none=True,
    summary="Listar materiales (HU-02 c3, filtros por definir)",
    responses=respuestas_error(400, 500),
)
async def listar_materiales(
    parametros: Annotated[ListadoMaterialesConsulta, Query()], servicio: Servicio
) -> MaterialesPaginaRespuesta:
    resultado = await servicio.listar(parametros.pagina, parametros.tamano_pagina)
    return MaterialesPaginaRespuesta.desde_pagina(resultado.datos, resultado.mensaje)


@router.get(
    "/{id_material}",
    response_model=MaterialFichaRespuesta,
    summary="Consultar un material (HU-02)",
    description="Devuelve la ficha técnica del material, en estado ACTIVO o INACTIVO.",
    responses=respuestas_error(404, 500),
)
async def consultar_material(id_material: IdMaterial, servicio: Servicio) -> MaterialFichaRespuesta:
    resultado = await servicio.consultar(id_material)
    return MaterialFichaRespuesta.desde_modelo(resultado.datos)


@router.put(
    "/{id_material}",
    response_model=MaterialRespuesta,
    response_model_exclude_none=True,
    summary="Modificar un material (HU-03)",
    description="Si cambia el nombre, primero lo cambia en Inventario. ID, SKU y Unidad de medida son de solo lectura.",
    responses=respuestas_error(400, 404, 409, 500, 503),
)
async def actualizar_material(
    id_material: IdMaterial, solicitud: MaterialActualizarSolicitud, servicio: Servicio
) -> MaterialRespuesta:
    resultado = await servicio.actualizar(id_material, solicitud.a_comando())
    return MaterialRespuesta.desde_modelo(resultado.datos, resultado.mensaje)


@router.delete(
    "/{id_material}",
    response_model=MaterialEstadoRespuesta,
    summary="Inhabilitar un material (HU-04)",
    description="Borrado lógico: cambia el estado a INACTIVO sin eliminar el registro.",
    responses=respuestas_error(400, 404, 409, 500),
    openapi_extra=mensaje_solicitud_invalida(mensajes.HU04_C3),
)
async def inhabilitar_material(
    id_material: Annotated[str, Path(pattern=PATRON_ID_MATERIAL, description="ID del material (mat-NNN).", examples=["mat-001"])],
    servicio: Servicio,
) -> MaterialEstadoRespuesta:
    # TODO(HU-04 c3): rechazar también parámetros de consulta o cuerpo no permitidos.
    resultado = await servicio.inhabilitar(id_material)
    return MaterialEstadoRespuesta.desde_modelo(resultado.datos, resultado.mensaje or "")
