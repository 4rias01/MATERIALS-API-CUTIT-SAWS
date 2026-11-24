"""Rutas del recurso /materiales (HU-01 y HU-02)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.api.dependencies import obtener_material_service
from app.api.schemas.comun import respuestas_error
from app.api.schemas.materiales import ConsultaMaterial, FichaMaterial, ListaMateriales, MaterialCrearSolicitud, MaterialRespuesta
from app.business.domain import mensajes
from app.business.services.material_service import TAMANO_PAGINA, MaterialService

router = APIRouter(prefix="/materiales", tags=["Materiales"])

Servicio = Annotated[MaterialService, Depends(obtener_material_service)]


@router.post(
    "",
    status_code=201,
    response_model=MaterialRespuesta,
    summary="Registrar un material (HU-01)",
    description="Registra el material como materia prima en Inventario, que asigna el SKU, y lo guarda en estado ACTIVO.",
    responses=respuestas_error(400, 409, 500, 503),
)
async def registrar_material(solicitud: MaterialCrearSolicitud, servicio: Servicio) -> MaterialRespuesta:
    resultado = await servicio.registrar(solicitud.a_comando())
    return MaterialRespuesta.desde_modelo(resultado.datos, resultado.mensaje or "")


@router.get("/{id}", summary="Consultar la ficha técnica de un material (HU-02)", responses=respuestas_error(404, 500))
async def consultar_material(
    id: Annotated[str, Path(description="ID del material, formato mat-NNN.", examples=["mat-101"])],
    servicio: Servicio,
) -> FichaMaterial:
    return FichaMaterial.de_material(await servicio.consultar(id))


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
