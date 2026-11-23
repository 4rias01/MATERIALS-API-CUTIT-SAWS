"""DTO del recurso /materiales (HU-01 y CRUD básico)."""

from datetime import datetime
from decimal import Decimal
from typing import Any, ClassVar, Self

from pydantic import Field, field_validator
from pydantic_core import ErrorDetails

from app.api.schemas.comun import DecimalEntrada, DecimalSalida, EsquemaEntrada, EsquemaSalida, error_de_negocio
from app.business.domain import mensajes
from app.business.domain.enums import Categoria, EstadoMaterial, UnidadMedida
from app.business.domain.errores import Motivo, ValorInvalidoError
from app.business.domain.value_objects import Densidad, NombreMaterial, Pureza, normalizar_nombre
from app.business.services.comandos import DatosMaterial, RegistrarMaterialComando

# ---------------------------------------------------------------------------------------
# Entrada
# ---------------------------------------------------------------------------------------


class MaterialCrearSolicitud(EsquemaEntrada):
    """Cuerpo de POST /materiales (HU-01 c1 y c2).

    Los campos se validan en el orden del criterio 1 y se responde 400 con el mensaje del
    primero que falla. Un campo enviado con ``null`` o un nombre vacío cuentan como
    omitidos (mensaje "es obligatorio"). Los campos desconocidos o de solo lectura (id,
    SKU, estado) se rechazan con 400 (OWASP A01/A08, asignación masiva).
    """

    mensajes_error: ClassVar[dict[tuple[str, str], str]] = {
        ("nombre", "missing"): mensajes.HU01_C2_1,
        ("nombre", "*"): mensajes.HU01_C2_2_B,  # p. ej. un número en vez de texto
        ("categoria", "missing"): mensajes.HU01_C2_3_A,
        ("categoria", "*"): mensajes.HU01_C2_3_B,
        ("unidadMedida", "missing"): mensajes.HU01_C2_4_A,
        ("unidadMedida", "*"): mensajes.HU01_C2_4_B,
        ("densidad", "missing"): mensajes.HU01_C2_5_A,
        ("densidad", "*"): mensajes.HU01_C2_5_B,
        ("pureza", "missing"): mensajes.HU01_C2_6_A,
        ("pureza", "*"): mensajes.HU01_C2_6_B,
    }

    nombre: str = Field(
        description="De 3 a 100 caracteres: letras con o sin tilde, ñ, dígitos, espacios y - . , / ( ) #. "
        "Se eliminan los espacios al inicio y al final y se reducen a uno los repetidos.",
        examples=["Acero al carbono 1045"],
    )
    categoria: Categoria = Field(examples=["Materia Prima"])
    unidad_medida: UnidadMedida = Field(examples=["kg"])
    densidad: DecimalEntrada = Field(
        description="Numérico, positivo, máximo 4 caracteres contando dígitos y punto decimal "
        "(los ceros a la derecha del decimal no cuentan).",
        examples=[7.85],
    )
    pureza: DecimalEntrada = Field(
        description="Numérico de 0 a 100 (%), máximo 3 caracteres contando dígitos y punto decimal.",
        examples=[98],
    )

    @classmethod
    def mensaje_para_error(cls, error: ErrorDetails, datos: Any) -> str | None:
        if error["type"] != "missing" and error.get("input", ...) is None:
            error = error.copy()
            error["type"] = "missing"
        return super().mensaje_para_error(error, datos)

    @field_validator("nombre")
    @classmethod
    def _validar_nombre(cls, valor: str) -> str:
        if not normalizar_nombre(valor):
            raise error_de_negocio(mensajes.HU01_C2_1)
        try:
            return NombreMaterial.crear(valor).valor
        except ValorInvalidoError as exc:
            mensaje = mensajes.HU01_C2_2_A if exc.motivo == Motivo.LONGITUD else mensajes.HU01_C2_2_B
            raise error_de_negocio(mensaje) from None

    @field_validator("densidad")
    @classmethod
    def _validar_densidad(cls, valor: Decimal) -> Decimal:
        try:
            return Densidad(valor).valor
        except ValorInvalidoError:
            raise error_de_negocio(mensajes.HU01_C2_5_B) from None

    @field_validator("pureza")
    @classmethod
    def _validar_pureza(cls, valor: Decimal) -> Decimal:
        try:
            return Pureza(valor).valor
        except ValorInvalidoError:
            raise error_de_negocio(mensajes.HU01_C2_6_B) from None

    def a_comando(self) -> RegistrarMaterialComando:
        return RegistrarMaterialComando(
            nombre=self.nombre,
            categoria=self.categoria.value,
            unidad_medida=self.unidad_medida.value,
            densidad=self.densidad,
            pureza=self.pureza,
        )


class MaterialActualizarSolicitud(EsquemaEntrada):
    """Cuerpo de PUT /materiales/{id} (CRUD básico; lo reemplazará HU-03).

    El id va en la ruta y el SKU y el estado no se editan: los campos desconocidos o de
    solo lectura se rechazan con 400 (OWASP A01/A08, asignación masiva).
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
    """Material del catálogo (GET y PUT del CRUD básico)."""

    material_id: str = Field(examples=["mat-001"])
    sku: str = Field(examples=["MP-00001"])
    nombre: str = Field(examples=["Acero al carbono 1045"])
    categoria: Categoria
    unidad_medida: UnidadMedida
    densidad: DecimalSalida = Field(examples=[7.85])
    pureza: DecimalSalida = Field(examples=[98])
    fecha_registro: datetime
    estado: EstadoMaterial
    fecha_ultima_actualizacion: datetime

    @classmethod
    def desde_modelo(cls, material: Any) -> Self:
        """Construye el DTO desde el Material que devuelve el servicio (la capa de
        presentación no importa los modelos de la capa de acceso a datos)."""
        return cls(**_campos(material))


class MaterialRegistradoRespuesta(MaterialRespuesta):
    """Material creado y mensaje (HU-01 c7: 201)."""

    mensaje: str = Field(examples=["Material 'Acero al carbono 1045' registrado exitosamente con el SKU MP-00001."])

    @classmethod
    def con_mensaje(cls, material: Any, mensaje: str) -> Self:
        return cls(**_campos(material), mensaje=mensaje)


def _campos(material: Any) -> dict[str, Any]:
    return {
        "material_id": material.id_material,
        "sku": material.sku,
        "nombre": material.nombre,
        "categoria": Categoria(material.categoria),
        "unidad_medida": UnidadMedida(material.unidad_medida),
        "densidad": Decimal(material.densidad),
        "pureza": Decimal(material.pureza),
        "fecha_registro": material.fecha_registro,
        "estado": EstadoMaterial(material.estado),
        "fecha_ultima_actualizacion": material.fecha_actualizacion,
    }
