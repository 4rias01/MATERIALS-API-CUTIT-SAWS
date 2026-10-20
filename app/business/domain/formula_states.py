"""Estados de la fórmula (patrón State).

Cada estado es una clase que decide qué acciones admite y a qué estado lleva cada
una. Agregar o cambiar una transición solo toca la clase del estado afectado.

Transiciones (diagrama de estados del DAS)::

    BORRADOR ──solicitar_evaluacion──> EVALUANDO_PATENTE          (HU-09)
    EVALUANDO_PATENTE ──dictamen SIN_INFRACCION──> APROBADA        (HU-10 c1)
    EVALUANDO_PATENTE ──dictamen INFRACCION──> RECHAZADA_POR_INFRACCION (HU-10 c2)
    BORRADOR | RECHAZADA_POR_INFRACCION ──modificar──> BORRADOR    (HU-07 c8)
    BORRADOR | APROBADA | RECHAZADA_POR_INFRACCION ──descontinuar──> DESCONTINUADA (HU-08 c2)

Uso en un servicio::

    estado = estado_formula(formula.estado)
    try:
        formula.estado = estado.descontinuar().nombre
    except TransicionNoPermitidaError:
        raise ConflictoError(mensajes.HU08_C5)
"""

from typing import ClassVar

from app.business.domain.enums import EstadoFormula, ResultadoDictamen
from app.business.domain.errores import TransicionNoPermitidaError


class EstadoFormulaBase:
    """Comportamiento por defecto: ninguna acción está permitida."""

    nombre: ClassVar[EstadoFormula]

    # --- Consultas ------------------------------------------------------------------------
    def admite_modificacion(self) -> bool:
        return False

    def admite_descontinuacion(self) -> bool:
        return False

    def admite_solicitud_evaluacion(self) -> bool:
        return False

    def admite_dictamen(self) -> bool:
        return False

    def es_vigente(self) -> bool:
        """Fórmula vigente: impide inhabilitar sus materiales (HU-04 c2 y c5)."""
        return False

    # --- Transiciones (devuelven el estado siguiente) ----------------------------------
    def modificar(self) -> "EstadoFormulaBase":
        raise self._no_permitida("modificar")

    def descontinuar(self) -> "EstadoFormulaBase":
        raise self._no_permitida("descontinuar")

    def solicitar_evaluacion(self) -> "EstadoFormulaBase":
        raise self._no_permitida("solicitar_evaluacion")

    def registrar_dictamen(self, resultado: ResultadoDictamen) -> "EstadoFormulaBase":
        raise self._no_permitida("registrar_dictamen")

    def _no_permitida(self, accion: str) -> TransicionNoPermitidaError:
        return TransicionNoPermitidaError(self.nombre.value, accion)

    def __repr__(self) -> str:
        return f"<Estado {self.nombre.value}>"


class Borrador(EstadoFormulaBase):
    nombre = EstadoFormula.BORRADOR

    def admite_modificacion(self) -> bool:
        return True

    def admite_descontinuacion(self) -> bool:
        return True

    def admite_solicitud_evaluacion(self) -> bool:
        return True

    def es_vigente(self) -> bool:
        return True

    def modificar(self) -> EstadoFormulaBase:
        return _ESTADOS[EstadoFormula.BORRADOR]

    def descontinuar(self) -> EstadoFormulaBase:
        return _ESTADOS[EstadoFormula.DESCONTINUADA]

    def solicitar_evaluacion(self) -> EstadoFormulaBase:
        return _ESTADOS[EstadoFormula.EVALUANDO_PATENTE]


class EvaluandoPatente(EstadoFormulaBase):
    nombre = EstadoFormula.EVALUANDO_PATENTE

    def admite_dictamen(self) -> bool:
        return True

    def es_vigente(self) -> bool:
        return True

    def registrar_dictamen(self, resultado: ResultadoDictamen) -> EstadoFormulaBase:
        if resultado == ResultadoDictamen.SIN_INFRACCION:
            return _ESTADOS[EstadoFormula.APROBADA]
        return _ESTADOS[EstadoFormula.RECHAZADA_POR_INFRACCION]


class Aprobada(EstadoFormulaBase):
    nombre = EstadoFormula.APROBADA

    def admite_descontinuacion(self) -> bool:
        return True

    def es_vigente(self) -> bool:
        return True

    def descontinuar(self) -> EstadoFormulaBase:
        return _ESTADOS[EstadoFormula.DESCONTINUADA]


class RechazadaPorInfraccion(EstadoFormulaBase):
    nombre = EstadoFormula.RECHAZADA_POR_INFRACCION

    def admite_modificacion(self) -> bool:
        return True

    def admite_descontinuacion(self) -> bool:
        return True

    def modificar(self) -> EstadoFormulaBase:
        return _ESTADOS[EstadoFormula.BORRADOR]

    def descontinuar(self) -> EstadoFormulaBase:
        return _ESTADOS[EstadoFormula.DESCONTINUADA]


class Descontinuada(EstadoFormulaBase):
    nombre = EstadoFormula.DESCONTINUADA


_ESTADOS: dict[EstadoFormula, EstadoFormulaBase] = {
    clase.nombre: clase() for clase in (Borrador, EvaluandoPatente, Aprobada, RechazadaPorInfraccion, Descontinuada)
}


def estado_formula(valor: EstadoFormula | str) -> EstadoFormulaBase:
    """Devuelve el objeto de estado que corresponde al valor guardado en la base de datos."""
    return _ESTADOS[EstadoFormula(valor)]


# Estados en los que una fórmula impide inhabilitar sus materiales (HU-04 c5).
ESTADOS_VIGENTES: tuple[EstadoFormula, ...] = tuple(e for e, estado in _ESTADOS.items() if estado.es_vigente())
