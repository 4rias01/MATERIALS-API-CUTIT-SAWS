"""Documentación OpenAPI (Swagger) del contrato publicado en /docs y /openapi.json."""

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import FastAPI

DESCRIPCION = """
API REST del módulo **Materiales y Fórmulas** de la plataforma backend de Cutit Saws Ltd.

* **Materiales** (HU-01): registrar un material nuevo, que también se registra como
  materia prima en Inventario.

**Formato de las respuestas**

* Éxito: los campos del recurso en camelCase y, cuando el backlog lo define, el campo
  `mensaje`.
* Error: `{"mensaje": "...", "traceId": "..."}`. El mismo traceId viaja en la cabecera
  `X-Trace-Id` y en el log del servidor.

**Cabeceras opcionales de entrada**

* `X-Trace-Id`: traceId de la petición de origen, para correlacionar logs entre células.
* `X-Servicio-Origen`: nombre del servicio que llama (se guarda en la auditoría).
"""

ETIQUETAS = [
    {"name": "Materiales", "description": "Catálogo de materiales (HU-01)."},
    {"name": "Monitoreo", "description": "Estado de la API (/health). Las métricas están en /metrics."},
]


def ajustar_openapi(app: "FastAPI") -> None:
    """Quita del contrato la respuesta 422 "Validation Error" que FastAPI agrega por
    defecto: esta API responde 400 cuando la solicitud no cumple el contrato y reserva
    el 422 para las reglas de negocio."""
    generar_original = app.openapi

    def generar() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        esquema = generar_original()
        for operaciones in esquema.get("paths", {}).values():
            for operacion in operaciones.values():
                respuesta = operacion.get("responses", {}).get("422")
                if respuesta and "HTTPValidationError" in json.dumps(respuesta):
                    del operacion["responses"]["422"]
        for nombre in ("HTTPValidationError", "ValidationError"):
            esquema.get("components", {}).get("schemas", {}).pop(nombre, None)
        return esquema

    app.openapi = generar  # type: ignore[method-assign]
