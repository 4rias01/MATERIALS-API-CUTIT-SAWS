"""Estado de la API para /health (patrón Health Endpoint)."""

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field

from app.core.exceptions import ErrorBaseDatos
from app.infraestructure.interfaces import IClienteExterno, IUnitOfWork

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class EstadoSalud:
    base_datos_disponible: bool
    circuitos: dict[str, str] = field(default_factory=dict)

    @property
    def saludable(self) -> bool:
        """La API está sana si alcanza su base de datos. Las APIs de otras células no
        cuentan: si fallan, la API sigue en pie y responde 503 solo en las operaciones
        que las usan."""
        return self.base_datos_disponible


class SaludService:
    def __init__(self, uow: IUnitOfWork, clientes: Mapping[str, IClienteExterno]) -> None:
        self._uow = uow
        self._clientes = clientes

    async def verificar(self) -> EstadoSalud:
        try:
            await self._uow.verificar_conexion()
            disponible = True
        except ErrorBaseDatos:
            logger.warning("La base de datos no responde", exc_info=True)
            disponible = False
        return EstadoSalud(
            base_datos_disponible=disponible,
            circuitos={nombre: cliente.estado_circuito() for nombre, cliente in self._clientes.items()},
        )
