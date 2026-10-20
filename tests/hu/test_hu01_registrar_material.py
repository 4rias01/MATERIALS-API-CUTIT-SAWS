"""HU-01 · POST /materiales · prioridad Must · 8 puntos.

Yo como operario de materiales y fórmulas, requiero registrar un material nuevo con sus propiedades,
para poder incluirlo como componente en el diseño de fórmulas.

Una prueba por criterio de aceptación del product backlog V1.3, pendiente de
implementar. Al implementar un criterio: quitar el ``skip``, escribir la prueba con
el código HTTP y el mensaje esperados (ver tests/unit/test_rutas.py y tests/dobles)
y dejarla pasar.
"""

import pytest

pytestmark = pytest.mark.hu


@pytest.mark.skip(reason="Pendiente: HU-01 criterio 1")
async def test_c01_regla() -> None:
    """Criterio 1:

    Cuando abre el registro de materiales del módulo Materiales (POST /materiales), entonces el
    sistema presenta los campos Nombre de tipo texto (letras con o sin tilde, ñ, dígitos, espacios y
    los símbolos - . , / ( ) #), de 3 a 100 caracteres, obligatorio; Categoría de selección única
    entre "Materia Prima", "Componentes" y "Lubricantes", obligatorio; Unidad de medida de selección
    única entre Unidad (und), Gramo (g), Kilogramo (kg), Mililitro (mL), Litro (L) y Metro (m),
    obligatorio; Densidad de tipo numérico, positivo, con máximo 4 caracteres, obligatorio; Pureza
    de tipo numérico, en escala de 0 a 100 %, con máximo 3 caracteres, obligatorio; y la acción de
    registrar. Antes de validar y guardar el Nombre, el sistema elimina los espacios al inicio y al
    final y reduce a uno los espacios repetidos entre palabras.
    """
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-01 criterio 2")
async def test_c02_responde_400() -> None:
    """Criterio 2:

    Dado que el registro omite un campo obligatorio o contiene un valor que no cumple lo definido en
    el criterio 1, cuando envía el registro, entonces el sistema rechaza el registro sin persistir
    datos y responde 400 Bad Request con el mensaje según la causa:
    2.1. "El campo 'Nombre' es obligatorio. Por favor, ingréselo e intente nuevamente."
    2.2. "El campo 'Nombre' debe tener entre 3 y 100 caracteres." o "El campo 'Nombre' contiene
    caracteres no permitidos.", según corresponda.
    2.3. "El campo 'Categoría' es obligatorio. Por favor, ingréselo e intente nuevamente." o "La
    Categoría '[valor]' no es válida. Valores permitidos: Materia Prima, Componentes o
    Lubricantes.", según corresponda.
    2.4. "El campo 'Unidad de medida' es obligatorio. Por favor, ingréselo e intente nuevamente." o
    "La Unidad de medida '[valor]' no es válida. Valores permitidos: und, g, kg, mL, L o m.", según
    corresponda.
    2.5. "El campo 'Densidad' es obligatorio. Por favor, ingréselo e intente nuevamente."
    2.6. "El campo 'Pureza' es obligatorio. Por favor, ingréselo e intente nuevamente."
    """
    # Mensajes: mensajes.HU01_C2_1, mensajes.HU01_C2_2_A, mensajes.HU01_C2_2_B, mensajes.HU01_C2_3_A, mensajes.HU01_C2_3_B, mensajes.HU01_C2_4_A, mensajes.HU01_C2_4_B, mensajes.HU01_C2_5, mensajes.HU01_C2_6
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-01 criterio 3")
async def test_c03_responde_409() -> None:
    """Criterio 3:

    Dado que ya existe un material con el mismo Nombre, sin distinguir mayúsculas de minúsculas y
    después de ajustar los espacios según el criterio 1, cuando envía el registro, entonces el
    sistema rechaza el registro sin persistir datos y responde 409 Conflict con el mensaje "El
    material con el nombre '[Nombre]' ya se encuentra registrado en el catálogo."
    """
    # Mensajes: mensajes.HU01_C3
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-01 criterio 4")
async def test_c04_regla() -> None:
    """Criterio 4:

    Dado que los datos no incumplen ninguno de los criterios 2 y 3, cuando envía el registro,
    entonces el sistema solicita al módulo Inventario el registro del material como materia prima
    (POST /inventario/materias-primas), enviando el Nombre y la Unidad de medida, sin importar la
    Categoría del material, para que Inventario lo registre con Tipo "Materia prima", Existencias en
    0 y le asigne su Código de artículo (formato MP-00000).
    """
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-01 criterio 5")
async def test_c05_responde_409() -> None:
    """Criterio 5:

    Dado que Inventario rechaza la solicitud del criterio 4 porque ya existe un artículo de
    cualquier tipo con el mismo Nombre (Inventario responde "Ya existe un artículo con el nombre
    [Nombre]"), cuando el sistema recibe la respuesta, entonces rechaza el registro sin persistir
    datos y responde 409 Conflict con el mensaje "Inventario ya tiene registrado un artículo con el
    nombre '[Nombre]'. Indique un nombre diferente para el material."
    """
    # Mensajes: mensajes.HU01_C5
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-01 criterio 6")
async def test_c06_responde_503() -> None:
    """Criterio 6:

    Dado que el módulo Inventario no responde, presenta un error interno o tarda más de 5 s en
    responder la solicitud del criterio 4, cuando el sistema procesa el registro, entonces no
    persiste el material, registra el error y el traceId en el log del sistema y responde 503
    Service Unavailable con el mensaje "Error de comunicación con el módulo Inventario al registrar
    el material. Por favor reintente más tarde" e incluye el traceId.
    """
    # Mensajes: mensajes.HU01_C6
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-01 criterio 7")
async def test_c07_responde_201() -> None:
    """Criterio 7:

    Dado que Inventario confirma el registro de la materia prima, cuando el sistema guarda el
    material, entonces asigna los siguientes campos y responde 201 Created con el material creado y
    el mensaje "Material '[Nombre]' registrado exitosamente con el SKU [SKU].":
    7.1. ID único: alfanumérico, solo lectura, con formato secuencial "mat-NNN".
    7.2. SKU: alfanumérico, solo lectura, igual al Código de artículo que asignó Inventario (formato
    MP-00000).
    7.3. Estado: alfabético, asignado automáticamente en estado ACTIVO al momento del registro.
    7.4. Fecha de registro: fecha y hora, solo lectura, con el timestamp del servidor al momento de
    crear el material.
    7.5. Fecha de última actualización: fecha y hora, solo lectura. Toma el mismo valor inicial de
    la fecha de registro.
    """
    # Mensajes: mensajes.HU01_C7
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-01 criterio 8")
async def test_c08_responde_500() -> None:
    """Criterio 8:

    Dado que ocurre un fallo de conexión o un timeout (> 5 s) en la BD durante el guardado del
    material, cuando el sistema procesa POST /materiales, entonces efectúa un rollback de la
    transacción, registra el error, el traceId y el SKU que asignó Inventario en el log del sistema
    y responde 500 Internal Server Error con el mensaje "Error interno de conexión con la base de
    datos. Por favor reintente más tarde" e incluye el traceId.
    """
    # Mensajes: mensajes.HU01_C8
    raise NotImplementedError
