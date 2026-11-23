"""HU-05: registro transaccional de una fórmula, sin operaciones de Inventario."""

from app.business.domain import mensajes
from app.business.domain.enums import EstadoFormula
from app.business.domain.eventos import TipoEvento
from app.business.domain.formulas import id_formula, validar_materiales
from app.business.domain.mensajes import formatear
from app.business.services.base import Resultado, ServicioBase, ahora, operacion_de_negocio
from app.business.services.comandos import RegistrarFormulaComando
from app.core.events import BusEventos
from app.core.exceptions import ConflictoError, ErrorIntegridadDatos
from app.infraestructure.interfaces import IAuditoriaRepository, IFormulaRepository, IMaterialRepository, IUnitOfWork
from app.infraestructure.models import Formula, FormulaComponente

OPERACION_REGISTRAR = "REGISTRAR_FORMULA"
RECURSO = "formula"


class FormulaService(ServicioBase):
    def __init__(
        self,
        uow: IUnitOfWork,
        auditoria: IAuditoriaRepository,
        eventos: BusEventos,
        formulas: IFormulaRepository,
        materiales: IMaterialRepository,
    ) -> None:
        super().__init__(uow, auditoria, eventos)
        self._formulas = formulas
        self._materiales = materiales

    @operacion_de_negocio(OPERACION_REGISTRAR, RECURSO, mensaje_error_bd=mensajes.HU05_C8)
    async def registrar(self, comando: RegistrarFormulaComando) -> Resultado[Formula]:
        try:
            async with self._uow:
                materiales = [await self._materiales.obtener_por_id(c.material_id) for c in comando.componentes]
                validar_materiales(comando.componentes, materiales)
                if await self._formulas.existe_nombre(comando.nombre):
                    raise _nombre_ya_registrado(comando.nombre)
                fecha = ahora()
                formula = Formula(
                    id_formula=id_formula(await self._formulas.siguiente_numero()),
                    nombre=comando.nombre,
                    aplicacion_tecnica=comando.aplicacion_tecnica,
                    version=1,
                    estado=EstadoFormula.BORRADOR.value,
                    fecha_registro=fecha,
                    fecha_actualizacion=fecha,
                    componentes=[
                        FormulaComponente(id_material=c.material_id, cantidad=c.cantidad, material=m)
                        for c, m in zip(comando.componentes, materiales, strict=True)
                    ],
                )
                await self._formulas.agregar(formula)
                self._auditar(OPERACION_REGISTRAR, RECURSO, formula.id_formula, 201)
                await self._uow.commit()
        except ErrorIntegridadDatos as exc:
            # El índice único protege también dos registros simultáneos del mismo nombre.
            if exc.restriccion != "uq_formula_nombre_lower":
                raise
            raise _nombre_ya_registrado(comando.nombre) from exc
        self._publicar(TipoEvento.FORMULA_REGISTRADA, formulaId=formula.id_formula)
        return Resultado(
            formula, formatear(mensajes.HU05_C6_2, {"Nombre": formula.nombre, "form-NNN": formula.id_formula})
        )


def _nombre_ya_registrado(nombre: str) -> ConflictoError:
    return ConflictoError(formatear(mensajes.HU05_C6_1, NombreIngresado=nombre))
