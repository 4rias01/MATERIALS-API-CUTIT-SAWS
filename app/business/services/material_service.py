"""Casos de uso del catálogo de materiales.

* HU-01 (registrar material): POST /materiales. Recorre las tres capas (router →
  servicio → repositorio y cliente de Inventario) y sirve de modelo para las siguientes
  historias de usuario.
* CRUD básico (equivalente al ``ProfesorService`` del dojo de Java): actualizar,
  eliminar, listar, obtener por id y buscar por nombre. Las HU-02 a HU-04 los
  reemplazarán con sus propios criterios.

Cada método usa la infraestructura del arquetipo: unidad de trabajo, auditoría de las
escrituras y eventos de dominio.
"""

import logging
from collections.abc import Sequence

from app.business.domain import mensajes
from app.business.domain.enums import EstadoMaterial
from app.business.domain.errores import ValorInvalidoError
from app.business.domain.eventos import TipoEvento
from app.business.domain.mensajes import formatear
from app.business.domain.value_objects import Sku, normalizar_nombre
from app.business.domain.value_objects import id_material as nuevo_id_material
from app.business.services.base import Resultado, ServicioBase, ahora, operacion_de_negocio
from app.business.services.comandos import ActualizarMaterialComando, RegistrarMaterialComando
from app.core.events import BusEventos
from app.core.exceptions import (
    ConflictoError,
    ErrorBaseDatos,
    ErrorIntegridadDatos,
    ErrorServicioExterno,
    RecursoNoEncontradoError,
)
from app.infraestructure.interfaces import (
    IAuditoriaRepository,
    IInventarioClient,
    IMaterialRepository,
    IUnitOfWork,
    NombreDuplicadoEnInventarioError,
)
from app.infraestructure.interfaces.material_repository import FiltrosMaterial
from app.infraestructure.models import Material
from app.infraestructure.models.material import RESTRICCION_NOMBRE_UNICO

logger = logging.getLogger(__name__)

TAMANO_PAGINA = 10
RECURSO = "material"
OPERACION_REGISTRAR = "REGISTRAR_MATERIAL"
OPERACION_ACTUALIZAR = "ACTUALIZAR_MATERIAL"
SERVICIO_INVENTARIO = "inventario"
ERROR_BD = mensajes.MATERIAL_ERROR_BASE_DATOS


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

    # --- HU-01 · Registrar material --------------------------------------------------

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

        await self._verificar_nombre_no_registrado(nombre)
        # Fuera de la transacción: no se retiene una conexión mientras se espera a Inventario.
        sku = await self._registrar_en_inventario(nombre, comando.unidad_medida)
        material = await self._guardar_registrado(comando, nombre, sku)

        self._publicar(TipoEvento.MATERIAL_REGISTRADO, materialId=material.id_material, sku=sku)
        return Resultado(material, formatear(mensajes.HU01_C7, Nombre=nombre, SKU=sku))

    async def _verificar_nombre_no_registrado(self, nombre: str) -> None:
        """c3: el nombre no se repite en el catálogo, sin distinguir mayúsculas."""
        async with self._uow:
            if await self._materiales.existe_nombre(nombre):
                raise _nombre_ya_registrado(nombre)

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

    async def _guardar_registrado(self, comando: RegistrarMaterialComando, nombre: str, sku: str) -> Material:
        """c7 y c8: guarda el material en estado ACTIVO; si la base de datos falla, la unidad
        de trabajo revierte y queda en el log el SKU que ya asignó Inventario."""
        try:
            async with self._uow:
                fecha = ahora()
                material = Material(
                    id_material=nuevo_id_material(await self._materiales.siguiente_numero()),
                    sku=sku,
                    nombre=nombre,
                    categoria=comando.categoria,
                    unidad_medida=comando.unidad_medida,
                    densidad=comando.densidad,
                    pureza=comando.pureza,
                    estado=EstadoMaterial.ACTIVO.value,
                    fecha_registro=fecha,
                    fecha_actualizacion=fecha,
                )
                await self._materiales.agregar(material)
                self._auditar(OPERACION_REGISTRAR, RECURSO, material.id_material, 201, {"sku": sku})
                await self._uow.commit()
        except ErrorIntegridadDatos as exc:
            if exc.restriccion != RESTRICCION_NOMBRE_UNICO:
                _registrar_fallo_al_guardar(sku, nombre)
                raise
            # Otra petición registró el mismo nombre entre la verificación (c3) y el commit.
            logger.warning("Nombre registrado por una petición simultánea", extra={"sku": sku, "nombre": nombre})
            raise _nombre_ya_registrado(nombre) from exc
        except ErrorBaseDatos:
            _registrar_fallo_al_guardar(sku, nombre)
            raise
        return material

    # --- CRUD básico: escrituras (se auditan) ----------------------------------------



