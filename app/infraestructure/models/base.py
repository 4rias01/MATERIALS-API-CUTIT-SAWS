"""Base declarativa de SQLAlchemy y secuencias de los identificadores."""

from sqlalchemy import MetaData, Sequence
from sqlalchemy.orm import DeclarativeBase

# Nombres predecibles para restricciones e índices (los usa Alembic y los mensajes de error).
CONVENCION_NOMBRES = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=CONVENCION_NOMBRES)


# Secuencias de los consecutivos mat-NNN, form-NNN y tck-NNN. Un número consumido en una
# transacción que se revierte no se reutiliza (puede haber saltos en la numeración).
SECUENCIA_MATERIAL = Sequence("seq_material", metadata=Base.metadata)
SECUENCIA_FORMULA = Sequence("seq_formula", metadata=Base.metadata)
SECUENCIA_TICKET_EVALUACION = Sequence("seq_ticket_evaluacion", metadata=Base.metadata)


def lista_sql(valores: tuple[str, ...]) -> str:
    """Valores para una restricción CHECK ... IN (...)."""
    return ", ".join(f"'{v}'" for v in valores)
