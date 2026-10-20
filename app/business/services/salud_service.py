"""Estado de la API para /health (patrón Health Endpoint)."""

import logging
from dataclasses import dataclass, field

from app.core.exceptions import ErrorBaseDatos
from app.data_access.interfaces import IInventarioClient, IPatentSweepClient, IUnitOfWork

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class EstadoSalud:
    base_datos_disponible: bool
    circuitos: dict[str, str] = field(default_factory=dict)

    @property
    def saludable(self) -> bool:
        """La API está sana si alcanza su base de datos. Las APIs de otras células no
        cuentan: si fallan, la API sigue en pie y responde 503 solo en esas operaciones."""
        return self.base_datos_disponible


class SaludService:
    def __init__(self, uow: IUnitOfWork, inventario: IInventarioClient, patent_sweep: IPatentSweepClient) -> None:
        self._uow = uow
        self._inventario = inventario
        self._patent_sweep = patent_sweep

    async def verificar(self) -> EstadoSalud:
        try:
            await self._uow.verificar_conexion()
            disponible = True
        except ErrorBaseDatos:
            logger.warning("La base de datos no responde", exc_info=True)
            disponible = False
        return EstadoSalud(
            base_datos_disponible=disponible,
            circuitos={
                "inventario": self._inventario.estado_circuito(),
                "patentSweep": self._patent_sweep.estado_circuito(),
            },
        )
