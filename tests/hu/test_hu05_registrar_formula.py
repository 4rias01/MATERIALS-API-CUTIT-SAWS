"""HU-05 · POST /formulas · prioridad Must · 13 puntos.

Yo como operario de materiales y fórmulas, requiero registrar una nueva fórmula, para que sea usada
en la fabricación de las cuchillas

Una prueba por criterio de aceptación del product backlog V1.3, pendiente de
implementar. Al implementar un criterio: quitar el ``skip``, escribir la prueba con
el código HTTP y el mensaje esperados (ver tests/unit/test_rutas.py y tests/dobles)
y dejarla pasar.
"""

import pytest

pytestmark = pytest.mark.hu


@pytest.mark.skip(reason="Pendiente: HU-05 criterio 1")
async def test_c01_regla() -> None:
    """Criterio 1:

    Cuando abre el registro de fórmulas del módulo Materiales (POST /formulas), entonces el sistema
    presenta los campos Nombre de tipo texto alfabético, con longitud máxima de 80 caracteres,
    obligatorio; Aplicación técnica de tipo texto alfanumérico, con longitud máxima de 200
    caracteres, obligatorio, que describe el uso técnico previsto de la fórmula en la fabricación de
    las cuchillas; una tabla de Componentes, obligatoria, en la que cada línea tiene los campos ID
    del material de tipo texto, con formato "mat-NNN", obligatorio, Cantidad de tipo numérico, mayor
    que 0, con máximo 6 dígitos enteros y 3 decimales, obligatorio, que indica cuánto se usa del
    material para fabricar una cuchilla, y Unidad de medida, de solo lectura, que el sistema toma
    del material registrado (und, g, kg, mL, L o m); y la acción de registrar. La tabla de
    Componentes debe tener mínimo 2 materiales diferentes. Si la Unidad de medida del material es
    Unidad (und), la Cantidad debe ser un número entero.
    """
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-05 criterio 2")
async def test_c02_responde_400() -> None:
    """Criterio 2:

    Dado que el registro omite un campo obligatorio, cuando envía el registro, entonces el sistema
    rechaza el registro sin persistir datos y responde 400 Bad Request con el mensaje según la
    causa:
    2.1. "El campo 'Nombre' es obligatorio. Por favor, ingréselo e intente nuevamente."
    2.2. "El campo 'Aplicación técnica' es obligatorio. Por favor, ingréselo e intente nuevamente."
    2.3. "La fórmula debe estar compuesta por mínimo 2 materiales diferentes. Por favor, agregue los
    componentes e intente nuevamente."
    2.4. "El campo 'Cantidad' del material '[IDMaterial]' es obligatorio. Por favor, ingréselo e
    intente nuevamente."
    """
    # Mensajes: mensajes.HU05_C2_1, mensajes.HU05_C2_2, mensajes.HU05_C2_3, mensajes.HU05_C2_4
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-05 criterio 3")
async def test_c03_responde_400() -> None:
    """Criterio 3:

    Dado que el registro tiene los campos obligatorios y la Cantidad de uno o más componentes no
    cumple el formato definido en el criterio 1, cuando envía el registro, entonces el sistema
    rechaza el registro sin persistir datos y responde 400 Bad Request con el mensaje según la
    causa:
    3.1. "La cantidad del material '[IDMaterial]' debe ser un número mayor que 0. Valor recibido:
    [Cantidad]."
    3.2. "La cantidad del material '[IDMaterial]' admite máximo 6 dígitos enteros y 3 decimales.
    Valor recibido: [Cantidad]."
    """
    # Mensajes: mensajes.HU05_C3_1, mensajes.HU05_C3_2
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-05 criterio 4")
async def test_c04_responde_422() -> None:
    """Criterio 4:

    Dado que uno o más componentes no existen en la BD o están en estado INACTIVO, cuando envía el
    registro, entonces el sistema rechaza el registro sin persistir datos y responde 422
    Unprocessable Entity con el mensaje según la causa:
    4.1. "La fórmula no puede registrarse. Los siguientes componentes no existen: [Lista de
    Materiales]."
    4.2. "La fórmula no puede registrarse. Los siguientes componentes están en estado INACTIVO:
    [Lista de Materiales]."
    """
    # Mensajes: mensajes.HU05_C4_1, mensajes.HU05_C4_2
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-05 criterio 5")
async def test_c05_responde_422() -> None:
    """Criterio 5:

    Dado que todos los componentes existen y están en estado ACTIVO, y la Cantidad de un material
    cuya Unidad de medida es Unidad (und) contiene decimales, cuando envía el registro, entonces el
    sistema rechaza el registro sin persistir datos y responde 422 Unprocessable Entity con el
    mensaje "La cantidad del material '[NombreMaterial]' debe ser un número entero, porque su unidad
    de medida es Unidad (und). Valor recibido: [Cantidad]."
    """
    # Mensajes: mensajes.HU05_C5
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-05 criterio 6")
async def test_c06_responde_409_201() -> None:
    """Criterio 6:

    Dado que los datos no incumplen ninguno de los criterios 2 a 5, cuando envía el registro,
    entonces el sistema valida si ya existe una fórmula con el mismo nombre:
    6.1. Si existe, rechaza el registro y responde 409 Conflict con el mensaje "Ya existe una
    fórmula registrada con el nombre '[NombreIngresado]'. Indique un nombre único para la receta."
    6.2. Si no existe, crea la fórmula y responde 201 Created con el mensaje "Fórmula '[Nombre]'
    registrada exitosamente en estado BORRADOR con el código [form-NNN]."
    """
    # Mensajes: mensajes.HU05_C6_1, mensajes.HU05_C6_2
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-05 criterio 7")
async def test_c07_regla() -> None:
    """Criterio 7:

    Dado que se crea una fórmula según el subcriterio 6.2, cuando el sistema la guarda, entonces
    autogenera los siguientes campos:
    7.1. Código: alfanumérico, solo lectura, con el formato secuencial "form-NNN".
    7.2. Estado: alfabético, con uno de estos valores: BORRADOR, EVALUANDO_PATENTE, APROBADA,
    RECHAZADA_POR_INFRACCION o DESCONTINUADA. Al crear la fórmula el valor es BORRADOR; los demás
    estados solo cambian mediante peticiones a la API (evaluación de patente, descontinuación).
    7.3. Versión: contador numérico con valor inicial 1, que aumenta en 1 cada vez que se actualiza
    la fórmula.
    7.4. Fecha de registro: fecha y hora, solo lectura, con la fecha y hora del servidor al momento
    de crear la fórmula. No cambia después.
    7.5. Fecha de última actualización: fecha y hora, solo lectura. Al crear la fórmula toma el
    mismo valor de la fecha de registro y se actualiza cada vez que se modifica la fórmula o cambia
    su estado.
    """
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-05 criterio 8")
async def test_c08_responde_500() -> None:
    """Criterio 8:

    Dado que ocurre un fallo de conexión o un timeout (> 5 s) en la BD durante el guardado de la
    fórmula, cuando el sistema procesa POST /formulas, entonces efectúa un rollback de la
    transacción, registra el error en el log del sistema y responde 500 Internal Server Error con el
    mensaje "Error interno de conexión con la base de datos al registrar la fórmula. Por favor,
    reintente más tarde."
    """
    # Mensajes: mensajes.HU05_C8
    raise NotImplementedError
