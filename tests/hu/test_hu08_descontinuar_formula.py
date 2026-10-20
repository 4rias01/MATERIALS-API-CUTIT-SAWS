"""HU-08 · PATCH /formulas/{id}/descontinuar · prioridad Must · 3 puntos.

Yo como operario de materiales y fórmulas, requiero descontinuar una fórmula, para evitar que el
departamento de Fabricación produzca un producto con una fórmula que ya no está vigente.

Una prueba por criterio de aceptación del product backlog V1.3, pendiente de
implementar. Al implementar un criterio: quitar el ``skip``, escribir la prueba con
el código HTTP y el mensaje esperados (ver tests/unit/test_rutas.py y tests/dobles)
y dejarla pasar.
"""

import pytest

pytestmark = pytest.mark.hu


@pytest.mark.skip(reason="Pendiente: HU-08 criterio 1")
async def test_c01_regla() -> None:
    """Criterio 1:

    Cuando recibe una solicitud en el servicio de descontinuación de fórmulas del módulo Materiales
    (PATCH /formulas/{id}/descontinuar), entonces el sistema procesa el campo ID de la fórmula de
    tipo texto, con formato "form-NNN", obligatorio, enviado en la ruta.
    """
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-08 criterio 2")
async def test_c02_responde_200() -> None:
    """Criterio 2:

    Dado que la fórmula está en estado BORRADOR, APROBADA o RECHAZADA_POR_INFRACCION, cuando recibe
    la solicitud (PATCH /formulas/{id}/descontinuar), entonces el sistema cambia el estado de la
    fórmula a DESCONTINUADA, actualiza la fecha de última actualización y responde 200 OK con el
    mensaje "Fórmula descontinuada exitosamente."
    """
    # Mensajes: mensajes.HU08_C2
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-08 criterio 3")
async def test_c03_responde_400() -> None:
    """Criterio 3:

    Dado que la solicitud contiene una estructura incoherente, parámetros no permitidos o datos
    corruptos, cuando el sistema valida la petición antes de consultar la base de datos, entonces
    rechaza la acción, no realiza cambios y responde 400 Bad Request con el mensaje "La solicitud
    contiene parámetros o un formato no válido. Por favor, verifique e intente nuevamente."
    """
    # Mensajes: mensajes.HU08_C3
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-08 criterio 4")
async def test_c04_responde_404() -> None:
    """Criterio 4:

    Dado que no existe una fórmula con el ID enviado (p. ej. form-999), cuando recibe la solicitud,
    entonces el sistema no efectúa ningún cambio y responde 404 Not Found con el mensaje "La fórmula
    solicitada no fue encontrada en el catálogo."
    """
    # Mensajes: mensajes.HU08_C4
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-08 criterio 5")
async def test_c05_responde_409() -> None:
    """Criterio 5:

    Dado que la fórmula está en estado EVALUANDO_PATENTE o ya está en estado DESCONTINUADA, cuando
    recibe la solicitud, entonces el sistema no modifica la base de datos y responde 409 Conflict
    con el mensaje "No es posible descontinuar la fórmula debido a que se encuentra en un estado no
    permitido."
    """
    # Mensajes: mensajes.HU08_C5
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-08 criterio 6")
async def test_c06_responde_500() -> None:
    """Criterio 6:

    Dado que ocurre un fallo de conexión o un timeout (> 5 s) en la base de datos durante la
    actualización del estado, cuando el sistema procesa la solicitud, entonces cancela la operación
    manteniendo el estado previo de la fórmula, registra el evento en el log del sistema y responde
    500 Internal Server Error con el mensaje "Error interno de conexión con la base de datos. Por
    favor reintente más tarde".
    """
    # Mensajes: mensajes.HU08_C6
    raise NotImplementedError
