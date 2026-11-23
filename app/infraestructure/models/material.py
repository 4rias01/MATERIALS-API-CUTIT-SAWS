"""Tabla material (HU-01)."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infraestructure.models.base import Base, lista_sql

# Valores permitidos (los mismos de app/business/domain/enums.py; lo verifica una prueba).
CATEGORIAS = ("Materia Prima", "Componentes", "Lubricantes")
UNIDADES_MEDIDA = ("und", "g", "kg", "mL", "L", "m")
ESTADOS_MATERIAL = ("ACTIVO", "INACTIVO")

# Nombre único sin distinguir mayúsculas de minúsculas (HU-01 c3).
RESTRICCION_NOMBRE_UNICO = "uq_material_nombre_lower"


class Material(Base):
    """Material del catálogo (HU-01)."""

    __tablename__ = "material"

    # mat-NNN; el número sale de la secuencia seq_material (app/infraestructure/models/base.py).
    id_material: Mapped[str] = mapped_column(String(10), primary_key=True)
    # Código de artículo que asigna Inventario (MP-00000).
    sku: Mapped[str] = mapped_column(String(8), unique=True)
    nombre: Mapped[str] = mapped_column(String(100))
    categoria: Mapped[str] = mapped_column(String(15))
    unidad_medida: Mapped[str] = mapped_column(String(3))
    densidad: Mapped[Decimal] = mapped_column(Numeric(8, 4))
    pureza: Mapped[Decimal] = mapped_column(Numeric(5, 2))
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


Index(RESTRICCION_NOMBRE_UNICO, func.lower(Material.nombre), unique=True)
