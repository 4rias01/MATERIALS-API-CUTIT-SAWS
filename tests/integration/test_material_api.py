"""Pruebas de integración del CRUD de materiales (equivalente a ProfesorIntegrationTest).

Levantan la API completa contra PostgreSQL real (``TEST_DATABASE_URL``) y hacen
peticiones HTTP: prueban el stack entero (DTO, servicio, repositorio, SQL y códigos HTTP).
Antes de cada prueba el fixture ``motor`` vacía las tablas.
"""

from collections.abc import AsyncIterator
from decimal import Decimal

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.infraestructure.models import Material
from app.infraestructure.repositories import MaterialRepository
from app.infraestructure.unit_of_work import UnitOfWork
from app.main import crear_app
from tests.conftest import configuracion_de_prueba

URL = "/materiales"


@pytest.fixture
async def cliente(motor: AsyncEngine, url_base_datos: str) -> AsyncIterator[httpx.AsyncClient]:
    """Cliente HTTP contra la API conectada a la base de pruebas."""
    app: FastAPI = crear_app(configuracion_de_prueba(database_url=url_base_datos))
    async with app.router.lifespan_context(app):
        transporte = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transporte, base_url="http://pruebas") as c:
            yield c


def cuerpo(nombre: str = "Acero al carbono") -> dict[str, object]:
    return {"nombre": nombre, "categoria": "Materia Prima", "unidadMedida": "kg", "densidad": 7.85, "pureza": 98}


async def guardar(sesion: AsyncSession, nombre: str = "Acero al carbono") -> Material:
    """Prepara datos directamente en la base, sin pasar por la API (como profesorRepository.save)."""
    material = Material(nombre=nombre, categoria="Materia Prima", unidad_medida="kg", densidad=Decimal("7.85"), pureza=Decimal("98"))
    async with UnitOfWork(sesion) as uow:
        await MaterialRepository(sesion).agregar(material)
        await uow.commit()
    return material


# ── Crear ──────────────────────────────────────────────────────────────────────


async def test_post_crea_material_y_responde_201(cliente: httpx.AsyncClient) -> None:
    r = await cliente.post(URL, json=cuerpo("  Acero   al carbono "))

    assert r.status_code == 201
    datos = r.json()
    assert datos["id"] > 0
    assert (datos["nombre"], datos["densidad"], datos["pureza"]) == ("Acero al carbono", 7.85, 98)


async def test_post_con_nombre_duplicado_responde_409(cliente: httpx.AsyncClient, sesion: AsyncSession) -> None:
    await guardar(sesion, "Acero al carbono")

    # Mismo nombre con otras mayúsculas: también es duplicado
    r = await cliente.post(URL, json=cuerpo("ACERO AL CARBONO"))

    assert r.status_code == 409
    assert r.json()["mensaje"] == "Ya existe un material con el nombre: ACERO AL CARBONO"


@pytest.mark.parametrize(
    ("cambios", "campo"),
    [({"nombre": "Ac"}, "nombre"), ({"densidad": 0}, "densidad"), ({"pureza": 101}, "pureza"), ({"categoria": "Otra"}, "categoria")],
)
async def test_post_con_datos_invalidos_responde_400(cliente: httpx.AsyncClient, cambios: dict[str, object], campo: str) -> None:
    r = await cliente.post(URL, json={**cuerpo(), **cambios})

    assert r.status_code == 400
    assert r.json()["mensaje"] == f"El campo '{campo}' es obligatorio o no tiene un formato válido."


async def test_post_no_acepta_el_id_en_el_cuerpo(cliente: httpx.AsyncClient) -> None:
    r = await cliente.post(URL, json={**cuerpo(), "id": 50})
    assert r.status_code == 400


# ── Obtener todos ──────────────────────────────────────────────────────────────


