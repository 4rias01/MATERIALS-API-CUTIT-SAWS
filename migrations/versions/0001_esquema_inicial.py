"""Esquema inicial del módulo Materiales y Fórmulas (MER del DAS).

Tablas material, formula, componente_formula, evaluacion_patente, patente_conflicto y
auditoria; secuencias de los consecutivos mat-NNN, form-NNN y tck-NNN; restricciones
PK, FK, UNIQUE, CHECK y NOT NULL; índices de filtro y orden.

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

SECUENCIAS = ("seq_material", "seq_formula", "seq_ticket_evaluacion")


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
        "formula",
        sa.Column("id_formula", sa.String(10), nullable=False),
        sa.Column("nombre", sa.String(80), nullable=False),
        sa.Column("aplicacion_tecnica", sa.String(200), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(25), nullable=False),
        sa.Column("fecha_registro", sa.DateTime(timezone=True), server_default=_ahora(), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), server_default=_ahora(), nullable=False),
        sa.PrimaryKeyConstraint("id_formula", name=op.f("pk_formula")),
        sa.CheckConstraint("version >= 1", name=op.f("ck_formula_version_minima")),
        sa.CheckConstraint(
            "estado IN ('BORRADOR', 'EVALUANDO_PATENTE', 'APROBADA', 'RECHAZADA_POR_INFRACCION', 'DESCONTINUADA')",
            name=op.f("ck_formula_estado"),
        ),
    )
    op.create_index("ix_formula_estado", "formula", ["estado"])
    op.create_index("ix_formula_fecha_actualizacion", "formula", ["fecha_actualizacion"])
    op.create_index("uq_formula_nombre_lower", "formula", [sa.text("lower(nombre)")], unique=True)

    op.create_table(
        "componente_formula",
        sa.Column("id_formula", sa.String(10), nullable=False),
        sa.Column("id_material", sa.String(10), nullable=False),
        sa.Column("cantidad", sa.Numeric(9, 3), nullable=False),
        sa.PrimaryKeyConstraint("id_formula", "id_material", name=op.f("pk_componente_formula")),
        sa.ForeignKeyConstraint(
            ["id_formula"],
            ["formula.id_formula"],
            name=op.f("fk_componente_formula_id_formula_formula"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["id_material"], ["material.id_material"], name=op.f("fk_componente_formula_id_material_material")
        ),
        sa.CheckConstraint("cantidad > 0", name=op.f("ck_componente_formula_cantidad_positiva")),
    )
    op.create_index("ix_componente_formula_id_material", "componente_formula", ["id_material"])

    op.create_table(
        "evaluacion_patente",
        sa.Column("ticket_evaluacion_id", sa.String(10), nullable=False),
        sa.Column("id_formula", sa.String(10), nullable=False),
        sa.Column("fecha_solicitud", sa.DateTime(timezone=True), server_default=_ahora(), nullable=False),
        sa.Column("resultado", sa.String(15), nullable=True),
        sa.Column("fecha_dictamen", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("ticket_evaluacion_id", name=op.f("pk_evaluacion_patente")),
        sa.ForeignKeyConstraint(
            ["id_formula"], ["formula.id_formula"], name=op.f("fk_evaluacion_patente_id_formula_formula")
        ),
        sa.CheckConstraint(
            "resultado IS NULL OR resultado IN ('SIN_INFRACCION', 'INFRACCION')",
            name=op.f("ck_evaluacion_patente_resultado"),
        ),
    )
    op.create_index("ix_evaluacion_patente_id_formula", "evaluacion_patente", ["id_formula"])
    # A lo sumo un trámite abierto (sin dictamen) por fórmula.
    op.create_index(
        "uq_evaluacion_patente_abierta",
        "evaluacion_patente",
        ["id_formula"],
        unique=True,
        postgresql_where=sa.text("resultado IS NULL"),
    )

    op.create_table(
        "patente_conflicto",
        sa.Column("ticket_evaluacion_id", sa.String(10), nullable=False),
        sa.Column("conflicto_id", sa.CHAR(6), nullable=False),
        sa.Column("titulo", sa.String(60), nullable=False),
        sa.PrimaryKeyConstraint("ticket_evaluacion_id", "conflicto_id", name=op.f("pk_patente_conflicto")),
        sa.ForeignKeyConstraint(
            ["ticket_evaluacion_id"],
            ["evaluacion_patente.ticket_evaluacion_id"],
            name=op.f("fk_patente_conflicto_ticket_evaluacion_id_evaluacion_patente"),
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("conflicto_id ~ '^[0-9]{6}$'", name=op.f("ck_patente_conflicto_conflicto_id_formato")),
    )

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
    op.drop_table("patente_conflicto")
    op.drop_table("evaluacion_patente")
    op.drop_table("componente_formula")
    op.drop_table("formula")
    op.drop_table("material")
    for nombre in reversed(SECUENCIAS):
        op.execute(sa.schema.DropSequence(sa.Sequence(nombre)))
