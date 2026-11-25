"""Pruebas unitarias de MaterialService (equivalente a ProfesorServiceTest del dojo).

El repositorio es un objeto simulado: no hay base de datos, solo se prueba la lógica de
negocio del servicio. Cada prueba sigue el esquema "dado que… cuando… entonces…".
Los criterios de aceptación de HU-01 se prueban de punta a punta en tests/hu.
"""

from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.business.domain import mensajes
from app.business.services.comandos import ActualizarMaterialComando, RegistrarMaterialComando
from app.business.services.material_service import MaterialService
from app.core.events import BusEventos
from app.core.exceptions import ConflictoError, ErrorIntegridadDatos, ErrorInterno, RecursoNoEncontradoError
from app.infraestructure.interfaces import IMaterialRepository
from app.infraestructure.models import Material
from tests.dobles import AuditoriaRepositoryFalso, InventarioClientFalso, UnitOfWorkFalsa
from tests.fabricas import un_material

# ── Fixtures y helpers ─────────────────────────────────────────────────────────


@pytest.fixture
def repositorio() -> AsyncMock:
    # Objeto simulado de IMaterialRepository: no accede a la base de datos, devuelve lo
    # que cada prueba le indique (como @Mock en Mockito). spec= impide llamar métodos
    # que la interfaz no tiene.
    return AsyncMock(spec=IMaterialRepository)


@pytest.fixture
def uow() -> UnitOfWorkFalsa:
    return UnitOfWorkFalsa()


@pytest.fixture
def auditoria() -> AuditoriaRepositoryFalso:
    return AuditoriaRepositoryFalso()


@pytest.fixture
def inventario() -> InventarioClientFalso:
    return InventarioClientFalso(sku="MP-00009")


@pytest.fixture
def servicio(
    repositorio: AsyncMock, uow: UnitOfWorkFalsa, auditoria: AuditoriaRepositoryFalso, inventario: InventarioClientFalso
) -> MaterialService:
    # El servicio REAL que se prueba, con sus dependencias simuladas.
    return MaterialService(uow, auditoria, BusEventos(), repositorio, inventario)


def comando(nombre: str = "Acero al carbono") -> RegistrarMaterialComando:
    return RegistrarMaterialComando(
        nombre=nombre, categoria="Materia Prima", unidad_medida="kg", densidad=Decimal("7.85"), pureza=Decimal("98")
    )


def datos_material(nombre: str = "Acero al carbono") -> ActualizarMaterialComando:
    return ActualizarMaterialComando(nombre=nombre, categoria="Materia Prima", densidad=Decimal("7.85"), pureza=Decimal("98"))


# ── Registrar (HU-01) ──────────────────────────────────────────────────────────


async def test_registrar_material_con_nombre_unico_lo_guarda_activo_con_el_sku_de_inventario(
    servicio: MaterialService,
    repositorio: AsyncMock,
    uow: UnitOfWorkFalsa,
    auditoria: AuditoriaRepositoryFalso,
    inventario: InventarioClientFalso,
) -> None:
    # Dado que ningún material usa ese nombre y la secuencia entrega el número 7
    repositorio.existe_nombre.return_value = False
    repositorio.siguiente_numero.return_value = 7

    # Cuando se registra el material (con espacios sobrantes en el nombre)
    resultado = await servicio.registrar(comando("  Acero   al carbono "))

    # Entonces se dio de alta en Inventario, se guardó ACTIVO con el SKU y quedó auditado
    assert inventario.altas == [("Acero al carbono", "kg")]
    repositorio.agregar.assert_awaited_once()
    material: Material = resultado.datos
    assert (material.id_material, material.sku, material.nombre, material.estado) == ("mat-007", "MP-00009", "Acero al carbono", "ACTIVO")
    assert material.fecha_registro == material.fecha_actualizacion
    assert resultado.mensaje == "Material 'Acero al carbono' registrado exitosamente con el SKU MP-00009."
    assert uow.confirmaciones == 1
    assert [(r.operacion, r.recurso_id, r.resultado_http) for r in auditoria.registros] == [("REGISTRAR_MATERIAL", "mat-007", 201)]


async def test_registrar_con_nombre_ya_registrado_no_llama_a_inventario(
    servicio: MaterialService, repositorio: AsyncMock, inventario: InventarioClientFalso
) -> None:
    # Dado que YA existe un material con ese nombre
    repositorio.existe_nombre.return_value = True

    # Cuando se intenta registrar, entonces se lanza ConflictoError (409)…
    with pytest.raises(ConflictoError, match="ya se encuentra registrado"):
        await servicio.registrar(comando())

    # …y NUNCA se llamó a Inventario ni se intentó guardar
    assert inventario.altas == []
    repositorio.agregar.assert_not_awaited()


async def test_registrar_si_falla_otra_restriccion_responde_500(servicio: MaterialService, repositorio: AsyncMock) -> None:
    # Dado que el SKU que asignó Inventario ya está en el catálogo (índice único del SKU)
    repositorio.existe_nombre.return_value = False
    repositorio.siguiente_numero.return_value = 1
    repositorio.agregar.side_effect = ErrorIntegridadDatos("duplicado", "uq_material_sku")

    with pytest.raises(ErrorInterno) as error:
        await servicio.registrar(comando())
    assert error.value.mensaje == mensajes.HU01_C8


