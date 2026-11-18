"""DTO del recurso /materiales (CRUD básico)."""

from datetime import datetime
from typing import Any, Self

from pydantic import Field, field_validator
from pydantic_core import ErrorDetails

from app.api.schemas.comun import DecimalEntrada, DecimalSalida, EsquemaEntrada, EsquemaSalida
from app.business.domain import mensajes
from app.business.domain.enums import Categoria, UnidadMedida
from app.business.services.comandos import DatosMaterial

# ---------------------------------------------------------------------------------------
# Entrada
# ---------------------------------------------------------------------------------------


class MaterialSolicitud(EsquemaEntrada):
    """Cuerpo de POST /materiales y PUT /materiales/{id}.

    El id no viaja en el cuerpo (lo asigna la base de datos y en PUT va en la ruta), y
    los campos desconocidos o de solo lectura se rechazan con 400: el cliente no puede
    fijar valores que no le corresponden (OWASP A01/A08, asignación masiva).
    """

    nombre: str = Field(min_length=3, max_length=100, examples=["Acero al carbono 1045"])
    categoria: Categoria = Field(examples=["Materia Prima"])
    unidad_medida: UnidadMedida = Field(examples=["kg"])
    densidad: DecimalEntrada = Field(gt=0, max_digits=8, decimal_places=4, examples=[7.85])
    pureza: DecimalEntrada = Field(ge=0, le=100, max_digits=5, decimal_places=2, examples=[98])

    @field_validator("nombre", mode="before")
    @classmethod
    def _normalizar_nombre(cls, valor: Any) -> Any:
        """Quita los espacios al inicio y al final y reduce a uno los repetidos."""
        return " ".join(valor.split()) if isinstance(valor, str) else valor

    @classmethod
    def mensaje_para_error(cls, error: ErrorDetails, datos: Any) -> str | None:
        """Un mensaje por campo; los campos desconocidos usan el mensaje genérico."""
        if error["type"] == "extra_forbidden" or not error["loc"]:
            return None
        return mensajes.formatear(mensajes.MATERIAL_CAMPO_INVALIDO, campo=error["loc"][0])

    def a_datos(self) -> DatosMaterial:
        return DatosMaterial(
            nombre=self.nombre,
            categoria=self.categoria.value,
            unidad_medida=self.unidad_medida.value,
            densidad=self.densidad,
            pureza=self.pureza,
        )


# ---------------------------------------------------------------------------------------
# Salida
# ---------------------------------------------------------------------------------------


class MaterialRespuesta(EsquemaSalida):
    id: int = Field(examples=[1])
    nombre: str = Field(examples=["Acero al carbono 1045"])
    categoria: Categoria
    unidad_medida: UnidadMedida
    densidad: DecimalSalida = Field(examples=[7.85])
    pureza: DecimalSalida = Field(examples=[98])
    fecha_registro: datetime
    fecha_actualizacion: datetime

    @classmethod
    def desde_modelo(cls, material: Any) -> Self:
        """Construye el DTO desde el Material que devuelve el servicio (la capa de
        presentación no importa los modelos de la capa de acceso a datos)."""
        return cls(
            id=material.id_material,
            nombre=material.nombre,
            categoria=Categoria(material.categoria),
            unidad_medida=UnidadMedida(material.unidad_medida),
            densidad=material.densidad,
            pureza=material.pureza,
            fecha_registro=material.fecha_registro,
            fecha_actualizacion=material.fecha_actualizacion,
        )
