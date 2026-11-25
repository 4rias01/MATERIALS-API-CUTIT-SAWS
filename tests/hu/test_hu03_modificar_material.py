"""HU-03: contrato HTTP de modificación de material (PUT /materiales/{id})."""

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.api import dependencies
from app.business.domain import mensajes
from tests.dobles import AuditoriaRepositoryFalso, InventarioClientFalso, MaterialRepositoryFalso, UnitOfWorkFalsa
from tests.fabricas import un_material

pytestmark = pytest.mark.hu

URL = "/materiales/{id_material}"
CUERPO_OK = {
    "nombre": "Acero actualizado",
    "categoria": "Materia Prima",
    "densidad": 8.5,
    "pureza": 99,
}


@pytest.fixture
def catalogo(app: FastAPI) -> MaterialRepositoryFalso:
    repo = MaterialRepositoryFalso(
        [
            un_material(1, nombre="Material 1"),  # ACTIVO
            un_material(2, nombre="Cobre"),  # ACTIVO, otro nombre
            un_material(3, nombre="Plomo", estado="INACTIVO"),  # INACTIVO
        ]
    )
    app.dependency_overrides[dependencies.obtener_repositorio_materiales] = lambda: repo
    return repo


@pytest.fixture
def inventario(app: FastAPI) -> InventarioClientFalso:
    fake = InventarioClientFalso()
    app.dependency_overrides[dependencies.obtener_cliente_inventario] = lambda: fake
    return fake


@pytest.fixture
def uow(app: FastAPI) -> UnitOfWorkFalsa:
    fake = UnitOfWorkFalsa()
    app.dependency_overrides[dependencies.obtener_unidad_de_trabajo] = lambda: fake
    app.dependency_overrides[dependencies.obtener_repositorio_auditoria] = AuditoriaRepositoryFalso
    return fake


# --- c1: campos editables vs solo lectura ----------------------------------------


async def test_c01_acepta_los_cuatro_campos_editables(cliente: AsyncClient, catalogo, inventario, uow) -> None:
    r = await cliente.put(URL.format(id_material="mat-001"), json=CUERPO_OK)
    assert r.status_code == 200


# --- c2: validaciones del schema -------------------------------------------------


@pytest.mark.parametrize(
    "campo, valor, mensaje",
    [
        ("ID", "mat-009", "El campo 'ID' es de solo lectura y no puede ser modificado"),
        ("ID", None, mensajes.HU03_C2_8),
        ("SKU", "MP-00009", "El campo 'SKU' es de solo lectura y no puede ser modificado"),
        ("Unidad de medida", "g", "El campo 'Unidad de medida' es de solo lectura y no puede ser modificado"),
        ("sku", None, mensajes.HU03_C2_1),
        ("unidadMedida", None, mensajes.HU03_C2_2),
    ],
)
async def test_c02_campos_solo_lectura(cliente: AsyncClient, catalogo, inventario, uow, campo: str, valor, mensaje: str) -> None:
    r = await cliente.put(URL.format(id_material="mat-001"), json={**CUERPO_OK, campo: valor})
    assert (r.status_code, r.json()["mensaje"]) == (400, mensaje)
    assert inventario.actualizaciones == []
    assert uow.confirmaciones == 0


async def test_c02_id_en_un_cuerpo_sin_otros_campos(cliente: AsyncClient, catalogo, inventario, uow) -> None:
    r = await cliente.put(URL.format(id_material="mat-001"), json={"ID": "mat-007"})
    assert (r.status_code, r.json()["mensaje"]) == (400, mensajes.HU03_C2_8)


