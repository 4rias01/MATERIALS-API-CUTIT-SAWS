"""Fábricas de objetos del modelo para las pruebas (valores por defecto válidos)."""

from datetime import UTC, datetime
from decimal import Decimal

from app.infraestructure.models import Auditoria, Material

FECHA = datetime(2026, 10, 20, 15, 30, tzinfo=UTC)


def un_material(
    numero: int = 1,
    nombre: str | None = None,
    unidad_medida: str = "kg",
    estado: str = "ACTIVO",
    categoria: str = "Materia Prima",
    fecha: datetime = FECHA,
) -> Material:
    return Material(
        id_material=f"mat-{numero:03d}",
        sku=f"MP-{numero:05d}",
        nombre=nombre or f"Material {numero}",
        categoria=categoria,
        unidad_medida=unidad_medida,
        densidad=Decimal("7.85"),
        pureza=Decimal("98"),
        estado=estado,
        fecha_registro=fecha,
        fecha_actualizacion=fecha,
    )


def un_registro_auditoria(operacion: str = "PRUEBA", resultado_http: int = 200) -> Auditoria:
    return Auditoria(
        fecha_hora=FECHA,
        trace_id="0123456789abcdef0123456789abcdef",
        operacion=operacion,
        recurso="material",
        recurso_id="mat-001",
        resultado_http=resultado_http,
        origen="pruebas",
        detalle={"clave": "valor"},
    )
