"""Motor y sesiones de SQLAlchemy asíncrono sobre PostgreSQL (driver asyncpg).

* Object Pool: el motor mantiene un pool de conexiones que se reutilizan entre
  peticiones (``DB_POOL_SIZE`` y ``DB_MAX_OVERFLOW``).
* Timeout de 5 s (``DB_TIMEOUT_S``) para conectar, para esperar una conexión libre del
  pool y para cada sentencia (``statement_timeout`` en el servidor y
  ``command_timeout`` en el driver).
"""

import asyncpg
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Configuracion
from app.core.exceptions import ErrorBaseDatos, ErrorIntegridadDatos

# Excepciones que significan "falló la base de datos". OSError incluye la conexión
# rechazada y el timeout de conexión, que asyncpg lanza sin envolver.
ERRORES_BASE_DATOS: tuple[type[BaseException], ...] = (
    SQLAlchemyError,
    OSError,
    asyncpg.PostgresError,
    asyncpg.InterfaceError,
)


def crear_motor(config: Configuracion) -> AsyncEngine:
    """Crea el motor con su pool de conexiones (se crea una vez, en el arranque de la API)."""
    timeout = config.db_timeout_s
    return create_async_engine(
        config.url_base_datos,
        pool_size=config.db_pool_size,
        max_overflow=config.db_max_overflow,
        pool_timeout=timeout,
        pool_pre_ping=True,
        connect_args={
            "timeout": timeout,
            "command_timeout": timeout,
            "server_settings": {
                "statement_timeout": str(int(timeout * 1000)),
                "application_name": config.nombre_servicio,
            },
        },
    )


def crear_fabrica_sesiones(motor: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Fábrica de sesiones. ``expire_on_commit=False`` permite leer los objetos después
    del commit sin volver a consultar (en modo asíncrono no hay carga perezosa)."""
    return async_sessionmaker(motor, expire_on_commit=False)


def traducir_error_base_datos(exc: BaseException) -> ErrorBaseDatos:
    """Convierte una excepción del driver o del ORM en ``ErrorBaseDatos``.

    Para las violaciones de restricciones devuelve ``ErrorIntegridadDatos`` con el
    nombre de la restricción (por ejemplo ``uq_material_nombre_lower``), útil para
    responder 409 si dos peticiones registran el mismo nombre a la vez.
    """
    if isinstance(exc, IntegrityError):
        causa = getattr(exc.orig, "__cause__", None)
        restriccion = getattr(causa, "constraint_name", None)
        return ErrorIntegridadDatos(f"Violación de integridad: {restriccion or exc.orig}", restriccion)
    return ErrorBaseDatos(f"{type(exc).__name__}: {exc}")
