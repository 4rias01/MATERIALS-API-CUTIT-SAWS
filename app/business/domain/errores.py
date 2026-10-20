"""Errores del dominio.

No tienen código HTTP ni mensaje para el cliente: el servicio que los captura decide
qué mensaje del backlog devolver (por ejemplo, una ``TransicionNoPermitidaError`` al
descontinuar se responde con ``mensajes.HU08_C5``).
"""

from enum import StrEnum


class Motivo(StrEnum):
    """Por qué un valor no es válido."""

    LONGITUD = "LONGITUD"
    CARACTERES = "CARACTERES"
    NO_POSITIVO = "NO_POSITIVO"
    FUERA_DE_RANGO = "FUERA_DE_RANGO"
    DEMASIADOS_DIGITOS = "DEMASIADOS_DIGITOS"
    FORMATO = "FORMATO"


class ErrorDominio(Exception):
    """Base de los errores del dominio."""


class ValorInvalidoError(ErrorDominio):
    """Un objeto de valor recibió un valor que no cumple sus reglas."""

    def __init__(self, campo: str, motivo: Motivo, valor: object) -> None:
        super().__init__(f"{campo}: {motivo} ({valor!r})")
        self.campo = campo
        self.motivo = motivo
        self.valor = valor


class TransicionNoPermitidaError(ErrorDominio):
    """La fórmula no admite la acción en su estado actual (patrón State)."""

    def __init__(self, estado_actual: str, accion: str) -> None:
        super().__init__(f"La acción '{accion}' no está permitida en el estado {estado_actual}")
        self.estado_actual = estado_actual
        self.accion = accion
