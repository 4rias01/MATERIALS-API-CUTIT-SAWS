"""Pruebas unitarias de MaterialService (equivalente a ProfesorServiceTest del dojo).

El repositorio es un objeto simulado: no hay base de datos, solo se prueba la lógica de
negocio del servicio. Cada prueba sigue el esquema "dado que… cuando… entonces…".
"""

from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.business.services.comandos import DatosMaterial
from app.business.services.material_service import MaterialService
from app.core.events import BusEventos
from app.core.exceptions import ConflictoError, RecursoNoEncontradoError
from app.infraestructure.interfaces import IMaterialRepository
from app.infraestructure.models import Material
from tests.dobles import AuditoriaRepositoryFalso, UnitOfWorkFalsa

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
def servicio(repositorio: AsyncMock, uow: UnitOfWorkFalsa, auditoria: AuditoriaRepositoryFalso) -> MaterialService:
    # El servicio REAL que se prueba, con sus dependencias simuladas.
    return MaterialService(uow, auditoria, BusEventos(), repositorio)


def datos_material(nombre: str = "Acero al carbono") -> DatosMaterial:
    return DatosMaterial(nombre=nombre, categoria="Materia Prima", unidad_medida="kg", densidad=Decimal("7.85"), pureza=Decimal("98"))


def un_material(id_material: int = 1, nombre: str = "Acero al carbono") -> Material:
    return Material(id_material=id_material, nombre=nombre, categoria="Materia Prima", unidad_medida="kg", densidad=Decimal("7.85"), pureza=Decimal("98"))


# ── Crear ──────────────────────────────────────────────────────────────────────


async def test_crear_material_con_nombre_unico_lo_guarda(
    servicio: MaterialService, repositorio: AsyncMock, uow: UnitOfWorkFalsa, auditoria: AuditoriaRepositoryFalso
) -> None:
    # Dado que ningún material usa ese nombre…
    repositorio.existe_nombre.return_value = False

    # …y que al agregarlo la base de datos le asigna el id 1
    def asignar_id(material: Material) -> None:
        material.id_material = 1

    repositorio.agregar.side_effect = asignar_id

    # Cuando se crea el material
    resultado = await servicio.crear(datos_material())

    # Entonces se agregó al repositorio, se confirmó la transacción y quedó auditado
    repositorio.agregar.assert_awaited_once()
    assert (resultado.datos.id_material, resultado.datos.nombre) == (1, "Acero al carbono")
    assert resultado.datos.fecha_registro == resultado.datos.fecha_actualizacion
    assert uow.confirmaciones == 1
    assert [(r.operacion, r.recurso_id, r.resultado_http) for r in auditoria.registros] == [("CREAR_MATERIAL", "1", 201)]


async def test_crear_material_con_nombre_duplicado_lanza_conflicto(servicio: MaterialService, repositorio: AsyncMock) -> None:
    # Dado que YA existe un material con ese nombre
    repositorio.existe_nombre.return_value = True

    # Cuando se intenta crear, entonces se lanza ConflictoError (409)…
    with pytest.raises(ConflictoError, match="Ya existe un material con el nombre: Acero al carbono"):
        await servicio.crear(datos_material())

    # …y NUNCA se intentó guardar
    repositorio.agregar.assert_not_awaited()


# ── Actualizar ─────────────────────────────────────────────────────────────────


async def test_actualizar_material_existente_cambia_sus_datos(
    servicio: MaterialService, repositorio: AsyncMock, uow: UnitOfWorkFalsa
) -> None:
    # Dado que el material existe y el nombre nuevo está libre
    material = un_material()
    repositorio.obtener_por_id.return_value = material
    repositorio.existe_nombre.return_value = False

    resultado = await servicio.actualizar(1, datos_material("Acero inoxidable"))

    assert resultado.datos.nombre == "Acero inoxidable"
    assert uow.confirmaciones == 1
    # La verificación de nombre excluye al propio material (puede conservar su nombre)
    repositorio.existe_nombre.assert_awaited_once_with("Acero inoxidable", excluir_id=1)


async def test_actualizar_material_inexistente_lanza_no_encontrado(
    servicio: MaterialService, repositorio: AsyncMock, auditoria: AuditoriaRepositoryFalso
) -> None:
    # Dado que el material NO existe
    repositorio.obtener_por_id.return_value = None

    with pytest.raises(RecursoNoEncontradoError, match="Material con id 99 no encontrado"):
        await servicio.actualizar(99, datos_material())

    # Si no existe, no se verifica el nombre; solo queda el rechazo en la auditoría
    repositorio.existe_nombre.assert_not_awaited()
    assert [(r.operacion, r.recurso_id, r.resultado_http) for r in auditoria.registros] == [("ACTUALIZAR_MATERIAL", "99", 404)]


async def test_actualizar_con_el_nombre_de_otro_material_lanza_conflicto(servicio: MaterialService, repositorio: AsyncMock) -> None:
    material = un_material()
    repositorio.obtener_por_id.return_value = material
    repositorio.existe_nombre.return_value = True  # otro material ya usa ese nombre

    with pytest.raises(ConflictoError):
        await servicio.actualizar(1, datos_material("Cobre"))
    # El material conserva su nombre
    assert material.nombre == "Acero al carbono"


# ── Eliminar ───────────────────────────────────────────────────────────────────


async def test_eliminar_material_existente_lo_borra(servicio: MaterialService, repositorio: AsyncMock, uow: UnitOfWorkFalsa) -> None:
    material = un_material()
    repositorio.obtener_por_id.return_value = material

    await servicio.eliminar(1)

    # Se pidió al repositorio borrar exactamente ese material y se confirmó
    repositorio.eliminar.assert_awaited_once_with(material)
    assert uow.confirmaciones == 1


async def test_eliminar_material_inexistente_lanza_no_encontrado(servicio: MaterialService, repositorio: AsyncMock) -> None:
    repositorio.obtener_por_id.return_value = None

    with pytest.raises(RecursoNoEncontradoError):
        await servicio.eliminar(99)

    # Si no existe, eliminar() no debe llamarse nunca
    repositorio.eliminar.assert_not_awaited()


# ── Consultas ──────────────────────────────────────────────────────────────────


async def test_obtener_todos_devuelve_lo_que_retorna_el_repositorio(servicio: MaterialService, repositorio: AsyncMock) -> None:
    materiales = [un_material(1), un_material(2, "Cobre")]
    repositorio.listar.return_value = materiales

    resultado = await servicio.obtener_todos()

    repositorio.listar.assert_awaited_once()
    assert resultado.datos == materiales


async def test_obtener_por_id_existente(servicio: MaterialService, repositorio: AsyncMock) -> None:
    material = un_material()
    repositorio.obtener_por_id.return_value = material

    assert (await servicio.obtener_por_id(1)).datos is material


async def test_obtener_por_id_inexistente_lanza_no_encontrado(servicio: MaterialService, repositorio: AsyncMock) -> None:
    repositorio.obtener_por_id.return_value = None

    with pytest.raises(RecursoNoEncontradoError):
        await servicio.obtener_por_id(99)


async def test_buscar_por_nombre_devuelve_las_coincidencias(servicio: MaterialService, repositorio: AsyncMock) -> None:
    materiales = [un_material()]
    repositorio.buscar_por_nombre.return_value = materiales

    resultado = await servicio.buscar_por_nombre("acero")

    repositorio.buscar_por_nombre.assert_awaited_once_with("acero")
    assert resultado.datos == materiales
