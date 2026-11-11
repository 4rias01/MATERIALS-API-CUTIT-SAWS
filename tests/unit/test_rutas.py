"""Routers y DTO: cada ruta llama a su servicio y arma la respuesta del contrato.

Los servicios se reemplazan por dobles (``app.dependency_overrides``), así que estas
pruebas siguen siendo válidas cuando se implementen las historias de usuario.
"""

from decimal import Decimal
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.api import dependencies
from app.business.services.base import Resultado
from app.business.services.comandos import RegistrarMaterialComando
from tests.fabricas import un_material


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
