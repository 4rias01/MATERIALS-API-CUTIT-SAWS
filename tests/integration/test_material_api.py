"""Pruebas de integración de /materiales (equivalente a ProfesorIntegrationTest).

Levantan la API completa contra PostgreSQL real (``TEST_DATABASE_URL``) y hacen
peticiones HTTP: prueban el stack entero (DTO, servicio, repositorio, SQL y códigos HTTP).
Inventario se reemplaza por un doble. Antes de cada prueba el fixture ``motor`` vacía
las tablas y reinicia la secuencia del ID.
"""

from collections.abc import AsyncIterator
from datetime import datetime

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.api.dependencies import obtener_cliente_inventario
from app.infraestructure.models import Auditoria, Material
from app.infraestructure.repositories import MaterialRepository
from app.infraestructure.unit_of_work import UnitOfWork
from app.main import crear_app
from tests.conftest import configuracion_de_prueba
from tests.dobles import InventarioClientFalso
from tests.fabricas import un_material

URL = "/materiales"


class InventarioSecuencial(InventarioClientFalso):
    """Asigna un SKU distinto en cada alta (MP-00001, MP-00002, …)."""

    async def registrar_materia_prima(self, nombre: str, unidad_medida: str) -> str:
        self.sku = f"MP-{len(self.altas) + 1:05d}"
        return await super().registrar_materia_prima(nombre, unidad_medida)


@pytest.fixture
def inventario() -> InventarioSecuencial:
    return InventarioSecuencial()


@pytest.fixture
async def cliente(motor: AsyncEngine, url_base_datos: str, inventario: InventarioSecuencial) -> AsyncIterator[httpx.AsyncClient]:
    """Cliente HTTP contra la API conectada a la base de pruebas."""
    app: FastAPI = crear_app(configuracion_de_prueba(database_url=url_base_datos))
    app.dependency_overrides[obtener_cliente_inventario] = lambda: inventario
    async with app.router.lifespan_context(app):
        transporte = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transporte, base_url="http://pruebas") as c:
            yield c


def cuerpo(nombre: str = "Acero al carbono") -> dict[str, object]:
    return {"nombre": nombre, "categoria": "Materia Prima", "unidadMedida": "kg", "densidad": 7.85, "pureza": 98}


async def guardar(sesion: AsyncSession, numero: int, nombre: str) -> Material:
    """Prepara datos directamente en la base, sin pasar por la API (como profesorRepository.save)."""
    material = un_material(numero, nombre=nombre)
    async with UnitOfWork(sesion) as uow:
        await MaterialRepository(sesion).agregar(material)
        await uow.commit()
    return material


# ── Registrar (HU-01) ──────────────────────────────────────────────────────────


async def test_post_registra_material_y_responde_201(
    cliente: httpx.AsyncClient, otra_sesion: AsyncSession, inventario: InventarioSecuencial
) -> None:
    r = await cliente.post(URL, json=cuerpo("  Ácido   cítrico "))

    assert r.status_code == 201
    datos = r.json()
    assert (datos["materialId"], datos["sku"], datos["nombre"], datos["estado"]) == ("mat-001", "MP-00001", "Ácido cítrico", "ACTIVO")
    assert (datos["densidad"], datos["pureza"]) == (7.85, 98)
    assert datos["mensaje"] == "Material 'Ácido cítrico' registrado exitosamente con el SKU MP-00001."
    assert inventario.altas == [("Ácido cítrico", "kg")]
    material = (await otra_sesion.scalars(select(Material))).one()
    assert (material.id_material, material.sku, material.estado) == ("mat-001", "MP-00001", "ACTIVO")
    assert material.fecha_registro == material.fecha_actualizacion


async def test_post_asigna_ids_secuenciales(cliente: httpx.AsyncClient) -> None:
    ids = [(await cliente.post(URL, json=cuerpo(nombre))).json()["materialId"] for nombre in ("Acero", "Cobre", "Zinc")]
    assert ids == ["mat-001", "mat-002", "mat-003"]


async def test_post_con_nombre_ya_registrado_responde_409_y_queda_en_la_auditoria(
    cliente: httpx.AsyncClient, otra_sesion: AsyncSession, inventario: InventarioSecuencial
) -> None:
    creado = await cliente.post(URL, json=cuerpo("Ácido cítrico"))
    # Mismo nombre con otras mayúsculas: también es duplicado
    repetido = await cliente.post(URL, json=cuerpo("ÁCIDO CÍTRICO"))

    assert (creado.status_code, repetido.status_code) == (201, 409)
    assert repetido.json()["mensaje"] == "El material con el nombre 'ÁCIDO CÍTRICO' ya se encuentra registrado en el catálogo."
    assert len(inventario.altas) == 1  # el repetido no llega a Inventario
    auditoria = (await otra_sesion.scalars(select(Auditoria).order_by(Auditoria.id_auditoria))).all()
    assert [(a.operacion, a.recurso_id, a.resultado_http) for a in auditoria] == [
        ("REGISTRAR_MATERIAL", "mat-001", 201),
        ("REGISTRAR_MATERIAL", None, 409),
    ]


