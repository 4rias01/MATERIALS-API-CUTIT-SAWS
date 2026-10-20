"""HU-09 · POST /formulas/{id}/evaluacion-patente · prioridad Must · 5 puntos.

Yo como operario de materiales y fórmulas, requiero solicitar la verificación legal de la
composición de una fórmula, para garantizar que la mezcla no infrinja propiedad intelectual antes de
ser aprobada para fabricación

Una prueba por criterio de aceptación del product backlog V1.3, pendiente de
implementar. Al implementar un criterio: quitar el ``skip``, escribir la prueba con
el código HTTP y el mensaje esperados (ver tests/unit/test_rutas.py y tests/dobles)
y dejarla pasar.
"""

import pytest

pytestmark = pytest.mark.hu


@pytest.mark.skip(reason="Pendiente: HU-09 criterio 1")
async def test_c01_responde_202() -> None:
    """Criterio 1:

    Dado que la fórmula está en estado BORRADOR y todos sus materiales componentes están en estado
    ACTIVO, cuando recibe una solicitud en el servicio de evaluación de patentes del módulo
    Materiales (POST /formulas/{id}/evaluacion-patente), entonces el sistema invoca al servicio
    externo del departamento de patentes, cambia el estado de la fórmula a EVALUANDO_PATENTE, genera
    un código único de ticket de evaluación (ticketEvaluacionId), alfanumérico con formato 'tck-NNN'
    (p. ej. 'tck-001'), y responde 202 Accepted con el mensaje "Solicitud enviada al departamento de
    patentes exitosamente. Ticket asignado: [ticketEvaluacionId]".
    """
    # Mensajes: mensajes.HU09_C1
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-09 criterio 2")
async def test_c02_regla() -> None:
    """Criterio 2:

    Dado que la fórmula pasó a revisión, cuando se envió la solicitud al departamento de patentes,
    entonces se envía un  JSON que contiene:
    2.1. formulaId: alfanumérico, formato "form-NNN", obligatorio.
    2.2. ticketEvaluacionId: alfanumérico, formato "tck-NNN", obligatorio.
    2.3. nombre: alfabético, máximo 80 caracteres, obligatorio.
    2.4. aplicacionTecnica: alfanumérico, máximo 200 caracteres, obligatorio.
    2.5. componentes: arreglo de mínimo 2 elementos, obligatorio; cada uno con materialId ("mat-
    NNN"), nombre (máximo 100 caracteres), cantidad (número mayor que 0, con máximo 6 dígitos
    enteros y 3 decimales; entero si la unidad es und) y unidadMedida (und, g, kg, mL, L o m).
    """
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-09 criterio 3")
async def test_c03_responde_202() -> None:
    """Criterio 3:

    Dado que el departamento de patentes recibe la solicitud, cuando responde 202 Accepted, entonces
    ese código significa que Patent Sweep aceptó la solicitud y aún no emite dictamen. La fórmula
    permanece en EVALUANDO_PATENTE hasta que Patent Sweep envíe el dictamen a POST
    /formulas/{id}/dictamen-patente.
    """
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-09 criterio 4")
async def test_c04_responde_409() -> None:
    """Criterio 4:

    Dado que la fórmula está en un estado diferente a BORRADOR (como EVALUANDO_PATENTE, APROBADA o
    DESCONTINUADA), cuando recibe la solicitud, entonces el sistema la rechaza y responde 409
    Conflict con el mensaje "La fórmula no se encuentra en estado BORRADOR. El estado actual es
    '[EstadoActual]' y no permite solicitar evaluación".
    """
    # Mensajes: mensajes.HU09_C4
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-09 criterio 5")
async def test_c05_responde_404() -> None:
    """Criterio 5:

    Dado que no existe una fórmula con el ID enviado, cuando recibe la solicitud, entonces el
    sistema responde 404 Not Found con el mensaje "La fórmula solicitada con el identificador de
    búsqueda no existe en el sistema".
    """
    # Mensajes: mensajes.HU09_C5
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-09 criterio 6")
async def test_c06_responde_422() -> None:
    """Criterio 6:

    Dado que la fórmula contiene al menos un material en estado INACTIVO, cuando recibe la
    solicitud, entonces el sistema no invoca al servicio externo del departamento de patentes,
    mantiene la fórmula en estado BORRADOR y responde 422 Unprocessable Entity con el mensaje "No se
    puede evaluar la fórmula: el material '[NombreMaterial]' está INACTIVO. Debe actualizar los
    componentes de la mezcla".
    """
    # Mensajes: mensajes.HU09_C6
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-09 criterio 7")
async def test_c07_responde_503() -> None:
    """Criterio 7:

    Dado que el servicio externo del departamento de patentes presenta una falla de conexión, un
    tiempo de espera agotado (timeout mayor a 5 segundos) o un error interno, cuando el sistema le
    envía la solicitud, entonces deshace la transacción manteniendo la fórmula en estado BORRADOR,
    registra el fallo técnico con su código de rastreo (traceId) en los registros de auditoría del
    servidor y responde 503 Service Unavailable con el mensaje "Error de comunicación con el
    servicio del departamento de patentes. Por favor reintente más tarde".
    """
    # Mensajes: mensajes.HU09_C7
    raise NotImplementedError
