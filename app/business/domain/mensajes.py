"""Catálogo de mensajes del product backlog V1.3.

Texto literal de los criterios de aceptación; no lo modifiquen sin el visto bueno del PO.
Cada constante se llama ``HU<historia>_C<criterio>[_<subcriterio>][_A|_B]``: la letra
distingue las alternativas de un mismo subcriterio ("... o ...", según corresponda).
El comentario de cada constante indica el criterio y el código HTTP con que se responde::

    # HU-01 · Registrar material ---------------------------------------------------------
    # c3 · 409 · marcadores: [Nombre]
    HU01_C3 = "El material con el nombre '[Nombre]' ya se encuentra registrado en el catálogo."

Los marcadores entre corchetes se reemplazan con ``formatear``::

    formatear(HU01_C3, Nombre="Acero 1045")
    formatear(HU01_C3, {"Nombre": "Acero 1045"})
"""

import re
from collections.abc import Mapping

# Mensajes de las historias de usuario ---------------------------------------------------
# (se agregan aquí a medida que se implementan las historias)


# CRUD básico de materiales ----------------------------------------------------------------
# No están en el backlog: son los del CRUD de ejemplo (equivalente al de profesores del dojo).

# 400 · marcadores: [campo]
MATERIAL_CAMPO_INVALIDO = "El campo '[campo]' es obligatorio o no tiene un formato válido."
# 404 · marcadores: [id]
MATERIAL_NO_ENCONTRADO = "Material con id [id] no encontrado"
# 409 · marcadores: [nombre]
MATERIAL_NOMBRE_DUPLICADO = "Ya existe un material con el nombre: [nombre]"
# 500
MATERIAL_ERROR_BASE_DATOS = "Error interno de conexión con la base de datos. Por favor reintente más tarde"


# Mensajes genéricos ----------------------------------------------------------------------
# No están en el backlog: los usa el manejador global de excepciones cuando ningún
# criterio define el texto. Propuesta del equipo; confirmar con el PO.

# 400 · cualquier solicitud que no cumple el contrato y no tiene mensaje propio.
SOLICITUD_INVALIDA = "La solicitud contiene parámetros o un formato no válido. Por favor, verifique e intente nuevamente."
# 404 · ruta inexistente.
RUTA_NO_ENCONTRADA = "La ruta solicitada no existe en la API."
# 405 · método HTTP no soportado por la ruta.
METODO_NO_PERMITIDO = "El método HTTP no está permitido en esta ruta."
# 500 · error no controlado (incluye el traceId en la respuesta).
ERROR_INTERNO = "Error interno del servidor. Por favor reintente más tarde"


# Utilidades ----------------------------------------------------------------------------------

_MARCADOR = re.compile(r"\[([^\[\]]+)\]")


def marcadores(plantilla: str) -> list[str]:
    """Nombres de los marcadores de una plantilla, por ejemplo ``["Nombre", "SKU"]``."""
    return _MARCADOR.findall(plantilla)


def formatear(plantilla: str, valores: Mapping[str, object] | None = None, /, **otros: object) -> str:
    """Reemplaza los marcadores ``[Nombre]`` de la plantilla.

    Los valores se pasan como argumentos con nombre o, si el marcador tiene espacios o
    guiones (por ejemplo ``[Lista de Materiales]``), en un diccionario. Lanza
    ``KeyError`` si falta algún valor, para detectar el error en las pruebas.
    """
    datos = {**(valores or {}), **otros}
    faltantes = [m for m in marcadores(plantilla) if m not in datos]
    if faltantes:
        raise KeyError(f"Faltan valores para los marcadores {faltantes}")
    return _MARCADOR.sub(lambda m: str(datos[m.group(1)]), plantilla)
