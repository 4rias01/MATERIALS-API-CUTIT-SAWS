"""Cliente de la API de Patent Sweep (célula 2).

El backlog define el cuerpo de la solicitud (HU-09 c2) y que Patent Sweep la acepta
con 202 (HU-09 c3). La ruta de su API es POR ACORDAR: se configura con la variable
``PATENT_SWEEP_RUTA_EVALUACION``.
"""

import httpx

from app.core.config import Configuracion
from app.core.exceptions import ErrorServicioExterno
from app.data_access.clients.base import ClienteHttpBase
from app.data_access.clients.circuit_breaker import CircuitBreaker
from app.data_access.interfaces.patent_sweep_client import IPatentSweepClient, SolicitudEvaluacionPatente

SERVICIO = "patent_sweep"

# --- POR ACORDAR con la célula de Patent Sweep -----------------------------------------
ESTADOS_ACEPTADA = (202,)  # HU-09 c3
# ----------------------------------------------------------------------------------------


class PatentSweepClient(ClienteHttpBase, IPatentSweepClient):
    def __init__(self, http: httpx.AsyncClient, config: Configuracion, circuito: CircuitBreaker) -> None:
        super().__init__(
            servicio=SERVICIO,
            http=http,
            url_base=config.patent_sweep_url,
            timeout_s=config.http_timeout_s,
            circuito=circuito,
            nombre_origen=config.nombre_servicio,
        )
        self._ruta_evaluacion = config.patent_sweep_ruta_evaluacion

    async def solicitar_evaluacion(self, solicitud: SolicitudEvaluacionPatente) -> None:
        if not self._ruta_evaluacion:
            self._contar("sin_configurar")
            raise ErrorServicioExterno(
                SERVICIO, ErrorServicioExterno.SIN_CONFIGURAR, detalle="PATENT_SWEEP_RUTA_EVALUACION no configurada"
            )
        respuesta = await self._enviar("POST", self._ruta_evaluacion, json=solicitud.a_json())
        if respuesta.status_code not in ESTADOS_ACEPTADA:
            raise self._respuesta_inesperada(respuesta)
