"""Routers y DTO: cada ruta llama a su servicio y arma la respuesta del contrato.

Los servicios se reemplazan por dobles (``app.dependency_overrides``), así que estas
pruebas siguen siendo válidas cuando se implementen las historias de usuario.
"""

from decimal import Decimal
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.business.services.base import Resultado
from app.business.services.comandos import ConsultaFormulas, RegistrarMaterialComando
from app.business.services.evaluacion_patente_service import TramiteEvaluacion
from app.core.paginacion import Pagina
from app.presentation import dependencies
from tests.fabricas import un_material, una_evaluacion, una_formula


class ServicioFalso:
    """Devuelve ``resultado`` en cualquier método y guarda los argumentos recibidos."""

    def __init__(self, resultado: Resultado[Any]) -> None:
        self.resultado = resultado
        self.llamadas: list[tuple[str, tuple[Any, ...]]] = []

    def __getattr__(self, nombre: str) -> Any:
        async def metodo(*args: Any) -> Resultado[Any]:
            self.llamadas.append((nombre, args))
            return self.resultado

        return metodo


@pytest.fixture
def con_servicio(app: FastAPI):  # type: ignore[no-untyped-def]
    def reemplazar(proveedor: Any, resultado: Resultado[Any]) -> ServicioFalso:
        servicio = ServicioFalso(resultado)
        app.dependency_overrides[proveedor] = lambda: servicio
        return servicio

    yield reemplazar
    app.dependency_overrides.clear()


async def test_registrar_material_201(cliente: httpx.AsyncClient, con_servicio) -> None:  # type: ignore[no-untyped-def]
    servicio = con_servicio(dependencies.obtener_material_service, Resultado(un_material(), "Material registrado"))
    cuerpo = {"nombre": "Material 1", "categoria": "Materia Prima", "unidadMedida": "kg", "densidad": 7.85, "pureza": 98}
    r = await cliente.post("/materiales", json=cuerpo)
    assert r.status_code == 201
    assert r.json() == {
        "materialId": "mat-001",
        "sku": "MP-00001",
        "nombre": "Material 1",
        "categoria": "Materia Prima",
        "unidadMedida": "kg",
        "densidad": 7.85,
        "pureza": 98,
        "fechaRegistro": "2026-10-20T15:30:00Z",
        "estado": "ACTIVO",
        "fechaUltimaActualizacion": "2026-10-20T15:30:00Z",
        "mensaje": "Material registrado",
    }
    assert servicio.llamadas == [
        ("registrar", (RegistrarMaterialComando("Material 1", "Materia Prima", "kg", Decimal("7.85"), Decimal("98")),))
    ]


async def test_consultar_material_devuelve_la_ficha_de_9_campos(cliente: httpx.AsyncClient, con_servicio) -> None:  # type: ignore[no-untyped-def]
    con_servicio(dependencies.obtener_material_service, Resultado(un_material(estado="INACTIVO")))
    r = await cliente.get("/materiales/mat-001")
    assert r.status_code == 200
    assert len(r.json()) == 9
    assert r.json()["estado"] == "INACTIVO"


async def test_inhabilitar_material(cliente: httpx.AsyncClient, con_servicio) -> None:  # type: ignore[no-untyped-def]
    con_servicio(dependencies.obtener_material_service, Resultado(un_material(estado="INACTIVO"), "Material 'mat-001' inhabilitado exitosamente"))
    r = await cliente.delete("/materiales/mat-001")
    assert r.json() == {"materialId": "mat-001", "estado": "INACTIVO", "mensaje": "Material 'mat-001' inhabilitado exitosamente"}


async def test_listar_materiales(cliente: httpx.AsyncClient, con_servicio) -> None:  # type: ignore[no-untyped-def]
    con_servicio(dependencies.obtener_material_service, Resultado(Pagina([un_material(1), un_material(2)], 1, 10, 2)))
    r = await cliente.get("/materiales")
    assert (r.json()["totalRegistros"], len(r.json()["materiales"]), "mensaje" in r.json()) == (2, 2, False)


async def test_registrar_formula_201(cliente: httpx.AsyncClient, con_servicio) -> None:  # type: ignore[no-untyped-def]
    con_servicio(dependencies.obtener_formula_service, Resultado(una_formula(), "Fórmula registrada"))
    cuerpo = {
        "nombre": "Formula uno",
        "aplicacionTecnica": "Corte",
        "componentes": [{"materialId": "mat-011", "cantidad": 2.5}, {"materialId": "mat-012", "cantidad": 1}],
    }
    r = await cliente.post("/formulas", json=cuerpo)
    assert r.status_code == 201
    datos = r.json()
    assert datos["formulaId"] == "form-001"
    assert datos["componentes"][0] == {
        "materialId": "mat-011",
        "sku": "MP-00011",
        "nombre": "Material 11",
        "cantidad": 2.5,
        "unidadMedida": "kg",
    }
    assert datos["componentes"][1]["cantidad"] == 1
    assert "patentesEnConflicto" not in datos


