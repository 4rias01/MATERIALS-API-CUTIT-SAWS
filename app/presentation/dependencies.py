"""Inyección de dependencias con Depends de FastAPI (raíz de composición).

Es el único lugar de la capa de presentación que conoce las implementaciones
concretas: arma cada servicio con sus repositorios, la unidad de trabajo y los
clientes HTTP, siempre detrás de sus interfaces. En las pruebas se reemplazan con
``app.dependency_overrides`` por dobles (patrón Test Double).

FastAPI reutiliza cada dependencia dentro de una misma petición, así que la unidad de
trabajo y los repositorios comparten la misma sesión de base de datos.
"""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services.evaluacion_patente_service import EvaluacionPatenteService
from app.business.services.formula_service import FormulaService
from app.business.services.material_service import MaterialService
from app.business.services.salud_service import SaludService
from app.core.config import Configuracion
from app.core.events import BusEventos
from app.data_access.interfaces import (
    IAuditoriaRepository,
    IFormulaRepository,
    IInventarioClient,
    IMaterialRepository,
    IPatentSweepClient,
    IUnitOfWork,
)
from app.data_access.repositories import AuditoriaRepository, FormulaRepository, MaterialRepository
from app.data_access.unit_of_work import UnitOfWork

# --- Recursos compartidos creados en el arranque (app/main.py) ---------------------------


def obtener_configuracion_app(request: Request) -> Configuracion:
    return request.app.state.config


def obtener_bus_eventos(request: Request) -> BusEventos:
    return request.app.state.bus_eventos


def obtener_cliente_inventario(request: Request) -> IInventarioClient:
    return request.app.state.cliente_inventario


def obtener_cliente_patent_sweep(request: Request) -> IPatentSweepClient:
    return request.app.state.cliente_patent_sweep


# --- Por petición -----------------------------------------------------------------------


async def obtener_sesion(request: Request) -> AsyncIterator[AsyncSession]:
    """Sesión de base de datos tomada del pool; se devuelve al terminar la petición."""
    async with request.app.state.fabrica_sesiones() as sesion:
        yield sesion


Sesion = Annotated[AsyncSession, Depends(obtener_sesion)]


def obtener_unidad_de_trabajo(sesion: Sesion) -> IUnitOfWork:
    return UnitOfWork(sesion)


def obtener_repositorio_materiales(sesion: Sesion) -> IMaterialRepository:
    return MaterialRepository(sesion)


def obtener_repositorio_formulas(sesion: Sesion) -> IFormulaRepository:
    return FormulaRepository(sesion)


def obtener_repositorio_auditoria(sesion: Sesion) -> IAuditoriaRepository:
    return AuditoriaRepository(sesion)


UnidadDeTrabajo = Annotated[IUnitOfWork, Depends(obtener_unidad_de_trabajo)]
RepositorioMateriales = Annotated[IMaterialRepository, Depends(obtener_repositorio_materiales)]
RepositorioFormulas = Annotated[IFormulaRepository, Depends(obtener_repositorio_formulas)]
RepositorioAuditoria = Annotated[IAuditoriaRepository, Depends(obtener_repositorio_auditoria)]
Eventos = Annotated[BusEventos, Depends(obtener_bus_eventos)]
ClienteInventario = Annotated[IInventarioClient, Depends(obtener_cliente_inventario)]
ClientePatentSweep = Annotated[IPatentSweepClient, Depends(obtener_cliente_patent_sweep)]
ConfiguracionApp = Annotated[Configuracion, Depends(obtener_configuracion_app)]


# --- Servicios ---------------------------------------------------------------------------


def obtener_material_service(
    uow: UnidadDeTrabajo,
    auditoria: RepositorioAuditoria,
    eventos: Eventos,
    materiales: RepositorioMateriales,
    inventario: ClienteInventario,
) -> MaterialService:
    return MaterialService(uow, auditoria, eventos, materiales, inventario)


def obtener_formula_service(
    uow: UnidadDeTrabajo,
    auditoria: RepositorioAuditoria,
    eventos: Eventos,
    formulas: RepositorioFormulas,
    materiales: RepositorioMateriales,
    config: ConfiguracionApp,
) -> FormulaService:
    return FormulaService(uow, auditoria, eventos, formulas, materiales, config.formulas_tamano_pagina)


def obtener_evaluacion_patente_service(
    uow: UnidadDeTrabajo,
    auditoria: RepositorioAuditoria,
    eventos: Eventos,
    formulas: RepositorioFormulas,
    patent_sweep: ClientePatentSweep,
) -> EvaluacionPatenteService:
    return EvaluacionPatenteService(uow, auditoria, eventos, formulas, patent_sweep)


def obtener_salud_service(
    uow: UnidadDeTrabajo,
    inventario: ClienteInventario,
    patent_sweep: ClientePatentSweep,
) -> SaludService:
    return SaludService(uow, inventario, patent_sweep)
