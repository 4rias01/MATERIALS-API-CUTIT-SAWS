"""API completa contra PostgreSQL: /health, registro de material (HU-01) y auditoría."""

from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.api.dependencies import obtener_cliente_inventario
from app.business.services.base import ServicioBase, operacion_de_negocio
from app.core.contexto import establecer_contexto, restablecer_contexto
from app.core.events import BusEventos
from app.core.exceptions import ConflictoError
from app.infraestructure.models import Auditoria, Material
from app.infraestructure.repositories import AuditoriaRepository
from app.infraestructure.unit_of_work import UnitOfWork
from app.main import crear_app
from tests.conftest import configuracion_de_prueba
from tests.dobles import InventarioClientFalso


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


async def test_registrar_material_persiste_el_material_y_la_auditoria(app_con_bd: FastAPI, otra_sesion: AsyncSession) -> None:
    inventario = InventarioClientFalso(sku="MP-00005")
    app_con_bd.dependency_overrides[obtener_cliente_inventario] = lambda: inventario
    cuerpo = {"nombre": "  Ácido   cítrico ", "categoria": "Componentes", "unidadMedida": "g", "densidad": 1.66, "pureza": 99}
    transporte = httpx.ASGITransport(app=app_con_bd)
    async with httpx.AsyncClient(transport=transporte, base_url="http://pruebas") as cliente:
        creado = await cliente.post("/materiales", json=cuerpo)
        repetido = await cliente.post("/materiales", json={**cuerpo, "nombre": "ÁCIDO CÍTRICO"})

    assert (creado.status_code, creado.json()["materialId"], creado.json()["sku"]) == (201, "mat-001", "MP-00005")
    assert repetido.status_code == 409
    material = (await otra_sesion.scalars(select(Material))).one()
    assert (material.nombre, material.estado, material.fecha_registro == material.fecha_actualizacion) == ("Ácido cítrico", "ACTIVO", True)
    auditoria = (await otra_sesion.scalars(select(Auditoria).order_by(Auditoria.id_auditoria))).all()
    assert [(a.operacion, a.recurso_id, a.resultado_http) for a in auditoria] == [
        ("REGISTRAR_MATERIAL", "mat-001", 201),
        ("REGISTRAR_MATERIAL", None, 409),
    ]
    assert inventario.altas == [("Ácido cítrico", "g")]


class ServicioQueRechaza(ServicioBase):
    @operacion_de_negocio("OPERACION_DE_PRUEBA", "material", mensaje_error_bd="error", parametro_id="id_material")
    async def operar(self, id_material: str) -> None:
        async with self._uow:
            raise ConflictoError(f"El material '{id_material}' no admite la operación")


async def test_un_rechazo_queda_en_la_tabla_de_auditoria(sesion: AsyncSession, otra_sesion: AsyncSession) -> None:
    servicio = ServicioQueRechaza(UnitOfWork(sesion), AuditoriaRepository(sesion), BusEventos())
    tokens = establecer_contexto("traza-integracion-01", "inventario")
    try:
        with pytest.raises(ConflictoError):
            await servicio.operar("mat-007")
    finally:
        restablecer_contexto(tokens)
    registro = (await otra_sesion.scalars(select(Auditoria))).one()
    assert (registro.operacion, registro.recurso_id, registro.resultado_http) == ("OPERACION_DE_PRUEBA", "mat-007", 409)
    assert (registro.trace_id, registro.origen) == ("traza-integracion-01", "inventario")
    assert registro.detalle == {"mensaje": "El material 'mat-007' no admite la operación"}
