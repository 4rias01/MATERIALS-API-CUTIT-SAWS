"""Nombres de los eventos de dominio que publican los servicios (ver app/core/events.py)."""

from enum import StrEnum


class TipoEvento(StrEnum):
    MATERIAL_REGISTRADO = "MaterialRegistrado"  # HU-01