# --- HU-03 · Modificar material --------------------------------------------------

    @operacion_de_negocio(
        OPERACION_ACTUALIZAR,
        RECURSO,
        mensaje_error_bd=mensajes.HU03_C10,
        mensaje_servicio_externo=mensajes.HU03_C6,
        parametro_id="id_material",
    )
    async def actualizar(self, id_material: str, comando: ActualizarMaterialComando) -> Resultado[Material]:
        """HU-03 · PUT /materiales/{id} → 200 con el material actualizado y ``HU03_C7``."""
        nombre = normalizar_nombre(comando.nombre)
        mensaje_404 = formatear(mensajes.HU03_C8, id_material=id_material)   # c8

        # --- Fase 1: validaciones (solo lectura)
        async with self._uow:
            material = await self._obtener_o_404(id_material, mensaje_404)   # c8
            if material.estado != EstadoMaterial.ACTIVO.value:               # c9
                raise ConflictoError(mensajes.HU03_C9)
            if await self._materiales.existe_nombre(nombre, excluir_id=id_material):  # c3
                raise _nombre_duplicado_hu03(nombre)
            sku = material.sku
            nombre_cambio = material.nombre != nombre                        # c4

        # --- Fase 2: sincronización con Inventario (solo si el Nombre cambió)
        if nombre_cambio:
            await self._actualizar_en_inventario(sku, nombre)                # c4/c5/c6

        # --- Fase 3: persistencia atómica
        try:
            async with self._uow:
                material = await self._obtener_o_404(id_material, mensaje_404)   # c8
                if material.estado != EstadoMaterial.ACTIVO.value:               # c9 (concurrencia)
                    raise ConflictoError(mensajes.HU03_C9)
                material.nombre = nombre
                material.categoria = comando.categoria
                material.densidad = comando.densidad
                material.pureza = comando.pureza
                material.fecha_actualizacion = ahora()                           # c7
                self._auditar(OPERACION_ACTUALIZAR, RECURSO, id_material, 200, {"sku": sku})
                await self._uow.commit()
        except ErrorIntegridadDatos as exc:
            if exc.restriccion != RESTRICCION_NOMBRE_UNICO:
                _registrar_fallo_al_actualizar(sku, nombre)
                raise
            logger.warning(
                "Nombre registrado por una petición simultánea; Inventario ya tiene %r para el SKU %s",
                nombre, sku, extra={"sku": sku, "nombre": nombre},
            )
            raise _nombre_duplicado_hu03(nombre) from exc
        except ErrorBaseDatos:
            _registrar_fallo_al_actualizar(sku, nombre)
            raise

        self._publicar(TipoEvento.MATERIAL_ACTUALIZADO, materialId=id_material)
        return Resultado(material, formatear(mensajes.HU03_C7, Nombre=nombre))


    async def _actualizar_en_inventario(self, sku: str, nombre: str) -> None:
        """c4: PATCH /inventario/articulos/{sku} con el nuevo Nombre.

        c5 (nombre duplicado en Inventario) se traduce a ConflictoError; los fallos técnicos
        los traduce el decorador a 503 con ``HU03_C6`` (c6).
        """
        try:
            await self._inventario.actualizar_articulo(sku, nombre)
        except NombreDuplicadoEnInventarioError as exc:
            raise ConflictoError(formatear(mensajes.HU03_C5, Nombre=nombre)) from exc

    @operacion_de_negocio("ELIMINAR_MATERIAL", RECURSO, mensaje_error_bd=ERROR_BD, parametro_id="id_material")
    async def eliminar(self, id_material: str) -> None:
        """DELETE /materiales/{id} → 204. 404 si no existe."""
        async with self._uow:
            material = await self._obtener_o_404(id_material)
            await self._materiales.eliminar(material)
            self._auditar("ELIMINAR_MATERIAL", RECURSO, id_material, 204)
            await self._uow.commit()
        self._publicar(TipoEvento.MATERIAL_ELIMINADO, materialId=id_material)

    # --- CRUD básico: consultas (no se auditan) --------------------------------------

    @operacion_de_negocio("LISTAR_MATERIALES", RECURSO, mensaje_error_bd=mensajes.HU02_C5, auditar=False)
    async def listar(self, filtros: FiltrosMaterial, pagina: int) -> tuple[list[Material], int]:
        async with self._uow:
            return await self._materiales.listar_pagina(filtros, (pagina - 1) * TAMANO_PAGINA, TAMANO_PAGINA)

    @operacion_de_negocio("LISTAR_MATERIALES", RECURSO, mensaje_error_bd=ERROR_BD, auditar=False)
    async def obtener_todos(self) -> Resultado[Sequence[Material]]:
        """GET /materiales → 200."""
        async with self._uow:
            return Resultado(await self._materiales.listar())

    @operacion_de_negocio("CONSULTAR_MATERIAL", RECURSO, mensaje_error_bd=mensajes.HU02_C5, auditar=False)
    async def obtener_por_id(self, id_material: str) -> Resultado[Material]:
        """GET /materiales/{id} → 200. 404 si no existe."""
        async with self._uow:
            material = await self._materiales.obtener_por_id(id_material)
            if material is None:
                raise RecursoNoEncontradoError(formatear(mensajes.HU02_C4, IDIngresado=id_material))
            return Resultado(material)

    @operacion_de_negocio("BUSCAR_MATERIALES", RECURSO, mensaje_error_bd=ERROR_BD, auditar=False)
    async def buscar_por_nombre(self, nombre: str) -> Resultado[Sequence[Material]]:
        """GET /materiales/buscar?nombre= → 200 con los que contienen el texto (puede ser vacía)."""
        async with self._uow:
            return Resultado(await self._materiales.buscar_por_nombre(nombre))

    # --- Auxiliares --------------------------------------------------------------------

    async def _obtener_o_404(self, id_material: str, mensaje: str | None = None) -> Material:
        """Devuelve el material o lanza 404. ``mensaje`` permite que cada HU use su texto
        literal del backlog; si se omite, se usa el genérico del CRUD."""
        material = await self._materiales.obtener_por_id(id_material)
        if material is None:
            raise RecursoNoEncontradoError(
                mensaje or formatear(mensajes.MATERIAL_NO_ENCONTRADO, id=id_material)
            )
        return material


def _nombre_ya_registrado(nombre: str) -> ConflictoError:
    """HU-01 c3."""
    return ConflictoError(formatear(mensajes.HU01_C3, Nombre=nombre))


def _nombre_duplicado_hu03(nombre: str) -> ConflictoError:
    """HU-03 c3."""
    return ConflictoError(formatear(mensajes.HU03_C3, Nombre=nombre))


def _registrar_fallo_al_actualizar(sku: str, nombre: str) -> None:
    # c10: el SKU y el nuevo nombre quedan en el log para reconciliar con Inventario
    # (Inventario ya tiene el nombre nuevo pero Materiales no lo persistió).
    logger.error(
        "No se pudo actualizar el material; Inventario ya tiene el nombre %r para el SKU %s",
        nombre, sku, extra={"sku": sku, "nombre": nombre},
    )


def _registrar_fallo_al_guardar(sku: str, nombre: str) -> None:
    # El traceId lo agrega el formateador del log; el detalle del error lo registra el
    # manejador global de excepciones con el mismo traceId.
    logger.error(
        "No se pudo guardar el material; Inventario ya le asignó el SKU %s",
        sku,
        extra={"sku": sku, "nombre": nombre},
    )
