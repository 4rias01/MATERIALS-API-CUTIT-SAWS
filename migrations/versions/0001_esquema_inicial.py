"""Esquema inicial del módulo Materiales y Fórmulas (sprint 0: flujo de ejemplo HU-01).

Tablas material y auditoria; secuencia del consecutivo mat-NNN; restricciones PK,
UNIQUE, CHECK y NOT NULL. Las tablas de las demás historias se agregan con nuevas
migraciones cuando se implementen.

Revision ID: 0001
Revises:
Create Date: 2026-10-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SECUENCIAS = ("seq_material",)


def _ahora() -> sa.TextClause:
    return sa.text("now()")


def upgrade() -> None:
    for nombre in SECUENCIAS:
        op.execute(sa.schema.CreateSequence(sa.Sequence(nombre)))

    op.create_table(
        "material",
        sa.Column("id_material", sa.String(10), nullable=False),
        sa.Column("sku", sa.String(8), nullable=False),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("categoria", sa.String(15), nullable=False),
        sa.Column("unidad_medida", sa.String(3), nullable=False),
        sa.Column("densidad", sa.Numeric(), nullable=False),
        sa.Column("pureza", sa.Numeric(), nullable=False),
        sa.Column("estado", sa.String(8), nullable=False),
        sa.Column("fecha_registro", sa.DateTime(timezone=True), server_default=_ahora(), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), server_default=_ahora(), nullable=False),
        sa.PrimaryKeyConstraint("id_material", name=op.f("pk_material")),
        sa.UniqueConstraint("sku", name=op.f("uq_material_sku")),
        sa.CheckConstraint(
            "categoria IN ('Materia Prima', 'Componentes', 'Lubricantes')", name=op.f("ck_material_categoria")
        ),
        sa.CheckConstraint(
            "unidad_medida IN ('und', 'g', 'kg', 'mL', 'L', 'm')", name=op.f("ck_material_unidad_medida")
        ),
        sa.CheckConstraint("densidad > 0", name=op.f("ck_material_densidad_positiva")),
        sa.CheckConstraint("pureza >= 0 AND pureza <= 100", name=op.f("ck_material_pureza_rango")),
        sa.CheckConstraint("estado IN ('ACTIVO', 'INACTIVO')", name=op.f("ck_material_estado")),
    )
    op.create_index("uq_material_nombre_lower", "material", [sa.text("lower(nombre)")], unique=True)

    op.create_table(
        "auditoria",
        sa.Column("id_auditoria", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("fecha_hora", sa.DateTime(timezone=True), server_default=_ahora(), nullable=False),
        sa.Column("trace_id", sa.String(64), nullable=False),
        sa.Column("operacion", sa.String(60), nullable=False),
        sa.Column("recurso", sa.String(20), nullable=False),
        sa.Column("recurso_id", sa.String(10), nullable=True),
        sa.Column("resultado_http", sa.SmallInteger(), nullable=False),
        sa.Column("origen", sa.String(100), nullable=True),
        sa.Column("detalle", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id_auditoria", name=op.f("pk_auditoria")),
    )
    op.create_index("ix_auditoria_trace_id", "auditoria", ["trace_id"])
    op.create_index("ix_auditoria_fecha_hora", "auditoria", ["fecha_hora"])


def downgrade() -> None:
    op.drop_table("auditoria")
    op.drop_table("material")
    for nombre in reversed(SECUENCIAS):
        op.execute(sa.schema.DropSequence(sa.Sequence(nombre)))
