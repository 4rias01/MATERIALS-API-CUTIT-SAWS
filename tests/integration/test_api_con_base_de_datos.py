"""API completa contra PostgreSQL: /health y auditoría de los fallos."""

from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.business.services.base import ServicioBase, operacion_de_negocio
from app.core.contexto import establecer_contexto, restablecer_contexto
from app.core.events import BusEventos
from app.core.exceptions import ConflictoError
from app.data_access.models import Auditoria
from app.data_access.repositories import AuditoriaRepository
from app.data_access.unit_of_work import UnitOfWork
from app.main import crear_app
from tests.conftest import configuracion_de_prueba


@pytest.fixture
async def app_con_bd(motor: AsyncEngine, url_base_datos: str) -> AsyncIterator[FastAPI]:
    aplicacion = crear_app(configuracion_de_prueba(database_url=url_base_datos))
    async with aplicacion.router.lifespan_context(aplicacion):
        yield aplicacion


async def test_health_ok_con_la_base_de_datos_disponible(app_con_bd: FastAPI) -> None:
    transporte = httpx.ASGITransport(app=app_con_bd)
    async with httpx.AsyncClient(transport=transporte, base_url="http://pruebas") as cliente:
        r = await cliente.get("/health")
    assert r.status_code == 200
    assert r.json()["estado"] == "OK"
    assert r.json()["baseDatos"] == "OK"


class ServicioQueRechaza(ServicioBase):
    @operacion_de_negocio("INHABILITAR_MATERIAL", "material", mensaje_error_bd="error", parametro_id="id_material")
    async def inhabilitar(self, id_material: str) -> None:
        async with self._uow:
            raise ConflictoError(f"El material '{id_material}' ya se encuentra en estado INACTIVO")


async def test_un_rechazo_queda_en_la_tabla_de_auditoria(sesion: AsyncSession, otra_sesion: AsyncSession) -> None:
    servicio = ServicioQueRechaza(UnitOfWork(sesion), AuditoriaRepository(sesion), BusEventos())
    tokens = establecer_contexto("traza-integracion-01", "patent-sweep")
    try:
        with pytest.raises(ConflictoError):
            await servicio.inhabilitar("mat-007")
    finally:
        restablecer_contexto(tokens)
    registro = (await otra_sesion.scalars(select(Auditoria))).one()
    assert (registro.operacion, registro.recurso_id, registro.resultado_http) == ("INHABILITAR_MATERIAL", "mat-007", 409)
    assert (registro.trace_id, registro.origen) == ("traza-integracion-01", "patent-sweep")
    assert registro.detalle == {"mensaje": "El material 'mat-007' ya se encuentra en estado INACTIVO"}
