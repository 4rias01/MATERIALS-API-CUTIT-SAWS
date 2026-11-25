"""HU-02: contrato HTTP de consulta individual y paginada."""

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.api.dependencies import obtener_repositorio_materiales
from tests.dobles import MaterialRepositoryFalso
from tests.fabricas import un_material

pytestmark = pytest.mark.hu


@pytest.fixture
def catalogo(app: FastAPI) -> MaterialRepositoryFalso:
    repo = MaterialRepositoryFalso([un_material(i) for i in range(11, 0, -1)])
    repo.sembrar(un_material(12, nombre="Aceite mineral", categoria="Lubricantes", unidad_medida="L", estado="INACTIVO"))
    app.dependency_overrides[obtener_repositorio_materiales] = lambda: repo
    return repo


def test_c01_id_obligatorio(app: FastAPI) -> None:
    (parametro,) = app.openapi()["paths"]["/materiales/{id_material}"]["get"]["parameters"]
    assert parametro["required"] and parametro["schema"]["type"] == "string"
    assert "mat-NNN" in parametro["description"]


@pytest.mark.parametrize(("numero", "estado"), [(1, "ACTIVO"), (12, "INACTIVO")])
async def test_c02_ficha(cliente: AsyncClient, catalogo: MaterialRepositoryFalso, numero: int, estado: str) -> None:
    material = catalogo.materiales[f"mat-{numero:03d}"]
    r = await cliente.get(f"/materiales/{material.id_material}")
    assert r.status_code == 200
    assert r.json() == {
        "materialId": material.id_material,
        "sku": material.sku,
        "nombre": material.nombre,
        "categoria": material.categoria,
        "unidadMedida": material.unidad_medida,
        "densidad": 7.85,
        "pureza": 98,
        "fechaRegistro": "2026-10-20T15:30:00Z",
        "estado": estado,
    }


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("nombre", "a" * 101),
        ("categoria", "Metales"),
        ("unidadMedida", "ml"),
        ("estado", "activo"),
        ("pagina", "abc"),
        ("pagina", "0"),
        ("pagina", "1.0"),
        ("limite", "10"),
        ("unidad_medida", "kg"),
    ],
)
async def test_c03_filtro_invalido_sin_bd(cliente: AsyncClient, campo: str, valor: str) -> None:
    r = await cliente.get("/materiales", params={campo: valor})
    assert r.status_code == 400
    assert r.json()["mensaje"] == (
        f"El valor del filtro de búsqueda '{campo}' es inválido. Por favor verifique los valores o tipos de datos ingresados."
    )


@pytest.mark.parametrize("identificador", ["mat-999", "abc"])
async def test_c04_no_encontrado(cliente: AsyncClient, catalogo: MaterialRepositoryFalso, identificador: str) -> None:
    r = await cliente.get(f"/materiales/{identificador}")
    assert r.status_code == 404
    assert r.json()["mensaje"] == f"El material solicitado con ID '{identificador}' no fue encontrado en el catálogo"


@pytest.mark.parametrize("ruta", ["/materiales", "/materiales/mat-101"])
async def test_c05_fallo_bd(cliente: AsyncClient, ruta: str, caplog: pytest.LogCaptureFixture) -> None:
    r = await cliente.get(ruta)
    trace = r.headers["X-Trace-Id"]
    mensaje = f"Error de comunicación con la base de datos al consultar el material. TraceID: {trace}"
    assert r.status_code == 500
    assert r.json() == {"mensaje": mensaje, "traceId": trace}
    assert any(record.getMessage() == mensaje for record in caplog.records)


async def test_c06_filtros_combinados(cliente: AsyncClient, catalogo: MaterialRepositoryFalso) -> None:
    filtros = {"nombre": "EITE", "categoria": "Lubricantes", "unidadMedida": "L", "estado": "INACTIVO"}
    r = await cliente.get("/materiales", params=filtros)
    assert r.status_code == 200
    ficha = await cliente.get("/materiales/mat-012")
    assert r.json()["materiales"] == [ficha.json()]
    for campo, distinto in (("nombre", "Metal"), ("categoria", "Componentes"), ("unidadMedida", "kg"), ("estado", "ACTIVO")):
        vacio = await cliente.get("/materiales", params={**filtros, campo: distinto})
        assert vacio.json() == {
            "materiales": [],
            "pagina": 1,
            "tamanoPagina": 10,
            "totalRegistros": 0,
            "totalPaginas": 0,
            "mensaje": "No se encontraron materiales que coincidan con los criterios indicados",
        }


async def test_c07_paginacion(cliente: AsyncClient, catalogo: MaterialRepositoryFalso) -> None:
    for pagina, numeros in [(1, range(1, 11)), (2, range(11, 13)), (3, range(0))]:
        r = await cliente.get("/materiales", params={} if pagina == 1 else {"pagina": pagina})
        assert r.status_code == 200
        datos = r.json()
        assert [m["materialId"] for m in datos.pop("materiales")] == [f"mat-{n:03d}" for n in numeros]
        assert datos == {"pagina": pagina, "tamanoPagina": 10, "totalRegistros": 12, "totalPaginas": 2}
