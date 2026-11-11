"""Rutas del recurso /materiales (HU-01)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import obtener_material_service
from app.api.schemas.comun import respuestas_error
from app.api.schemas.materiales import MaterialCrearSolicitud, MaterialRespuesta
from app.business.services.material_service import MaterialService

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
