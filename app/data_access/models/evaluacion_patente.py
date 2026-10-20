"""Tablas evaluacion_patente y patente_conflicto (HU-09 y HU-10)."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CHAR, CheckConstraint, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data_access.models.base import Base, lista_sql

if TYPE_CHECKING:
    from app.data_access.models.formula import Formula

RESULTADOS_DICTAMEN = ("SIN_INFRACCION", "INFRACCION")


class EvaluacionPatente(Base):
    """Trámite de evaluación de patente de una fórmula.

    ``resultado`` es NULL mientras el trámite está abierto (fórmula en EVALUANDO_PATENTE).
    Un índice único parcial garantiza a lo sumo un trámite abierto por fórmula.
    """

    __tablename__ = "evaluacion_patente"

    ticket_evaluacion_id: Mapped[str] = mapped_column(String(10), primary_key=True)
    id_formula: Mapped[str] = mapped_column(ForeignKey("formula.id_formula"))
    fecha_solicitud: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resultado: Mapped[str | None] = mapped_column(String(15))
    fecha_dictamen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    formula: Mapped["Formula"] = relationship(back_populates="evaluaciones", lazy="raise")
    patentes: Mapped[list["PatenteConflicto"]] = relationship(
        back_populates="evaluacion",
        cascade="all, delete-orphan",
        lazy="raise",
        order_by="PatenteConflicto.conflicto_id",
    )

    __table_args__ = (
        CheckConstraint(f"resultado IS NULL OR resultado IN ({lista_sql(RESULTADOS_DICTAMEN)})", name="resultado"),
        Index("ix_evaluacion_patente_id_formula", "id_formula"),
        Index(
            "uq_evaluacion_patente_abierta",
            "id_formula",
            unique=True,
            postgresql_where=text("resultado IS NULL"),
        ),
    )

    @property
    def esta_abierta(self) -> bool:
        return self.resultado is None

    def __repr__(self) -> str:
        return f"<EvaluacionPatente {self.ticket_evaluacion_id} {self.id_formula} {self.resultado}>"


class PatenteConflicto(Base):
    """Patente en conflicto registrada por un dictamen INFRACCION (HU-10 c2 y c3)."""

    __tablename__ = "patente_conflicto"

    ticket_evaluacion_id: Mapped[str] = mapped_column(
        ForeignKey("evaluacion_patente.ticket_evaluacion_id", ondelete="CASCADE"), primary_key=True
    )
    conflicto_id: Mapped[str] = mapped_column(CHAR(6), primary_key=True)
    titulo: Mapped[str] = mapped_column(String(60))

    evaluacion: Mapped["EvaluacionPatente"] = relationship(back_populates="patentes", lazy="raise")

    __table_args__ = (CheckConstraint("conflicto_id ~ '^[0-9]{6}$'", name="conflicto_id_formato"),)

    def __repr__(self) -> str:
        return f"<PatenteConflicto {self.conflicto_id} {self.titulo!r}>"
