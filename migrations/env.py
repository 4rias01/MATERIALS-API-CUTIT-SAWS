"""Entorno de Alembic con SQLAlchemy asíncrono (asyncpg).

La URL se toma, en este orden, de ``sqlalchemy.url`` (si un script la fija con
``Config.set_main_option``) o de la configuración de la API (DATABASE_URL o POSTGRES_*).
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import obtener_configuracion
from app.infraestructure.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata

# Tablas que existen en la base a propósito sin modelo ORM: el autogenerate no las borra
# ni las compara. material_crud_respaldo: filas del CRUD básico (migración 0003).
TABLAS_SIN_MODELO = {"material_crud_respaldo"}


def _incluir_objeto(objeto: object, nombre: str | None, tipo: str, reflejado: bool, comparar_con: object) -> bool:
    return not (tipo == "table" and nombre in TABLAS_SIN_MODELO)


def _url() -> str:
    return config.get_main_option("sqlalchemy.url") or obtener_configuracion().url_base_datos


def _configurar(**opciones: object) -> None:
    context.configure(
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_object=_incluir_objeto,
        **opciones,
    )


def run_migrations_offline() -> None:
    """Genera el SQL sin conectarse (``alembic upgrade head --sql``)."""
    _configurar(url=_url(), literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def _ejecutar(conexion: Connection) -> None:
    _configurar(connection=conexion)
    with context.begin_transaction():
        context.run_migrations()


async def _ejecutar_async() -> None:
    motor = create_async_engine(_url(), poolclass=NullPool)
    async with motor.connect() as conexion:
        await conexion.run_sync(_ejecutar)
    await motor.dispose()


def run_migrations_online() -> None:
    asyncio.run(_ejecutar_async())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
