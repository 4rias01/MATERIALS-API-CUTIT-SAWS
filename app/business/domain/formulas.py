"""Reglas de registro de fórmulas (HU-05)."""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar, Protocol

from app.business.domain import mensajes
from app.business.domain.enums import EstadoMaterial, UnidadMedida
from app.business.domain.errores import Motivo, ValorInvalidoError
from app.business.domain.mensajes import formatear
from app.business.domain.value_objects import a_decimal, normalizar_nombre
from app.core.exceptions import ReglaDeNegocioError, SolicitudInvalidaError


@dataclass(frozen=True, slots=True)
class NombreFormula:
    valor: str

    PATRON: ClassVar[re.Pattern[str]] = re.compile(r"[A-Za-zÁÉÍÓÚÜáéíóúüÑñ ]+")

    def __post_init__(self) -> None:
        if not self.valor.strip():
            raise SolicitudInvalidaError(mensajes.HU05_C2_1)
        if len(self.valor) > 80:
            raise SolicitudInvalidaError(mensajes.HU05_C9_1_A)
        if not self.PATRON.fullmatch(self.valor):
            raise SolicitudInvalidaError(mensajes.HU05_C9_1_B)

    @classmethod
    def crear(cls, valor: str) -> "NombreFormula":
        return cls(normalizar_nombre(valor))


@dataclass(frozen=True, slots=True)
class AplicacionTecnica:
    valor: str

    def __post_init__(self) -> None:
        if not self.valor.strip():
            raise SolicitudInvalidaError(mensajes.HU05_C2_2)
        if len(self.valor) > 200:
            raise SolicitudInvalidaError(mensajes.HU05_C9_2)
        if not all(c.isalnum() or c == " " for c in self.valor):
            raise SolicitudInvalidaError(mensajes.SOLICITUD_INVALIDA)


@dataclass(frozen=True, slots=True)
class Cantidad:
    valor: Decimal

    def __post_init__(self) -> None:
        numero = a_decimal(self.valor, "cantidad")
        object.__setattr__(self, "valor", numero)
        if numero <= 0:
            raise ValorInvalidoError("cantidad", Motivo.NO_POSITIVO, numero)
        if numero >= 1_000_000 or _decimales_significativos(numero) > 3:
            raise ValorInvalidoError("cantidad", Motivo.DEMASIADOS_DIGITOS, numero)


def _decimales_significativos(numero: Decimal) -> int:
    """Cuenta sin redondear por la precisión del contexto Decimal ni expandir exponentes."""
    partes = numero.as_tuple()
    decimales = -int(partes.exponent)
    for digito in reversed(partes.digits):
        if digito != 0:
            break
        decimales -= 1
    return max(0, decimales)


@dataclass(frozen=True, slots=True)
class ComponenteFormula:
    material_id: str
    cantidad: Decimal

    def __post_init__(self) -> None:
        if not re.fullmatch(r"mat-[0-9]{3,}", self.material_id):
            raise SolicitudInvalidaError(mensajes.SOLICITUD_INVALIDA)
        try:
            object.__setattr__(self, "cantidad", Cantidad(self.cantidad).valor)
        except ValorInvalidoError as exc:
            plantilla = mensajes.HU05_C3_2 if exc.motivo == Motivo.DEMASIADOS_DIGITOS else mensajes.HU05_C3_1
            raise SolicitudInvalidaError(formatear(plantilla, IDMaterial=self.material_id, Cantidad=self.cantidad)) from exc


def validar_componentes(componentes: tuple[ComponenteFormula, ...]) -> None:
    if len(componentes) < 2:
        raise SolicitudInvalidaError(mensajes.HU05_C2_3)
    vistos: set[str] = set()
    for componente in componentes:
        if componente.material_id in vistos:
            raise SolicitudInvalidaError(formatear(mensajes.HU05_C9_3, IDMaterial=componente.material_id))
        vistos.add(componente.material_id)


class MaterialComponente(Protocol):
    @property
    def nombre(self) -> str: ...

    @property
    def estado(self) -> str: ...

    @property
    def unidad_medida(self) -> str: ...


def validar_materiales(
    componentes: tuple[ComponenteFormula, ...], materiales: Sequence[MaterialComponente | None]
) -> None:
    faltantes = [c.material_id for c, m in zip(componentes, materiales, strict=True) if m is None]
    if faltantes:
        raise ReglaDeNegocioError(formatear(mensajes.HU05_C4_1, {"Lista de Materiales": ", ".join(faltantes)}))
    inactivos = [
        c.material_id for c, m in zip(componentes, materiales, strict=True) if m is not None and m.estado != EstadoMaterial.ACTIVO
    ]
    if inactivos:
        raise ReglaDeNegocioError(formatear(mensajes.HU05_C4_2, {"Lista de Materiales": ", ".join(inactivos)}))
    for componente, material in zip(componentes, materiales, strict=True):
        if material is not None and material.unidad_medida == UnidadMedida.UNIDAD and componente.cantidad % 1:
            raise ReglaDeNegocioError(
                formatear(mensajes.HU05_C5, NombreMaterial=material.nombre, Cantidad=componente.cantidad)
            )


def id_formula(numero: int) -> str:
    if numero < 1:
        raise ValorInvalidoError("form", Motivo.FUERA_DE_RANGO, numero)
    return f"form-{numero:03d}"
