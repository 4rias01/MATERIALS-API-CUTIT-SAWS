"""Reglas de negocio encapsuladas como especificaciones (patrón Specification).

Una especificación responde si un candidato cumple una regla. Se pueden combinar con
``&`` (y), ``|`` (o) y ``~`` (no)::

    regla = MinimoMaterialesDistintos(2)
    if not regla.es_satisfecha_por(["mat-001", "mat-001"]):
        ...  # responder 400 con mensajes.HU05_C2_3
"""

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any, Generic, Protocol, TypeVar

from app.business.domain.enums import EstadoMaterial, UnidadMedida
from app.business.domain.value_objects import Cantidad

T = TypeVar("T")


class Especificacion(ABC, Generic[T]):
    """Regla de negocio que un candidato cumple o no."""

    @abstractmethod
    def es_satisfecha_por(self, candidato: T) -> bool: ...

    def __and__(self, otra: "Especificacion[T]") -> "Especificacion[T]":
        return _Y(self, otra)

    def __or__(self, otra: "Especificacion[T]") -> "Especificacion[T]":
        return _O(self, otra)

    def __invert__(self) -> "Especificacion[T]":
        return _No(self)


class _Y(Especificacion[T]):
    def __init__(self, a: Especificacion[T], b: Especificacion[T]) -> None:
        self._a, self._b = a, b

    def es_satisfecha_por(self, candidato: T) -> bool:
        return self._a.es_satisfecha_por(candidato) and self._b.es_satisfecha_por(candidato)


class _O(Especificacion[T]):
    def __init__(self, a: Especificacion[T], b: Especificacion[T]) -> None:
        self._a, self._b = a, b

    def es_satisfecha_por(self, candidato: T) -> bool:
        return self._a.es_satisfecha_por(candidato) or self._b.es_satisfecha_por(candidato)


class _No(Especificacion[T]):
    def __init__(self, a: Especificacion[T]) -> None:
        self._a = a

    def es_satisfecha_por(self, candidato: T) -> bool:
        return not self._a.es_satisfecha_por(candidato)


# ---------------------------------------------------------------------------------------
# Reglas del módulo
# ---------------------------------------------------------------------------------------


class MinimoMaterialesDistintos(Especificacion[Iterable[str]]):
    """La fórmula tiene mínimo ``minimo`` materiales diferentes (HU-05 c1, HU-07 c2).

    El candidato es la lista de IDs de material de los componentes.
    """

    def __init__(self, minimo: int = 2) -> None:
        self.minimo = minimo

    def es_satisfecha_por(self, candidato: Iterable[str]) -> bool:
        return len(set(candidato)) >= self.minimo


class CantidadEnteraSiUnidad(Especificacion[tuple[Cantidad, UnidadMedida | str]]):
    """Si la unidad de medida del material es und, la cantidad es un número entero
    (HU-05 c1 y c5, HU-07 c2 y c5).

    El candidato es la tupla ``(cantidad, unidad de medida del material)``.
    """

    def es_satisfecha_por(self, candidato: tuple[Cantidad, UnidadMedida | str]) -> bool:
        cantidad, unidad = candidato
        return unidad != UnidadMedida.UNIDAD or cantidad.es_entera()


class _ConEstado(Protocol):
    estado: Any


class MaterialActivo(Especificacion[_ConEstado]):
    """El material está en estado ACTIVO (HU-05 c4, HU-07 c4, HU-09 c1 y c6).

    Acepta cualquier objeto con el atributo ``estado`` (por ejemplo, el modelo Material).
    """

    def es_satisfecha_por(self, candidato: _ConEstado) -> bool:
        return candidato.estado == EstadoMaterial.ACTIVO
