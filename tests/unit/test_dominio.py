"""Catálogo de mensajes, utilidades de formato y errores del dominio."""

import re

import pytest

from app.business.domain import mensajes
from app.business.domain.errores import ErrorDominio, Motivo, ValorInvalidoError

PLANTILLA = "Material '[Nombre]' registrado exitosamente con el SKU [SKU]."


def _constantes_del_backlog() -> dict[str, str]:
    return {k: v for k, v in vars(mensajes).items() if re.fullmatch(r"HU\d{2}_C\w+", k)}


def test_el_catalogo_tiene_los_17_mensajes_de_hu01() -> None:
    constantes = {k: v for k, v in _constantes_del_backlog().items() if k.startswith("HU01")}
    assert len(constantes) == 17
    assert all(isinstance(v, str) and v.strip() == v and v for v in constantes.values())


def test_mensajes_de_hu01_con_marcadores() -> None:
    assert mensajes.formatear(mensajes.HU01_C7, Nombre="Acero", SKU="MP-00001") == (
        "Material 'Acero' registrado exitosamente con el SKU MP-00001."
    )
    assert mensajes.formatear(mensajes.HU01_C3, {"Nombre": "Acero"}).startswith("El material con el nombre 'Acero'")
    assert mensajes.marcadores(mensajes.HU01_C2_3_B) == ["valor"]
    assert mensajes.formatear(mensajes.HU01_C8) == mensajes.HU01_C8


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
