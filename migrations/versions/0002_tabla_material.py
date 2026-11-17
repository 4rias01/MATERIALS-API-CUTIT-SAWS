"""Tabla material (CRUD básico).

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "material",
        sa.Column("id_material", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("categoria", sa.String(15), nullable=False),
        sa.Column("unidad_medida", sa.String(3), nullable=False),
        sa.Column("densidad", sa.Numeric(8, 4), nullable=False),
        sa.Column("pureza", sa.Numeric(5, 2), nullable=False),
        sa.Column("fecha_registro", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id_material", name=op.f("pk_material")),
        sa.CheckConstraint(
            "categoria IN ('Materia Prima', 'Componentes', 'Lubricantes')", name=op.f("ck_material_categoria")
        ),
        sa.CheckConstraint(
            "unidad_medida IN ('und', 'g', 'kg', 'mL', 'L', 'm')", name=op.f("ck_material_unidad_medida")
        ),
        sa.CheckConstraint("densidad > 0", name=op.f("ck_material_densidad_positiva")),
        sa.CheckConstraint("pureza >= 0 AND pureza <= 100", name=op.f("ck_material_pureza_rango")),
    )
    op.create_index("uq_material_nombre_lower", "material", [sa.text("lower(nombre)")], unique=True)


def downgrade() -> None:
    op.drop_table("material")
