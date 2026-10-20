"""DTO de GET /health."""

from typing import Literal

from pydantic import Field

from app.presentation.schemas.comun import EsquemaSalida


class SaludRespuesta(EsquemaSalida):
    estado: Literal["OK", "DEGRADADO"] = Field(description="DEGRADADO si la base de datos no responde (HTTP 503).")
    version: str = Field(examples=["0.1.0"])
    base_datos: Literal["OK", "ERROR"]
    circuitos: dict[str, str] = Field(
        description="Estado del circuit breaker de cada API externa: CERRADO, ABIERTO o SEMIABIERTO.",
        examples=[{"inventario": "CERRADO", "patentSweep": "CERRADO"}],
    )
