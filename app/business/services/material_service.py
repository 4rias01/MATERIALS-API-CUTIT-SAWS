"""Casos de uso del catálogo de materiales.

HU-01 (registrar material) es el flujo de ejemplo del sprint 0: recorre las tres capas
(router → servicio → repositorio y cliente de Inventario) y sirve de modelo para las
siguientes historias de usuario.
"""

import logging

from app.business.domain import mensajes
from app.business.domain.enums import EstadoMaterial
from app.business.domain.errores import ValorInvalidoError
from app.business.domain.eventos import TipoEvento
from app.business.domain.mensajes import formatear
from app.business.domain.value_objects import Sku, id_material, normalizar_nombre
from app.business.services.base import Resultado, ServicioBase, ahora, operacion_de_negocio
from app.business.services.comandos import RegistrarMaterialComando
from app.core.events import BusEventos
from app.core.exceptions import ConflictoError, ErrorBaseDatos, ErrorIntegridadDatos, ErrorServicioExterno
from app.infraestructure.interfaces import (
    IAuditoriaRepository,
    IInventarioClient,
    IMaterialRepository,
    IUnitOfWork,
    NombreDuplicadoEnInventarioError,
)
from app.infraestructure.models import Material

logger = logging.getLogger(__name__)

RECURSO = "material"
OPERACION_REGISTRAR = "REGISTRAR_MATERIAL"
SERVICIO_INVENTARIO = "inventario"
# Índice único lower(nombre) de la tabla material (app/infraestructure/models/material.py).
RESTRICCION_NOMBRE_UNICO = "uq_material_nombre_lower"


class MaterialService(ServicioBase):
    def __init__(
        self,
        uow: IUnitOfWork,
        auditoria: IAuditoriaRepository,
        eventos: BusEventos,
        materiales: IMaterialRepository,
        inventario: IInventarioClient,
    ) -> None:
        super().__init__(uow, auditoria, eventos)
        self._materiales = materiales
        self._inventario = inventario

    @operacion_de_negocio(
        OPERACION_REGISTRAR,
        RECURSO,
        mensaje_error_bd=mensajes.HU01_C8,
        mensaje_servicio_externo=mensajes.HU01_C6,
    )
    async def registrar(self, comando: RegistrarMaterialComando) -> Resultado[Material]:
        """HU-01 · POST /materiales → 201 con el material creado y ``HU01_C7``.

        El schema ya validó los campos y normalizó el nombre (c1 y c2). El decorador
        traduce los fallos técnicos: Inventario caído o lento → 503 con ``HU01_C6`` (c6);
        base de datos caída o lenta → 500 con ``HU01_C8`` (c8). Ambos incluyen el traceId.
        """
        # Idempotente: el schema ya lo hizo, pero el servicio no depende de quién lo llame.
        nombre = normalizar_nombre(comando.nombre)

        await self._verificar_nombre_disponible(nombre)
        # Fuera de la transacción: no se retiene una conexión mientras se espera a Inventario.
        sku = await self._registrar_en_inventario(nombre, comando.unidad_medida)
        material = await self._guardar(comando, nombre, sku)

        self._publicar(TipoEvento.MATERIAL_REGISTRADO, materialId=material.id_material, sku=sku)
        return Resultado(material, formatear(mensajes.HU01_C7, Nombre=nombre, SKU=sku))

    async def _verificar_nombre_disponible(self, nombre: str) -> None:
        """c3: el nombre no se repite en el catálogo, sin distinguir mayúsculas."""
        async with self._uow:
            if await self._materiales.existe_nombre(nombre):
                raise ConflictoError(formatear(mensajes.HU01_C3, Nombre=nombre))

    async def _registrar_en_inventario(self, nombre: str, unidad_medida: str) -> str:
        """c4 y c5: registra la materia prima en Inventario (sin importar la categoría) y
        devuelve el SKU que asignó."""
        try:
            codigo = await self._inventario.registrar_materia_prima(nombre, unidad_medida)
        except NombreDuplicadoEnInventarioError as exc:
            raise ConflictoError(formatear(mensajes.HU01_C5, Nombre=nombre)) from exc
        try:
            return Sku(codigo).valor  # c7.2: formato MP-00000
        except ValorInvalidoError as exc:
            logger.error("Inventario devolvió un Código de artículo con formato inválido", extra={"codigoRecibido": codigo})
            raise ErrorServicioExterno(
                SERVICIO_INVENTARIO, ErrorServicioExterno.RESPUESTA_INESPERADA, detalle=f"codigo={codigo!r}"
            ) from exc

    async def _guardar(self, comando: RegistrarMaterialComando, nombre: str, sku: str) -> Material:
        """c7 y c8: guarda el material en estado ACTIVO; si la base de datos falla, la unidad
        de trabajo revierte y queda en el log el SKU que ya asignó Inventario."""
        try:
            async with self._uow:
                fecha = ahora()
                material = Material(
                    id_material=id_material(await self._materiales.siguiente_numero()),
                    sku=sku,
                    nombre=nombre,
                    categoria=comando.categoria,
                    unidad_medida=comando.unidad_medida,
                    densidad=comando.densidad,
                    pureza=comando.pureza,
                    estado=EstadoMaterial.ACTIVO,
                    fecha_registro=fecha,
                    fecha_actualizacion=fecha,
                )
                self._materiales.agregar(material)
                self._auditar(OPERACION_REGISTRAR, RECURSO, material.id_material, 201, {"sku": sku})
                await self._uow.commit()
        except ErrorIntegridadDatos as exc:
            if exc.restriccion != RESTRICCION_NOMBRE_UNICO:
                self._registrar_fallo_al_guardar(sku, nombre)
                raise
            # Otra petición registró el mismo nombre entre la verificación (c3) y el commit.
            logger.warning("Nombre registrado por una petición simultánea", extra={"sku": sku, "nombre": nombre})
            raise ConflictoError(formatear(mensajes.HU01_C3, Nombre=nombre)) from exc
        except ErrorBaseDatos:
            self._registrar_fallo_al_guardar(sku, nombre)
            raise
        return material

    @staticmethod
    def _registrar_fallo_al_guardar(sku: str, nombre: str) -> None:
        # El traceId lo agrega el formateador del log; el detalle del error lo registra el
        # manejador global de excepciones con el mismo traceId.
        logger.error(
            "No se pudo guardar el material; Inventario ya le asignó el SKU %s",
            sku,
            extra={"sku": sku, "nombre": nombre},
        )
