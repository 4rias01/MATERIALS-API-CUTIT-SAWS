"""Excepciones de la aplicación, usadas por todas las capas.

Hay dos familias:

* ``ErrorAplicacion`` y sus subclases: resultados que se devuelven al cliente. Llevan
  el mensaje del backlog y el código HTTP que les corresponde. Las lanza la capa de
  lógica de negocio y el manejador global de excepciones
  (app/presentation/exception_handlers.py) las traduce a la respuesta
  ``{"mensaje": ..., "traceId": ...}``.
* ``ErrorTecnico`` y sus subclases: fallos de una dependencia (base de datos o API
  externa). Las lanza la capa de acceso a datos, no tienen mensaje para el cliente y
  el servicio decide con qué mensaje del backlog responder.
"""

from typing import ClassVar

# ---------------------------------------------------------------------------------------
# Resultados para el cliente
# ---------------------------------------------------------------------------------------


class ErrorAplicacion(Exception):
    """Error con mensaje para el cliente."""

    codigo_http: ClassVar[int] = 500

    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje


class SolicitudInvalidaError(ErrorAplicacion):
    """400: la solicitud no cumple el contrato."""

    codigo_http = 400


class RecursoNoEncontradoError(ErrorAplicacion):
    """404: el recurso no existe."""

    codigo_http = 404


class ConflictoError(ErrorAplicacion):
    """409: la operación choca con el estado actual del recurso."""

    codigo_http = 409


class ReglaDeNegocioError(ErrorAplicacion):
    """422: la solicitud es válida pero incumple una regla de negocio."""

    codigo_http = 422


class ErrorInterno(ErrorAplicacion):
    """500: fallo interno (base de datos, timeout); la respuesta incluye el traceId."""

    codigo_http = 500


class NoImplementadoError(ErrorAplicacion):
    """501: la historia de usuario aún no está implementada (solo durante la codificación)."""

    codigo_http = 501

    def __init__(self, historia: str) -> None:
        super().__init__(f"La funcionalidad de la {historia} aún no está implementada.")
        self.historia = historia


class DependenciaNoDisponibleError(ErrorAplicacion):
    """503: Inventario o Patent Sweep no respondió, falló o tardó más de 5 s."""

    codigo_http = 503


# ---------------------------------------------------------------------------------------
# Fallos técnicos de las dependencias
# ---------------------------------------------------------------------------------------


class ErrorTecnico(Exception):
    """Fallo de una dependencia. No lleva mensaje para el cliente."""


class ErrorBaseDatos(ErrorTecnico):
    """Fallo de conexión, error de persistencia o timeout (> 5 s) de la base de datos."""


class ErrorIntegridadDatos(ErrorBaseDatos):
    """La base de datos rechazó la operación por una restricción (UNIQUE, CHECK, FK)."""

    def __init__(self, mensaje: str, restriccion: str | None = None) -> None:
        super().__init__(mensaje)
        self.restriccion = restriccion


class ErrorServicioExterno(ErrorTecnico):
    """Fallo al llamar a una API externa (Inventario o Patent Sweep)."""

    # Valores posibles de ``causa``.
    TIMEOUT = "TIMEOUT"
    CONEXION = "CONEXION"
    ERROR_INTERNO = "ERROR_INTERNO"
    CIRCUITO_ABIERTO = "CIRCUITO_ABIERTO"
    RESPUESTA_INESPERADA = "RESPUESTA_INESPERADA"
    SIN_CONFIGURAR = "SIN_CONFIGURAR"

    def __init__(self, servicio: str, causa: str, estado_recibido: int | None = None, detalle: str = "") -> None:
        texto = f"{servicio}: {causa}" + (f" (HTTP {estado_recibido})" if estado_recibido else "")
        super().__init__(texto + (f" - {detalle}" if detalle else ""))
        self.servicio = servicio
        self.causa = causa
        self.estado_recibido = estado_recibido
        self.detalle = detalle
