"""Los valores de las restricciones CHECK coinciden con los enums del dominio."""

from app.business.domain.enums import Categoria, EstadoMaterial, UnidadMedida
from app.infraestructure.models import Base
from app.infraestructure.models.material import CATEGORIAS, ESTADOS_MATERIAL, UNIDADES_MEDIDA


def test_valores_permitidos_iguales_en_modelo_y_dominio() -> None:
    assert set(CATEGORIAS) == {c.value for c in Categoria}
    assert set(UNIDADES_MEDIDA) == {u.value for u in UnidadMedida}
    assert set(ESTADOS_MATERIAL) == {e.value for e in EstadoMaterial}


def test_tablas_del_mer() -> None:
    assert set(Base.metadata.tables) == {"material", "auditoria"}


def test_la_auditoria_no_tiene_llaves_foraneas() -> None:
    assert not Base.metadata.tables["auditoria"].foreign_keys