async def test_post_con_datos_invalidos_responde_400_sin_guardar(cliente: httpx.AsyncClient, otra_sesion: AsyncSession) -> None:
    r = await cliente.post(URL, json={**cuerpo(), "densidad": 0})

    assert (r.status_code, r.json()["mensaje"]) == (400, "El campo 'Densidad' debe ser un número positivo de máximo 4 caracteres.")
    assert (await otra_sesion.scalars(select(Material))).all() == []


async def test_post_no_acepta_campos_de_solo_lectura(cliente: httpx.AsyncClient) -> None:
    for campo, valor in (("id", 50), ("sku", "MP-00001"), ("estado", "INACTIVO")):
        assert (await cliente.post(URL, json={**cuerpo(), campo: valor})).status_code == 400


# ── Obtener todos ──────────────────────────────────────────────────────────────


async def test_get_lista_los_materiales(cliente: httpx.AsyncClient, sesion: AsyncSession) -> None:
    await guardar(sesion, 1, "Acero")
    await guardar(sesion, 2, "Cobre")

    r = await cliente.get(URL)

    assert r.status_code == 200
    assert [(m["materialId"], m["nombre"]) for m in r.json()] == [("mat-001", "Acero"), ("mat-002", "Cobre")]


# ── Obtener por id ─────────────────────────────────────────────────────────────


async def test_get_por_id_existente_responde_200(cliente: httpx.AsyncClient, sesion: AsyncSession) -> None:
    guardado = await guardar(sesion, 1, "Acero")

    r = await cliente.get(f"{URL}/{guardado.id_material}")

    assert r.status_code == 200
    assert (r.json()["materialId"], r.json()["sku"]) == ("mat-001", "MP-00001")


async def test_get_por_id_inexistente_responde_404(cliente: httpx.AsyncClient) -> None:
    r = await cliente.get(f"{URL}/mat-999")

    assert r.status_code == 404
    assert r.json()["mensaje"] == "Material con id mat-999 no encontrado"


async def test_get_con_id_no_valido_responde_400(cliente: httpx.AsyncClient) -> None:
    for id_invalido in ("abc", "1", "mat-1"):
        assert (await cliente.get(f"{URL}/{id_invalido}")).status_code == 400


# ── Actualizar ─────────────────────────────────────────────────────────────────


async def test_put_actualiza_material_y_responde_200(cliente: httpx.AsyncClient, sesion: AsyncSession) -> None:
    guardado = await guardar(sesion, 1, "Acero")

    r = await cliente.put(f"{URL}/{guardado.id_material}", json=cuerpo("Acero actualizado"))

    assert r.status_code == 200
    datos = r.json()
    assert (datos["nombre"], datos["sku"], datos["estado"]) == ("Acero actualizado", "MP-00001", "ACTIVO")
    assert datetime.fromisoformat(datos["fechaUltimaActualizacion"]) > datetime.fromisoformat(datos["fechaRegistro"])


async def test_put_material_inexistente_responde_404(cliente: httpx.AsyncClient) -> None:
    r = await cliente.put(f"{URL}/mat-999", json=cuerpo())
    assert r.status_code == 404


async def test_put_con_el_nombre_de_otro_material_responde_409(cliente: httpx.AsyncClient, sesion: AsyncSession) -> None:
    await guardar(sesion, 1, "Acero")
    cobre = await guardar(sesion, 2, "Cobre")

    r = await cliente.put(f"{URL}/{cobre.id_material}", json=cuerpo("acero"))
    assert r.status_code == 409


# ── Eliminar ───────────────────────────────────────────────────────────────────


async def test_delete_elimina_material_y_responde_204(cliente: httpx.AsyncClient, sesion: AsyncSession) -> None:
    guardado = await guardar(sesion, 1, "Acero")

    r = await cliente.delete(f"{URL}/{guardado.id_material}")

    assert r.status_code == 204
    assert (await cliente.get(f"{URL}/{guardado.id_material}")).status_code == 404


async def test_delete_material_inexistente_responde_404(cliente: httpx.AsyncClient) -> None:
    r = await cliente.delete(f"{URL}/mat-999")
    assert r.status_code == 404


# ── Buscar por nombre ──────────────────────────────────────────────────────────


async def test_buscar_por_nombre_devuelve_coincidencias_sin_distinguir_mayusculas(cliente: httpx.AsyncClient, sesion: AsyncSession) -> None:
    await guardar(sesion, 1, "Acero al carbono")
    await guardar(sesion, 2, "Acero inoxidable")
    await guardar(sesion, 3, "Cobre")

    r = await cliente.get(f"{URL}/buscar", params={"nombre": "ACERO"})

    assert r.status_code == 200
    assert [m["nombre"] for m in r.json()] == ["Acero al carbono", "Acero inoxidable"]


async def test_buscar_trata_los_comodines_como_texto(cliente: httpx.AsyncClient, sesion: AsyncSession) -> None:
    await guardar(sesion, 1, "Acero")

    # "%" no debe actuar como comodín de LIKE: no hay ningún nombre que lo contenga
    r = await cliente.get(f"{URL}/buscar", params={"nombre": "%"})

    assert (r.status_code, r.json()) == (200, [])
