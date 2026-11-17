"""Mecanismo de los DTO: traducción de errores al mensaje del backlog y formatos."""

from decimal import Decimal
from typing import Any, ClassVar

import pytest
from pydantic import Field, ValidationError, field_validator

from app.api.schemas.comun import TIPO_ERROR_NEGOCIO, DecimalSalida, EsquemaEntrada, EsquemaSalida, error_de_negocio, respuestas_error

OBLIGATORIO = "El campo 'Nombre' es obligatorio."
NO_VALIDA = "La Categoría '[valor]' no es válida. Valores permitidos: A o B."


class Ejemplo(EsquemaEntrada):
    mensajes_error: ClassVar[dict[tuple[str, str], str]] = {
        ("nombre", "missing"): OBLIGATORIO,
        ("categoriaMaterial", "*"): NO_VALIDA,
        ("sku", "extra_forbidden"): "El campo 'SKU' es de solo lectura",
    }

    nombre: str
    categoria_material: str = Field(pattern="^(A|B)$")

    @field_validator("nombre")
    @classmethod
    def _sin_numeros(cls, valor: str) -> str:
        if any(c.isdigit() for c in valor):
            raise error_de_negocio("El nombre no lleva números")
        return valor


def _error(datos: dict[str, Any]) -> dict[str, Any]:
    with pytest.raises(ValidationError) as error:
        Ejemplo.model_validate(datos)
    return dict(error.value.errors()[0])


def test_campo_obligatorio_faltante() -> None:
    error = _error({"categoriaMaterial": "A"})
    assert (error["type"], error["msg"]) == (TIPO_ERROR_NEGOCIO, OBLIGATORIO)


def test_comodin_y_marcador_valor() -> None:
    assert _error({"nombre": "Acero", "categoriaMaterial": "Z"})["msg"] == "La Categoría 'Z' no es válida. Valores permitidos: A o B."


def test_campo_de_solo_lectura() -> None:
    assert _error({"nombre": "Acero", "categoriaMaterial": "A", "sku": "MP-00001"})["msg"] == "El campo 'SKU' es de solo lectura"


def test_validador_de_campo_con_mensaje_propio() -> None:
    assert _error({"nombre": "Acero 1", "categoriaMaterial": "A"})["msg"] == "El nombre no lleva números"


def test_error_sin_mensaje_en_la_tabla_queda_como_error_de_pydantic() -> None:
    assert _error({"nombre": "Acero", "categoriaMaterial": "A", "otro": 1})["type"] == "extra_forbidden"


def test_solo_acepta_los_nombres_en_camel_case() -> None:
    with pytest.raises(ValidationError):
        Ejemplo.model_validate({"nombre": "Acero", "categoria_material": "A"})
    assert Ejemplo.model_validate({"nombre": "Acero", "categoriaMaterial": "A"}).categoria_material == "A"


class Salida(EsquemaSalida):
    valor_decimal: DecimalSalida


@pytest.mark.parametrize(("valor", "json"), [("2.000", '{"valorDecimal":2}'), ("7.850", '{"valorDecimal":7.85}')])
def test_decimales_se_escriben_como_numeros_json(valor: str, json: str) -> None:
    assert Salida(valor_decimal=Decimal(valor)).model_dump_json() == json


def test_respuestas_de_error_documentadas() -> None:
    assert set(respuestas_error(400, 404)) == {400, 404}
