"""HU-05 contra PostgreSQL: persistencia, restricciones, rollback y concurrencia."""

import asyncio
from collections.abc import AsyncIterator
from decimal import Decimal
from unittest.mock import Mock

import httpx
import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.api.dependencies import obtener_repositorio_auditoria
from app.business.domain import mensajes
from app.core.exceptions import ErrorBaseDatos
from app.infraestructure.interfaces import IAuditoriaRepository
from app.infraestructure.models import Auditoria, Formula, FormulaComponente
from app.infraestructure.repositories import FormulaRepository, MaterialRepository
from app.infraestructure.unit_of_work import UnitOfWork
from app.main import crear_app
from tests.conftest import configuracion_de_prueba
from tests.fabricas import un_material
from tests.hu.test_hu05_registrar_formula import _cuerpo


@pytest.fixture
async def cliente_formula(motor: AsyncEngine, url_base_datos: str) -> AsyncIterator[httpx.AsyncClient]:
    async with AsyncSession(motor) as sesion, UnitOfWork(sesion) as uow:
        repo = MaterialRepository(sesion)
        await repo.agregar(un_material(1, nombre="Acero"))
        await repo.agregar(un_material(2, nombre="Tornillo", unidad_medida="und"))
        await uow.commit()
    app = crear_app(configuracion_de_prueba(database_url=url_base_datos))
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://pruebas") as cliente,
    ):
        yield cliente


async def test_registro_persiste_formula_componentes_y_auditoria(
    cliente_formula: httpx.AsyncClient, otra_sesion: AsyncSession
) -> None:
    r = await cliente_formula.post("/formulas", json=_cuerpo())
    assert r.status_code == 201, r.json()
    formula = (await otra_sesion.scalars(select(Formula))).one()
    assert (formula.id_formula, formula.estado, formula.version) == ("form-001", "BORRADOR", 1)
    assert formula.fecha_registro == formula.fecha_actualizacion
    componentes = (await otra_sesion.scalars(select(FormulaComponente).order_by(FormulaComponente.id_material))).all()
    assert [(c.id_material, c.cantidad) for c in componentes] == [("mat-001", Decimal("2.125")), ("mat-002", Decimal(3))]
    auditoria = (await otra_sesion.scalars(select(Auditoria))).one()
    assert (auditoria.operacion, auditoria.recurso_id, auditoria.resultado_http) == ("REGISTRAR_FORMULA", "form-001", 201)


async def test_error_despues_del_flush_revierte_formula_y_componentes(
    cliente_formula: httpx.AsyncClient, otra_sesion: AsyncSession
) -> None:
    # Falla después del INSERT de fórmula y componentes, antes del commit.
    app = cliente_formula._transport.app
    auditoria = Mock(spec=IAuditoriaRepository)
    auditoria.agregar.side_effect = ErrorBaseDatos("Fallo al guardar auditoría")
    app.dependency_overrides[obtener_repositorio_auditoria] = lambda: auditoria
    r = await cliente_formula.post("/formulas", json=_cuerpo())
    assert (r.status_code, r.json()["mensaje"]) == (500, mensajes.HU05_C8)
    assert await otra_sesion.scalar(select(func.count()).select_from(Formula)) == 0
    assert await otra_sesion.scalar(select(func.count()).select_from(FormulaComponente)) == 0
    assert await otra_sesion.scalar(select(func.count()).select_from(Auditoria)) == 0


async def test_nombre_simultaneo_solo_crea_una_formula(cliente_formula: httpx.AsyncClient, otra_sesion: AsyncSession) -> None:
    respuestas = await asyncio.gather(*[cliente_formula.post("/formulas", json=_cuerpo()) for _ in range(2)])
    assert sorted(r.status_code for r in respuestas) == [201, 409]
    assert await otra_sesion.scalar(select(func.count()).select_from(Formula)) == 1
    assert await otra_sesion.scalar(select(func.count()).select_from(FormulaComponente)) == 2


async def test_repositorio_compara_nombres_y_secuencia(cliente_formula: httpx.AsyncClient, sesion: AsyncSession) -> None:
    assert (await cliente_formula.post("/formulas", json=_cuerpo(nombre="Fórmula ácida"))).status_code == 201
    repo = FormulaRepository(sesion)
    async with UnitOfWork(sesion):
        assert await repo.existe_nombre("FÓRMULA ÁCIDA")
        assert not await repo.existe_nombre("Otra fórmula")
        assert await repo.siguiente_numero() == 2


async def test_timeout_real_revierte_y_responde_mensaje_hu05(
    cliente_formula: httpx.AsyncClient, otra_sesion: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = FormulaRepository.agregar

    async def agregar_lento(self: FormulaRepository, formula: Formula) -> None:
        await original(self, formula)
        # Mismo mecanismo de timeout que producción, acortado solo para esta prueba.
        await self._sesion.execute(text("SET LOCAL statement_timeout = '50ms'"))
        await self._sesion.execute(text("SELECT pg_sleep(0.2)"))

    monkeypatch.setattr(FormulaRepository, "agregar", agregar_lento)
    r = await cliente_formula.post("/formulas", json=_cuerpo())
    assert (r.status_code, r.json()["mensaje"]) == (500, mensajes.HU05_C8)
    assert await otra_sesion.scalar(select(func.count()).select_from(Formula)) == 0
    assert await otra_sesion.scalar(select(func.count()).select_from(FormulaComponente)) == 0
