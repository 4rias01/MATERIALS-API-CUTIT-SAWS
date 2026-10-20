"""HU-07 · PUT /formulas/{id} · prioridad Must · 8 puntos.

Yo como operario de materiales y fórmulas, requiero modificar los componentes de una fórmula
existente, para corregirla o mejorarla antes de su uso en producción

Una prueba por criterio de aceptación del product backlog V1.3, pendiente de
implementar. Al implementar un criterio: quitar el ``skip``, escribir la prueba con
el código HTTP y el mensaje esperados (ver tests/unit/test_rutas.py y tests/dobles)
y dejarla pasar.
"""

import pytest

pytestmark = pytest.mark.hu


@pytest.mark.skip(reason="Pendiente: HU-07 criterio 1")
async def test_c01_regla() -> None:
    """Criterio 1:

    Cuando abre la modificación de fórmulas del módulo Materiales (PUT /formulas/{id}) sobre una
    fórmula en estado BORRADOR o RECHAZADA_POR_INFRACCION, entonces el sistema carga la información
    actual de la fórmula para su modificación.
    """
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-07 criterio 2")
async def test_c02_regla() -> None:
    """Criterio 2:

    Dado que la fórmula se puede modificar según el criterio 1, cuando se carga su información,
    entonces el sistema presenta como campos editables, con sus valores actuales, Nombre de tipo
    texto alfabético, con longitud máxima de 80 caracteres, obligatorio; Aplicación técnica de tipo
    texto alfanumérico, con longitud máxima de 200 caracteres, obligatorio; y la tabla de
    Componentes, con mínimo 2 materiales diferentes, en la que cada línea tiene los campos ID del
    material de tipo texto, con formato "mat-NNN", obligatorio, Cantidad de tipo numérico, mayor que
    0, con máximo 6 dígitos enteros y 3 decimales, obligatorio, que indica cuánto se usa del
    material para fabricar una cuchilla, y Unidad de medida, de solo lectura, que el sistema toma
    del material registrado (und, g, kg, mL, L o m); presenta el Código (form-NNN) solo para
    lectura; y presenta la acción de guardar. Si la Unidad de medida del material es Unidad (und),
    la Cantidad debe ser un número entero.
    """
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-07 criterio 3")
async def test_c03_responde_400() -> None:
    """Criterio 3:

    Dado que se omite un campo obligatorio o los valores no cumplen las reglas del criterio 2,
    cuando guarda, entonces el sistema rechaza la actualización sin persistir cambios y responde 400
    Bad Request con el mensaje según la causa:
    3.1. "El campo nombre es obligatorio, por favor, ingrésalo e intenta nuevamente."
    3.2. "El campo aplicación técnica es obligatorio, por favor, ingrésalo e intenta nuevamente."
    3.3. "La fórmula debe estar compuesta por mínimo 2 materiales diferentes, por favor, agregue los
    componentes e intente nuevamente."
    3.4. "La cantidad del material '[IDMaterial]' es obligatoria y debe ser un número mayor que 0,
    por favor, verifique las cantidades e intente nuevamente."
    3.5. "La cantidad del material '[IDMaterial]' admite máximo 6 dígitos enteros y 3 decimales, por
    favor, verifique las cantidades e intente nuevamente."
    """
    # Mensajes: mensajes.HU07_C3_1, mensajes.HU07_C3_2, mensajes.HU07_C3_3, mensajes.HU07_C3_4, mensajes.HU07_C3_5
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-07 criterio 4")
async def test_c04_responde_422() -> None:
    """Criterio 4:

    Dado que la actualización incluye al menos un material que no existe en el catálogo o que está
    en estado INACTIVO, cuando guarda, entonces el sistema no modifica la información y responde 422
    Unprocessable Entity con el mensaje "La fórmula no puede actualizarse porque contiene materiales
    inactivos o no registrados en el catálogo. Por favor, reemplace los componentes e intente
    nuevamente."
    """
    # Mensajes: mensajes.HU07_C4
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-07 criterio 5")
async def test_c05_responde_422() -> None:
    """Criterio 5:

    Dado que todos los materiales existen y están en estado ACTIVO, y la Cantidad de un material
    cuya Unidad de medida es Unidad (und) contiene decimales, cuando guarda, entonces el sistema no
    modifica la información y responde 422 Unprocessable Entity con el mensaje "La cantidad del
    material '[NombreMaterial]' debe ser un número entero porque su unidad de medida es Unidad
    (und), por favor, verifique las cantidades e intente nuevamente."
    """
    # Mensajes: mensajes.HU07_C5
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-07 criterio 6")
async def test_c06_responde_409() -> None:
    """Criterio 6:

    Dado que la fórmula está en estado EVALUANDO_PATENTE, APROBADA o DESCONTINUADA, cuando abre la
    modificación o guarda, entonces el sistema bloquea la operación y responde 409 Conflict con el
    mensaje "La fórmula se encuentra en un estado que no permite modificaciones."
    """
    # Mensajes: mensajes.HU07_C6
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-07 criterio 7")
async def test_c07_responde_404() -> None:
    """Criterio 7:

    Dado que no existe una fórmula con el ID enviado (p. ej. form-999), cuando se procesa PUT
    /formulas/{id}, entonces el sistema no realiza ningún cambio y responde 404 Not Found con el
    mensaje "La fórmula solicitada no fue encontrada en la base de datos."
    """
    # Mensajes: mensajes.HU07_C7
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-07 criterio 8")
async def test_c08_responde_200() -> None:
    """Criterio 8:

    Dado que los datos no incumplen ninguno de los criterios 3 a 7, cuando guarda, entonces el
    sistema actualiza la fórmula, incrementa la versión en 1, asigna o mantiene el estado BORRADOR,
    actualiza la fecha de última actualización y responde 200 OK con el mensaje "Fórmula actualizada
    exitosamente."
    """
    # Mensajes: mensajes.HU07_C8
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-07 criterio 9")
async def test_c09_responde_500() -> None:
    """Criterio 9:

    Dado que ocurre un fallo de conexión o un timeout (> 5 s) con la base de datos durante el
    guardado de los cambios, cuando el sistema procesa la solicitud, entonces efectúa un rollback de
    la transacción, registra el evento en el log del sistema y responde 500 Internal Server Error
    con el mensaje "Error interno de conexión con la base de datos. Por favor reintente más tarde".
    """
    # Mensajes: mensajes.HU07_C9
    raise NotImplementedError
