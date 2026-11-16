"""Rutas del recurso /materiales (CRUD básico, equivalente al ProfesorController del dojo)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response

from app.api.dependencies import obtener_material_service
from app.api.schemas.comun import mensaje_solicitud_invalida, respuestas_error
from app.api.schemas.materiales import MaterialRespuesta, MaterialSolicitud
from app.business.domain import mensajes
from app.business.services.material_service import MaterialService

router = APIRouter(prefix="/materiales", tags=["Materiales"])

Servicio = Annotated[MaterialService, Depends(obtener_material_service)]
# Entero positivo dentro del rango de BIGINT de PostgreSQL.
IdMaterial = Annotated[int, Path(gt=0, le=2**63 - 1, description="Id del material.")]
ID_INVALIDO = mensaje_solicitud_invalida(mensajes.formatear(mensajes.MATERIAL_CAMPO_INVALIDO, campo="id"))


@router.post(
    "",
    status_code=201,
    response_model=MaterialRespuesta,
    summary="Crear material",
    responses=respuestas_error(400, 409, 500),
)
async def crear(solicitud: MaterialSolicitud, servicio: Servicio) -> MaterialRespuesta:
    resultado = await servicio.crear(solicitud.a_datos())
    return MaterialRespuesta.desde_modelo(resultado.datos)


@router.get("", response_model=list[MaterialRespuesta], summary="Listar materiales", responses=respuestas_error(500))
async def obtener_todos(servicio: Servicio) -> list[MaterialRespuesta]:
    resultado = await servicio.obtener_todos()
    return [MaterialRespuesta.desde_modelo(m) for m in resultado.datos]


# Antes de /{id_material}: si no, "buscar" se tomaría como un id.
@router.get(
    "/buscar",
    response_model=list[MaterialRespuesta],
    summary="Buscar por nombre",
    description="Materiales cuyo nombre contiene el texto, sin distinguir mayúsculas.",
    responses=respuestas_error(400, 500),
    openapi_extra=mensaje_solicitud_invalida(mensajes.formatear(mensajes.MATERIAL_CAMPO_INVALIDO, campo="nombre")),
)
async def buscar_por_nombre(
    servicio: Servicio, nombre: Annotated[str, Query(min_length=1, max_length=100)]
) -> list[MaterialRespuesta]:
    resultado = await servicio.buscar_por_nombre(nombre)
    return [MaterialRespuesta.desde_modelo(m) for m in resultado.datos]


@router.get(
    "/{id_material}",
    response_model=MaterialRespuesta,
    summary="Buscar por id",
    responses=respuestas_error(400, 404, 500),
    openapi_extra=ID_INVALIDO,
)
async def obtener_por_id(id_material: IdMaterial, servicio: Servicio) -> MaterialRespuesta:
    resultado = await servicio.obtener_por_id(id_material)
    return MaterialRespuesta.desde_modelo(resultado.datos)


@router.put(
    "/{id_material}",
    response_model=MaterialRespuesta,
    summary="Actualizar material",
    responses=respuestas_error(400, 404, 409, 500),
    openapi_extra=ID_INVALIDO,
)
async def actualizar(id_material: IdMaterial, solicitud: MaterialSolicitud, servicio: Servicio) -> MaterialRespuesta:
    resultado = await servicio.actualizar(id_material, solicitud.a_datos())
    return MaterialRespuesta.desde_modelo(resultado.datos)


@router.delete(
    "/{id_material}",
    status_code=204,
    summary="Eliminar material",
    responses=respuestas_error(400, 404, 500),
    openapi_extra=ID_INVALIDO,
)
async def eliminar(id_material: IdMaterial, servicio: Servicio) -> Response:
    await servicio.eliminar(id_material)
    return Response(status_code=204)
