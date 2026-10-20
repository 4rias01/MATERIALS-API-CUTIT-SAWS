"""HU-02 · GET /materiales/{id} · prioridad Must · 5 puntos.

Yo como operario de materiales y fórmulas, requiero consultar las especificaciones de un material
registrado, para verificar sus características físicas y químicas antes de usarlo en una fórmula.

Una prueba por criterio de aceptación del product backlog V1.3, pendiente de
implementar. Al implementar un criterio: quitar el ``skip``, escribir la prueba con
el código HTTP y el mensaje esperados (ver tests/unit/test_rutas.py y tests/dobles)
y dejarla pasar.
"""

import pytest

pytestmark = pytest.mark.hu


@pytest.mark.skip(reason="Pendiente: HU-02 criterio 1")
async def test_c01_regla() -> None:
    """Criterio 1:

    Cuando abre la consulta de materiales del módulo Materiales (GET /materiales/{id}), entonces el
    sistema presenta el campo ID del material de tipo texto, con formato "mat-NNN" (p. ej. mat-101),
    obligatorio; y la acción de consultar.
    """
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-02 criterio 2")
async def test_c02_responde_200() -> None:
    """Criterio 2:

    Dado que el ID corresponde a un material registrado, en estado ACTIVO o INACTIVO, cuando
    consulta, entonces el sistema responde 200 OK con la ficha técnica del material, de solo
    lectura, con los siguientes 9 campos:
    2.1. ID: alfanumérico, formato "mat-NNN".
    2.2. SKU: alfanumérico, igual al Código de artículo que asignó Inventario (formato MP-00000).
    2.3. Nombre: texto.
    2.4. Categoría: alfabético ("Materia Prima", "Componentes" o "Lubricantes").
    2.5. Unidad de medida: und, g, kg, mL, L o m.
    2.6. Densidad: numérico.
    2.7. Pureza: numérico en porcentaje.
    2.8. Fecha de creación: fecha y hora de registro.
    2.9. Estado: "ACTIVO" o "INACTIVO" (los materiales en estado INACTIVO también son consultables).
    """
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-02 criterio 3")
async def test_c03_responde_400() -> None:
    """Criterio 3:

    Dado que la consulta del listado de materiales (GET /materiales) recibe en uno de sus parámetros
    de filtro un valor o tipo de dato no permitido (p. ej. densidad=abc), cuando consulta, entonces
    el sistema no ejecuta la consulta y responde 400 Bad Request con el mensaje "El valor del filtro
    de búsqueda '[NombreParametro]' es inválido. Por favor verifique los valores o tipos de datos
    ingresados."
    """
    # Mensajes: mensajes.HU02_C3
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-02 criterio 4")
async def test_c04_responde_404() -> None:
    """Criterio 4:

    Dado que no existe un material con el ID ingresado (p. ej. GET /materiales/mat-999), cuando
    consulta, entonces el sistema responde 404 Not Found con el mensaje "El material solicitado con
    ID '[IDIngresado]' no fue encontrado en el catálogo".
    """
    # Mensajes: mensajes.HU02_C4
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-02 criterio 5")
async def test_c05_responde_500() -> None:
    """Criterio 5:

    Dado que ocurre un fallo de conexión o un timeout de comunicación en la base de datos durante la
    consulta, cuando el sistema procesa GET /materiales/{id}, entonces registra el evento y el
    traceId en los logs del sistema y responde 500 Internal Server Error con el mensaje "Error de
    comunicación con la base de datos al consultar el material. TraceID: [traceId]".
    """
    # Mensajes: mensajes.HU02_C5
    raise NotImplementedError
