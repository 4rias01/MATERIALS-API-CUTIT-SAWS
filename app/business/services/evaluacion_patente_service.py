"""Casos de uso de la integración con Patent Sweep (HU-09 y HU-10).

Request-reply asíncrono con callback: la solicitud se envía con timeout de 5 s y la API
responde 202 con el ticketEvaluacionId; el dictamen llega después a
POST /formulas/{id}/dictamen-patente.

Estado: esqueleto. Cada método documenta los pasos que pide el backlog y lanza
``NoImplementadoError`` (501) hasta que se implemente.
"""

from dataclasses import dataclass

from app.business.domain import mensajes
from app.business.services.base import Resultado, ServicioBase, operacion_de_negocio
from app.business.services.comandos import RegistrarDictamenComando
from app.core.events import BusEventos
from app.core.exceptions import NoImplementadoError
from app.data_access.interfaces import IAuditoriaRepository, IFormulaRepository, IPatentSweepClient, IUnitOfWork

RECURSO = "formula"


@dataclass(frozen=True, slots=True)
class TramiteEvaluacion:
    """Respuesta de HU-09 y HU-10: la fórmula, el ticket y el estado resultante."""

    formula_id: str
    ticket_evaluacion_id: str
    estado: str


class EvaluacionPatenteService(ServicioBase):
    def __init__(
        self,
        uow: IUnitOfWork,
        auditoria: IAuditoriaRepository,
        eventos: BusEventos,
        formulas: IFormulaRepository,
        patent_sweep: IPatentSweepClient,
    ) -> None:
        super().__init__(uow, auditoria, eventos)
        self._formulas = formulas
        self._patent_sweep = patent_sweep

    @operacion_de_negocio(
        "SOLICITAR_EVALUACION_PATENTE",
        RECURSO,
        mensaje_error_bd=mensajes.ERROR_INTERNO,  # el backlog no define el 500 de HU-09
        mensaje_servicio_externo=mensajes.HU09_C7,
        parametro_id="id_formula",
    )
    async def solicitar(self, id_formula: str) -> Resultado[TramiteEvaluacion]:
        """HU-09 · POST /formulas/{id}/evaluacion-patente → 202 con ``HU09_C1``.

        TODO(HU-09):
        1. ``async with self._uow:``
           - Si no existe → ``RecursoNoEncontradoError(HU09_C5)`` (c5).
           - Si no ``estado_formula(formula.estado).admite_solicitud_evaluacion()`` →
             ``ConflictoError(formatear(HU09_C4, EstadoActual=formula.estado))`` (c4).
           - Primer componente cuyo material no cumple ``MaterialActivo`` →
             ``ReglaDeNegocioError(formatear(HU09_C6, NombreMaterial=...))`` sin llamar a
             Patent Sweep; la fórmula sigue en BORRADOR (c6).
           - ``ticket = id_ticket_evaluacion(await self._formulas.siguiente_numero_ticket())``.
           - Cambiar a EVALUANDO_PATENTE con ``estado.solicitar_evaluacion()``, agregar
             ``EvaluacionPatente(ticket_evaluacion_id=ticket, fecha_solicitud=ahora())`` a
             ``formula.evaluaciones`` y actualizar ``fecha_actualizacion``.
           - ``await self._patent_sweep.solicitar_evaluacion(SolicitudEvaluacionPatente(...))``
             con los campos de c2. Si falla, al salir del bloque sin commit se revierte todo y
             la fórmula queda en BORRADOR; el decorador responde 503 con ``HU09_C7`` y lo
             registra en la auditoría con el traceId (c7).
           - Auditar (202) y ``commit`` (c1 y c3).
           Decisión del equipo: si el commit falla después de que Patent Sweep aceptó, el
           dictamen llegará con un ticket desconocido (HU-10 c6 lo rechaza con 409).
        2. Publicar ``TipoEvento.EVALUACION_PATENTE_SOLICITADA`` y
           ``return Resultado(TramiteEvaluacion(id_formula, ticket, "EVALUANDO_PATENTE"),
           formatear(HU09_C1, ticketEvaluacionId=ticket))``.
        """
        raise NoImplementadoError("HU-09")

    @operacion_de_negocio(
        "REGISTRAR_DICTAMEN_PATENTE",
        RECURSO,
        mensaje_error_bd=mensajes.HU10_C7,
        parametro_id="id_formula",
    )
    async def registrar_dictamen(self, id_formula: str, comando: RegistrarDictamenComando) -> Resultado[TramiteEvaluacion]:
        """HU-10 · POST /formulas/{id}/dictamen-patente → 200 (callback de Patent Sweep).

        TODO(HU-10):
        1. El schema ya validó el JSON del dictamen (c3 y c4).
        2. ``async with self._uow:``
           - Si no existe → ``RecursoNoEncontradoError(formatear(HU10_C5, id_formula=id_formula))`` (c5).
           - Si no ``estado_formula(formula.estado).admite_dictamen()`` → ``ConflictoError(HU10_C6_1)`` (c6).
           - ``tramite = await self._formulas.obtener_evaluacion_abierta(id_formula)``; si no
             existe o su ticket no coincide con ``comando.ticket_evaluacion_id`` →
             ``ConflictoError(HU10_C6_2)`` (c6).
           - Guardar ``resultado`` y ``fecha_dictamen`` en el trámite y, si es INFRACCION, una
             ``PatenteConflicto`` por cada patente (c2, para la auditoría).
           - ``formula.estado = estado.registrar_dictamen(resultado).nombre`` (APROBADA o
             RECHAZADA_POR_INFRACCION), ``fecha_actualizacion = ahora()``; auditar (200) con el
             resultado y las patentes en ``detalle``; ``commit``.
           Fallo de BD → el decorador responde 500 con ``HU10_C7`` (c7).
        3. Publicar ``TipoEvento.DICTAMEN_PATENTE_REGISTRADO`` y devolver el trámite con
           ``HU10_C1`` (SIN_INFRACCION) o ``HU10_C2`` (INFRACCION).
        """
        raise NoImplementadoError("HU-10")