@pytest.mark.parametrize(
    "campo, valor, mensaje",
    [
        ("nombre", ..., mensajes.HU03_C2_3),
        ("nombre", None, mensajes.HU03_C2_3),
        ("nombre", "   ", mensajes.HU03_C2_3),
        ("nombre", 123, mensajes.HU03_C2_4_B),
        ("nombre", "ab", mensajes.HU03_C2_4_A),  # c2.4 · longitud
        ("nombre", "Acero @#", mensajes.HU03_C2_4_B),  # c2.4 · caracteres
        ("nombre", "\tAcero", mensajes.HU03_C2_4_B),
        ("categoria", "Metales", mensajes.formatear(mensajes.HU03_C2_5, valor="Metales")),
        ("categoria", ..., mensajes.formatear(mensajes.HU03_C2_5, valor="")),
        ("categoria", None, mensajes.formatear(mensajes.HU03_C2_5, valor="")),
        ("densidad", ..., mensajes.HU03_C2_6),
        ("densidad", -1, mensajes.HU03_C2_6),  # c2.6
        ("densidad", None, mensajes.HU03_C2_6),  # c2.6
        ("densidad", "7.85000000000000000000000000001", mensajes.HU03_C2_6),
        ("densidad", "1e1000000", mensajes.HU03_C2_6),
        ("pureza", ..., mensajes.HU03_C2_7),
        ("pureza", 150, mensajes.HU03_C2_7),  # c2.7
        ("pureza", None, mensajes.HU03_C2_7),  # c2.7
    ],
)
async def test_c02_validaciones_del_schema(cliente: AsyncClient, catalogo, inventario, uow, campo: str, valor, mensaje: str) -> None:
    cuerpo = {**CUERPO_OK}
    if valor is ...:
        cuerpo.pop(campo, None)
    else:
        cuerpo[campo] = valor
    r = await cliente.put(URL.format(id_material="mat-001"), json=cuerpo)
    assert (r.status_code, r.json()["mensaje"]) == (400, mensaje)
    assert inventario.actualizaciones == []
    assert uow.confirmaciones == 0


@pytest.mark.parametrize("campo", ["id", "materialId", "modelId", "id_model", "id_material"])
async def test_c02_rechaza_variantes_de_ID_como_campos_desconocidos(cliente: AsyncClient, catalogo, inventario, uow, campo: str) -> None:
    r = await cliente.put(URL.format(id_material="mat-001"), json={**CUERPO_OK, campo: "mat-002"})
    assert (r.status_code, r.json()["mensaje"]) == (400, mensajes.SOLICITUD_INVALIDA)
    assert inventario.actualizaciones == []
    assert uow.confirmaciones == 0


# --- c3: nombre duplicado en el catálogo -----------------------------------------


async def test_c03_nombre_duplicado_responde_409(cliente: AsyncClient, catalogo, inventario, uow) -> None:
    r = await cliente.put(URL.format(id_material="mat-001"), json={**CUERPO_OK, "nombre": "Cobre"})
    assert r.status_code == 409
    assert r.json()["mensaje"] == mensajes.formatear(mensajes.HU03_C3, Nombre="Cobre")
    assert inventario.actualizaciones == []  # no se llega a Inventario


async def test_c03_duplicado_ignora_mayusculas(cliente: AsyncClient, catalogo, inventario, uow) -> None:
    r = await cliente.put(URL.format(id_material="mat-001"), json={**CUERPO_OK, "nombre": "  COBRE  "})
    assert r.status_code == 409


# --- c4: solo se llama a Inventario si el nombre cambió --------------------------


async def test_c04_nombre_no_cambia_no_llama_inventario(cliente: AsyncClient, catalogo, inventario, uow) -> None:
    r = await cliente.put(URL.format(id_material="mat-001"), json={**CUERPO_OK, "nombre": "  Material   1 "})
    assert r.status_code == 200
    assert inventario.actualizaciones == []


async def test_c04_cambio_solo_de_mayusculas_si_llama_inventario(cliente: AsyncClient, catalogo, inventario, uow) -> None:
    r = await cliente.put(URL.format(id_material="mat-001"), json={**CUERPO_OK, "nombre": "MATERIAL 1"})
    assert r.status_code == 200
    assert inventario.actualizaciones == [("MP-00001", "MATERIAL 1")]


