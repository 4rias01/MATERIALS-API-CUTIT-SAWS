"""HU-06 · GET /formulas y GET /formulas/{id} · prioridad Must · 8 puntos.

Yo como operario de materiales y fórmulas, requiero consultar una fórmula, para conocer su
composición y en qué punto de la validación se encuentra.

Una prueba por criterio de aceptación del product backlog V1.3, pendiente de
implementar. Al implementar un criterio: quitar el ``skip``, escribir la prueba con
el código HTTP y el mensaje esperados (ver tests/unit/test_rutas.py y tests/dobles)
y dejarla pasar.
"""

import pytest

pytestmark = pytest.mark.hu


@pytest.mark.skip(reason="Pendiente: HU-06 criterio 1")
async def test_c01_regla() -> None:
    """Criterio 1:

    Cuando abre la consulta de fórmulas del módulo Materiales (GET /formulas), entonces el sistema
    presenta los campos Buscar de tipo texto alfanumérico, con longitud máxima de 80 caracteres,
    opcional, que busca coincidencias parciales por Código o Nombre sin distinguir mayúsculas de
    minúsculas; Estado de selección única entre BORRADOR, EVALUANDO_PATENTE, APROBADA,
    RECHAZADA_POR_INFRACCION y DESCONTINUADA, opcional; Fecha de registro desde y Fecha de registro
    hasta de tipo fecha, con formato DD/MM/AAAA, opcionales; Fecha de última actualización desde y
    Fecha de última actualización hasta de tipo fecha, con formato DD/MM/AAAA, opcionales;
    Materiales usados de selección múltiple entre los materiales del catálogo, opcional, que
    devuelve las fórmulas que contienen todos los materiales seleccionados; y la acción de
    consultar. Los filtros se pueden combinar entre sí.
    """
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-06 criterio 2")
async def test_c02_regla() -> None:
    """Criterio 2:

    Dado que hay fórmulas que cumplen la búsqueda y los filtros indicados, cuando consulta, entonces
    el sistema presenta para cada fórmula las columnas Código, Nombre, Aplicación técnica, Estado y
    Fecha de última actualización, ordena el listado por Fecha de última actualización en orden
    descendente (la más reciente primero) y, si hay más de 10 fórmulas, lo presenta en páginas de 10
    registros e indica el número de página actual y el total de páginas.
    """
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-06 criterio 3")
async def test_c03_responde_200() -> None:
    """Criterio 3:

    Dado que se consulta el detalle de una fórmula registrada (GET /formulas/{id}), cuando consulta,
    entonces el sistema responde 200 OK con la ficha técnica de la fórmula, con los campos Código,
    Nombre, Aplicación técnica, Versión, Estado, Fecha de registro, Fecha de última actualización y
    la lista de Componentes con los campos SKU del material, Nombre del material, Cantidad y Unidad
    de medida.
    """
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-06 criterio 4")
async def test_c04_responde_200() -> None:
    """Criterio 4:

    Dado que la fórmula consultada según el criterio 3 está en estado RECHAZADA_POR_INFRACCION,
    cuando consulta, entonces el sistema responde 200 OK con los mismos campos del criterio 3 y,
    adicionalmente, la lista de códigos de las patentes en conflicto. Cada patente muestra su
    identificador de conflicto (conflictoId, 6 dígitos numéricos) y su título (máximo 60
    caracteres), tal como los registró el dictamen de HU-10.
    """
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-06 criterio 5")
async def test_c05_responde_400() -> None:
    """Criterio 5:

    Dado que la búsqueda o los filtros del criterio 1 reciben un parámetro no válido, cuando
    consulta (GET /formulas), entonces el sistema valida los parámetros antes de consultar la BD, no
    ejecuta la consulta y responde 400 Bad Request con el mensaje según la causa:
    5.1. "El valor del parámetro de búsqueda '[NombreParametro]' es inválido. Por favor, verifique
    el valor ingresado."
    5.2. "El valor del filtro '[NombreFiltro]' no tiene un formato de fecha válido. Use el formato
    DD/MM/AAAA."
    5.3. "En el filtro '[NombreFiltro]', la fecha inicial no puede ser posterior a la fecha final."
    5.4. "El estado '[Estado]' no es válido. Valores permitidos: BORRADOR, EVALUANDO_PATENTE,
    APROBADA, RECHAZADA_POR_INFRACCION o DESCONTINUADA."
    5.5. "El texto de búsqueda no puede superar los 80 caracteres."
    """
    # Mensajes: mensajes.HU06_C5_1, mensajes.HU06_C5_2, mensajes.HU06_C5_3, mensajes.HU06_C5_4, mensajes.HU06_C5_5
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-06 criterio 6")
async def test_c06_responde_200_404() -> None:
    """Criterio 6:

    Dado que no existen fórmulas que cumplan la consulta o el ID solicitado, cuando consulta,
    entonces el sistema responde según la causa:
    6.1. Búsqueda o filtros sin resultados (GET /formulas): responde 200 OK con una lista vacía y el
    mensaje "No se encontraron fórmulas que coincidan con los criterios indicados".
    6.2. ID inexistente (GET /formulas/{id}): responde 404 Not Found con el mensaje "La fórmula
    solicitada con ID '[ID]' no fue encontrada en el catálogo. Por favor, verifique el valor
    ingresado".
    """
    # Mensajes: mensajes.HU06_C6_1, mensajes.HU06_C6_2
    raise NotImplementedError


@pytest.mark.skip(reason="Pendiente: HU-06 criterio 7")
async def test_c07_responde_500() -> None:
    """Criterio 7:

    Dado que ocurre un error de lectura o un timeout (> 5 s) en la BD durante la consulta del
    listado, del detalle o de los componentes de una fórmula, cuando el sistema atiende GET
    /formulas o GET /formulas/{id}, entonces registra el error en el log del sistema y responde 500
    Internal Server Error con el mensaje "Error interno de comunicación con la base de datos al
    consultar las fórmulas. Por favor, reintente más tarde" e incluye el traceId.
    """
    # Mensajes: mensajes.HU06_C7
    raise NotImplementedError
