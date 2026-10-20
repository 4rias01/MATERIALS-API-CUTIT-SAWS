"""Mecanismo de los DTO: traducción de errores al mensaje del backlog y formatos."""

from datetime import date
from decimal import Decimal
from typing import Any, ClassVar

import pytest
from pydantic import Field, ValidationError, field_validator

from app.business.domain import mensajes
from app.presentation.schemas.comun import (
    TIPO_ERROR_NEGOCIO,
    DecimalSalida,
    EsquemaEntrada,
    EsquemaSalida,
    error_de_negocio,
)
from app.presentation.schemas.formulas import FiltrosFormulasConsulta, PaginacionAprobadasConsulta


class Ejemplo(EsquemaEntrada):
    mensajes_error: ClassVar[dict[tuple[str, str], str]] = {
        ("nombre", "missing"): mensajes.HU01_C2_1,
        ("categoriaMaterial", "*"): mensajes.HU01_C2_3_B,
        ("sku", "extra_forbidden"): mensajes.HU03_C2_1,
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
    return error.value.errors()[0]


def test_campo_obligatorio_faltante() -> None:
    error = _error({"categoriaMaterial": "A"})
    assert (error["type"], error["msg"]) == (TIPO_ERROR_NEGOCIO, mensajes.HU01_C2_1)


def test_comodin_y_marcador_valor() -> None:
    error = _error({"nombre": "Acero", "categoriaMaterial": "Z"})
    assert error["msg"] == "La Categoría 'Z' no es válida. Valores permitidos: Materia Prima, Componentes o Lubricantes."


def test_campo_de_solo_lectura() -> None:
    error = _error({"nombre": "Acero", "categoriaMaterial": "A", "sku": "MP-00001"})
    assert error["msg"] == mensajes.HU03_C2_1


def test_validador_de_campo_con_mensaje_propio() -> None:
    assert _error({"nombre": "Acero 1", "categoriaMaterial": "A"})["msg"] == "El nombre no lleva números"


def test_error_sin_mensaje_en_la_tabla_queda_como_error_de_pydantic() -> None:
    error = _error({"nombre": "Acero", "categoriaMaterial": "A", "otro": 1})
    assert error["type"] == "extra_forbidden"


def test_solo_acepta_los_nombres_en_camel_case() -> None:
    with pytest.raises(ValidationError):
        Ejemplo.model_validate({"nombre": "Acero", "categoria_material": "A"})
    assert Ejemplo.model_validate({"nombre": "Acero", "categoriaMaterial": "A"}).categoria_material == "A"


class Salida(EsquemaSalida):
    valor_decimal: DecimalSalida


@pytest.mark.parametrize(("valor", "json"), [("2.000", '{"valorDecimal":2}'), ("7.850", '{"valorDecimal":7.85}')])
def test_decimales_se_escriben_como_numeros_json(valor: str, json: str) -> None:
    assert Salida(valor_decimal=Decimal(valor)).model_dump_json() == json


def test_fechas_dd_mm_aaaa() -> None:
    filtros = FiltrosFormulasConsulta.model_validate({"fechaRegistroDesde": "31/01/2026"})
    assert filtros.fecha_registro_desde == date(2026, 1, 31)
    with pytest.raises(ValidationError) as error:
        FiltrosFormulasConsulta.model_validate({"fechaRegistroDesde": "2026-01-31"})
    assert error.value.errors()[0]["type"] == "fecha_ddmmaaaa"


def test_paginacion_de_aprobadas_por_defecto() -> None:
    parametros = PaginacionAprobadasConsulta.model_validate({})
    assert (parametros.pagina, parametros.tamano_pagina) == (1, 50)
    with pytest.raises(ValidationError):
        PaginacionAprobadasConsulta.model_validate({"tamanoPagina": 101})
