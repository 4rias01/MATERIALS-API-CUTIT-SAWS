"""Tablas de registro de fórmulas y su composición (HU-05)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infraestructure.models.base import Base, lista_sql
from app.infraestructure.models.material import Material

RESTRICCION_NOMBRE_UNICO = "uq_formula_nombre_lower"
ESTADOS_FORMULA = ("BORRADOR", "EVALUANDO_PATENTE", "APROBADA", "RECHAZADA_POR_INFRACCION", "DESCONTINUADA")


class Formula(Base):
    __tablename__ = "formula"

    id_formula: Mapped[str] = mapped_column(String(11), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80))
    aplicacion_tecnica: Mapped[str] = mapped_column(String(200))
    version: Mapped[int] = mapped_column()
    estado: Mapped[str] = mapped_column(String(25))
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    fecha_actualizacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    componentes: Mapped[list[FormulaComponente]] = relationship(cascade="all, delete-orphan", lazy="raise")

    __table_args__ = (
        CheckConstraint("version >= 1", name="version"),
        CheckConstraint(f"estado IN ({lista_sql(ESTADOS_FORMULA)})", name="estado"),
    )


class FormulaComponente(Base):
    __tablename__ = "formula_componente"

    id_formula: Mapped[str] = mapped_column(ForeignKey("formula.id_formula", ondelete="CASCADE"), primary_key=True)
    id_material: Mapped[str] = mapped_column(ForeignKey("material.id_material"), primary_key=True)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(9, 3))
    material: Mapped[Material] = relationship(lazy="raise")

    __table_args__ = (CheckConstraint("cantidad > 0 AND cantidad < 1000000", name="cantidad_rango"),)


Index(RESTRICCION_NOMBRE_UNICO, func.lower(Formula.nombre), unique=True)
