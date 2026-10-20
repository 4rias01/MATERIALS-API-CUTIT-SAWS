"""HU-03 · PUT /materiales/{id} · prioridad Must · 5 puntos.

Yo como operario de materiales y fórmulas, requiero modificar los datos de un material registrado,
para mantener actualizada la información de los materiales.

Una prueba por criterio de aceptación del product backlog V1.3, pendiente de
implementar. Al implementar un criterio: quitar el ``skip``, escribir la prueba con
el código HTTP y el mensaje esperados (ver tests/unit/test_rutas.py y tests/dobles)
y dejarla pasar.
"""

import pytest

pytestmark = pytest.mark.hu


@pytest.mark.skip(reason="Pendiente: HU-03 criterio 1")
async def test_c01_regla() -> None:
    """Criterio 1:

    Cuando abre la modificación de materiales del módulo Materiales (PUT /materiales/{id}) sobre un
    material en estado ACTIVO, entonces el sistema presenta como campos editables, con sus valores
    actuales, Nombre de tipo texto (letras con o sin tilde, ñ, dígitos, espacios y los símbolos - .
    , / ( ) #), de 3 a 100 caracteres, obligatorio; Categoría de selección única entre "Materia
    Prima", "Componentes" y "Lubricantes", obligatorio; Densidad de tipo numérico, positivo, con
    máximo 4 caracteres, obligatorio; y Pureza de tipo numérico, en escala de 0 a 100 %, con máximo
    3 caracteres, obligatorio; presenta ID, SKU y Unidad de medida solo para lectura; y presenta la
    acción de guardar. Antes de validar y guardar el Nombre, el sistema elimina los espacios al
    inicio y al final y reduce a uno los espacios repetidos entre palabras.
    """
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-03 criterio 2")
async def test_c02_responde_400() -> None:
    """Criterio 2:

    Dado que la solicitud omite un campo obligatorio, contiene datos no válidos o intenta alterar un
    campo de solo lectura, cuando guarda, entonces el sistema rechaza la modificación sin persistir
    cambios y responde 400 Bad Request con el mensaje según la causa:
    2.1. "El campo 'SKU' es de solo lectura y no puede ser modificado".
    2.2. "El campo 'Unidad de medida' es de solo lectura y no puede ser modificado".
    2.3. "El campo nombre es obligatorio, por favor, ingrésalo e intenta nuevamente".
    2.4. "El campo nombre debe tener entre 3 y 100 caracteres" o "El campo nombre contiene
    caracteres no permitidos", según corresponda.
    2.5. "La categoría '[valor]' no es válida. Valores permitidos: Materia Prima, Componentes o
    Lubricantes".
    2.6. "El campo densidad es obligatorio y debe contener un valor numérico positivo".
    2.7. "El campo pureza es obligatorio y debe estar en una escala de 0 a 100%".
    """
    # Mensajes: mensajes.HU03_C2_1, mensajes.HU03_C2_2, mensajes.HU03_C2_3, mensajes.HU03_C2_4_A, mensajes.HU03_C2_4_B, mensajes.HU03_C2_5, mensajes.HU03_C2_6, mensajes.HU03_C2_7
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-03 criterio 3")
async def test_c03_responde_409() -> None:
    """Criterio 3:

    Dado que el nuevo Nombre coincide con el de otro material, sin distinguir mayúsculas de
    minúsculas y después de ajustar los espacios según el criterio 1, cuando guarda, entonces el
    sistema rechaza la modificación sin persistir cambios y responde 409 Conflict con el mensaje "El
    material con el nombre '[Nombre]' ya se encuentra registrado en el catálogo".
    """
    # Mensajes: mensajes.HU03_C3
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-03 criterio 4")
async def test_c04_regla() -> None:
    """Criterio 4:

    Dado que la solicitud no incumple ninguno de los criterios 2 y 3 y el Nombre cambió, cuando
    guarda, entonces el sistema solicita al módulo Inventario la modificación del artículo cuyo
    Código es el SKU del material (PATCH /inventario/articulos/{codigo}), enviando el nuevo Nombre,
    y solo guarda los cambios si Inventario confirma la modificación. Si solo cambian Categoría,
    Densidad o Pureza, el sistema no envía ninguna solicitud a Inventario, porque esos datos no se
    registran allí.
    """
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-03 criterio 5")
async def test_c05_responde_409() -> None:
    """Criterio 5:

    Dado que Inventario rechaza la solicitud del criterio 4 porque ya existe otro artículo de
    cualquier tipo con el mismo Nombre, cuando el sistema recibe la respuesta, entonces no persiste
    cambios y responde 409 Conflict con el mensaje "Inventario ya tiene registrado un artículo con
    el nombre '[Nombre]'. Indique un nombre diferente para el material".
    """
    # Mensajes: mensajes.HU03_C5
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-03 criterio 6")
async def test_c06_responde_503() -> None:
    """Criterio 6:

    Dado que el módulo Inventario no responde, presenta un error interno o tarda más de 5 s en
    responder la solicitud del criterio 4, cuando el sistema procesa la modificación, entonces no
    persiste cambios, registra el error y el traceId en el log del sistema y responde 503 Service
    Unavailable con el mensaje "Error de comunicación con el módulo Inventario al actualizar el
    material. Por favor reintente más tarde" e incluye el traceId.
    """
    # Mensajes: mensajes.HU03_C6
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-03 criterio 7")
async def test_c07_responde_200() -> None:
    """Criterio 7:

    Dado que la solicitud no incumple ninguno de los criterios 2 y 3 y, si el Nombre cambió,
    Inventario confirmó la modificación, cuando guarda, entonces el sistema actualiza los datos del
    material, asigna la fecha y hora actual como fecha de última actualización y responde 200 OK con
    el mensaje "Material '[Nombre]' actualizado exitosamente".
    """
    # Mensajes: mensajes.HU03_C7
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-03 criterio 8")
async def test_c08_responde_404() -> None:
    """Criterio 8:

    Dado que no existe un material con el ID enviado en la ruta, cuando se procesa PUT
    /materiales/{id}, entonces el sistema rechaza la operación y responde 404 Not Found con el
    mensaje "El material solicitado con ID '[id_material]' no fue encontrado en el catálogo".
    """
    # Mensajes: mensajes.HU03_C8
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-03 criterio 9")
async def test_c09_responde_409() -> None:
    """Criterio 9:

    Dado que el material se encuentra en estado INACTIVO, cuando se procesa PUT /materiales/{id},
    entonces el sistema rechaza la actualización y responde 409 Conflict con el mensaje "No se
    pueden modificar materiales en estado INACTIVO. Debe reactivar el material antes de editar sus
    propiedades".
    """
    # Mensajes: mensajes.HU03_C9
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-03 criterio 10")
async def test_c10_responde_500() -> None:
    """Criterio 10:

    Dado que ocurre un fallo de conexión, un error de base de datos o un timeout mayor a 5 segundos
    durante la actualización, cuando el sistema procesa la solicitud, entonces efectúa el rollback
    de la transacción, registra el evento en el log del sistema con un identificador único traceId y
    responde 500 Internal Server Error con el mensaje "Error interno al actualizar el material. La
    transacción fue cancelada".
    """
    # Mensajes: mensajes.HU03_C10
    raise NotImplementedError
