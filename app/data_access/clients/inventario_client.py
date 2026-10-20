"""Cliente de la API de Inventario (célula 4).

El backlog fija las rutas (POST /inventario/materias-primas y PATCH
/inventario/articulos/{codigo}) y qué datos se envían, pero no los nombres de los
campos JSON ni el código HTTP con que Inventario rechaza un nombre repetido. Esos
valores están en las constantes POR ACORDAR de abajo y deben confirmarse con la
célula de Inventario.
"""

from urllib.parse import quote

import httpx

from app.core.config import Configuracion
from app.data_access.clients.base import ClienteHttpBase
from app.data_access.clients.circuit_breaker import CircuitBreaker
from app.data_access.interfaces.inventario_client import IInventarioClient, NombreDuplicadoEnInventarioError

SERVICIO = "inventario"

# --- POR ACORDAR con la célula de Inventario ------------------------------------------
CAMPO_NOMBRE = "nombre"
CAMPO_UNIDAD_MEDIDA = "unidadMedida"
CAMPO_CODIGO_ARTICULO = "codigo"  # en la respuesta del alta: el Código de artículo (MP-00000)
CAMPO_MENSAJE = "mensaje"  # en las respuestas de error
ESTADO_NOMBRE_DUPLICADO = 409  # "Ya existe un artículo con el nombre [Nombre]" (HU-01 c5)
ESTADOS_ALTA_EXITOSA = (200, 201)
ESTADOS_MODIFICACION_EXITOSA = (200, 204)
# ----------------------------------------------------------------------------------------


class InventarioClient(ClienteHttpBase, IInventarioClient):
    def __init__(self, http: httpx.AsyncClient, config: Configuracion, circuito: CircuitBreaker) -> None:
        super().__init__(
            servicio=SERVICIO,
            http=http,
            url_base=config.inventario_url,
            timeout_s=config.http_timeout_s,
            circuito=circuito,
            nombre_origen=config.nombre_servicio,
        )
        self._ruta_materias_primas = config.inventario_ruta_materias_primas
        self._ruta_articulo = config.inventario_ruta_articulo

    async def registrar_materia_prima(self, nombre: str, unidad_medida: str) -> str:
        respuesta = await self._enviar(
            "POST",
            self._ruta_materias_primas,
            json={CAMPO_NOMBRE: nombre, CAMPO_UNIDAD_MEDIDA: unidad_medida},
        )
        if respuesta.status_code == ESTADO_NOMBRE_DUPLICADO:
            raise NombreDuplicadoEnInventarioError(self._json(respuesta).get(CAMPO_MENSAJE))
        if respuesta.status_code not in ESTADOS_ALTA_EXITOSA:
            raise self._respuesta_inesperada(respuesta)
        codigo = self._json(respuesta).get(CAMPO_CODIGO_ARTICULO)
        if not isinstance(codigo, str) or not codigo:
            raise self._respuesta_inesperada(respuesta)
        return codigo

    async def modificar_nombre_articulo(self, codigo: str, nombre: str) -> None:
        respuesta = await self._enviar(
            "PATCH",
            self._ruta_articulo.format(codigo=quote(codigo, safe="")),
            json={CAMPO_NOMBRE: nombre},
        )
        if respuesta.status_code == ESTADO_NOMBRE_DUPLICADO:
            raise NombreDuplicadoEnInventarioError(self._json(respuesta).get(CAMPO_MENSAJE))
        if respuesta.status_code not in ESTADOS_MODIFICACION_EXITOSA:
            raise self._respuesta_inesperada(respuesta)