async def test_get_lista_los_materiales(cliente: httpx.AsyncClient, sesion: AsyncSession) -> None:
    await guardar(sesion, "Acero")
    await guardar(sesion, "Cobre")

    r = await cliente.get(URL)

    assert r.status_code == 200
    assert [m["nombre"] for m in r.json()] == ["Acero", "Cobre"]


# ── Obtener por id ─────────────────────────────────────────────────────────────


async def test_get_por_id_existente_responde_200(cliente: httpx.AsyncClient, sesion: AsyncSession) -> None:
    guardado = await guardar(sesion)

    r = await cliente.get(f"{URL}/{guardado.id_material}")

    assert r.status_code == 200
    assert r.json()["id"] == guardado.id_material


async def test_get_por_id_inexistente_responde_404(cliente: httpx.AsyncClient) -> None:
    r = await cliente.get(f"{URL}/999")

    assert r.status_code == 404
    assert r.json()["mensaje"] == "Material con id 999 no encontrado"


async def test_get_con_id_no_valido_responde_400(cliente: httpx.AsyncClient) -> None:
    for id_invalido in ("abc", "0", str(2**63)):
        assert (await cliente.get(f"{URL}/{id_invalido}")).status_code == 400


# ── Actualizar ─────────────────────────────────────────────────────────────────


async def test_put_actualiza_material_y_responde_200(cliente: httpx.AsyncClient, sesion: AsyncSession) -> None:
    guardado = await guardar(sesion)

    r = await cliente.put(f"{URL}/{guardado.id_material}", json=cuerpo("Acero actualizado"))

    assert r.status_code == 200
    assert r.json()["nombre"] == "Acero actualizado"
    assert r.json()["fechaActualizacion"] >= r.json()["fechaRegistro"]


async def test_put_material_inexistente_responde_404(cliente: httpx.AsyncClient) -> None:
    r = await cliente.put(f"{URL}/999", json=cuerpo())
    assert r.status_code == 404


async def test_put_con_el_nombre_de_otro_material_responde_409(cliente: httpx.AsyncClient, sesion: AsyncSession) -> None:
    await guardar(sesion, "Acero")
    cobre = await guardar(sesion, "Cobre")

    r = await cliente.put(f"{URL}/{cobre.id_material}", json=cuerpo("acero"))
    assert r.status_code == 409


# ── Eliminar ───────────────────────────────────────────────────────────────────


async def test_delete_elimina_material_y_responde_204(cliente: httpx.AsyncClient, sesion: AsyncSession) -> None:
    guardado = await guardar(sesion)

    r = await cliente.delete(f"{URL}/{guardado.id_material}")

    assert r.status_code == 204
    assert (await cliente.get(f"{URL}/{guardado.id_material}")).status_code == 404


async def test_delete_material_inexistente_responde_404(cliente: httpx.AsyncClient) -> None:
    r = await cliente.delete(f"{URL}/999")
    assert r.status_code == 404


# ── Buscar por nombre ──────────────────────────────────────────────────────────


async def test_buscar_por_nombre_devuelve_coincidencias_sin_distinguir_mayusculas(cliente: httpx.AsyncClient, sesion: AsyncSession) -> None:
    await guardar(sesion, "Acero al carbono")
    await guardar(sesion, "Acero inoxidable")
    await guardar(sesion, "Cobre")

    r = await cliente.get(f"{URL}/buscar", params={"nombre": "ACERO"})

    assert r.status_code == 200
    assert [m["nombre"] for m in r.json()] == ["Acero al carbono", "Acero inoxidable"]


async def test_buscar_trata_los_comodines_como_texto(cliente: httpx.AsyncClient, sesion: AsyncSession) -> None:
    await guardar(sesion, "Acero")

    # "%" no debe actuar como comodín de LIKE: no hay ningún nombre que lo contenga
    r = await cliente.get(f"{URL}/buscar", params={"nombre": "%"})

    assert (r.status_code, r.json()) == (200, [])
