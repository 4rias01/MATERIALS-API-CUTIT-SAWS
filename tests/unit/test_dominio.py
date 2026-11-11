"""Catálogo de mensajes del backlog."""

import re

import pytest

from app.business.domain import mensajes


def _constantes() -> dict[str, str]:
    return {k: v for k, v in vars(mensajes).items() if re.fullmatch(r"HU\d{2}_C\w+", k)}


def test_el_catalogo_tiene_los_17_mensajes_de_hu01() -> None:
    constantes = _constantes()
    assert len(constantes) == 17
    assert {k[:4] for k in constantes} == {"HU01"}
    assert all(isinstance(v, str) and v.strip() == v and v for v in constantes.values())


def test_formatear_reemplaza_los_marcadores() -> None:
    assert mensajes.formatear(mensajes.HU01_C7, Nombre="Acero", SKU="MP-00001") == (
        "Material 'Acero' registrado exitosamente con el SKU MP-00001."
    )
    assert mensajes.formatear(mensajes.HU01_C3, {"Nombre": "Acero"}).startswith("El material con el nombre 'Acero'")
    assert mensajes.formatear(mensajes.HU01_C8) == mensajes.HU01_C8


def test_formatear_avisa_si_falta_un_valor() -> None:
    with pytest.raises(KeyError):
        mensajes.formatear(mensajes.HU01_C7, Nombre="Acero")


def test_marcadores() -> None:
    assert mensajes.marcadores(mensajes.HU01_C7) == ["Nombre", "SKU"]
    assert mensajes.marcadores(mensajes.HU01_C2_3_B) == ["valor"]
