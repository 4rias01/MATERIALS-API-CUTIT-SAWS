"""Casos de uso del catálogo de materiales (HU-01 a HU-04).

Estado: esqueleto. Cada método documenta los pasos que pide el backlog y lanza
``NoImplementadoError`` (501) hasta que se implemente. El router, el DTO, la
inyección de dependencias, el manejo de errores y la auditoría ya funcionan.
"""

from app.business.domain import mensajes
from app.business.services.base import Resultado, ServicioBase, operacion_de_negocio
from app.business.services.comandos import ActualizarMaterialComando, RegistrarMaterialComando
from app.core.events import BusEventos
from app.core.exceptions import NoImplementadoError
from app.core.paginacion import Pagina
from app.data_access.interfaces import IAuditoriaRepository, IInventarioClient, IMaterialRepository, IUnitOfWork
from app.data_access.models import Material

RECURSO = "material"


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
        "REGISTRAR_MATERIAL",
        RECURSO,
        mensaje_error_bd=mensajes.HU01_C8,
        mensaje_servicio_externo=mensajes.HU01_C6,
    )
    async def registrar(self, comando: RegistrarMaterialComando) -> Resultado[Material]:
        """HU-01 · POST /materiales → 201 con el material creado y ``HU01_C7``.

        TODO(HU-01):
        1. Nombre ya normalizado y validado por el schema (c1 y c2); usar
           ``NombreMaterial.crear`` si se necesita el objeto de valor.
        2. ``async with self._uow:`` si ``await self._materiales.existe_nombre(nombre)``
           → ``ConflictoError(formatear(HU01_C3, Nombre=nombre))`` (c3).
        3. Fuera de la transacción (no retener la conexión mientras se espera):
           ``sku = await self._inventario.registrar_materia_prima(nombre, unidad_medida)``
           (c4, se envía sin importar la categoría).
           - ``NombreDuplicadoEnInventarioError`` → ``ConflictoError(formatear(HU01_C5, Nombre=nombre))`` (c5).
           - ``ErrorServicioExterno`` → el decorador responde 503 con ``HU01_C6`` (c6).
        4. ``async with self._uow:``
           - ``id = id_material(await self._materiales.siguiente_numero())`` y ``fecha = ahora()``.
           - Agregar ``Material(id_material=id, sku=sku, ..., estado=EstadoMaterial.ACTIVO,
             fecha_registro=fecha, fecha_actualizacion=fecha)`` (c7.1 a c7.5).
           - ``self._auditar("REGISTRAR_MATERIAL", RECURSO, id, 201, {"sku": sku})``.
           - ``await self._uow.commit()``. Si lanza ``ErrorBaseDatos``: registrar en el log
             el SKU que asignó Inventario (c8) y relanzar; el decorador responde 500 con
             ``HU01_C8``. Si es ``ErrorIntegridadDatos`` con restricción
             ``uq_material_nombre_lower`` (registro simultáneo), responder 409 con ``HU01_C3``.
        5. ``self._publicar(TipoEvento.MATERIAL_REGISTRADO, materialId=id, sku=sku)``.
        6. ``return Resultado(material, formatear(HU01_C7, Nombre=nombre, SKU=sku))``.
        """
        raise NoImplementadoError("HU-01")

    @operacion_de_negocio("CONSULTAR_MATERIAL", RECURSO, mensaje_error_bd=mensajes.HU02_C5, auditar=False)
    async def consultar(self, id_material: str) -> Resultado[Material]:
        """HU-02 · GET /materiales/{id} → 200 con la ficha técnica (9 campos), sin mensaje.

        TODO(HU-02):
        1. ``async with self._uow:`` ``material = await self._materiales.obtener_por_id(id_material)``
           (ACTIVO o INACTIVO, c2).
        2. Si no existe → ``RecursoNoEncontradoError(formatear(HU02_C4, IDIngresado=id_material))`` (c4).
        3. Fallo de BD → el decorador responde 500 con ``HU02_C5`` y reemplaza ``[traceId]`` (c5).
        4. ``return Resultado(material)``.
        """
        raise NoImplementadoError("HU-02")

    @operacion_de_negocio("LISTAR_MATERIALES", RECURSO, mensaje_error_bd=mensajes.HU02_C5, auditar=False)
    async def listar(self, pagina: int, tamano_pagina: int) -> Resultado[Pagina[Material]]:
        """HU-02 c3 · GET /materiales → 200 con la página de materiales.

        TODO(HU-02 c3): el backlog solo menciona el listado para el error de filtros
        (400 con ``HU02_C3``). Definir con el PO los filtros, el tamaño de página y el
        orden antes de implementar. El repositorio ya pagina y ordena por ID.
        """
        raise NoImplementadoError("HU-02")

    @operacion_de_negocio(
        "ACTUALIZAR_MATERIAL",
        RECURSO,
        mensaje_error_bd=mensajes.HU03_C10,
        mensaje_servicio_externo=mensajes.HU03_C6,
        parametro_id="id_material",
    )
    async def actualizar(self, id_material: str, comando: ActualizarMaterialComando) -> Resultado[Material]:
        """HU-03 · PUT /materiales/{id} → 200 con el material y ``HU03_C7``.

        TODO(HU-03):
        1. El schema ya rechazó SKU, Unidad de medida y los datos no válidos (c2).
        2. ``async with self._uow:``
           - ``material = await self._materiales.obtener_por_id(id_material)``; si no existe →
             ``RecursoNoEncontradoError(formatear(HU03_C8, id_material=id_material))`` (c8).
           - Si ``material.estado == EstadoMaterial.INACTIVO`` → ``ConflictoError(HU03_C9)`` (c9).
           - Si ``await self._materiales.existe_nombre(nombre, excluir_id=id_material)`` →
             ``ConflictoError(formatear(HU03_C3, Nombre=nombre))`` (c3).
        3. Si el nombre cambió (comparar sin distinguir mayúsculas lo decide el equipo):
           ``await self._inventario.modificar_nombre_articulo(material.sku, nombre)`` (c4).
           Si solo cambian Categoría, Densidad o Pureza no se llama a Inventario.
           - ``NombreDuplicadoEnInventarioError`` → ``ConflictoError(formatear(HU03_C5, Nombre=nombre))`` (c5).
           - ``ErrorServicioExterno`` → el decorador responde 503 con ``HU03_C6`` (c6).
        4. Actualizar los campos, ``material.fecha_actualizacion = ahora()``, auditar (200) y
           ``commit`` (c7). Fallo de BD → el decorador responde 500 con ``HU03_C10`` (c10).
        5. Publicar ``TipoEvento.MATERIAL_ACTUALIZADO`` y
           ``return Resultado(material, formatear(HU03_C7, Nombre=nombre))``.
        """
        raise NoImplementadoError("HU-03")

    @operacion_de_negocio("INHABILITAR_MATERIAL", RECURSO, mensaje_error_bd=mensajes.HU04_C7, parametro_id="id_material")
    async def inhabilitar(self, id_material: str) -> Resultado[Material]:
        """HU-04 · DELETE /materiales/{id} → 200 con ``HU04_C2`` (borrado lógico).

        TODO(HU-04):
        1. El router ya validó el formato mat-NNN; si no, responde 400 con ``HU04_C3`` (c1 y c3).
        2. ``async with self._uow:``
           - Si no existe → ``RecursoNoEncontradoError(formatear(HU04_C4, id_material=id_material))`` (c4).
           - Si ya está INACTIVO → ``ConflictoError(formatear(HU04_C6, id_material=id_material))`` (c6).
           - Si ``await self._materiales.pertenece_a_formulas_con_estado(id_material, ESTADOS_VIGENTES)``
             → ``ConflictoError(HU04_C5)`` (c5; ``ESTADOS_VIGENTES`` está en formula_states).
           - ``material.estado = EstadoMaterial.INACTIVO``; ``material.fecha_actualizacion = ahora()``;
             auditar (200); ``commit``. No se llama a Inventario (c2).
           Fallo de BD → el decorador responde 500 con ``HU04_C7`` (c7).
        3. Publicar ``TipoEvento.MATERIAL_INHABILITADO`` y
           ``return Resultado(material, formatear(HU04_C2, id_material=id_material))``.
        """
        raise NoImplementadoError("HU-04")
