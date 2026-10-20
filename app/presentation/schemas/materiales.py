"""DTO del recurso /materiales (HU-01 a HU-04)."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Self

from pydantic import Field

from app.business.domain.enums import Categoria, EstadoMaterial, UnidadMedida
from app.business.services.comandos import ActualizarMaterialComando, RegistrarMaterialComando
from app.core.paginacion import Pagina
from app.presentation.schemas.comun import DecimalEntrada, DecimalSalida, EsquemaEntrada, EsquemaSalida

# ---------------------------------------------------------------------------------------
# Entrada
# ---------------------------------------------------------------------------------------


class MaterialCrearSolicitud(EsquemaEntrada):
    """Cuerpo de POST /materiales (HU-01 c1).

    TODO(HU-01 c1 y c2):
    * ``mensajes_error``: ("nombre", "missing") → ``HU01_C2_1``; ("categoria", "missing") →
      ``HU01_C2_3_A``; ("categoria", "enum") → ``HU01_C2_3_B``; ("unidadMedida", "missing") →
      ``HU01_C2_4_A``; ("unidadMedida", "enum") → ``HU01_C2_4_B``; ("densidad", "missing") →
      ``HU01_C2_5``; ("pureza", "missing") → ``HU01_C2_6``.
    * ``@field_validator("nombre")``: ``NombreMaterial.crear(valor)`` y devolver el nombre
      normalizado; ``ValorInvalidoError`` con motivo LONGITUD → ``error_de_negocio(HU01_C2_2_A)``,
      CARACTERES → ``HU01_C2_2_B``.
    * ``@field_validator("densidad", "pureza")``: ``Densidad(valor)`` y ``Pureza(valor)``. El
      backlog no define el mensaje para un valor no válido en HU-01 (ver README).
    """

    nombre: str = Field(
        description="De 3 a 100 caracteres: letras con o sin tilde, ñ, dígitos, espacios y - . , / ( ) #. "
        "Se eliminan los espacios al inicio y al final y se reducen a uno los repetidos.",
        examples=["Acero al carbono 1045"],
    )
    categoria: Categoria = Field(examples=["Materia Prima"])
    unidad_medida: UnidadMedida = Field(examples=["kg"])
    densidad: DecimalEntrada = Field(description="Numérico, positivo, máximo 4 caracteres.", examples=[7.85])
    pureza: DecimalEntrada = Field(description="Numérico de 0 a 100 (%), máximo 3 caracteres.", examples=[98])

    def a_comando(self) -> RegistrarMaterialComando:
        return RegistrarMaterialComando(
            nombre=self.nombre,
            categoria=self.categoria.value,
            unidad_medida=self.unidad_medida.value,
            densidad=self.densidad,
            pureza=self.pureza,
        )


class MaterialActualizarSolicitud(EsquemaEntrada):
    """Cuerpo de PUT /materiales/{id} (HU-03 c1). ID, SKU y Unidad de medida son de solo lectura.

    TODO(HU-03 c1 y c2):
    * ``mensajes_error``: ("sku", "extra_forbidden") → ``HU03_C2_1``; ("unidadMedida",
      "extra_forbidden") → ``HU03_C2_2``; ("nombre", "missing") → ``HU03_C2_3``; ("categoria", "*")
      → ``HU03_C2_5``; ("densidad", "*") → ``HU03_C2_6``; ("pureza", "*") → ``HU03_C2_7``.
      Nota: los campos sobrantes se reportan después de los demás errores; si el orden de
      prioridad importa, sobrescribir ``mensaje_para_error``.
    * ``@field_validator("nombre")``: como en HU-01, con ``HU03_C2_4_A`` y ``HU03_C2_4_B``.
    * ``@field_validator("densidad", "pureza")``: ``Densidad``/``Pureza`` → ``HU03_C2_6``/``HU03_C2_7``.
    """

    nombre: str = Field(examples=["Acero al carbono 1045"])
    categoria: Categoria = Field(examples=["Materia Prima"])
    densidad: DecimalEntrada = Field(examples=[7.85])
    pureza: DecimalEntrada = Field(examples=[98])

    def a_comando(self) -> ActualizarMaterialComando:
        return ActualizarMaterialComando(
            nombre=self.nombre,
            categoria=self.categoria.value,
            densidad=self.densidad,
            pureza=self.pureza,
        )


class ListadoMaterialesConsulta(EsquemaEntrada):
    """Parámetros de GET /materiales.

    TODO(HU-02 c3): el backlog no define los filtros del listado (solo el ejemplo
    ``densidad=abc``) ni el tamaño de página. Agregarlos cuando el PO los defina; un valor
    no válido responde 400 con ``HU02_C3`` (marcador [NombreParametro]).
    """

    pagina: int = Field(default=1, ge=1, description="Número de página (desde 1).")
    tamano_pagina: int = Field(default=10, ge=1, le=100, description="Registros por página (por definir con el PO).")


# ---------------------------------------------------------------------------------------
# Salida
# ---------------------------------------------------------------------------------------


class MaterialFichaRespuesta(EsquemaSalida):
    """Ficha técnica del material, de solo lectura (HU-02 c2: 9 campos)."""

    material_id: str = Field(examples=["mat-001"])
    sku: str = Field(examples=["MP-00001"])
    nombre: str = Field(examples=["Acero al carbono 1045"])
    categoria: Categoria
    unidad_medida: UnidadMedida
    densidad: DecimalSalida = Field(examples=[7.85])
    pureza: DecimalSalida = Field(examples=[98])
    fecha_registro: datetime
    estado: EstadoMaterial

    @classmethod
    def _campos(cls, material: Any) -> dict[str, Any]:
        return {
            "material_id": material.id_material,
            "sku": material.sku,
            "nombre": material.nombre,
            "categoria": material.categoria,
            "unidad_medida": material.unidad_medida,
            "densidad": Decimal(material.densidad),
            "pureza": Decimal(material.pureza),
            "fecha_registro": material.fecha_registro,
            "estado": material.estado,
        }

    @classmethod
    def desde_modelo(cls, material: Any) -> Self:
        """Construye el DTO desde el modelo Material que devuelve el servicio."""
        return cls(**cls._campos(material))


class MaterialRespuesta(MaterialFichaRespuesta):
    """Material completo y mensaje (HU-01 c7: 201; HU-03 c7: 200)."""

    fecha_ultima_actualizacion: datetime
    mensaje: str | None = Field(default=None, examples=["Material 'Acero al carbono 1045' registrado exitosamente con el SKU MP-00001."])

    @classmethod
    def desde_modelo(cls, material: Any, mensaje: str | None = None) -> Self:  # type: ignore[override]
        return cls(
            **cls._campos(material),
            fecha_ultima_actualizacion=material.fecha_actualizacion,
            mensaje=mensaje,
        )


class MaterialEstadoRespuesta(EsquemaSalida):
    """Resultado de la inhabilitación (HU-04 c2)."""

    material_id: str = Field(examples=["mat-001"])
    estado: EstadoMaterial
    mensaje: str = Field(examples=["Material 'mat-001' inhabilitado exitosamente"])

    @classmethod
    def desde_modelo(cls, material: Any, mensaje: str) -> Self:
        return cls(material_id=material.id_material, estado=material.estado, mensaje=mensaje)


class MaterialesPaginaRespuesta(EsquemaSalida):
    """Página del listado de materiales (GET /materiales)."""

    pagina: int
    tamano_pagina: int
    total_registros: int
    total_paginas: int
    materiales: list[MaterialFichaRespuesta]
    mensaje: str | None = None

    @classmethod
    def desde_pagina(cls, pagina: Pagina[Any], mensaje: str | None = None) -> Self:
        return cls(
            pagina=pagina.pagina,
            tamano_pagina=pagina.tamano_pagina,
            total_registros=pagina.total_registros,
            total_paginas=pagina.total_paginas,
            materiales=[MaterialFichaRespuesta.desde_modelo(m) for m in pagina.elementos],
            mensaje=mensaje,
        )
