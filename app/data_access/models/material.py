"""Tabla material."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.data_access.models.base import Base, lista_sql

# Valores permitidos (los mismos de app/business/domain/enums.py; lo verifica una prueba).
CATEGORIAS = ("Materia Prima", "Componentes", "Lubricantes")
UNIDADES_MEDIDA = ("und", "g", "kg", "mL", "L", "m")
ESTADOS_MATERIAL = ("ACTIVO", "INACTIVO")


class Material(Base):
    """Material del catálogo. El estado INACTIVO es el borrado lógico (HU-04)."""

    __tablename__ = "material"

    id_material: Mapped[str] = mapped_column(String(10), primary_key=True)
    sku: Mapped[str] = mapped_column(String(8), unique=True)
    nombre: Mapped[str] = mapped_column(String(100))
    categoria: Mapped[str] = mapped_column(String(15))
    unidad_medida: Mapped[str] = mapped_column(String(3))
    densidad: Mapped[Decimal] = mapped_column(Numeric)
    pureza: Mapped[Decimal] = mapped_column(Numeric)
    estado: Mapped[str] = mapped_column(String(8))
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    fecha_actualizacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint(f"categoria IN ({lista_sql(CATEGORIAS)})", name="categoria"),
        CheckConstraint(f"unidad_medida IN ({lista_sql(UNIDADES_MEDIDA)})", name="unidad_medida"),
        CheckConstraint("densidad > 0", name="densidad_positiva"),
        CheckConstraint("pureza >= 0 AND pureza <= 100", name="pureza_rango"),
        CheckConstraint(f"estado IN ({lista_sql(ESTADOS_MATERIAL)})", name="estado"),
    )

    def __repr__(self) -> str:
        return f"<Material {self.id_material} {self.nombre!r} {self.estado}>"


# Nombre único sin distinguir mayúsculas de minúsculas (HU-01 c3, HU-03 c3).
Index("uq_material_nombre_lower", func.lower(Material.nombre), unique=True)
