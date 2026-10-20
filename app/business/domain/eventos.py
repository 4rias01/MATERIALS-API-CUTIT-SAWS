"""Nombres de los eventos de dominio que publican los servicios (ver app/core/events.py)."""

from enum import StrEnum


class TipoEvento(StrEnum):
    MATERIAL_REGISTRADO = "MaterialRegistrado"  # HU-01
    MATERIAL_ACTUALIZADO = "MaterialActualizado"  # HU-03
    MATERIAL_INHABILITADO = "MaterialInhabilitado"  # HU-04
    FORMULA_REGISTRADA = "FormulaRegistrada"  # HU-05
    FORMULA_ACTUALIZADA = "FormulaActualizada"  # HU-07
    FORMULA_DESCONTINUADA = "FormulaDescontinuada"  # HU-08
    EVALUACION_PATENTE_SOLICITADA = "EvaluacionPatenteSolicitada"  # HU-09
    DICTAMEN_PATENTE_REGISTRADO = "DictamenPatenteRegistrado"  # HU-10
