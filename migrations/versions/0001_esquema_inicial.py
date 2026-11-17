"""Esquema inicial del módulo Materiales y Fórmulas (arquetipo).

Solo la tabla transversal auditoria. Las tablas de las historias de usuario se agregan
con nuevas migraciones (``alembic revision --autogenerate``) cuando se implementen.

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


def upgrade() -> None:
    op.create_table(
        "auditoria",
        sa.Column("id_auditoria", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("fecha_hora", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
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
