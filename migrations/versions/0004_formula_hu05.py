"""Registro de fórmulas y componentes (HU-05), sin alterar materiales existentes.

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.schema.CreateSequence(sa.Sequence("seq_formula")))
    op.create_table(
        "formula",
        sa.Column("id_formula", sa.String(11), nullable=False),
        sa.Column("nombre", sa.String(80), nullable=False),
        sa.Column("aplicacion_tecnica", sa.String(200), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(25), nullable=False),
        sa.Column("fecha_registro", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id_formula", name=op.f("pk_formula")),
        sa.CheckConstraint("version >= 1", name=op.f("ck_formula_version")),
        sa.CheckConstraint(
            "estado IN ('BORRADOR', 'EVALUANDO_PATENTE', 'APROBADA', 'RECHAZADA_POR_INFRACCION', 'DESCONTINUADA')",
            name=op.f("ck_formula_estado"),
        ),
    )
    op.create_index("uq_formula_nombre_lower", "formula", [sa.text("lower(nombre)")], unique=True)
    op.create_table(
        "formula_componente",
        sa.Column("id_formula", sa.String(11), nullable=False),
        sa.Column("id_material", sa.String(10), nullable=False),
        sa.Column("cantidad", sa.Numeric(9, 3), nullable=False),
        sa.PrimaryKeyConstraint("id_formula", "id_material", name=op.f("pk_formula_componente")),
        sa.ForeignKeyConstraint(
            ["id_formula"], ["formula.id_formula"], name=op.f("fk_formula_componente_id_formula_formula"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["id_material"], ["material.id_material"], name=op.f("fk_formula_componente_id_material_material")),
        sa.CheckConstraint("cantidad > 0 AND cantidad < 1000000", name=op.f("ck_formula_componente_cantidad_rango")),
    )


def downgrade() -> None:
    op.drop_table("formula_componente")
    op.drop_index("uq_formula_nombre_lower", table_name="formula")
    op.drop_table("formula")
    op.execute(sa.schema.DropSequence(sa.Sequence("seq_formula")))
