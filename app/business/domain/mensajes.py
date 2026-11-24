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


# HU-02 · Consultar materiales
HU02_C3 = (
    "El valor del filtro de búsqueda '[NombreParametro]' es inválido. "
    "Por favor verifique los valores o tipos de datos ingresados."
)
HU02_C4 = "El material solicitado con ID '[IDIngresado]' no fue encontrado en el catálogo"
HU02_C5 = "Error de comunicación con la base de datos al consultar el material. TraceID: [traceId]"
HU02_C7 = "No se encontraron materiales que coincidan con los criterios indicados"


# HU-05 · Registrar fórmula --------------------------------------------------------------
HU05_C2_1 = "El campo 'Nombre' es obligatorio. Por favor, ingréselo e intente nuevamente."
HU05_C2_2 = "El campo 'Aplicación técnica' es obligatorio. Por favor, ingréselo e intente nuevamente."
HU05_C2_3 = (
    "La fórmula debe estar compuesta por mínimo 2 materiales diferentes. "
    "Por favor, agregue los componentes e intente nuevamente."
)
HU05_C2_4 = "El campo 'Cantidad' del material '[IDMaterial]' es obligatorio. Por favor, ingréselo e intente nuevamente."
HU05_C3_1 = "La cantidad del material '[IDMaterial]' debe ser un número mayor que 0. Valor recibido: [Cantidad]."
HU05_C3_2 = (
    "La cantidad del material '[IDMaterial]' admite máximo 6 dígitos enteros y 3 decimales. Valor recibido: [Cantidad]."
)
HU05_C4_1 = "La fórmula no puede registrarse. Los siguientes componentes no existen: [Lista de Materiales]."
HU05_C4_2 = "La fórmula no puede registrarse. Los siguientes componentes están en estado INACTIVO: [Lista de Materiales]."
HU05_C5 = (
    "La cantidad del material '[NombreMaterial]' debe ser un número entero, "
    "porque su unidad de medida es Unidad (und). Valor recibido: [Cantidad]."
)
HU05_C6_1 = "Ya existe una fórmula registrada con el nombre '[NombreIngresado]'. Indique un nombre único para la receta."
HU05_C6_2 = "Fórmula '[Nombre]' registrada exitosamente en estado BORRADOR con el código [form-NNN]."
HU05_C8 = "Error interno de conexión con la base de datos al registrar la fórmula. Por favor, reintente más tarde."
HU05_C9_1_A = "El campo 'Nombre' admite máximo 80 caracteres."
HU05_C9_1_B = "El campo 'Nombre' solo admite letras y espacios."
HU05_C9_2 = "El campo 'Aplicación técnica' admite máximo 200 caracteres."
HU05_C9_3 = "El material '[IDMaterial]' está repetido en la tabla de Componentes. Cada material debe aparecer una sola vez."
HU05_C9_4 = "El campo 'Unidad de medida' es de solo lectura: el sistema la toma del material registrado."


# CRUD básico de materiales ----------------------------------------------------------------
# No están en el backlog: son los del CRUD de ejemplo (equivalente al de profesores del dojo).
# El alta (POST /materiales) ya no es del CRUD: la cubre HU-01 con sus propios mensajes.

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
