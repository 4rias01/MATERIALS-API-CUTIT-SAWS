"""Routers y DTO: cada ruta llama a su servicio y arma la respuesta del contrato.

Los servicios se reemplazan por dobles (``app.dependency_overrides``), así que estas
pruebas no dependen de la lógica de negocio.
"""

from collections.abc import Callable, Iterator
from decimal import Decimal
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.api import dependencies
from app.business.services.base import Resultado
from app.business.services.comandos import DatosMaterial, RegistrarMaterialComando
from tests.fabricas import un_material

MATERIAL_JSON = {
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
}
CUERPO = {"nombre": "Material 1", "categoria": "Materia Prima", "unidadMedida": "kg", "densidad": 7.85, "pureza": 98}


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


ConServicio = Callable[[Resultado[Any]], ServicioFalso]


@pytest.fixture
def con_servicio(app: FastAPI) -> Iterator[ConServicio]:
    def reemplazar(resultado: Resultado[Any]) -> ServicioFalso:
        servicio = ServicioFalso(resultado)
        app.dependency_overrides[dependencies.obtener_material_service] = lambda: servicio
        return servicio

    yield reemplazar
    app.dependency_overrides.clear()


async def test_registrar_material_201(cliente: httpx.AsyncClient, con_servicio: ConServicio) -> None:
    servicio = con_servicio(Resultado(un_material(), "Material registrado"))
    r = await cliente.post("/materiales", json=CUERPO)
    assert r.status_code == 201
    assert r.json() == {**MATERIAL_JSON, "mensaje": "Material registrado"}
    assert servicio.llamadas == [
        ("registrar", (RegistrarMaterialComando("Material 1", "Materia Prima", "kg", Decimal("7.85"), Decimal("98")),))
    ]


async def test_consultas_responden_el_material_sin_mensaje(cliente: httpx.AsyncClient, con_servicio: ConServicio) -> None:
    servicio = con_servicio(Resultado(un_material()))
    r = await cliente.get("/materiales/mat-001")
    assert (r.status_code, r.json()) == (200, MATERIAL_JSON)
    assert servicio.llamadas == [("obtener_por_id", ("mat-001",))]


async def test_actualizar_pasa_el_id_de_la_ruta_y_los_datos(cliente: httpx.AsyncClient, con_servicio: ConServicio) -> None:
    servicio = con_servicio(Resultado(un_material()))
    r = await cliente.put("/materiales/mat-001", json=CUERPO)
    assert r.status_code == 200
    assert servicio.llamadas == [("actualizar", ("mat-001", DatosMaterial("Material 1", "Materia Prima", "kg", Decimal("7.85"), Decimal("98"))))]


@pytest.mark.parametrize("id_invalido", ["1", "abc", "mat-1", "MAT-001", "mat-0000001"])
async def test_id_con_formato_invalido_responde_400_sin_llamar_al_servicio(
    cliente: httpx.AsyncClient, con_servicio: ConServicio, id_invalido: str
) -> None:
    servicio = con_servicio(Resultado(un_material()))
    r = await cliente.get(f"/materiales/{id_invalido}")
    assert (r.status_code, r.json()["mensaje"]) == (400, "El campo 'id' es obligatorio o no tiene un formato válido.")
    assert servicio.llamadas == []
