"""Cliente de la API de Inventario (célula 4).

El backlog fija la ruta (POST /inventario/materias-primas, HU-01 c4) y qué datos se
envían, pero no los nombres de los campos JSON ni el código HTTP con que Inventario
rechaza un nombre repetido. Esos valores están en las constantes POR ACORDAR de abajo y
deben confirmarse con la célula de Inventario.
"""

import httpx

from app.core.config import Configuracion
from app.infraestructure.clients.base import ClienteHttpBase
from app.infraestructure.clients.circuit_breaker import CircuitBreaker
from app.infraestructure.interfaces.inventario_client import IInventarioClient, NombreDuplicadoEnInventarioError

SERVICIO = "inventario"

# --- POR ACORDAR con la célula de Inventario ------------------------------------------
CAMPO_NOMBRE = "nombre"
CAMPO_UNIDAD_MEDIDA = "unidadMedida"
CAMPO_CODIGO_ARTICULO = "codigo"  # en la respuesta del alta: el Código de artículo (MP-00000)
CAMPO_MENSAJE = "mensaje"  # en las respuestas de error
ESTADO_NOMBRE_DUPLICADO = 409  # "Ya existe un artículo con el nombre [Nombre]" (HU-01 c5)
ESTADOS_ALTA_EXITOSA = (200, 201)
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
