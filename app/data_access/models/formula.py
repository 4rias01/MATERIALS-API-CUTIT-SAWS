"""Tablas formula y componente_formula."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data_access.models.base import Base, lista_sql

if TYPE_CHECKING:
    from app.data_access.models.evaluacion_patente import EvaluacionPatente
    from app.data_access.models.material import Material

ESTADOS_FORMULA = ("BORRADOR", "EVALUANDO_PATENTE", "APROBADA", "RECHAZADA_POR_INFRACCION", "DESCONTINUADA")


class Formula(Base):
    """Fórmula (receta) de al menos dos materiales.

    Las relaciones usan ``lazy="raise"``: con SQLAlchemy asíncrono no se pueden cargar
    de forma perezosa, así que el repositorio las carga explícitamente (selectinload).
    """

    __tablename__ = "formula"

    id_formula: Mapped[str] = mapped_column(String(10), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80))
    aplicacion_tecnica: Mapped[str] = mapped_column(String(200))
    version: Mapped[int] = mapped_column(Integer, default=1)
    estado: Mapped[str] = mapped_column(String(25))
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    fecha_actualizacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    componentes: Mapped[list["ComponenteFormula"]] = relationship(
        back_populates="formula",
        cascade="all, delete-orphan",
        lazy="raise",
        order_by="ComponenteFormula.id_material",
    )
    evaluaciones: Mapped[list["EvaluacionPatente"]] = relationship(
        back_populates="formula",
        cascade="all, delete-orphan",
        lazy="raise",
        order_by="EvaluacionPatente.fecha_solicitud",
    )

    __table_args__ = (
        CheckConstraint("version >= 1", name="version_minima"),
        CheckConstraint(f"estado IN ({lista_sql(ESTADOS_FORMULA)})", name="estado"),
        Index("ix_formula_estado", "estado"),
        Index("ix_formula_fecha_actualizacion", "fecha_actualizacion"),
    )

    def __repr__(self) -> str:
        return f"<Formula {self.id_formula} {self.nombre!r} {self.estado} v{self.version}>"


class ComponenteFormula(Base):
    """Línea de la tabla de componentes: un material y su cantidad para fabricar una cuchilla."""

    __tablename__ = "componente_formula"

    id_formula: Mapped[str] = mapped_column(ForeignKey("formula.id_formula", ondelete="CASCADE"), primary_key=True)
    id_material: Mapped[str] = mapped_column(ForeignKey("material.id_material"), primary_key=True)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(9, 3))

    formula: Mapped["Formula"] = relationship(back_populates="componentes", lazy="raise")
    material: Mapped["Material"] = relationship(lazy="raise")

    __table_args__ = (
        CheckConstraint("cantidad > 0", name="cantidad_positiva"),
        # Búsqueda de fórmulas por material (HU-04 c5 y filtro "Materiales usados" de HU-06).
        Index("ix_componente_formula_id_material", "id_material"),
    )

    def __repr__(self) -> str:
        return f"<ComponenteFormula {self.id_formula} {self.id_material} {self.cantidad}>"


# Nombre de fórmula único sin distinguir mayúsculas (HU-05 c6.1; ver "Vacíos del backlog" en el README).
Index("uq_formula_nombre_lower", func.lower(Formula.nombre), unique=True)
