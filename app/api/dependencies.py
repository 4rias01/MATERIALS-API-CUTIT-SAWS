"""Inyección de dependencias con Depends de FastAPI (raíz de composición).

Es el único lugar de la capa de presentación que conoce las implementaciones
concretas: arma cada servicio con sus repositorios, la unidad de trabajo y los
clientes HTTP, siempre detrás de sus interfaces. En las pruebas se reemplazan con
``app.dependency_overrides`` por dobles (patrón Test Double).

FastAPI reutiliza cada dependencia dentro de una misma petición, así que la unidad de
trabajo y los repositorios comparten la misma sesión de base de datos.

Para un servicio nuevo: agregar el proveedor de su repositorio (``obtener_repositorio_x``),
el de su cliente externo si lo usa, y ``obtener_x_service`` que los combine.
"""

from collections.abc import AsyncIterator, Mapping
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services.salud_service import SaludService
from app.core.config import Configuracion
from app.core.events import BusEventos
from app.infraestructure.interfaces import IAuditoriaRepository, IClienteExterno, IUnitOfWork
from app.infraestructure.repositories import AuditoriaRepository
from app.infraestructure.unit_of_work import UnitOfWork

# --- Recursos compartidos creados en el arranque (app/main.py) ---------------------------


def obtener_configuracion_app(request: Request) -> Configuracion:
    return request.app.state.config


def obtener_bus_eventos(request: Request) -> BusEventos:
    return request.app.state.bus_eventos


def obtener_clientes_externos(request: Request) -> Mapping[str, IClienteExterno]:
    """Clientes de las APIs de otras células, por nombre de servicio."""
    return request.app.state.clientes_externos


# --- Por petición -----------------------------------------------------------------------


async def obtener_sesion(request: Request) -> AsyncIterator[AsyncSession]:
    """Sesión de base de datos tomada del pool; se devuelve al terminar la petición."""
    async with request.app.state.fabrica_sesiones() as sesion:
        yield sesion


Sesion = Annotated[AsyncSession, Depends(obtener_sesion)]


def obtener_unidad_de_trabajo(sesion: Sesion) -> IUnitOfWork:
    return UnitOfWork(sesion)


def obtener_repositorio_auditoria(sesion: Sesion) -> IAuditoriaRepository:
    return AuditoriaRepository(sesion)


UnidadDeTrabajo = Annotated[IUnitOfWork, Depends(obtener_unidad_de_trabajo)]
RepositorioAuditoria = Annotated[IAuditoriaRepository, Depends(obtener_repositorio_auditoria)]
Eventos = Annotated[BusEventos, Depends(obtener_bus_eventos)]
ClientesExternos = Annotated[Mapping[str, IClienteExterno], Depends(obtener_clientes_externos)]


# --- Servicios ---------------------------------------------------------------------------


def obtener_salud_service(uow: UnidadDeTrabajo, clientes: ClientesExternos) -> SaludService:
    return SaludService(uow, clientes)
