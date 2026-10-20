"""Los valores de las restricciones CHECK coinciden con los enums del dominio."""

from app.business.domain.enums import Categoria, EstadoFormula, EstadoMaterial, ResultadoDictamen, UnidadMedida
from app.data_access.models import Base
from app.data_access.models.evaluacion_patente import RESULTADOS_DICTAMEN
from app.data_access.models.formula import ESTADOS_FORMULA
from app.data_access.models.material import CATEGORIAS, ESTADOS_MATERIAL, UNIDADES_MEDIDA


def test_valores_permitidos_iguales_en_modelo_y_dominio() -> None:
    assert set(CATEGORIAS) == {c.value for c in Categoria}
    assert set(UNIDADES_MEDIDA) == {u.value for u in UnidadMedida}
    assert set(ESTADOS_MATERIAL) == {e.value for e in EstadoMaterial}
    assert set(ESTADOS_FORMULA) == {e.value for e in EstadoFormula}
    assert set(RESULTADOS_DICTAMEN) == {r.value for r in ResultadoDictamen}


def test_tablas_del_mer() -> None:
    assert set(Base.metadata.tables) == {
        "material",
        "formula",
        "componente_formula",
        "evaluacion_patente",
        "patente_conflicto",
        "auditoria",
    }


def test_la_auditoria_no_tiene_llaves_foraneas() -> None:
    assert not Base.metadata.tables["auditoria"].foreign_keys
