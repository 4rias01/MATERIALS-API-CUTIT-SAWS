"""Tabla auditoria (patrón Tabla de auditoría).

Pista de solo inserción: cada operación de negocio deja un registro con fecha,
operación, recurso, resultado HTTP, origen y traceId. No tiene llaves foráneas para
poder registrar también operaciones fallidas sobre recursos que no existen.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Index, SmallInteger, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.data_access.models.base import Base


class Auditoria(Base):
    __tablename__ = "auditoria"

    id_auditoria: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    trace_id: Mapped[str] = mapped_column(String(64))
    operacion: Mapped[str] = mapped_column(String(60))
    recurso: Mapped[str] = mapped_column(String(20))
    recurso_id: Mapped[str | None] = mapped_column(String(10))
    resultado_http: Mapped[int] = mapped_column(SmallInteger)
    origen: Mapped[str | None] = mapped_column(String(100))
    detalle: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    __table_args__ = (
        Index("ix_auditoria_trace_id", "trace_id"),
        Index("ix_auditoria_fecha_hora", "fecha_hora"),
    )

    def __repr__(self) -> str:
        return f"<Auditoria {self.operacion} {self.recurso}:{self.recurso_id} {self.resultado_http}>"
