"""Objetos de valor del dominio."""

from decimal import Decimal

import pytest

from app.business.domain.errores import Motivo, ValorInvalidoError
from app.business.domain.value_objects import (
    Cantidad,
    Densidad,
    NombreMaterial,
    Pureza,
    Sku,
    Version,
    contar_caracteres,
    id_formula,
    id_material,
    id_ticket_evaluacion,
    normalizar_nombre,
)


class TestNombreMaterial:
    def test_normaliza_espacios_al_inicio_al_final_y_repetidos(self) -> None:
        assert NombreMaterial.crear("  Acero   al  carbono 1045 ").valor == "Acero al carbono 1045"

    @pytest.mark.parametrize("nombre", ["Ácido cítrico", "Aceite Ñandú", "Lámina 3/4 (tipo #2), cal. 1.5-A"])
    def test_acepta_letras_con_tilde_ene_digitos_y_simbolos_permitidos(self, nombre: str) -> None:
        assert NombreMaterial.crear(nombre).valor == nombre

    @pytest.mark.parametrize("nombre", ["Ac", "x" * 101, "   ab   "])
    def test_rechaza_longitud_fuera_de_3_a_100(self, nombre: str) -> None:
        with pytest.raises(ValorInvalidoError) as error:
            NombreMaterial.crear(nombre)
        assert error.value.motivo == Motivo.LONGITUD

    @pytest.mark.parametrize("nombre", ["Acero@1045", "Acero_1045", "Acero\t1045", "Acero ü"])
    def test_rechaza_caracteres_no_permitidos(self, nombre: str) -> None:
        with pytest.raises(ValorInvalidoError) as error:
            NombreMaterial.crear(nombre)
        assert error.value.motivo == Motivo.CARACTERES

    def test_clave_de_unicidad_no_distingue_mayusculas(self) -> None:
        assert NombreMaterial.crear("ÁCIDO Cítrico").clave_unicidad == NombreMaterial.crear("ácido cítrico").clave_unicidad

    def test_es_inmutable(self) -> None:
        nombre = NombreMaterial.crear("Acero")
        with pytest.raises(AttributeError):
            nombre.valor = "Otro"  # type: ignore[misc]


def test_normalizar_nombre_conserva_el_texto_sin_espacios_sobrantes() -> None:
    assert normalizar_nombre("a  b   c") == "a b c"


class TestDensidad:
    @pytest.mark.parametrize("valor", ["7.85", "1000", "0.5", 12, "7.850"])
    def test_acepta_positivos_de_hasta_4_caracteres(self, valor: object) -> None:
        assert Densidad(valor).valor == Decimal(str(valor))  # type: ignore[arg-type]

    @pytest.mark.parametrize("valor", ["0", "-1"])
    def test_rechaza_no_positivos(self, valor: str) -> None:
        with pytest.raises(ValorInvalidoError) as error:
            Densidad(Decimal(valor))
        assert error.value.motivo == Motivo.NO_POSITIVO

    @pytest.mark.parametrize("valor", ["7.856", "10000", "12.25"])
    def test_rechaza_mas_de_4_caracteres(self, valor: str) -> None:
        with pytest.raises(ValorInvalidoError) as error:
            Densidad(Decimal(valor))
        assert error.value.motivo == Motivo.DEMASIADOS_DIGITOS

    @pytest.mark.parametrize("valor", ["abc", True, None, "NaN", "Infinity"])
    def test_rechaza_valores_no_numericos(self, valor: object) -> None:
        with pytest.raises(ValorInvalidoError) as error:
            Densidad(valor)  # type: ignore[arg-type]
        assert error.value.motivo == Motivo.FORMATO


class TestPureza:
    @pytest.mark.parametrize("valor", ["0", "100", "9.5", "98"])
    def test_acepta_de_0_a_100_con_hasta_3_caracteres(self, valor: str) -> None:
        assert Pureza(Decimal(valor)).valor == Decimal(valor)

    @pytest.mark.parametrize("valor", ["-1", "100.1", "101"])
    def test_rechaza_fuera_de_rango(self, valor: str) -> None:
        with pytest.raises(ValorInvalidoError) as error:
            Pureza(Decimal(valor))
        assert error.value.motivo == Motivo.FUERA_DE_RANGO

    def test_rechaza_mas_de_3_caracteres(self) -> None:
        with pytest.raises(ValorInvalidoError) as error:
            Pureza(Decimal("99.5"))
        assert error.value.motivo == Motivo.DEMASIADOS_DIGITOS


class TestCantidad:
    @pytest.mark.parametrize("valor", ["0.001", "1", "999999.999", "2.500"])
    def test_acepta_mayor_que_0_con_hasta_6_enteros_y_3_decimales(self, valor: str) -> None:
        assert Cantidad(Decimal(valor)).valor == Decimal(valor)

    @pytest.mark.parametrize("valor", ["0", "-2"])
    def test_rechaza_no_positivas(self, valor: str) -> None:
        with pytest.raises(ValorInvalidoError) as error:
            Cantidad(Decimal(valor))
        assert error.value.motivo == Motivo.NO_POSITIVO

    @pytest.mark.parametrize("valor", ["1000000", "1.0001"])
    def test_rechaza_mas_digitos_de_los_permitidos(self, valor: str) -> None:
        with pytest.raises(ValorInvalidoError) as error:
            Cantidad(Decimal(valor))
        assert error.value.motivo == Motivo.DEMASIADOS_DIGITOS

    @pytest.mark.parametrize(("valor", "entera"), [("3", True), ("3.000", True), ("3.5", False)])
    def test_es_entera(self, valor: str, entera: bool) -> None:
        assert Cantidad(Decimal(valor)).es_entera() is entera


def test_sku_valida_formato_mp_00000() -> None:
    assert str(Sku("MP-00001")) == "MP-00001"
    for invalido in ("MP-1", "mp-00001", "MP-000001", ""):
        with pytest.raises(ValorInvalidoError):
            Sku(invalido)


def test_version_empieza_en_1_y_aumenta_de_1_en_1() -> None:
    assert Version().valor == 1
    assert Version(3).siguiente() == Version(4)
    with pytest.raises(ValorInvalidoError):
        Version(0)


def test_identificadores_secuenciales() -> None:
    assert id_material(1) == "mat-001"
    assert id_material(1000) == "mat-1000"
    assert id_formula(42) == "form-042"
    assert id_ticket_evaluacion(7) == "tck-007"
    with pytest.raises(ValorInvalidoError):
        id_material(0)


def test_contar_caracteres_sin_ceros_sobrantes_ni_notacion_cientifica() -> None:
    assert contar_caracteres(Decimal("7.850")) == 4
    assert contar_caracteres(Decimal("1E+2")) == 3