# ── Actualizar ─────────────────────────────────────────────────────────────────


async def test_actualizar_material_existente_cambia_sus_datos(
    servicio: MaterialService, repositorio: AsyncMock, uow: UnitOfWorkFalsa
) -> None:
    # Dado que el material existe y el nombre nuevo está libre
    material = un_material(1, nombre="Acero al carbono")
    repositorio.obtener_por_id.return_value = material
    repositorio.existe_nombre.return_value = False

    resultado = await servicio.actualizar("mat-001", datos_material("Acero inoxidable"))

    assert resultado.datos.nombre == "Acero inoxidable"
    assert resultado.datos.fecha_actualizacion > resultado.datos.fecha_registro
    assert uow.confirmaciones == 1
    # La verificación de nombre excluye al propio material (puede conservar su nombre)
    repositorio.existe_nombre.assert_awaited_once_with("Acero inoxidable", excluir_id="mat-001")


async def test_actualizar_material_inexistente_lanza_no_encontrado(
    servicio: MaterialService, repositorio: AsyncMock, auditoria: AuditoriaRepositoryFalso
) -> None:
    # Dado que el material NO existe
    repositorio.obtener_por_id.return_value = None

    with pytest.raises(RecursoNoEncontradoError, match="El material solicitado con ID 'mat-099' no fue encontrado en el catálogo"):
        await servicio.actualizar("mat-099", datos_material())

    # Si no existe, no se verifica el nombre; solo queda el rechazo en la auditoría
    repositorio.existe_nombre.assert_not_awaited()
    assert [(r.operacion, r.recurso_id, r.resultado_http) for r in auditoria.registros] == [("ACTUALIZAR_MATERIAL", "mat-099", 404)]


async def test_actualizar_con_el_nombre_de_otro_material_lanza_conflicto(servicio: MaterialService, repositorio: AsyncMock) -> None:
    material = un_material(1, nombre="Acero al carbono")
    repositorio.obtener_por_id.return_value = material
    repositorio.existe_nombre.return_value = True  # otro material ya usa ese nombre

    with pytest.raises(ConflictoError, match="El material con el nombre 'Cobre' ya se encuentra registrado en el catálogo"):
        await servicio.actualizar("mat-001", datos_material("Cobre"))
    # El material conserva su nombre
    assert material.nombre == "Acero al carbono"


async def test_actualizar_con_nombre_guardado_a_la_vez_por_otra_peticion_lanza_conflicto(
    servicio: MaterialService, repositorio: AsyncMock, uow: UnitOfWorkFalsa
) -> None:
    repositorio.obtener_por_id.return_value = un_material(1)
    repositorio.existe_nombre.return_value = False
    uow.error_en_commit = ErrorIntegridadDatos("duplicado", "uq_material_nombre_lower")

    with pytest.raises(ConflictoError):
        await servicio.actualizar("mat-001", datos_material("Cobre"))


# ── Eliminar ───────────────────────────────────────────────────────────────────


async def test_eliminar_material_existente_lo_borra(servicio: MaterialService, repositorio: AsyncMock, uow: UnitOfWorkFalsa) -> None:
    material = un_material(1)
    repositorio.obtener_por_id.return_value = material

    await servicio.eliminar("mat-001")

    # Se pidió al repositorio borrar exactamente ese material y se confirmó
    repositorio.eliminar.assert_awaited_once_with(material)
    assert uow.confirmaciones == 1


async def test_eliminar_material_inexistente_lanza_no_encontrado(servicio: MaterialService, repositorio: AsyncMock) -> None:
    repositorio.obtener_por_id.return_value = None

    with pytest.raises(RecursoNoEncontradoError):
        await servicio.eliminar("mat-099")

    # Si no existe, eliminar() no debe llamarse nunca
    repositorio.eliminar.assert_not_awaited()


# ── Consultas ──────────────────────────────────────────────────────────────────


async def test_obtener_todos_devuelve_lo_que_retorna_el_repositorio(servicio: MaterialService, repositorio: AsyncMock) -> None:
    materiales = [un_material(1), un_material(2, nombre="Cobre")]
    repositorio.listar.return_value = materiales

    resultado = await servicio.obtener_todos()

    repositorio.listar.assert_awaited_once()
    assert resultado.datos == materiales


async def test_obtener_por_id_existente(servicio: MaterialService, repositorio: AsyncMock) -> None:
    material = un_material(1)
    repositorio.obtener_por_id.return_value = material

    assert (await servicio.obtener_por_id("mat-001")).datos is material


async def test_obtener_por_id_inexistente_lanza_no_encontrado(servicio: MaterialService, repositorio: AsyncMock) -> None:
    repositorio.obtener_por_id.return_value = None

    with pytest.raises(RecursoNoEncontradoError):
        await servicio.obtener_por_id("mat-099")


async def test_buscar_por_nombre_devuelve_las_coincidencias(servicio: MaterialService, repositorio: AsyncMock) -> None:
    materiales = [un_material(1)]
    repositorio.buscar_por_nombre.return_value = materiales

    resultado = await servicio.buscar_por_nombre("acero")

    repositorio.buscar_por_nombre.assert_awaited_once_with("acero")
    assert resultado.datos == materiales