# --- c5: Inventario rechaza por duplicado ----------------------------------------


async def test_c05_inventario_duplicado_responde_409(cliente: AsyncClient, catalogo, inventario, uow) -> None:
    inventario.nombre_duplicado = True
    r = await cliente.put(URL.format(id_material="mat-001"), json=CUERPO_OK)
    assert r.status_code == 409
    assert r.json()["mensaje"] == mensajes.formatear(mensajes.HU03_C5, Nombre="Acero actualizado")
    assert catalogo.materiales["mat-001"].nombre == "Material 1"


# --- c6: Inventario caído --------------------------------------------------------


async def test_c06_inventario_caido_responde_503(cliente: AsyncClient, catalogo, inventario, uow, caplog: pytest.LogCaptureFixture) -> None:
    inventario.caido = True
    r = await cliente.put(URL.format(id_material="mat-001"), json=CUERPO_OK)
    assert r.status_code == 503
    assert r.json()["mensaje"] == mensajes.HU03_C6
    assert catalogo.materiales["mat-001"].nombre == "Material 1"
    traza = r.json()["traceId"]
    assert traza and traza == r.headers["X-Trace-Id"]
    assert any(getattr(registro, "trace_id", None) == traza for registro in caplog.records)


# --- c7: happy path --------------------------------------------------------------


async def test_c07_actualiza_y_responde_200(cliente: AsyncClient, catalogo, inventario, uow) -> None:
    r = await cliente.put(URL.format(id_material="mat-001"), json=CUERPO_OK)
    assert r.status_code == 200
    data = r.json()
    assert data["materialId"] == "mat-001"
    assert data["sku"] == "MP-00001"  # readonly, no cambió
    assert data["nombre"] == "Acero actualizado"
    assert data["categoria"] == "Materia Prima"
    assert (data["densidad"], data["pureza"]) == (8.5, 99)
    assert data["unidadMedida"] == "kg"  # readonly, no cambió
    assert data["estado"] == "ACTIVO"
    assert data["mensaje"] == mensajes.formatear(mensajes.HU03_C7, Nombre="Acero actualizado")
    assert data["fechaRegistro"] == "2026-10-20T15:30:00Z"  # no cambia
    assert data["fechaUltimaActualizacion"] != "2026-10-20T15:30:00Z"  # sí cambia


# --- c8: id inexistente o mal formado --------------------------------------------


@pytest.mark.parametrize("id_material", ["mat-999", "abc", "form-001"])
async def test_c08_id_inexistente_responde_404(cliente: AsyncClient, catalogo, inventario, uow, id_material: str) -> None:
    r = await cliente.put(URL.format(id_material=id_material), json=CUERPO_OK)
    assert r.status_code == 404
    assert r.json()["mensaje"] == mensajes.formatear(mensajes.HU03_C8, id_material=id_material)


# --- c9: material INACTIVO -------------------------------------------------------


async def test_c09_material_inactivo_responde_409(cliente: AsyncClient, catalogo, inventario, uow) -> None:
    r = await cliente.put(URL.format(id_material="mat-003"), json=CUERPO_OK)
    assert r.status_code == 409
    assert r.json()["mensaje"] == mensajes.HU03_C9


# --- c10: fallo de BD ------------------------------------------------------------


async def test_c10_bd_falla_responde_500_y_loguea_el_sku(
    cliente: AsyncClient, catalogo, inventario, uow, caplog: pytest.LogCaptureFixture
) -> None:
    uow.fallar_en_commit = True
    r = await cliente.put(URL.format(id_material="mat-001"), json=CUERPO_OK)
    assert r.status_code == 500
    assert r.json()["mensaje"] == mensajes.HU03_C10
    traza = r.json()["traceId"]
    assert traza and traza == r.headers["X-Trace-Id"]
    assert any(getattr(registro, "trace_id", None) == traza for registro in caplog.records)
    assert uow.reversiones > 0
    assert "MP-00001" in caplog.text  # SKU en el log para reconciliar con Inventario
