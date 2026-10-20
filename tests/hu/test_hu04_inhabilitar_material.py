"""HU-04 · DELETE /materiales/{id} · prioridad Must · 5 puntos.

Yo como operario de materiales y fórmulas, requiero desactivar un material, para evitar que sea
utilizado en futuras formulaciones por estar descontinuado

Una prueba por criterio de aceptación del product backlog V1.3, pendiente de
implementar. Al implementar un criterio: quitar el ``skip``, escribir la prueba con
el código HTTP y el mensaje esperados (ver tests/unit/test_rutas.py y tests/dobles)
y dejarla pasar.
"""

import pytest

pytestmark = pytest.mark.hu


@pytest.mark.skip(reason="Pendiente: HU-04 criterio 1")
async def test_c01_regla() -> None:
    """Criterio 1:

    Cuando recibe una solicitud en el servicio de inhabilitación de materiales del módulo Materiales
    (DELETE /materiales/{id}), entonces el sistema procesa el campo ID del material de tipo texto,
    con formato "mat-NNN", obligatorio, enviado en la ruta.
    """
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-04 criterio 2")
async def test_c02_responde_200() -> None:
    """Criterio 2:

    Dado que el material está en estado ACTIVO y no pertenece a ninguna fórmula en estado BORRADOR,
    EVALUANDO_PATENTE o APROBADA, cuando recibe la solicitud, entonces el sistema realiza un borrado
    lógico cambiando su estado a INACTIVO, no envía ninguna solicitud a Inventario y responde 200 OK
    con el mensaje "Material '[id_material]' inhabilitado exitosamente".
    """
    # Mensajes: mensajes.HU04_C2
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-04 criterio 3")
async def test_c03_responde_400() -> None:
    """Criterio 3:

    Dado que la solicitud contiene una estructura no permitida o parámetros mal formados, cuando el
    sistema valida la sintaxis de la petición DELETE /materiales/{id}, entonces rechaza la solicitud
    y responde 400 Bad Request con el mensaje "La solicitud de inhabilitación contiene parámetros o
    una estructura no válida".
    """
    # Mensajes: mensajes.HU04_C3
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-04 criterio 4")
async def test_c04_responde_404() -> None:
    """Criterio 4:

    Dado que no existe un material con el ID enviado, cuando se procesa DELETE /materiales/{id},
    entonces el sistema rechaza la solicitud y responde 404 Not Found con el mensaje "El material
    solicitado con ID '[id_material]' no fue encontrado en el catálogo".
    """
    # Mensajes: mensajes.HU04_C4
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-04 criterio 5")
async def test_c05_responde_409() -> None:
    """Criterio 5:

    Dado que el material está asociado como componente a al menos una fórmula en estado BORRADOR,
    EVALUANDO_PATENTE o APROBADA, cuando se procesa DELETE /materiales/{id}, entonces el sistema no
    cambia el estado del material y responde 409 Conflict con el mensaje "El material no puede
    inhabilitarse porque pertenece a fórmulas vigentes (en estado Borrador, Evaluando Patente o
    Aprobada)".
    """
    # Mensajes: mensajes.HU04_C5
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-04 criterio 6")
async def test_c06_responde_409() -> None:
    """Criterio 6:

    Dado que el material ya se encuentra en estado INACTIVO, cuando se procesa DELETE
    /materiales/{id}, entonces el sistema rechaza la solicitud y responde 409 Conflict con el
    mensaje "El material '[id_material]' ya se encuentra en estado INACTIVO".
    """
    # Mensajes: mensajes.HU04_C6
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-04 criterio 7")
async def test_c07_responde_500() -> None:
    """Criterio 7:

    Dado que ocurre una falla de conexión, un error de persistencia o un timeout mayor a 5 segundos
    en la base de datos durante la inhabilitación lógica, cuando el sistema procesa la solicitud,
    entonces efectúa el rollback de la transacción manteniendo el estado previo del material,
    registra el evento en el log del sistema con un identificador único traceId y responde 500
    Internal Server Error con el mensaje "Error de comunicación con la base de datos al inhabilitar
    el material. Por favor reintente más tarde".
    """
    # Mensajes: mensajes.HU04_C7
    raise NotImplementedError
