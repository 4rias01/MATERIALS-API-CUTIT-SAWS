"""DTO del recurso /formulas (HU-05 a HU-08 y HU-11)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Self

from pydantic import BeforeValidator, Field, WithJsonSchema
from pydantic_core import PydanticCustomError

from app.business.domain.enums import EstadoFormula, ResultadoDictamen, UnidadMedida
from app.business.services.comandos import (
    ActualizarFormulaComando,
    ComponenteComando,
    ConsultaFormulas,
    RegistrarFormulaComando,
)
from app.core.config import obtener_configuracion
from app.core.paginacion import Pagina
from app.presentation.schemas.comun import DecimalEntrada, DecimalSalida, EsquemaEntrada, EsquemaSalida

# ---------------------------------------------------------------------------------------
# Tipos auxiliares
# ---------------------------------------------------------------------------------------


def _fecha_dd_mm_aaaa(valor: Any) -> Any:
    """Convierte 'DD/MM/AAAA' en date. Un texto mal formado produce el error "fecha_ddmmaaaa"."""
    if valor is None or isinstance(valor, date):
        return valor
    try:
        return datetime.strptime(str(valor), "%d/%m/%Y").date()
    except ValueError:
        raise PydanticCustomError("fecha_ddmmaaaa", "Formato de fecha no válido: use DD/MM/AAAA") from None


FechaDDMMAAAA = Annotated[
    date,
    BeforeValidator(_fecha_dd_mm_aaaa),
    WithJsonSchema({"type": "string", "pattern": r"^\d{2}/\d{2}/\d{4}$", "examples": ["31/01/2026"]}),
]

# ---------------------------------------------------------------------------------------
# Entrada
# ---------------------------------------------------------------------------------------


class ComponenteSolicitud(EsquemaEntrada):
    """Línea de la tabla de componentes (HU-05 c1, HU-07 c2). La Unidad de medida no se
    envía: el sistema la toma del material registrado."""

    material_id: str = Field(examples=["mat-001"])
    cantidad: DecimalEntrada = Field(
        description="Mayor que 0, máximo 6 dígitos enteros y 3 decimales; entera si la unidad es und.",
        examples=[2.5],
    )


class FormulaCrearSolicitud(EsquemaEntrada):
    """Cuerpo de POST /formulas (HU-05 c1).

    TODO(HU-05 c2 y c3):
    * ``mensajes_error``: ("nombre", "missing") → ``HU05_C2_1``; ("aplicacionTecnica", "missing")
      → ``HU05_C2_2``; ("componentes", "missing") → ``HU05_C2_3``.
    * Sobrescribir ``mensaje_para_error`` para la cantidad faltante de una línea
      (loc ``("componentes", i, "cantidad")``) → ``HU05_C2_4`` con [IDMaterial] de esa línea.
    * ``@field_validator("componentes")``: ``MinimoMaterialesDistintos(2)`` → ``HU05_C2_3``;
      ``Cantidad(valor)`` con motivo NO_POSITIVO → ``HU05_C3_1``, DEMASIADOS_DIGITOS →
      ``HU05_C3_2`` (marcadores [IDMaterial] y [Cantidad]).
    * El backlog no define mensajes para nombre > 80, aplicación técnica > 200, nombre no
      alfabético ni líneas repetidas del mismo material (ver README).
    """

    nombre: str = Field(max_length=80, description="Texto alfabético, máximo 80 caracteres.", examples=["Aleación corte rápido"])
    aplicacion_tecnica: str = Field(
        max_length=200,
        description="Uso técnico previsto en la fabricación de las cuchillas; máximo 200 caracteres.",
        examples=["Cuchillas para corte de madera dura"],
    )
    componentes: list[ComponenteSolicitud] = Field(description="Mínimo 2 materiales diferentes.")

    def a_comando(self) -> RegistrarFormulaComando:
        return RegistrarFormulaComando(
            nombre=self.nombre,
            aplicacion_tecnica=self.aplicacion_tecnica,
            componentes=tuple(ComponenteComando(c.material_id, c.cantidad) for c in self.componentes),
        )


class FormulaActualizarSolicitud(EsquemaEntrada):
    """Cuerpo de PUT /formulas/{id} (HU-07 c2). El código form-NNN es de solo lectura.

    TODO(HU-07 c3): como en HU-05, con ``HU07_C3_1`` a ``HU07_C3_5``.
    """

    nombre: str = Field(max_length=80, examples=["Aleación corte rápido"])
    aplicacion_tecnica: str = Field(max_length=200, examples=["Cuchillas para corte de madera dura"])
    componentes: list[ComponenteSolicitud]

    def a_comando(self) -> ActualizarFormulaComando:
        return ActualizarFormulaComando(
            nombre=self.nombre,
            aplicacion_tecnica=self.aplicacion_tecnica,
            componentes=tuple(ComponenteComando(c.material_id, c.cantidad) for c in self.componentes),
        )


class FiltrosFormulasConsulta(EsquemaEntrada):
    """Parámetros de GET /formulas (HU-06 c1). Todos son opcionales y se combinan.

    Los nombres de los parámetros son propuesta del equipo (el backlog no los fija).

    TODO(HU-06 c5):
    * ``mensajes_error``: ("buscar", "string_too_long") → ``HU06_C5_5``; ("estado", "enum") →
      ``HU06_C5_4`` con [Estado] (sobrescribir ``mensaje_para_error``); errores
      "fecha_ddmmaaaa" de las fechas → ``HU06_C5_2`` con [NombreFiltro]; parámetro desconocido
      ("extra_forbidden") → ``HU06_C5_1`` con [NombreParametro].
    * ``@model_validator(mode="after")``: fecha "desde" posterior a "hasta" → ``HU06_C5_3``.
    """

    buscar: str | None = Field(
        default=None,
        max_length=80,
        description="Coincidencia parcial en el código o el nombre, sin distinguir mayúsculas.",
    )
    estado: EstadoFormula | None = None
    fecha_registro_desde: FechaDDMMAAAA | None = Field(default=None, description="DD/MM/AAAA")
    fecha_registro_hasta: FechaDDMMAAAA | None = Field(default=None, description="DD/MM/AAAA")
    fecha_actualizacion_desde: FechaDDMMAAAA | None = Field(default=None, description="DD/MM/AAAA")
    fecha_actualizacion_hasta: FechaDDMMAAAA | None = Field(default=None, description="DD/MM/AAAA")
    materiales: list[str] = Field(
        default_factory=list,
        description="IDs de material; devuelve las fórmulas que contienen todos (repetir el parámetro).",
    )
    pagina: int = Field(default=1, ge=1, description="Número de página (páginas de 10 fórmulas).")

    def a_consulta(self) -> ConsultaFormulas:
        return ConsultaFormulas(
            texto=self.buscar,
            estado=self.estado.value if self.estado else None,
            registro_desde=self.fecha_registro_desde,
            registro_hasta=self.fecha_registro_hasta,
            actualizacion_desde=self.fecha_actualizacion_desde,
            actualizacion_hasta=self.fecha_actualizacion_hasta,
            materiales=tuple(self.materiales),
            pagina=self.pagina,
        )


class PaginacionAprobadasConsulta(EsquemaEntrada):
    """Parámetros de GET /formulas/aprobadas (HU-11 c1).

    TODO(HU-11 c6): ``mensajes_error`` con ("pagina", "*") → ``HU11_C6_1`` y
    ("tamanoPagina", "*") → ``HU11_C6_2``.
    """

    pagina: int = Field(default=1, ge=1, description="Número de página, entero ≥ 1.")
    tamano_pagina: int = Field(
        default=obtener_configuracion().aprobadas_tamano_pagina_defecto,
        ge=1,
        le=100,
        description="Fórmulas por página, entero de 1 a 100.",
    )


# ---------------------------------------------------------------------------------------
# Salida
# ---------------------------------------------------------------------------------------


class ComponenteRespuesta(EsquemaSalida):
    """Componente con los datos de su material (HU-06 c3, HU-11 c3.7)."""

    material_id: str = Field(examples=["mat-001"])
    sku: str = Field(examples=["MP-00001"])
    nombre: str
    cantidad: DecimalSalida = Field(examples=[2.5])
    unidad_medida: UnidadMedida

    @classmethod
    def desde_modelo(cls, componente: Any) -> Self:
        """``componente`` es un ComponenteFormula con su ``material`` cargado."""
        material = componente.material
        return cls(
            material_id=componente.id_material,
            sku=material.sku,
            nombre=material.nombre,
            cantidad=Decimal(componente.cantidad),
            unidad_medida=material.unidad_medida,
        )


class PatenteConflictoRespuesta(EsquemaSalida):
    """Patente en conflicto registrada por el dictamen (HU-06 c4)."""

    conflicto_id: str = Field(examples=["123456"])
    titulo: str


class FormulaRespuesta(EsquemaSalida):
    """Ficha técnica de la fórmula (HU-06 c3 y c4) y respuesta de HU-05 (201) y HU-07 (200).

    ``patentesEnConflicto`` solo aparece si la fórmula está RECHAZADA_POR_INFRACCION.
    """

    formula_id: str = Field(examples=["form-001"])
    nombre: str
    aplicacion_tecnica: str
    version: int = Field(ge=1)
    estado: EstadoFormula
    fecha_registro: datetime
    fecha_ultima_actualizacion: datetime
    componentes: list[ComponenteRespuesta]
    patentes_en_conflicto: list[PatenteConflictoRespuesta] | None = None
    mensaje: str | None = None

    @classmethod
    def desde_modelo(cls, formula: Any, mensaje: str | None = None) -> Self:
        """``formula`` es un modelo Formula con sus componentes cargados (y sus evaluaciones
        si está RECHAZADA_POR_INFRACCION)."""
        patentes = None
        if formula.estado == EstadoFormula.RECHAZADA_POR_INFRACCION:
            ultimo = next(
                (e for e in reversed(formula.evaluaciones) if e.resultado == ResultadoDictamen.INFRACCION), None
            )
            patentes = [
                PatenteConflictoRespuesta(conflicto_id=p.conflicto_id, titulo=p.titulo)
                for p in (ultimo.patentes if ultimo else [])
            ]
        return cls(
            formula_id=formula.id_formula,
            nombre=formula.nombre,
            aplicacion_tecnica=formula.aplicacion_tecnica,
            version=formula.version,
            estado=formula.estado,
            fecha_registro=formula.fecha_registro,
            fecha_ultima_actualizacion=formula.fecha_actualizacion,
            componentes=[ComponenteRespuesta.desde_modelo(c) for c in formula.componentes],
            patentes_en_conflicto=patentes,
            mensaje=mensaje,
        )


class FormulaResumenRespuesta(EsquemaSalida):
    """Columna del listado de fórmulas (HU-06 c2)."""

    formula_id: str = Field(examples=["form-001"])
    nombre: str
    aplicacion_tecnica: str
    estado: EstadoFormula
    fecha_ultima_actualizacion: datetime

    @classmethod
    def desde_modelo(cls, formula: Any) -> Self:
        return cls(
            formula_id=formula.id_formula,
            nombre=formula.nombre,
            aplicacion_tecnica=formula.aplicacion_tecnica,
            estado=formula.estado,
            fecha_ultima_actualizacion=formula.fecha_actualizacion,
        )


class FormulasPaginaRespuesta(EsquemaSalida):
    """Listado de fórmulas (HU-06 c2 y c6.1)."""

    pagina: int
    tamano_pagina: int
    total_registros: int
    total_paginas: int
    formulas: list[FormulaResumenRespuesta]
    mensaje: str | None = None

    @classmethod
    def desde_pagina(cls, pagina: Pagina[Any], mensaje: str | None = None) -> Self:
        return cls(
            pagina=pagina.pagina,
            tamano_pagina=pagina.tamano_pagina,
            total_registros=pagina.total_registros,
            total_paginas=pagina.total_paginas,
            formulas=[FormulaResumenRespuesta.desde_modelo(f) for f in pagina.elementos],
            mensaje=mensaje,
        )


class FormulaAprobadaRespuesta(EsquemaSalida):
    """Fórmula del listado de aprobadas (HU-11 c3)."""

    formula_id: str = Field(examples=["form-001"])
    nombre: str
    aplicacion_tecnica: str
    version: int = Field(ge=1)
    estado: EstadoFormula
    fecha_ultima_actualizacion: datetime
    componentes: list[ComponenteRespuesta]

    @classmethod
    def desde_modelo(cls, formula: Any) -> Self:
        return cls(
            formula_id=formula.id_formula,
            nombre=formula.nombre,
            aplicacion_tecnica=formula.aplicacion_tecnica,
            version=formula.version,
            estado=formula.estado,
            fecha_ultima_actualizacion=formula.fecha_actualizacion,
            componentes=[ComponenteRespuesta.desde_modelo(c) for c in formula.componentes],
        )


class FormulasAprobadasRespuesta(EsquemaSalida):
    """Respuesta de GET /formulas/aprobadas (HU-11 c2, c4 y c5)."""

    pagina: int = Field(ge=1)
    tamano_pagina: int = Field(ge=1, le=100)
    total_registros: int = Field(ge=0)
    total_paginas: int = Field(ge=0)
    formulas: list[FormulaAprobadaRespuesta]
    mensaje: str | None = None

    @classmethod
    def desde_pagina(cls, pagina: Pagina[Any], mensaje: str | None = None) -> Self:
        return cls(
            pagina=pagina.pagina,
            tamano_pagina=pagina.tamano_pagina,
            total_registros=pagina.total_registros,
            total_paginas=pagina.total_paginas,
            formulas=[FormulaAprobadaRespuesta.desde_modelo(f) for f in pagina.elementos],
            mensaje=mensaje,
        )


class FormulaEstadoRespuesta(EsquemaSalida):
    """Resultado de la descontinuación (HU-08 c2)."""

    formula_id: str = Field(examples=["form-001"])
    estado: EstadoFormula
    mensaje: str = Field(examples=["Fórmula descontinuada exitosamente."])

    @classmethod
    def desde_modelo(cls, formula: Any, mensaje: str) -> Self:
        return cls(formula_id=formula.id_formula, estado=formula.estado, mensaje=mensaje)
