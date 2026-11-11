"""Catálogo de mensajes del product backlog V1.3.

Texto literal de los criterios de aceptación; no lo modifiquen sin el visto bueno del PO.
Cada constante se llama ``HU<historia>_C<criterio>[_<subcriterio>][_A|_B]``: la letra
distingue las alternativas de un mismo subcriterio ("... o ...", según corresponda).
El comentario de cada constante indica el criterio y el código HTTP con que se responde.

Los marcadores entre corchetes se reemplazan con ``formatear``::

    formatear(HU01_C3, Nombre="Acero 1045")
    formatear(HU01_C7, {"Nombre": "Acero 1045", "SKU": "MP-00001"})
"""

import re
from collections.abc import Mapping

# HU-01 · Registrar material -------------------------------------------------------------
# c2.1 · 400
HU01_C2_1 = "El campo 'Nombre' es obligatorio. Por favor, ingréselo e intente nuevamente."
# c2.2 · 400
HU01_C2_2_A = "El campo 'Nombre' debe tener entre 3 y 100 caracteres."
# c2.2 · 400
HU01_C2_2_B = "El campo 'Nombre' contiene caracteres no permitidos."
# c2.3 · 400
HU01_C2_3_A = "El campo 'Categoría' es obligatorio. Por favor, ingréselo e intente nuevamente."
# c2.3 · 400 · marcadores: [valor]
HU01_C2_3_B = "La Categoría '[valor]' no es válida. Valores permitidos: Materia Prima, Componentes o Lubricantes."
# c2.4 · 400
HU01_C2_4_A = "El campo 'Unidad de medida' es obligatorio. Por favor, ingréselo e intente nuevamente."
# c2.4 · 400 · marcadores: [valor]
HU01_C2_4_B = "La Unidad de medida '[valor]' no es válida. Valores permitidos: und, g, kg, mL, L o m."
# c2.5 · 400
HU01_C2_5_A = "El campo 'Densidad' es obligatorio. Por favor, ingréselo e intente nuevamente."
# c2.5 · 400
HU01_C2_5_B = "El campo 'Densidad' debe ser un número positivo de máximo 4 caracteres."
# c2.6 · 400
HU01_C2_6_A = "El campo 'Pureza' es obligatorio. Por favor, ingréselo e intente nuevamente."
# c2.6 · 400
HU01_C2_6_B = "El campo 'Pureza' debe ser un número entre 0 y 100 de máximo 3 caracteres."
# c3 · 409 · marcadores: [Nombre]
HU01_C3 = "El material con el nombre '[Nombre]' ya se encuentra registrado en el catálogo."
# c5 · texto que responde Inventario (no lo devuelve esta API) · marcadores: [Nombre]
HU01_C5_RESPUESTA_INVENTARIO = "Ya existe un artículo con el nombre [Nombre]"
# c5 · 409 · marcadores: [Nombre]
HU01_C5 = (
    "Inventario ya tiene registrado un artículo con el nombre '[Nombre]'. Indique un nombre "
    "diferente para el material."
)
# c6 · 503
HU01_C6 = "Error de comunicación con el módulo Inventario al registrar el material. Por favor reintente más tarde"
# c7 · 201 · marcadores: [Nombre], [SKU]
HU01_C7 = "Material '[Nombre]' registrado exitosamente con el SKU [SKU]."
# c8 · 500
HU01_C8 = "Error interno de conexión con la base de datos. Por favor reintente más tarde"

# Mensajes genéricos --------------------------------------------------------------------------
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
