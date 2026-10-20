"""Casos de uso del catálogo y ciclo de vida de las fórmulas (HU-05 a HU-08 y HU-11).

También es el Domain Service del DAS: verifica a la vez todos los materiales de una
fórmula (existen, están activos y la cantidad es compatible con su unidad).

Estado: esqueleto. Cada método documenta los pasos que pide el backlog y lanza
``NoImplementadoError`` (501) hasta que se implemente.
"""

from app.business.domain import mensajes
from app.business.services.base import Resultado, ServicioBase, operacion_de_negocio
from app.business.services.comandos import ActualizarFormulaComando, ConsultaFormulas, RegistrarFormulaComando
from app.core.events import BusEventos
from app.core.exceptions import NoImplementadoError
from app.core.paginacion import Pagina
from app.data_access.interfaces import IAuditoriaRepository, IFormulaRepository, IMaterialRepository, IUnitOfWork
from app.data_access.models import Formula

RECURSO = "formula"


class FormulaService(ServicioBase):
    def __init__(
        self,
        uow: IUnitOfWork,
        auditoria: IAuditoriaRepository,
        eventos: BusEventos,
        formulas: IFormulaRepository,
        materiales: IMaterialRepository,
        tamano_pagina_listado: int = 10,
    ) -> None:
        super().__init__(uow, auditoria, eventos)
        self._formulas = formulas
        self._materiales = materiales
        self._tamano_pagina_listado = tamano_pagina_listado

    @operacion_de_negocio("REGISTRAR_FORMULA", RECURSO, mensaje_error_bd=mensajes.HU05_C8)
    async def registrar(self, comando: RegistrarFormulaComando) -> Resultado[Formula]:
        """HU-05 · POST /formulas → 201 con la fórmula creada y ``HU05_C6_2``.

        TODO(HU-05):
        1. El schema ya validó obligatorios, mínimo 2 materiales diferentes y el formato de
           cada cantidad (c2 y c3; ``MinimoMaterialesDistintos`` y ``Cantidad``).
        2. ``async with self._uow:``
           - ``materiales = await self._materiales.obtener_por_ids(ids)`` (una sola consulta).
           - IDs que no volvieron → ``ReglaDeNegocioError(formatear(HU05_C4_1, {"Lista de Materiales": ...}))``;
             materiales que no cumplen ``MaterialActivo`` → ``HU05_C4_2`` (c4, 422).
           - Cantidad con decimales de un material en und (``CantidadEnteraSiUnidad``) →
             ``ReglaDeNegocioError(formatear(HU05_C5, NombreMaterial=..., Cantidad=...))`` (c5).
           - Si ``await self._formulas.existe_nombre(nombre)`` →
             ``ConflictoError(formatear(HU05_C6_1, NombreIngresado=nombre))`` (c6.1).
           - ``id = id_formula(await self._formulas.siguiente_numero())``; ``fecha = ahora()``.
           - ``Formula(id_formula=id, ..., version=1, estado=EstadoFormula.BORRADOR,
             fecha_registro=fecha, fecha_actualizacion=fecha)`` con un ``ComponenteFormula`` por
             línea: asignar ``material=<objeto Material>`` (no solo el ID) para poder armar la
             respuesta sin consultar de nuevo (c7).
           - ``self._formulas.agregar(formula)``, auditar (201) y ``commit``.
           Fallo de BD → el decorador responde 500 con ``HU05_C8`` (c8).
        3. Publicar ``TipoEvento.FORMULA_REGISTRADA`` y
           ``return Resultado(formula, formatear(HU05_C6_2, {"Nombre": nombre, "form-NNN": id}))``.
        """
        raise NoImplementadoError("HU-05")

    @operacion_de_negocio("LISTAR_FORMULAS", RECURSO, mensaje_error_bd=mensajes.HU06_C7, auditar=False)
    async def listar(self, consulta: ConsultaFormulas) -> Resultado[Pagina[Formula]]:
        """HU-06 c1, c2 y c6.1 · GET /formulas → 200 con la página de fórmulas.

        TODO(HU-06):
        1. El schema ya validó los parámetros (c5): texto ≤ 80, estado válido, fechas
           DD/MM/AAAA y rangos con inicio ≤ fin.
        2. Convertir las fechas en ``FiltrosBusquedaFormulas`` con rangos [desde, hasta):
           ``hasta`` es el día siguiente a la 00:00. Zona horaria: definir con el PO (ver README).
        3. ``async with self._uow:``
           ``pagina = await self._formulas.buscar(filtros, consulta.pagina, self._tamano_pagina_listado)``
           (orden por fecha de última actualización descendente, páginas de 10; c2).
        4. Sin resultados → ``Resultado(pagina, mensajes.HU06_C6_1)`` (c6.1); si no, ``Resultado(pagina)``.
           Fallo de BD → el decorador responde 500 con ``HU06_C7`` (c7).
        """
        raise NoImplementadoError("HU-06")

    @operacion_de_negocio("CONSULTAR_FORMULA", RECURSO, mensaje_error_bd=mensajes.HU06_C7, auditar=False)
    async def consultar(self, id_formula: str) -> Resultado[Formula]:
        """HU-06 c3, c4 y c6.2 · GET /formulas/{id} → 200 con la ficha técnica.

        TODO(HU-06):
        1. ``async with self._uow:`` ``formula = await self._formulas.obtener_por_id(id_formula)``
           (trae componentes con su material y las evaluaciones con sus patentes).
        2. Si no existe → ``RecursoNoEncontradoError(formatear(HU06_C6_2, ID=id_formula))`` (c6.2).
        3. ``return Resultado(formula)``. El DTO agrega las patentes en conflicto del último
           dictamen solo si el estado es RECHAZADA_POR_INFRACCION (c4).
        """
        raise NoImplementadoError("HU-06")

    @operacion_de_negocio("ACTUALIZAR_FORMULA", RECURSO, mensaje_error_bd=mensajes.HU07_C9, parametro_id="id_formula")
    async def actualizar(self, id_formula: str, comando: ActualizarFormulaComando) -> Resultado[Formula]:
        """HU-07 · PUT /formulas/{id} → 200 con la fórmula y ``HU07_C8``.

        TODO(HU-07):
        1. El schema ya validó obligatorios, mínimo 2 materiales y cantidades (c3).
        2. ``async with self._uow:``
           - Si no existe → ``RecursoNoEncontradoError(HU07_C7)`` (c7).
           - ``estado = estado_formula(formula.estado)``; si no ``estado.admite_modificacion()``
             → ``ConflictoError(HU07_C6)`` (c6: EVALUANDO_PATENTE, APROBADA o DESCONTINUADA).
           - Materiales inexistentes o INACTIVOS → ``ReglaDeNegocioError(HU07_C4)`` (c4).
           - Cantidad con decimales en und → ``ReglaDeNegocioError(formatear(HU07_C5, NombreMaterial=...))`` (c5).
           - Nombre repetido: el backlog no lo define para HU-07 (ver README, "Vacíos del backlog").
           - Reemplazar ``formula.componentes``, actualizar nombre y aplicación técnica,
             ``formula.estado = estado.modificar().nombre`` (BORRADOR),
             ``formula.version = Version(formula.version).siguiente().valor`` y
             ``formula.fecha_actualizacion = ahora()`` (c8); auditar (200); ``commit``.
           Fallo de BD → el decorador responde 500 con ``HU07_C9`` (c9).
        3. Publicar ``TipoEvento.FORMULA_ACTUALIZADA`` y ``return Resultado(formula, mensajes.HU07_C8)``.
        """
        raise NoImplementadoError("HU-07")

    @operacion_de_negocio("DESCONTINUAR_FORMULA", RECURSO, mensaje_error_bd=mensajes.HU08_C6, parametro_id="id_formula")
    async def descontinuar(self, id_formula: str) -> Resultado[Formula]:
        """HU-08 · PATCH /formulas/{id}/descontinuar → 200 con ``HU08_C2``.

        TODO(HU-08):
        1. El router ya validó el formato form-NNN; si no, responde 400 con ``HU08_C3`` (c1 y c3).
        2. ``async with self._uow:``
           - Si no existe → ``RecursoNoEncontradoError(HU08_C4)`` (c4).
           - ``formula.estado = estado_formula(formula.estado).descontinuar().nombre``;
             ``TransicionNoPermitidaError`` → ``ConflictoError(HU08_C5)`` (c5).
           - ``formula.fecha_actualizacion = ahora()``; auditar (200); ``commit`` (c2).
           Fallo de BD → el decorador responde 500 con ``HU08_C6`` (c6).
        3. Publicar ``TipoEvento.FORMULA_DESCONTINUADA`` y ``return Resultado(formula, mensajes.HU08_C2)``.
        """
        raise NoImplementadoError("HU-08")

    @operacion_de_negocio("LISTAR_FORMULAS_APROBADAS", RECURSO, mensaje_error_bd=mensajes.HU11_C9, auditar=False)
    async def listar_aprobadas(self, pagina: int, tamano_pagina: int) -> Resultado[Pagina[Formula]]:
        """HU-11 · GET /formulas/aprobadas → 200 (consulta de solo lectura para Patent Sweep).

        TODO(HU-11):
        1. El schema ya validó ``pagina`` ≥ 1 y ``tamanoPagina`` de 1 a 100 (c1 y c6).
        2. ``async with self._uow:``
           ``resultado = await self._formulas.listar_por_estado(EstadoFormula.APROBADA, pagina, tamano_pagina)``
           (orden por formulaId ascendente, con componentes; c2, c3 y c7). Sin caché: refleja el
           estado actual. No modificar nada (c8).
        3. Si ``resultado.total_registros == 0`` → ``Resultado(resultado, mensajes.HU11_C4)`` (c4).
           Página mayor que el total → lista vacía con los totales reales y sin mensaje (c5).
           Fallo de BD → el decorador responde 500 con ``HU11_C9`` (c9).
        """
        raise NoImplementadoError("HU-11")
