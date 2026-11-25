"""Cliente de la API de Inventario (célula 4).

El alta (POST /inventario/materias-primas, HU-01 c4) sigue el contrato que publica Inventario
en ``/v3/api-docs``: recibe ``nombre`` y ``unidadMedida`` y responde
``{"mensaje": ..., "articulo": {"codigo": "MP-00000", ...}}``. Ese contrato no documenta los
errores ni incluye todavía PATCH /inventario/articulos/{codigo} (HU-03 c4): lo marcado POR
ACORDAR debe confirmarse con la célula de Inventario.
"""

import httpx

from app.core.config import Configuracion
from app.infraestructure.clients.base import ClienteHttpBase
from app.infraestructure.clients.circuit_breaker import CircuitBreaker
from app.infraestructure.interfaces.inventario_client import IInventarioClient, NombreDuplicadoEnInventarioError

SERVICIO = "inventario"

# --- Contrato del alta publicado por Inventario ----------------------------------------
CAMPO_NOMBRE = "nombre"
CAMPO_UNIDAD_MEDIDA = "unidadMedida"
CAMPO_ARTICULO = "articulo"  # en la respuesta del alta: el artículo creado
CAMPO_CODIGO_ARTICULO = "codigo"  # dentro de "articulo": el Código de artículo (MP-00000)

# --- POR ACORDAR con la célula de Inventario ------------------------------------------
CAMPO_MENSAJE = "mensaje"  # en las respuestas de error
ESTADO_NOMBRE_DUPLICADO = 409  # "Ya existe un artículo con el nombre [Nombre]" (HU-01 c5)
ESTADOS_ALTA_EXITOSA = (200, 201)
# HU-03: códigos de éxito del PATCH. POR ACORDAR con la célula de Inventario.
ESTADOS_ACTUALIZACION_EXITOSA = (200, 204)
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
        self._ruta_articulos = config.inventario_ruta_articulos

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
        articulo = self._json(respuesta).get(CAMPO_ARTICULO)
        codigo = articulo.get(CAMPO_CODIGO_ARTICULO) if isinstance(articulo, dict) else None
        if not isinstance(codigo, str) or not codigo:
            raise self._respuesta_inesperada(respuesta)
        return codigo

    async def actualizar_articulo(self, codigo: str, nombre: str) -> None:
        """HU-03 c4: PATCH /inventario/articulos/{codigo} con el nuevo Nombre."""
        respuesta = await self._enviar(
            "PATCH",
            f"{self._ruta_articulos}/{codigo}",
            json={CAMPO_NOMBRE: nombre},
        )
        if respuesta.status_code == ESTADO_NOMBRE_DUPLICADO:
            raise NombreDuplicadoEnInventarioError(self._json(respuesta).get(CAMPO_MENSAJE))
        if respuesta.status_code not in ESTADOS_ACTUALIZACION_EXITOSA:
            raise self._respuesta_inesperada(respuesta)
