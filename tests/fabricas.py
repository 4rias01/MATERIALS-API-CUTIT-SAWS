"""Fábricas de objetos del modelo para las pruebas (valores por defecto válidos)."""

from datetime import UTC, datetime
from decimal import Decimal

from app.data_access.models import Auditoria, ComponenteFormula, EvaluacionPatente, Formula, Material, PatenteConflicto

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


def una_formula(
    numero: int = 1,
    materiales: list[tuple[Material, Decimal | str | int]] | None = None,
    nombre: str | None = None,
    estado: str = "BORRADOR",
    version: int = 1,
    fecha_registro: datetime = FECHA,
    fecha_actualizacion: datetime | None = None,
) -> Formula:
    """Fórmula con sus componentes (por defecto, dos materiales nuevos)."""
    if materiales is None:
        materiales = [(un_material(numero * 10 + 1), "2.5"), (un_material(numero * 10 + 2), "1")]
    formula = Formula(
        id_formula=f"form-{numero:03d}",
        nombre=nombre or f"Formula {numero}",
        aplicacion_tecnica="Cuchillas para corte de madera dura",
        version=version,
        estado=estado,
        fecha_registro=fecha_registro,
        fecha_actualizacion=fecha_actualizacion or fecha_registro,
    )
    formula.componentes = [
        ComponenteFormula(id_material=m.id_material, material=m, cantidad=Decimal(str(c))) for m, c in materiales
    ]
    formula.evaluaciones = []
    return formula


def una_evaluacion(
    formula: Formula,
    numero: int = 1,
    resultado: str | None = None,
    patentes: list[tuple[str, str]] = (),
) -> EvaluacionPatente:
    """Agrega a la fórmula un trámite de evaluación (abierto si ``resultado`` es None)."""
    evaluacion = EvaluacionPatente(
        ticket_evaluacion_id=f"tck-{numero:03d}",
        fecha_solicitud=FECHA,
        resultado=resultado,
        fecha_dictamen=FECHA if resultado else None,
    )
    evaluacion.patentes = [PatenteConflicto(conflicto_id=c, titulo=t) for c, t in patentes]
    formula.evaluaciones.append(evaluacion)
    return evaluacion


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
