"""Tabla material (CRUD básico)."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Identity, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infraestructure.models.base import Base, lista_sql

# Valores permitidos (los mismos de app/business/domain/enums.py).
CATEGORIAS = ("Materia Prima", "Componentes", "Lubricantes")
UNIDADES_MEDIDA = ("und", "g", "kg", "mL", "L", "m")

# Nombre único sin distinguir mayúsculas de minúsculas.
RESTRICCION_NOMBRE_UNICO = "uq_material_nombre_lower"


class Material(Base):
    __tablename__ = "material"

    id_material: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    categoria: Mapped[str] = mapped_column(String(15))
    unidad_medida: Mapped[str] = mapped_column(String(3))
    densidad: Mapped[Decimal] = mapped_column(Numeric(8, 4))
    pureza: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    fecha_actualizacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint(f"categoria IN ({lista_sql(CATEGORIAS)})", name="categoria"),
        CheckConstraint(f"unidad_medida IN ({lista_sql(UNIDADES_MEDIDA)})", name="unidad_medida"),
        CheckConstraint("densidad > 0", name="densidad_positiva"),
        CheckConstraint("pureza >= 0 AND pureza <= 100", name="pureza_rango"),
    )

    def __repr__(self) -> str:
        return f"<Material {self.id_material} {self.nombre!r}>"


Index(RESTRICCION_NOMBRE_UNICO, func.lower(Material.nombre), unique=True)
