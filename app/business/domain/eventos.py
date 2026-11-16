"""Nombres de los eventos de dominio que publican los servicios (ver app/core/events.py).

Cada historia de usuario agrega aquí sus eventos, por ejemplo::

    class TipoEvento(StrEnum):
        MATERIAL_REGISTRADO = "MaterialRegistrado"
"""

from enum import StrEnum


class TipoEvento(StrEnum):
    """Eventos de dominio del módulo (aún no hay historias implementadas)."""
