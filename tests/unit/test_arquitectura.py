"""Reglas de dependencia de la arquitectura en capas del DAS (sección 2).

* Cada capa depende solo de la de abajo: api → business → infraestructure.
* Todas pueden usar app/core; app/core no depende de ninguna capa.
* Los servicios no dependen de FastAPI ni de SQL concreto (meta de Reuso).
* El dominio no depende de frameworks.
* Excepciones (raíces de composición): app/main.py y app/api/dependencies.py
  conocen las implementaciones concretas para inyectarlas.
"""

import ast
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
APP = RAIZ / "app"
RAICES_DE_COMPOSICION = {APP / "main.py", APP / "api" / "dependencies.py"}


def _importaciones(archivo: Path) -> set[str]:
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    modulos: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos.update(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
            modulos.add(nodo.module)
    return modulos


def _archivos(paquete: str) -> list[Path]:
    return [a for a in (APP / paquete).rglob("*.py") if a not in RAICES_DE_COMPOSICION]


def _violaciones(paquete: str, prohibidos: tuple[str, ...]) -> list[str]:
    return [
        f"{archivo.relative_to(RAIZ)} importa {modulo}"
        for archivo in _archivos(paquete)
        for modulo in sorted(_importaciones(archivo))
        if modulo.startswith(prohibidos)
    ]


@pytest.mark.parametrize(
    ("paquete", "prohibidos"),
    [
        ("core", ("app.api", "app.business", "app.infraestructure")),
        ("infraestructure", ("app.api", "app.business")),
        ("business", ("app.api", "fastapi", "starlette", "sqlalchemy", "httpx", "pydantic")),
        ("business/domain", ("app.infraestructure", "app.api", "fastapi", "sqlalchemy", "pydantic", "httpx")),
        ("api", ("app.infraestructure", "sqlalchemy", "httpx")),
    ],
)
def test_cada_capa_depende_solo_de_la_de_abajo(paquete: str, prohibidos: tuple[str, ...]) -> None:
    assert _archivos(paquete), f"app/{paquete} no existe o está vacío"
    assert _violaciones(paquete, prohibidos) == []
