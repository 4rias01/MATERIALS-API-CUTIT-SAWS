"""Tabla material de HU-01: ID mat-NNN, SKU de Inventario y estado.

La tabla del CRUD básico (0002) tenía un ID numérico y no tenía SKU ni estado. Sus filas
no se pueden convertir (el SKU solo lo asigna Inventario al registrar el material), así
que no se borran: la tabla se renombra a ``material_crud_respaldo`` y se crea la nueva.
El respaldo no tiene modelo ORM (migrations/env.py lo excluye de la comparación) y se
puede eliminar con una migración cuando el equipo confirme que no se necesita.

Si la base está en 0002 pero la tabla material no existe (por ejemplo, porque se borró a
mano, como pasó en la EC2), no hay nada que respaldar y solo se crea la tabla nueva. El
downgrade restaura el respaldo si existe y, si no, crea la tabla del CRUD vacía, para que
la base siempre quede con el esquema de 0002.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RESPALDO = "material_crud_respaldo"
SECUENCIA = "seq_material"


def _existe_tabla(nombre: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(nombre)


def _respaldar_tabla_del_crud() -> None:
    if not _existe_tabla("material"):
        return
    # Los nombres de índices (y de la llave primaria) son únicos en el esquema: se renombran
    # para que la tabla nueva pueda usar los suyos.
    op.rename_table("material", RESPALDO)
    op.execute("ALTER TABLE material_crud_respaldo RENAME CONSTRAINT pk_material TO pk_material_crud_respaldo")
    op.execute("ALTER INDEX uq_material_nombre_lower RENAME TO uq_material_crud_respaldo_nombre_lower")


def _restaurar_tabla_del_crud() -> None:
    if not _existe_tabla(RESPALDO):
        _crear_tabla_del_crud()
        return
    op.execute("ALTER INDEX uq_material_crud_respaldo_nombre_lower RENAME TO uq_material_nombre_lower")
    op.execute("ALTER TABLE material_crud_respaldo RENAME CONSTRAINT pk_material_crud_respaldo TO pk_material")
    op.rename_table(RESPALDO, "material")


def _crear_tabla_del_crud() -> None:
    """Tabla material tal como la deja la migración 0002 (vacía)."""
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
        sa.CheckConstraint("categoria IN ('Materia Prima', 'Componentes', 'Lubricantes')", name=op.f("ck_material_categoria")),
        sa.CheckConstraint("unidad_medida IN ('und', 'g', 'kg', 'mL', 'L', 'm')", name=op.f("ck_material_unidad_medida")),
        sa.CheckConstraint("densidad > 0", name=op.f("ck_material_densidad_positiva")),
        sa.CheckConstraint("pureza >= 0 AND pureza <= 100", name=op.f("ck_material_pureza_rango")),
    )
    op.create_index("uq_material_nombre_lower", "material", [sa.text("lower(nombre)")], unique=True)


def upgrade() -> None:
    _respaldar_tabla_del_crud()
    op.execute(sa.schema.CreateSequence(sa.Sequence(SECUENCIA)))
    op.create_table(
        "material",
        sa.Column("id_material", sa.String(10), nullable=False),
        sa.Column("sku", sa.String(8), nullable=False),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("categoria", sa.String(15), nullable=False),
        sa.Column("unidad_medida", sa.String(3), nullable=False),
        sa.Column("densidad", sa.Numeric(8, 4), nullable=False),
        sa.Column("pureza", sa.Numeric(5, 2), nullable=False),
        sa.Column("estado", sa.String(8), nullable=False),
        sa.Column("fecha_registro", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id_material", name=op.f("pk_material")),
        sa.UniqueConstraint("sku", name=op.f("uq_material_sku")),
        sa.CheckConstraint("categoria IN ('Materia Prima', 'Componentes', 'Lubricantes')", name=op.f("ck_material_categoria")),
        sa.CheckConstraint("unidad_medida IN ('und', 'g', 'kg', 'mL', 'L', 'm')", name=op.f("ck_material_unidad_medida")),
        sa.CheckConstraint("densidad > 0", name=op.f("ck_material_densidad_positiva")),
        sa.CheckConstraint("pureza >= 0 AND pureza <= 100", name=op.f("ck_material_pureza_rango")),
        sa.CheckConstraint("estado IN ('ACTIVO', 'INACTIVO')", name=op.f("ck_material_estado")),
    )
    op.create_index("uq_material_nombre_lower", "material", [sa.text("lower(nombre)")], unique=True)


def downgrade() -> None:
    op.drop_table("material")
    op.execute(sa.schema.DropSequence(sa.Sequence(SECUENCIA)))
    _restaurar_tabla_del_crud()
