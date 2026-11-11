"""Bases de los DTO (patrones DTO y Canonical Schema).

* JSON en camelCase en todos los contratos (``unidad_medida`` → ``unidadMedida``).
* Los DTO de entrada rechazan campos desconocidos o de solo lectura (``extra="forbid"``).
* Los errores de validación se traducen al mensaje del backlog con la tabla
  ``mensajes_error`` de cada DTO o con el método ``mensaje_para_error``; el manejador
  global responde 400 con ese mensaje. Los validadores de campo también pueden lanzar
  ``error_de_negocio(mensaje)`` directamente.

Ejemplo (TODO de cada HU)::

    class MaterialCrearSolicitud(EsquemaEntrada):
        mensajes_error = {
            ("nombre", "missing"): mensajes.HU01_C2_1,
            ("categoria", "*"): mensajes.HU01_C2_3_B,  # "*" = cualquier error del campo
        }
"""

from collections.abc import Mapping
from decimal import Decimal
from typing import Annotated, Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, ValidationError, WithJsonSchema, model_validator
from pydantic.alias_generators import to_camel
from pydantic_core import ErrorDetails, PydanticCustomError

from app.business.domain.mensajes import formatear, marcadores

# Tipo de error que reconoce el manejador global: su texto es el mensaje para el cliente.
TIPO_ERROR_NEGOCIO = "mensaje_negocio"


def error_de_negocio(mensaje: str) -> PydanticCustomError:
    """Error de validación cuyo texto se devuelve tal cual al cliente (400)."""
    return PydanticCustomError(TIPO_ERROR_NEGOCIO, "{mensaje}", {"mensaje": mensaje})


def _decimal_a_json(valor: Decimal) -> int | float:
    return int(valor) if valor == valor.to_integral_value() else float(valor)


# Número decimal en la entrada: se documenta como "number" (también acepta texto numérico).
DecimalEntrada = Annotated[Decimal, WithJsonSchema({"type": "number"})]
# Número decimal en la salida: se escribe como número JSON (2 en vez de "2.000").
DecimalSalida = Annotated[
    Decimal,
    PlainSerializer(_decimal_a_json, return_type=int | float, when_used="json"),
    WithJsonSchema({"type": "number"}),
]


def _titulo(nombre: str, _: Any) -> str:
    return to_camel(nombre)


class EsquemaBase(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, serialize_by_alias=True, field_title_generator=_titulo)


class EsquemaEntrada(EsquemaBase):
    """Base de los DTO de entrada (cuerpo JSON o parámetros de consulta)."""

    model_config = ConfigDict(validate_by_alias=True, validate_by_name=False, extra="forbid")

    # (campo en camelCase, tipo de error de Pydantic o "*") -> mensaje del backlog.
    # Los tipos más comunes: "missing", "extra_forbidden", "enum", "string_too_long",
    # "string_pattern_mismatch", "int_parsing", "greater_than_equal", "decimal_parsing".
    mensajes_error: ClassVar[Mapping[tuple[str, str], str]] = {}

    @classmethod
    def mensaje_para_error(cls, error: ErrorDetails, datos: Any) -> str | None:
        """Mensaje del backlog para el primer error de validación (None = mensaje genérico).

        Se puede sobrescribir cuando el mensaje depende de otros datos de la solicitud
        (por ejemplo, el ID del material de la línea con la cantidad errónea).
        """
        campo = str(error["loc"][0]) if error["loc"] else ""
        plantilla = cls.mensajes_error.get((campo, error["type"])) or cls.mensajes_error.get((campo, "*"))
        if plantilla is None:
            return None
        if "valor" in marcadores(plantilla):
            valor = "" if error["type"] == "missing" else error.get("input", "")
            return formatear(plantilla, valor=valor)
        return plantilla

    @model_validator(mode="wrap")
    @classmethod
    def _traducir_errores(cls, datos: Any, siguiente: Any) -> Any:
        try:
            return siguiente(datos)
        except ValidationError as exc:
            errores = exc.errors()
            if not errores or errores[0]["type"] == TIPO_ERROR_NEGOCIO:
                raise
            mensaje = cls.mensaje_para_error(errores[0], datos)
            if mensaje is None:
                raise
            raise error_de_negocio(mensaje) from None


class EsquemaSalida(EsquemaBase):
    """Base de los DTO de salida: se construyen con los nombres de Python."""

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)


class ErrorRespuesta(EsquemaSalida):
    """Cuerpo de toda respuesta de error."""

    mensaje: str = Field(examples=["El material solicitado con ID 'mat-999' no fue encontrado en el catálogo"])
    trace_id: str = Field(examples=["3f2a9c1e5b7d4e8f9a0b1c2d3e4f5a6b"], description="Identificador para rastrear el error en los logs.")


class MensajeRespuesta(EsquemaSalida):
    """Respuesta que solo lleva un mensaje."""

    mensaje: str


_DESCRIPCIONES = {
    400: "Solicitud con campos faltantes, no permitidos o con formato no válido.",
    404: "El recurso no existe.",
    409: "Conflicto con el estado actual del recurso.",
    422: "La solicitud incumple una regla de negocio.",
    500: "Error interno (base de datos o timeout); incluye el traceId.",
    503: "La API de otra célula no respondió, falló o tardó más de 5 s.",
}


def respuestas_error(*codigos: int) -> dict[int | str, dict[str, Any]]:
    """Documenta en OpenAPI las respuestas de error de una ruta."""
    return {codigo: {"model": ErrorRespuesta, "description": _DESCRIPCIONES[codigo]} for codigo in codigos}


# Clave de ``openapi_extra`` con el mensaje 400 de una ruta cuando falla la validación de
# la ruta o de parámetros que no tienen su propio mensaje (HU-04 c3, HU-08 c3).
CLAVE_MENSAJE_SOLICITUD_INVALIDA = "x-mensaje-solicitud-invalida"


def mensaje_solicitud_invalida(mensaje: str) -> dict[str, str]:
    """Valor para ``openapi_extra`` de una ruta."""
    return {CLAVE_MENSAJE_SOLICITUD_INVALIDA: mensaje}
