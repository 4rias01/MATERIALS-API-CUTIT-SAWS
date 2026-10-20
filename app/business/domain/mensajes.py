"""Catálogo de mensajes del product backlog V1.3.

Texto literal de los criterios de aceptación; no lo modifiquen sin el visto bueno del PO.
Cada constante se llama ``HU<historia>_C<criterio>[_<subcriterio>][_A|_B]``: la letra
distingue las alternativas de un mismo subcriterio ("... o ...", según corresponda).
El comentario de cada constante indica el criterio y el código HTTP con que se responde.

Los marcadores entre corchetes se reemplazan con ``formatear``::

    formatear(HU01_C3, Nombre="Acero 1045")
    formatear(HU05_C4_1, {"Lista de Materiales": "mat-001, mat-002"})
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
HU01_C2_5 = "El campo 'Densidad' es obligatorio. Por favor, ingréselo e intente nuevamente."
# c2.6 · 400
HU01_C2_6 = "El campo 'Pureza' es obligatorio. Por favor, ingréselo e intente nuevamente."
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

# HU-02 · Consultar material -------------------------------------------------------------
# c3 · 400 · marcadores: [NombreParametro]
HU02_C3 = (
    "El valor del filtro de búsqueda '[NombreParametro]' es inválido. Por favor verifique los "
    "valores o tipos de datos ingresados."
)
# c4 · 404 · marcadores: [IDIngresado]
HU02_C4 = "El material solicitado con ID '[IDIngresado]' no fue encontrado en el catálogo"
# c5 · 500 · marcadores: [traceId]
HU02_C5 = "Error de comunicación con la base de datos al consultar el material. TraceID: [traceId]"

# HU-03 · Modificar material -------------------------------------------------------------
# c2.1 · 400
HU03_C2_1 = "El campo 'SKU' es de solo lectura y no puede ser modificado"
# c2.2 · 400
HU03_C2_2 = "El campo 'Unidad de medida' es de solo lectura y no puede ser modificado"
# c2.3 · 400
HU03_C2_3 = "El campo nombre es obligatorio, por favor, ingrésalo e intenta nuevamente"
# c2.4 · 400
HU03_C2_4_A = "El campo nombre debe tener entre 3 y 100 caracteres"
# c2.4 · 400
HU03_C2_4_B = "El campo nombre contiene caracteres no permitidos"
# c2.5 · 400 · marcadores: [valor]
HU03_C2_5 = "La categoría '[valor]' no es válida. Valores permitidos: Materia Prima, Componentes o Lubricantes"
# c2.6 · 400
HU03_C2_6 = "El campo densidad es obligatorio y debe contener un valor numérico positivo"
# c2.7 · 400
HU03_C2_7 = "El campo pureza es obligatorio y debe estar en una escala de 0 a 100%"
# c3 · 409 · marcadores: [Nombre]
HU03_C3 = "El material con el nombre '[Nombre]' ya se encuentra registrado en el catálogo"
# c5 · 409 · marcadores: [Nombre]
HU03_C5 = (
    "Inventario ya tiene registrado un artículo con el nombre '[Nombre]'. Indique un nombre "
    "diferente para el material"
)
# c6 · 503
HU03_C6 = "Error de comunicación con el módulo Inventario al actualizar el material. Por favor reintente más tarde"
# c7 · 200 · marcadores: [Nombre]
HU03_C7 = "Material '[Nombre]' actualizado exitosamente"
# c8 · 404 · marcadores: [id_material]
HU03_C8 = "El material solicitado con ID '[id_material]' no fue encontrado en el catálogo"
# c9 · 409
HU03_C9 = (
    "No se pueden modificar materiales en estado INACTIVO. Debe reactivar el material antes de "
    "editar sus propiedades"
)
# c10 · 500
HU03_C10 = "Error interno al actualizar el material. La transacción fue cancelada"

# HU-04 · Inhabilitar material -----------------------------------------------------------
# c2 · 200 · marcadores: [id_material]
HU04_C2 = "Material '[id_material]' inhabilitado exitosamente"
# c3 · 400
HU04_C3 = "La solicitud de inhabilitación contiene parámetros o una estructura no válida"
# c4 · 404 · marcadores: [id_material]
HU04_C4 = "El material solicitado con ID '[id_material]' no fue encontrado en el catálogo"
# c5 · 409
HU04_C5 = (
    "El material no puede inhabilitarse porque pertenece a fórmulas vigentes (en estado Borrador, "
    "Evaluando Patente o Aprobada)"
)
# c6 · 409 · marcadores: [id_material]
HU04_C6 = "El material '[id_material]' ya se encuentra en estado INACTIVO"
# c7 · 500
HU04_C7 = "Error de comunicación con la base de datos al inhabilitar el material. Por favor reintente más tarde"

# HU-05 · Registrar fórmula --------------------------------------------------------------
# c2.1 · 400
HU05_C2_1 = "El campo 'Nombre' es obligatorio. Por favor, ingréselo e intente nuevamente."
# c2.2 · 400
HU05_C2_2 = "El campo 'Aplicación técnica' es obligatorio. Por favor, ingréselo e intente nuevamente."
# c2.3 · 400
HU05_C2_3 = (
    "La fórmula debe estar compuesta por mínimo 2 materiales diferentes. Por favor, agregue los "
    "componentes e intente nuevamente."
)
# c2.4 · 400 · marcadores: [IDMaterial]
HU05_C2_4 = "El campo 'Cantidad' del material '[IDMaterial]' es obligatorio. Por favor, ingréselo e intente nuevamente."
# c3.1 · 400 · marcadores: [IDMaterial], [Cantidad]
HU05_C3_1 = "La cantidad del material '[IDMaterial]' debe ser un número mayor que 0. Valor recibido: [Cantidad]."
# c3.2 · 400 · marcadores: [IDMaterial], [Cantidad]
HU05_C3_2 = (
    "La cantidad del material '[IDMaterial]' admite máximo 6 dígitos enteros y 3 decimales. Valor "
    "recibido: [Cantidad]."
)
# c4.1 · 422 · marcadores: [Lista de Materiales]
HU05_C4_1 = "La fórmula no puede registrarse. Los siguientes componentes no existen: [Lista de Materiales]."
# c4.2 · 422 · marcadores: [Lista de Materiales]
HU05_C4_2 = (
    "La fórmula no puede registrarse. Los siguientes componentes están en estado INACTIVO: [Lista "
    "de Materiales]."
)
# c5 · 422 · marcadores: [NombreMaterial], [Cantidad]
HU05_C5 = (
    "La cantidad del material '[NombreMaterial]' debe ser un número entero, porque su unidad de "
    "medida es Unidad (und). Valor recibido: [Cantidad]."
)
# c6.1 · 409 · marcadores: [NombreIngresado]
HU05_C6_1 = (
    "Ya existe una fórmula registrada con el nombre '[NombreIngresado]'. Indique un nombre único "
    "para la receta."
)
# c6.2 · 201 · marcadores: [Nombre], [form-NNN]
HU05_C6_2 = "Fórmula '[Nombre]' registrada exitosamente en estado BORRADOR con el código [form-NNN]."
# c8 · 500
HU05_C8 = "Error interno de conexión con la base de datos al registrar la fórmula. Por favor, reintente más tarde."

# HU-06 · Consultar fórmulas -------------------------------------------------------------
# c5.1 · 400 · marcadores: [NombreParametro]
HU06_C5_1 = (
    "El valor del parámetro de búsqueda '[NombreParametro]' es inválido. Por favor, verifique el "
    "valor ingresado."
)
# c5.2 · 400 · marcadores: [NombreFiltro]
HU06_C5_2 = "El valor del filtro '[NombreFiltro]' no tiene un formato de fecha válido. Use el formato DD/MM/AAAA."
# c5.3 · 400 · marcadores: [NombreFiltro]
HU06_C5_3 = "En el filtro '[NombreFiltro]', la fecha inicial no puede ser posterior a la fecha final."
# c5.4 · 400 · marcadores: [Estado]
HU06_C5_4 = (
    "El estado '[Estado]' no es válido. Valores permitidos: BORRADOR, EVALUANDO_PATENTE, APROBADA, "
    "RECHAZADA_POR_INFRACCION o DESCONTINUADA."
)
# c5.5 · 400
HU06_C5_5 = "El texto de búsqueda no puede superar los 80 caracteres."
# c6.1 · 200
HU06_C6_1 = "No se encontraron fórmulas que coincidan con los criterios indicados"
# c6.2 · 404 · marcadores: [ID]
HU06_C6_2 = (
    "La fórmula solicitada con ID '[ID]' no fue encontrada en el catálogo. Por favor, verifique el "
    "valor ingresado"
)
# c7 · 500
HU06_C7 = "Error interno de comunicación con la base de datos al consultar las fórmulas. Por favor, reintente más tarde"

# HU-07 · Modificar fórmula --------------------------------------------------------------
# c3.1 · 400
HU07_C3_1 = "El campo nombre es obligatorio, por favor, ingrésalo e intenta nuevamente."
# c3.2 · 400
HU07_C3_2 = "El campo aplicación técnica es obligatorio, por favor, ingrésalo e intenta nuevamente."
# c3.3 · 400
HU07_C3_3 = (
    "La fórmula debe estar compuesta por mínimo 2 materiales diferentes, por favor, agregue los "
    "componentes e intente nuevamente."
)
# c3.4 · 400 · marcadores: [IDMaterial]
HU07_C3_4 = (
    "La cantidad del material '[IDMaterial]' es obligatoria y debe ser un número mayor que 0, por "
    "favor, verifique las cantidades e intente nuevamente."
)
# c3.5 · 400 · marcadores: [IDMaterial]
HU07_C3_5 = (
    "La cantidad del material '[IDMaterial]' admite máximo 6 dígitos enteros y 3 decimales, por "
    "favor, verifique las cantidades e intente nuevamente."
)
# c4 · 422
HU07_C4 = (
    "La fórmula no puede actualizarse porque contiene materiales inactivos o no registrados en el "
    "catálogo. Por favor, reemplace los componentes e intente nuevamente."
)
# c5 · 422 · marcadores: [NombreMaterial]
HU07_C5 = (
    "La cantidad del material '[NombreMaterial]' debe ser un número entero porque su unidad de "
    "medida es Unidad (und), por favor, verifique las cantidades e intente nuevamente."
)
# c6 · 409
HU07_C6 = "La fórmula se encuentra en un estado que no permite modificaciones."
# c7 · 404
HU07_C7 = "La fórmula solicitada no fue encontrada en la base de datos."
# c8 · 200
HU07_C8 = "Fórmula actualizada exitosamente."
# c9 · 500
HU07_C9 = "Error interno de conexión con la base de datos. Por favor reintente más tarde"

# HU-08 · Descontinuar fórmula -----------------------------------------------------------
# c2 · 200
HU08_C2 = "Fórmula descontinuada exitosamente."
# c3 · 400
HU08_C3 = "La solicitud contiene parámetros o un formato no válido. Por favor, verifique e intente nuevamente."
# c4 · 404
HU08_C4 = "La fórmula solicitada no fue encontrada en el catálogo."
# c5 · 409
HU08_C5 = "No es posible descontinuar la fórmula debido a que se encuentra en un estado no permitido."
# c6 · 500
HU08_C6 = "Error interno de conexión con la base de datos. Por favor reintente más tarde"

# HU-09 · Solicitar evaluación de patente ------------------------------------------------
# c1 · 202 · marcadores: [ticketEvaluacionId]
HU09_C1 = "Solicitud enviada al departamento de patentes exitosamente. Ticket asignado: [ticketEvaluacionId]"
# c4 · 409 · marcadores: [EstadoActual]
HU09_C4 = (
    "La fórmula no se encuentra en estado BORRADOR. El estado actual es '[EstadoActual]' y no "
    "permite solicitar evaluación"
)
# c5 · 404
HU09_C5 = "La fórmula solicitada con el identificador de búsqueda no existe en el sistema"
# c6 · 422 · marcadores: [NombreMaterial]
HU09_C6 = (
    "No se puede evaluar la fórmula: el material '[NombreMaterial]' está INACTIVO. Debe actualizar "
    "los componentes de la mezcla"
)
# c7 · 503
HU09_C7 = "Error de comunicación con el servicio del departamento de patentes. Por favor reintente más tarde"

# HU-10 · Recibir el dictamen de patente (callback) --------------------------------------
# c1 · 200
HU10_C1 = "Fórmula aprobada legalmente para producción"
# c2 · 200
HU10_C2 = "Dictamen registrado: Fórmula rechazada por infracción de propiedad intelectual"
# c4.1 · 400
HU10_C4_1 = (
    "El campo 'ticketEvaluacionId' es obligatorio para procesar el dictamen legal, por favor, "
    "verifícalo e intenta nuevamente"
)
# c4.2 · 400
HU10_C4_2 = "El campo 'resultado' es obligatorio y debe contener un valor válido ('SIN_INFRACCION' o 'INFRACCION')"
# c4.3 · 400
HU10_C4_3 = (
    "Si el resultado es 'INFRACCION', el arreglo 'patentesEnConflicto' debe contener al menos un "
    "código de patente asociada"
)
# c4.4 · 400
HU10_C4_4 = "Si el resultado es 'SIN_INFRACCION', el arreglo 'patentesEnConflicto' debe enviarse vacío"
# c4.5 · 400
HU10_C4_5 = (
    "Cada elemento de 'patentesEnConflicto' debe incluir 'conflictoId' (6 dígitos numéricos) y "
    "'titulo' (máximo 60 caracteres)"
)
# c4.6 · 400
HU10_C4_6 = "El arreglo 'patentesEnConflicto' no puede superar los 50 elementos"
# c5 · 404 · marcadores: [id_formula]
HU10_C5 = "La fórmula con ID '[id_formula]' no fue encontrada en el sistema"
# c6.1 · 409
HU10_C6_1 = "Conflicto de trámite: La fórmula no se encuentra en estado EVALUANDO_PATENTE para recibir un dictamen"
# c6.2 · 409
HU10_C6_2 = "Conflicto de trámite: El ticketEvaluacionId proporcionado no corresponde al trámite activo de la fórmula"
# c7 · 500
HU10_C7 = "Error interno del servidor al procesar el dictamen legal. Por favor reintente más tarde"

# HU-11 · Consultar fórmulas aprobadas ---------------------------------------------------
# c4 · 200
HU11_C4 = "No hay fórmulas en estado APROBADA registradas."
# c6.1 · 400
HU11_C6_1 = "El parámetro 'pagina' debe ser un entero mayor o igual a 1."
# c6.2 · 400
HU11_C6_2 = "El parámetro 'tamanoPagina' debe ser un entero entre 1 y 100."
# c9 · 500
HU11_C9 = (
    "Error interno de comunicación con la base de datos al consultar las fórmulas aprobadas. Por "
    "favor, reintente más tarde"
)


# Mensajes genéricos --------------------------------------------------------------------------
# No están en el backlog: los usa el manejador global de excepciones cuando ningún
# criterio define el texto. Propuesta del equipo; confirmar con el PO.

# 400 · cualquier solicitud que no cumple el contrato y no tiene mensaje propio (mismo texto de HU-08 c3).
SOLICITUD_INVALIDA = HU08_C3
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
    guiones (``[Lista de Materiales]``, ``[form-NNN]``), en un diccionario. Lanza
    ``KeyError`` si falta algún valor, para detectar el error en las pruebas.
    """
    datos = {**(valores or {}), **otros}
    faltantes = [m for m in marcadores(plantilla) if m not in datos]
    if faltantes:
        raise KeyError(f"Faltan valores para los marcadores {faltantes}")
    return _MARCADOR.sub(lambda m: str(datos[m.group(1)]), plantilla)
