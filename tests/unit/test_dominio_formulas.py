"""Invariantes de HU-05 para llamadas que no pasan por HTTP."""

from decimal import Decimal, localcontext

import pytest

from app.business.domain.errores import ValorInvalidoError
from app.business.domain.formulas import Cantidad, ComponenteFormula, id_formula
from app.business.services.comandos import RegistrarFormulaComando
from app.core.exceptions import SolicitudInvalidaError


def test_precision_decimal_no_altera_la_validacion() -> None:
    with localcontext() as contexto:
        contexto.prec = 2
        assert Cantidad(Decimal("999999.999")).valor == Decimal("999999.999")
        for valor in ("1.00000000000000000000000000001", "1e-1000000000000000000"):
            with pytest.raises(ValorInvalidoError):
                Cantidad(Decimal(valor))


def test_comando_rechaza_componentes_repetidos() -> None:
    componente = ComponenteFormula("mat-001", Decimal(1))
    with pytest.raises(SolicitudInvalidaError, match="repetido"):
        RegistrarFormulaComando("Mezcla", "Corte 1045", (componente, componente))


def test_componente_rechaza_id_invalido() -> None:
    with pytest.raises(SolicitudInvalidaError):
        ComponenteFormula("mat-1", Decimal(1))


def test_codigo_secuencial_admite_mas_de_tres_digitos() -> None:
    assert id_formula(1) == "form-001"
    assert id_formula(1000) == "form-1000"
    with pytest.raises(ValorInvalidoError):
        id_formula(0)
