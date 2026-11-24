"""Contrato de POST /formulas (HU-05)."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Self

from pydantic import Field, ValidationInfo, field_validator
from pydantic_core import ErrorDetails

from app.api.schemas.comun import DecimalEntrada, DecimalSalida, EsquemaEntrada, EsquemaSalida, error_de_negocio
from app.business.domain import mensajes
from app.business.domain.enums import EstadoFormula, UnidadMedida
from app.business.domain.formulas import AplicacionTecnica, ComponenteFormula, NombreFormula, validar_componentes
from app.business.services.comandos import RegistrarFormulaComando
from app.core.exceptions import SolicitudInvalidaError


class ComponenteCrearSolicitud(EsquemaEntrada):
    material_id: str = Field(pattern=r"^mat-[0-9]{3,}$", examples=["mat-001"])
    cantidad: DecimalEntrada = Field(description="Mayor que 0, máximo 6 enteros y 3 decimales; entera para und.")

    @classmethod
    def mensaje_para_error(cls, error: ErrorDetails, datos: Any) -> str | None:
        campo = error["loc"][0] if error["loc"] else ""
        if campo == "unidadMedida":
            return mensajes.HU05_C9_4
        if campo == "cantidad" and isinstance(datos, dict):
            plantilla = mensajes.HU05_C2_4 if error["type"] == "missing" or datos.get("cantidad") is None else mensajes.HU05_C3_1
            return mensajes.formatear(plantilla, IDMaterial=datos.get("materialId", ""), Cantidad=datos.get("cantidad"))
        return None

    @field_validator("cantidad", mode="before")
    @classmethod
    def _validar_cantidad(cls, valor: Any, info: ValidationInfo) -> Decimal:
        material_id = info.data.get("material_id", "")
        if valor is None:
            raise error_de_negocio(mensajes.formatear(mensajes.HU05_C2_4, IDMaterial=material_id))
        # Si falla el ID, Pydantic conserva primero ese error.
        if not material_id:
            return valor
        try:
            return ComponenteFormula(material_id, valor).cantidad
        except SolicitudInvalidaError as exc:
            raise error_de_negocio(exc.mensaje) from None


class FormulaCrearSolicitud(EsquemaEntrada):
    nombre: str = Field(description="Texto alfabético, máximo 80 caracteres.", examples=["Mezcla de corte"])
    aplicacion_tecnica: str = Field(description="Texto alfanumérico, máximo 200 caracteres.", examples=["Corte de acero 1045"])
    componentes: list[ComponenteCrearSolicitud] = Field(description="Mínimo dos materiales distintos del catálogo.")

    @classmethod
    def mensaje_para_error(cls, error: ErrorDetails, datos: Any) -> str | None:
        campo = error["loc"][0] if error["loc"] else ""
        omitido = error["type"] == "missing" or error.get("input", ...) is None
        if campo == "nombre":
            return mensajes.HU05_C2_1 if omitido else mensajes.HU05_C9_1_B
        if campo == "aplicacionTecnica":
            return mensajes.HU05_C2_2 if omitido else None
        if campo == "componentes" and omitido:
            return mensajes.HU05_C2_3
        return None

    @field_validator("nombre")
    @classmethod
    def _validar_nombre(cls, valor: str) -> str:
        try:
            return NombreFormula.crear(valor).valor
        except SolicitudInvalidaError as exc:
            raise error_de_negocio(exc.mensaje) from None

    @field_validator("aplicacion_tecnica")
    @classmethod
    def _validar_aplicacion(cls, valor: str) -> str:
        try:
            return AplicacionTecnica(valor).valor
        except SolicitudInvalidaError as exc:
            raise error_de_negocio(exc.mensaje) from None

    @field_validator("componentes")
    @classmethod
    def _validar_componentes(cls, valor: list[ComponenteCrearSolicitud]) -> list[ComponenteCrearSolicitud]:
        try:
            validar_componentes(tuple(ComponenteFormula(c.material_id, c.cantidad) for c in valor))
        except SolicitudInvalidaError as exc:
            raise error_de_negocio(exc.mensaje) from None
        return valor

    def a_comando(self) -> RegistrarFormulaComando:
        return RegistrarFormulaComando(
            self.nombre, self.aplicacion_tecnica, tuple(ComponenteFormula(c.material_id, c.cantidad) for c in self.componentes)
        )


class ComponenteRegistradoRespuesta(EsquemaSalida):
    sku: str
    nombre: str
    cantidad: DecimalSalida
    unidad_medida: UnidadMedida


class FormulaRegistradaRespuesta(EsquemaSalida):
    """Ficha técnica requerida por HU-05 c6.2, sin implementar la consulta de HU-06."""

    formula_id: str
    nombre: str
    aplicacion_tecnica: str
    version: int
    estado: EstadoFormula
    fecha_registro: datetime
    fecha_ultima_actualizacion: datetime
    componentes: list[ComponenteRegistradoRespuesta]
    mensaje: str

    @classmethod
    def con_mensaje(cls, formula: Any, mensaje: str) -> Self:
        return cls(
            formula_id=formula.id_formula,
            nombre=formula.nombre,
            aplicacion_tecnica=formula.aplicacion_tecnica,
            version=formula.version,
            estado=EstadoFormula(formula.estado),
            fecha_registro=formula.fecha_registro,
            fecha_ultima_actualizacion=formula.fecha_actualizacion,
            componentes=[
                ComponenteRegistradoRespuesta(
                    sku=c.material.sku, nombre=c.material.nombre, cantidad=c.cantidad,
                    unidad_medida=UnidadMedida(c.material.unidad_medida),
                )
                for c in formula.componentes
            ],
            mensaje=mensaje,
        )
