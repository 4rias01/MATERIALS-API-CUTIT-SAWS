"""Rutas del recurso /materiales.

* POST: HU-01 (registrar material).
* GET: ficha técnica y listado paginado (HU-02).
* PUT: modificación de materiales activos (HU-03).
* El CRUD conserva la búsqueda por nombre y la eliminación.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response

from app.api.dependencies import obtener_material_service
from app.api.schemas.comun import mensaje_solicitud_invalida, respuestas_error
from app.api.schemas.materiales import (
    ConsultaMaterial,
    FichaMaterial,
    ListaMateriales,
    MaterialActualizadoRespuesta,
    MaterialActualizarSolicitud,
    MaterialCrearSolicitud,
    MaterialRegistradoRespuesta,
    MaterialRespuesta,
)
from app.business.domain import mensajes
from app.business.services.material_service import TAMANO_PAGINA, MaterialService

router = APIRouter(prefix="/materiales", tags=["Materiales"])

Servicio = Annotated[MaterialService, Depends(obtener_material_service)]
# ID secuencial mat-NNN (HU-01 c7.1). Sin ``pattern``: HU-02 c4, HU-03 c8 y HU-04 c4
# exigen que un id mal formado (p. ej. "abc") también responda 404 desde el servicio.
IdMaterial = Annotated[
    str,
    Path(
        description="Id del material (mat-NNN).",
        examples=["mat-001"],
    ),
]


@router.post(
    "",
    status_code=201,
    response_model=MaterialRegistradoRespuesta,
    summary="Registrar un material (HU-01)",
    description="Registra el material como materia prima en Inventario, que asigna el SKU, y lo guarda en estado ACTIVO.",
    responses=respuestas_error(400, 409, 500, 503),
)
async def registrar_material(solicitud: MaterialCrearSolicitud, servicio: Servicio) -> MaterialRegistradoRespuesta:
    resultado = await servicio.registrar(solicitud.a_comando())
    return MaterialRegistradoRespuesta.con_mensaje(resultado.datos, resultado.mensaje or "")


@router.get("", summary="Listar materiales (HU-02)", responses=respuestas_error(400, 500), response_model_exclude_none=True)
async def listar_materiales(consulta: Annotated[ConsultaMaterial, Query()], servicio: Servicio) -> ListaMateriales:
    materiales, total = await servicio.listar(consulta.a_filtros(), consulta.pagina)
    return ListaMateriales(
        pagina=consulta.pagina,
        tamano_pagina=TAMANO_PAGINA,
        total_registros=total,
        total_paginas=(total + TAMANO_PAGINA - 1) // TAMANO_PAGINA,
        materiales=[FichaMaterial.de_material(material) for material in materiales],
        mensaje=mensajes.HU02_C7 if total == 0 else None,
    )


# Antes de /{id_material}: si no, "buscar" se tomaría como un id.
@router.get(
    "/buscar",
    response_model=list[MaterialRespuesta],
    summary="Buscar por nombre",
    description="Materiales cuyo nombre contiene el texto, sin distinguir mayúsculas.",
    responses=respuestas_error(400, 500),
    openapi_extra=mensaje_solicitud_invalida(mensajes.formatear(mensajes.MATERIAL_CAMPO_INVALIDO, campo="nombre")),
)
async def buscar_por_nombre(servicio: Servicio, nombre: Annotated[str, Query(min_length=1, max_length=100)]) -> list[MaterialRespuesta]:
    resultado = await servicio.buscar_por_nombre(nombre)
    return [MaterialRespuesta.desde_modelo(m) for m in resultado.datos]


@router.get("/{id_material}", summary="Consultar la ficha técnica de un material (HU-02)", responses=respuestas_error(404, 500))
async def obtener_por_id(
    id_material: Annotated[str, Path(description="ID del material, formato mat-NNN.", examples=["mat-101"])],
    servicio: Servicio,
) -> FichaMaterial:
    resultado = await servicio.obtener_por_id(id_material)
    return FichaMaterial.de_material(resultado.datos)


@router.put(
    "/{id_material}",
    status_code=200,
    response_model=MaterialActualizadoRespuesta,
    summary="Modificar un material (HU-03)",
    description=(
        "Actualiza Nombre, Categoría, Densidad y Pureza de un material ACTIVO. "
        "ID, SKU y Unidad de medida son de solo lectura. Si el Nombre cambia, "
        "se sincroniza con Inventario (PATCH /inventario/articulos/{sku}) antes de persistir."
    ),
    responses=respuestas_error(400, 404, 409, 500, 503),
)
async def actualizar(
    id_material: IdMaterial,
    solicitud: MaterialActualizarSolicitud,
    servicio: Servicio,
) -> MaterialActualizadoRespuesta:
    resultado = await servicio.actualizar(id_material, solicitud.a_comando())
    return MaterialActualizadoRespuesta.con_mensaje(resultado.datos, resultado.mensaje or "")


@router.delete(
    "/{id_material}",
    status_code=204,
    summary="Eliminar material",
    responses=respuestas_error(400, 404, 500),
)
async def eliminar(id_material: IdMaterial, servicio: Servicio) -> Response:
    await servicio.eliminar(id_material)
    return Response(status_code=204)
