"""Decorador ``operacion_de_negocio``: traducción de fallos y auditoría."""

import pytest

from app.business.services.base import Resultado, ServicioBase, operacion_de_negocio
from app.core.contexto import establecer_contexto, restablecer_contexto
from app.core.events import BusEventos, EventoDominio
from app.core.exceptions import (
    ConflictoError,
    DependenciaNoDisponibleError,
    ErrorBaseDatos,
    ErrorInterno,
    ErrorServicioExterno,
    NoImplementadoError,
)
from tests.dobles import AuditoriaRepositoryFalso, UnitOfWorkFalsa


class ServicioDePrueba(ServicioBase):
    def __init__(self, error: Exception | None = None, uow: UnitOfWorkFalsa | None = None) -> None:
        self.auditoria = AuditoriaRepositoryFalso()
        self.uow = uow or UnitOfWorkFalsa()
        self.eventos_recibidos: list[EventoDominio] = []
        bus = BusEventos()
        bus.suscribir(self.eventos_recibidos.append)
        super().__init__(self.uow, self.auditoria, bus)
        self.error = error

    @operacion_de_negocio(
        "OPERAR", "material", mensaje_error_bd="Fallo BD [traceId]", mensaje_servicio_externo="Inventario caído", parametro_id="id_material"
    )
    async def operar(self, id_material: str) -> Resultado[str]:
        if self.error:
            raise self.error
        async with self._uow:
            self._auditar("OPERAR", "material", id_material, 200)
            await self._uow.commit()
        self._publicar("Operado", materialId=id_material)
        return Resultado(id_material, "ok")

    @operacion_de_negocio("CONSULTAR", "material", mensaje_error_bd="Fallo BD", auditar=False)
    async def consultar(self) -> None:
        raise ConflictoError("no")


async def test_exito_audita_en_la_misma_transaccion_y_publica_el_evento() -> None:
    servicio = ServicioDePrueba()
    tokens = establecer_contexto("traza-0000000001", "pruebas")
    try:
        resultado = await servicio.operar("mat-001")
    finally:
        restablecer_contexto(tokens)
    assert resultado == Resultado("mat-001", "ok")
    registro = servicio.auditoria.registros[0]
    assert (registro.operacion, registro.recurso_id, registro.resultado_http) == ("OPERAR", "mat-001", 200)
    assert (registro.trace_id, registro.origen) == ("traza-0000000001", "pruebas")
    assert servicio.uow.confirmaciones == 1
    assert servicio.eventos_recibidos[0].nombre == "Operado"


async def test_fallo_de_base_de_datos_responde_error_interno_con_trace_id() -> None:
    servicio = ServicioDePrueba(ErrorBaseDatos("caída"))
    tokens = establecer_contexto("traza-0000000002", None)
    try:
        with pytest.raises(ErrorInterno) as error:
            await servicio.operar("mat-001")
    finally:
        restablecer_contexto(tokens)
    assert error.value.mensaje == "Fallo BD traza-0000000002"
    assert isinstance(error.value.__cause__, ErrorBaseDatos)


async def test_fallo_de_servicio_externo_responde_503_y_queda_auditado() -> None:
    servicio = ServicioDePrueba(ErrorServicioExterno("inventario", ErrorServicioExterno.TIMEOUT))
    with pytest.raises(DependenciaNoDisponibleError) as error:
        await servicio.operar("mat-001")
    assert error.value.mensaje == "Inventario caído"
    assert [(r.resultado_http, r.recurso_id) for r in servicio.auditoria.registros] == [(503, "mat-001")]


async def test_rechazo_de_negocio_queda_auditado_y_se_propaga() -> None:
    servicio = ServicioDePrueba(ConflictoError("El material ya existe"))
    with pytest.raises(ConflictoError):
        await servicio.operar("mat-001")
    registro = servicio.auditoria.registros[0]
    assert (registro.resultado_http, registro.detalle) == (409, {"mensaje": "El material ya existe"})


async def test_no_implementado_no_se_audita() -> None:
    servicio = ServicioDePrueba(NoImplementadoError("HU-01"))
    with pytest.raises(NoImplementadoError):
        await servicio.operar("mat-001")
    assert servicio.auditoria.registros == []


async def test_las_consultas_no_se_auditan() -> None:
    servicio = ServicioDePrueba()
    with pytest.raises(ConflictoError):
        await servicio.consultar()
    assert servicio.auditoria.registros == []


async def test_si_la_auditoria_falla_se_conserva_el_error_original() -> None:
    servicio = ServicioDePrueba(ConflictoError("conflicto"), uow=UnitOfWorkFalsa(fallar_en_commit=True))
    with pytest.raises(ConflictoError):
        await servicio.operar("mat-001")


async def test_un_id_demasiado_largo_va_al_detalle() -> None:
    servicio = ServicioDePrueba(ConflictoError("x"))
    with pytest.raises(ConflictoError):
        await servicio.operar("mat-00000000001")
    registro = servicio.auditoria.registros[0]
    assert registro.recurso_id is None
    assert registro.detalle["recursoIdRecibido"] == "mat-00000000001"
