"""GET /health: estado de la API para Docker, Prometheus y el equipo (patrón Health Endpoint)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.business.services.salud_service import SaludService
from app.core.config import Configuracion
from app.presentation.dependencies import obtener_configuracion_app, obtener_salud_service
from app.presentation.schemas.salud import SaludRespuesta

router = APIRouter(tags=["Monitoreo"])


@router.get(
    "/health",
    response_model=SaludRespuesta,
    summary="Estado de la API",
    description="200 si la API alcanza su base de datos; 503 si no. Incluye el estado de los circuit breakers.",
    responses={503: {"model": SaludRespuesta, "description": "La base de datos no responde."}},
)
async def salud(
    response: Response,
    servicio: Annotated[SaludService, Depends(obtener_salud_service)],
    config: Annotated[Configuracion, Depends(obtener_configuracion_app)],
) -> SaludRespuesta:
    estado = await servicio.verificar()
    response.status_code = 200 if estado.saludable else 503
    return SaludRespuesta(
        estado="OK" if estado.saludable else "DEGRADADO",
        version=config.app_version,
        base_datos="OK" if estado.base_datos_disponible else "ERROR",
        circuitos=estado.circuitos,
    )
