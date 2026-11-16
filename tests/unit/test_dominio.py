"""Catálogo de mensajes, utilidades de formato y errores del dominio."""

import pytest

from app.business.domain import mensajes
from app.business.domain.errores import ErrorDominio, Motivo, ValorInvalidoError

PLANTILLA = "Material '[Nombre]' registrado exitosamente con el SKU [SKU]."


def test_formatear_reemplaza_los_marcadores() -> None:
    assert mensajes.formatear(PLANTILLA, Nombre="Acero", SKU="MP-00001") == "Material 'Acero' registrado exitosamente con el SKU MP-00001."
    assert mensajes.formatear("[Lista de Materiales] vacía", {"Lista de Materiales": "La lista"}) == "La lista vacía"
    assert mensajes.formatear(mensajes.ERROR_INTERNO) == mensajes.ERROR_INTERNO


def test_formatear_avisa_si_falta_un_valor() -> None:
    with pytest.raises(KeyError):
        mensajes.formatear(PLANTILLA, Nombre="Acero")


def test_marcadores() -> None:
    assert mensajes.marcadores(PLANTILLA) == ["Nombre", "SKU"]
    assert mensajes.marcadores(mensajes.MATERIAL_NO_ENCONTRADO) == ["id"]


def test_valor_invalido_lleva_campo_motivo_y_valor() -> None:
    error = ValorInvalidoError("nombre", Motivo.LONGITUD, "ab")
    assert isinstance(error, ErrorDominio)
    assert (error.campo, error.motivo, error.valor) == ("nombre", Motivo.LONGITUD, "ab")
    assert str(error) == "nombre: LONGITUD ('ab')"
