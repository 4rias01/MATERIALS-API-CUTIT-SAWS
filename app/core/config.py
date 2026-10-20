"""Configuración externalizada (patrón Externalized Configuration).

Toda la configuración se lee de variables de entorno (en desarrollo también de un
archivo ``.env``) con pydantic-settings. La misma imagen Docker corre en cualquier
entorno cambiando solo estas variables: URLs de las otras APIs, timeouts, tamaños
de página y credenciales.

Los valores marcados como POR ACORDAR dependen de las células de Inventario y
Patent Sweep y deben confirmarse con ellas antes de desplegar.
"""

from functools import lru_cache
from typing import Literal
from urllib.parse import quote

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracion(BaseSettings):
    """Variables de entorno de la API (el nombre de la variable es el del campo en mayúsculas)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Aplicación -------------------------------------------------------------
    app_nombre: str = "API Materiales y Fórmulas"
    app_version: str = "0.1.0"
    entorno: Literal["desarrollo", "pruebas", "produccion"] = "desarrollo"
    log_nivel: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    # Se envía en la cabecera X-Servicio-Origen de las llamadas salientes.
    nombre_servicio: str = "materiales-formulas"
    # Publica /docs (Swagger UI), /redoc y /openapi.json.
    docs_habilitada: bool = True

    # --- Base de datos (PostgreSQL) ------------------------------------------------
    # Si DATABASE_URL está definida, tiene prioridad sobre las variables POSTGRES_*.
    database_url: str | None = None
    postgres_user: str = "materiales"
    postgres_password: str = "materiales"
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "materiales_formulas"
    # Object Pool: conexiones reutilizadas entre peticiones.
    db_pool_size: int = Field(default=5, ge=1)
    db_max_overflow: int = Field(default=5, ge=0)
    # Timeout de 5 s para conectar, esperar una conexión del pool y ejecutar cada sentencia.
    db_timeout_s: float = Field(default=5.0, gt=0)

    # --- Integraciones HTTP (timeout de 5 s) ------------------------------------------
    http_timeout_s: float = Field(default=5.0, gt=0)
    # POR ACORDAR con la célula de Inventario: URL base de su API.
    inventario_url: str | None = None
    # Rutas definidas en el backlog (HU-01 c4 y HU-03 c4).
    inventario_ruta_materias_primas: str = "/inventario/materias-primas"
    inventario_ruta_articulo: str = "/inventario/articulos/{codigo}"
    # POR ACORDAR con la célula de Patent Sweep: URL base y ruta de la solicitud de evaluación (HU-09).
    patent_sweep_url: str | None = None
    patent_sweep_ruta_evaluacion: str | None = None
    # Circuit Breaker de cada cliente: fallos seguidos para abrir y segundos que permanece abierto.
    cb_umbral_fallos: int = Field(default=5, ge=1)
    cb_tiempo_abierto_s: float = Field(default=30.0, gt=0)

    # --- Paginación --------------------------------------------------------------------
    # HU-06 c2: el listado de fórmulas se presenta en páginas de 10 registros.
    formulas_tamano_pagina: int = Field(default=10, ge=1)
    # HU-11 c1: tamaño de página por defecto de GET /formulas/aprobadas (el máximo, 100, es del contrato).
    aprobadas_tamano_pagina_defecto: int = Field(default=50, ge=1, le=100)

    @property
    def url_base_datos(self) -> str:
        """URL de conexión de SQLAlchemy con el driver asíncrono asyncpg."""
        if self.database_url:
            return self.database_url
        usuario = quote(self.postgres_user, safe="")
        clave = quote(self.postgres_password, safe="")
        return (
            f"postgresql+asyncpg://{usuario}:{clave}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def obtener_configuracion() -> Configuracion:
    """Devuelve la configuración leída una sola vez por proceso."""
    return Configuracion()