async def test_detalle_de_formula_rechazada_incluye_las_patentes(cliente: httpx.AsyncClient, con_servicio) -> None:  # type: ignore[no-untyped-def]
    formula = una_formula(estado="RECHAZADA_POR_INFRACCION")
    una_evaluacion(formula, 1, "INFRACCION", [("111111", "Patente vieja")])
    una_evaluacion(formula, 2, "INFRACCION", [("123456", "Aleación de tungsteno")])
    con_servicio(dependencies.obtener_formula_service, Resultado(formula))
    r = await cliente.get("/formulas/form-001")
    assert r.json()["patentesEnConflicto"] == [{"conflictoId": "123456", "titulo": "Aleación de tungsteno"}]
    assert "mensaje" not in r.json()


async def test_listado_de_formulas_con_filtros(cliente: httpx.AsyncClient, con_servicio) -> None:  # type: ignore[no-untyped-def]
    servicio = con_servicio(dependencies.obtener_formula_service, Resultado(Pagina([], 1, 10, 0), "Sin resultados"))
    r = await cliente.get(
        "/formulas",
        params=[("buscar", "form"), ("estado", "APROBADA"), ("fechaRegistroDesde", "01/02/2026"), ("materiales", "mat-001"), ("materiales", "mat-002")],
    )
    assert r.status_code == 200
    assert r.json() == {"pagina": 1, "tamanoPagina": 10, "totalRegistros": 0, "totalPaginas": 0, "formulas": [], "mensaje": "Sin resultados"}
    consulta = servicio.llamadas[0][1][0]
    assert isinstance(consulta, ConsultaFormulas)
    assert (consulta.texto, consulta.estado, str(consulta.registro_desde), consulta.materiales) == (
        "form",
        "APROBADA",
        "2026-02-01",
        ("mat-001", "mat-002"),
    )


async def test_formulas_aprobadas(cliente: httpx.AsyncClient, con_servicio) -> None:  # type: ignore[no-untyped-def]
    servicio = con_servicio(
        dependencies.obtener_formula_service, Resultado(Pagina([una_formula(estado="APROBADA")], 1, 50, 1))
    )
    r = await cliente.get("/formulas/aprobadas")
    assert r.status_code == 200
    assert servicio.llamadas == [("listar_aprobadas", (1, 50))]
    formula = r.json()["formulas"][0]
    assert set(formula) == {"formulaId", "nombre", "aplicacionTecnica", "version", "estado", "fechaUltimaActualizacion", "componentes"}


async def test_descontinuar_formula(cliente: httpx.AsyncClient, con_servicio) -> None:  # type: ignore[no-untyped-def]
    con_servicio(dependencies.obtener_formula_service, Resultado(una_formula(estado="DESCONTINUADA"), "Fórmula descontinuada exitosamente."))
    r = await cliente.patch("/formulas/form-001/descontinuar")
    assert r.json() == {"formulaId": "form-001", "estado": "DESCONTINUADA", "mensaje": "Fórmula descontinuada exitosamente."}


async def test_solicitar_evaluacion_202(cliente: httpx.AsyncClient, con_servicio) -> None:  # type: ignore[no-untyped-def]
    tramite = TramiteEvaluacion("form-001", "tck-001", "EVALUANDO_PATENTE")
    con_servicio(dependencies.obtener_evaluacion_patente_service, Resultado(tramite, "Ticket asignado: tck-001"))
    r = await cliente.post("/formulas/form-001/evaluacion-patente")
    assert r.status_code == 202
    assert r.json() == {"formulaId": "form-001", "ticketEvaluacionId": "tck-001", "estado": "EVALUANDO_PATENTE", "mensaje": "Ticket asignado: tck-001"}


async def test_dictamen_de_patente(cliente: httpx.AsyncClient, con_servicio) -> None:  # type: ignore[no-untyped-def]
    tramite = TramiteEvaluacion("form-001", "tck-001", "RECHAZADA_POR_INFRACCION")
    servicio = con_servicio(dependencies.obtener_evaluacion_patente_service, Resultado(tramite, "Dictamen registrado"))
    cuerpo = {"ticketEvaluacionId": "tck-001", "resultado": "INFRACCION", "patentesEnConflicto": [{"conflictoId": "123456", "titulo": "X"}]}
    r = await cliente.post("/formulas/form-001/dictamen-patente", json=cuerpo)
    assert r.status_code == 200
    _, (id_formula, comando) = servicio.llamadas[0]
    assert id_formula == "form-001"
    assert comando.resultado == "INFRACCION"
    assert comando.patentes_en_conflicto[0].conflicto_id == "123456"

