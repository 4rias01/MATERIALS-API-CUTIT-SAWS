"""Objetos de valor del dominio (patrón Value Object).

Cada objeto es inmutable y garantiza su propia validez: si se puede crear, el valor
cumple las reglas del backlog. Si no, lanza ``ValorInvalidoError`` con el campo y el
motivo, y el servicio o el schema decide qué mensaje del backlog devolver.

Interpretaciones que el equipo debe confirmar con el PO (ver README, "Vacíos del backlog"):

* "máximo N caracteres" en Densidad y Pureza cuenta dígitos y punto decimal del número
  escrito sin ceros a la derecha del decimal ni notación científica (7.850 → "7.85" → 4
  caracteres), como precisa HU-01 c1.
* El ID del material usa mínimo 3 dígitos (mat-001 … mat-999, mat-1000).
"""

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import ClassVar

from app.business.domain.errores import Motivo, ValorInvalidoError

# ---------------------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------------------

_ESPACIOS_REPETIDOS = re.compile(r" {2,}")


def normalizar_nombre(texto: str) -> str:
    """Quita los espacios al inicio y al final y reduce a uno los repetidos (HU-01 c1)."""
    return _ESPACIOS_REPETIDOS.sub(" ", texto.strip())


def a_decimal(valor: object, campo: str) -> Decimal:
    """Convierte ``valor`` en Decimal finito o lanza ``ValorInvalidoError`` (motivo FORMATO)."""
    if isinstance(valor, bool):
        raise ValorInvalidoError(campo, Motivo.FORMATO, valor)
    try:
        numero = valor if isinstance(valor, Decimal) else Decimal(str(valor))
    except (InvalidOperation, ValueError) as exc:
        raise ValorInvalidoError(campo, Motivo.FORMATO, valor) from exc
    if not numero.is_finite():
        raise ValorInvalidoError(campo, Motivo.FORMATO, valor)
    return numero


def contar_caracteres(numero: Decimal) -> int:
    """Caracteres del número sin ceros sobrantes ni notación científica (7.850 → "7.85" → 4)."""
    return len(format(numero.normalize(), "f"))


# ---------------------------------------------------------------------------------------
# Material
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class NombreMaterial:
    """Nombre del material: 3 a 100 caracteres; letras con o sin tilde, ñ, dígitos,
    espacios y los símbolos - . , / ( ) # (HU-01 c1).

    Usar ``NombreMaterial.crear(texto)`` para normalizar los espacios antes de validar.
    """

    valor: str

    LONGITUD_MINIMA: ClassVar[int] = 3
    LONGITUD_MAXIMA: ClassVar[int] = 100
    PATRON: ClassVar[re.Pattern[str]] = re.compile(r"[A-Za-zÁÉÍÓÚáéíóúÑñ0-9 \-.,/()#]+")

    def __post_init__(self) -> None:
        if not self.LONGITUD_MINIMA <= len(self.valor) <= self.LONGITUD_MAXIMA:
            raise ValorInvalidoError("nombre", Motivo.LONGITUD, self.valor)
        if not self.PATRON.fullmatch(self.valor):
            raise ValorInvalidoError("nombre", Motivo.CARACTERES, self.valor)

    @classmethod
    def crear(cls, texto: str) -> "NombreMaterial":
        """Normaliza los espacios y valida."""
        return cls(normalizar_nombre(texto))

    @property
    def clave_unicidad(self) -> str:
        """Clave para comparar nombres sin distinguir mayúsculas (igual que el índice lower(nombre))."""
        return self.valor.lower()

    def __str__(self) -> str:
        return self.valor


@dataclass(frozen=True, slots=True)
class Densidad:
    """Densidad del material: numérica, positiva y de máximo 4 caracteres (HU-01 c1, p. ej. 7.85 o 1000)."""

    valor: Decimal

    MAX_CARACTERES: ClassVar[int] = 4

    def __post_init__(self) -> None:
        numero = a_decimal(self.valor, "densidad")
        object.__setattr__(self, "valor", numero)
        if numero <= 0:
            raise ValorInvalidoError("densidad", Motivo.NO_POSITIVO, numero)
        if contar_caracteres(numero) > self.MAX_CARACTERES:
            raise ValorInvalidoError("densidad", Motivo.DEMASIADOS_DIGITOS, numero)


@dataclass(frozen=True, slots=True)
class Pureza:
    """Pureza del material: numérica de 0 a 100 % y de máximo 3 caracteres (HU-01 c1)."""

    valor: Decimal

    MAX_CARACTERES: ClassVar[int] = 3

    def __post_init__(self) -> None:
        numero = a_decimal(self.valor, "pureza")
        object.__setattr__(self, "valor", numero)
        if not Decimal(0) <= numero <= Decimal(100):
            raise ValorInvalidoError("pureza", Motivo.FUERA_DE_RANGO, numero)
        if contar_caracteres(numero) > self.MAX_CARACTERES:
            raise ValorInvalidoError("pureza", Motivo.DEMASIADOS_DIGITOS, numero)


@dataclass(frozen=True, slots=True)
class Sku:
    """Código de artículo que asigna Inventario, formato MP-00000 (HU-01 c7.2). Solo lectura."""

    valor: str

    PATRON: ClassVar[re.Pattern[str]] = re.compile(r"MP-\d{5}")

    def __post_init__(self) -> None:
        if not isinstance(self.valor, str) or not self.PATRON.fullmatch(self.valor):
            raise ValorInvalidoError("sku", Motivo.FORMATO, self.valor)

    def __str__(self) -> str:
        return self.valor


# ---------------------------------------------------------------------------------------
# Identificador secuencial (el número sale de una secuencia de PostgreSQL)
# ---------------------------------------------------------------------------------------


def id_material(numero: int) -> str:
    """ID del material con formato secuencial mat-NNN (HU-01 c7.1)."""
    if numero < 1:
        raise ValorInvalidoError("mat", Motivo.FUERA_DE_RANGO, numero)
    return f"mat-{numero:03d}"
