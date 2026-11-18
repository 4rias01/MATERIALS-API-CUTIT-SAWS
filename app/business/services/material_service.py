"""Casos de uso del CRUD básico de materiales.

Equivale al ``ProfesorService`` del dojo de Java: crear (nombre único), actualizar,
eliminar, listar, obtener por id y buscar por nombre. Cada método recorre las tres
capas (router → servicio → repositorio) y usa la infraestructura del arquetipo:
unidad de trabajo, auditoría de las escrituras y eventos de dominio.
"""

from collections.abc import Sequence

from app.business.domain import mensajes
from app.business.domain.eventos import TipoEvento
from app.business.domain.mensajes import formatear
from app.business.services.base import Resultado, ServicioBase, ahora, operacion_de_negocio
from app.business.services.comandos import DatosMaterial
from app.core.events import BusEventos
from app.core.exceptions import ConflictoError, ErrorIntegridadDatos, RecursoNoEncontradoError
from app.infraestructure.interfaces import IAuditoriaRepository, IMaterialRepository, IUnitOfWork
from app.infraestructure.models import Material
from app.infraestructure.models.material import RESTRICCION_NOMBRE_UNICO

RECURSO = "material"
ERROR_BD = mensajes.MATERIAL_ERROR_BASE_DATOS


class MaterialService(ServicioBase):
    def __init__(
        self,
        uow: IUnitOfWork,
        auditoria: IAuditoriaRepository,
        eventos: BusEventos,
        materiales: IMaterialRepository,
    ) -> None:
        super().__init__(uow, auditoria, eventos)
        self._materiales = materiales

    # --- Escrituras (se auditan) -----------------------------------------------------

    @operacion_de_negocio("CREAR_MATERIAL", RECURSO, mensaje_error_bd=ERROR_BD)
    async def crear(self, datos: DatosMaterial) -> Resultado[Material]:
        """POST /materiales → 201. 409 si el nombre ya existe."""
        try:
            async with self._uow:
                await self._verificar_nombre_disponible(datos.nombre)
                fecha = ahora()
                material = Material(
                    nombre=datos.nombre,
                    categoria=datos.categoria,
                    unidad_medida=datos.unidad_medida,
                    densidad=datos.densidad,
                    pureza=datos.pureza,
                    fecha_registro=fecha,
                    fecha_actualizacion=fecha,
                )
                await self._materiales.agregar(material)
                self._auditar("CREAR_MATERIAL", RECURSO, str(material.id_material), 201)
                await self._uow.commit()
        except ErrorIntegridadDatos as exc:
            # Otra petición guardó el mismo nombre entre la verificación y el commit: el
            # índice único lo rechaza y se responde 409 como en la verificación. Cualquier
            # otra violación es un fallo de base de datos (500).
            if exc.restriccion != RESTRICCION_NOMBRE_UNICO:
                raise
            raise _nombre_duplicado(datos.nombre) from exc
        self._publicar(TipoEvento.MATERIAL_CREADO, materialId=material.id_material)
        return Resultado(material)

    @operacion_de_negocio("ACTUALIZAR_MATERIAL", RECURSO, mensaje_error_bd=ERROR_BD, parametro_id="id_material")
    async def actualizar(self, id_material: int, datos: DatosMaterial) -> Resultado[Material]:
        """PUT /materiales/{id} → 200. 404 si no existe; 409 si el nombre lo usa otro material."""
        try:
            async with self._uow:
                material = await self._obtener_o_404(id_material)
                await self._verificar_nombre_disponible(datos.nombre, excluir_id=id_material)
                material.nombre = datos.nombre
                material.categoria = datos.categoria
                material.unidad_medida = datos.unidad_medida
                material.densidad = datos.densidad
                material.pureza = datos.pureza
                material.fecha_actualizacion = ahora()
                self._auditar("ACTUALIZAR_MATERIAL", RECURSO, str(id_material), 200)
                await self._uow.commit()
        except ErrorIntegridadDatos as exc:
            # Otra petición guardó el mismo nombre entre la verificación y el commit: el
            # índice único lo rechaza y se responde 409 como en la verificación. Cualquier
            # otra violación es un fallo de base de datos (500).
            if exc.restriccion != RESTRICCION_NOMBRE_UNICO:
                raise
            raise _nombre_duplicado(datos.nombre) from exc
        self._publicar(TipoEvento.MATERIAL_ACTUALIZADO, materialId=id_material)
        return Resultado(material)

    @operacion_de_negocio("ELIMINAR_MATERIAL", RECURSO, mensaje_error_bd=ERROR_BD, parametro_id="id_material")
    async def eliminar(self, id_material: int) -> None:
        """DELETE /materiales/{id} → 204. 404 si no existe."""
        async with self._uow:
            material = await self._obtener_o_404(id_material)
            await self._materiales.eliminar(material)
            self._auditar("ELIMINAR_MATERIAL", RECURSO, str(id_material), 204)
            await self._uow.commit()
        self._publicar(TipoEvento.MATERIAL_ELIMINADO, materialId=id_material)

    # --- Consultas (no se auditan) ---------------------------------------------------

    @operacion_de_negocio("LISTAR_MATERIALES", RECURSO, mensaje_error_bd=ERROR_BD, auditar=False)
    async def obtener_todos(self) -> Resultado[Sequence[Material]]:
        """GET /materiales → 200."""
        async with self._uow:
            return Resultado(await self._materiales.listar())

    @operacion_de_negocio("CONSULTAR_MATERIAL", RECURSO, mensaje_error_bd=ERROR_BD, auditar=False)
    async def obtener_por_id(self, id_material: int) -> Resultado[Material]:
        """GET /materiales/{id} → 200. 404 si no existe."""
        async with self._uow:
            return Resultado(await self._obtener_o_404(id_material))

    @operacion_de_negocio("BUSCAR_MATERIALES", RECURSO, mensaje_error_bd=ERROR_BD, auditar=False)
    async def buscar_por_nombre(self, nombre: str) -> Resultado[Sequence[Material]]:
        """GET /materiales/buscar?nombre= → 200 con los que contienen el texto (puede ser vacía)."""
        async with self._uow:
            return Resultado(await self._materiales.buscar_por_nombre(nombre))

    # --- Auxiliares --------------------------------------------------------------------

    async def _obtener_o_404(self, id_material: int) -> Material:
        material = await self._materiales.obtener_por_id(id_material)
        if material is None:
            raise RecursoNoEncontradoError(formatear(mensajes.MATERIAL_NO_ENCONTRADO, id=id_material))
        return material

    async def _verificar_nombre_disponible(self, nombre: str, excluir_id: int | None = None) -> None:
        if await self._materiales.existe_nombre(nombre, excluir_id=excluir_id):
            raise _nombre_duplicado(nombre)


def _nombre_duplicado(nombre: str) -> ConflictoError:
    return ConflictoError(formatear(mensajes.MATERIAL_NOMBRE_DUPLICADO, nombre=nombre))
