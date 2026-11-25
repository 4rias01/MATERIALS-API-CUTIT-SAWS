"""Repositorios y unidad de trabajo en memoria.

En las pruebas unitarias del servicio el repositorio de materiales también se puede
simular con ``AsyncMock(spec=IMaterialRepository)`` (el equivalente al ``@Mock`` de
Mockito); ``MaterialRepositoryFalso`` sirve cuando la prueba recorre la API completa.
"""

from collections.abc import Sequence
from types import TracebackType

from app.core.exceptions import ErrorBaseDatos
from app.infraestructure.interfaces import IAuditoriaRepository, IMaterialRepository, IUnitOfWork
from app.infraestructure.interfaces.material_repository import FiltrosMaterial
from app.infraestructure.models import Auditoria, Material


class UnitOfWorkFalsa(IUnitOfWork):
    """Cuenta confirmaciones y reversiones; puede simular un fallo de la base de datos.

    Un bloque ``async with`` que termina sin ``commit`` (con o sin excepción) cuenta como
    reversión. ``error_en_commit`` es la excepción que lanza el commit (por ejemplo, un
    ``ErrorIntegridadDatos``); ``fallar_en_commit`` lanza un ``ErrorBaseDatos`` genérico y
    ``base_disponible=False`` simula una base que no responde (para /health).
    """

    def __init__(
        self,
        fallar_en_commit: bool = False,
        base_disponible: bool = True,
        error_en_commit: ErrorBaseDatos | None = None,
    ) -> None:
        self.fallar_en_commit = fallar_en_commit
        self.base_disponible = base_disponible
        self.error_en_commit = error_en_commit
        self.confirmaciones = 0
        self.reversiones = 0
        self._confirmado = False

    async def __aenter__(self) -> "UnitOfWorkFalsa":
        self._confirmado = False
        return self

    async def __aexit__(self, tipo: type[BaseException] | None, exc: BaseException | None, traza: TracebackType | None) -> None:
        if exc is not None or not self._confirmado:
            self.reversiones += 1

    async def commit(self) -> None:
        if self.error_en_commit is not None:
            raise self.error_en_commit
        if self.fallar_en_commit or not self.base_disponible:
            raise ErrorBaseDatos("Fallo simulado de la base de datos")
        self.confirmaciones += 1
        self._confirmado = True

    async def rollback(self) -> None:
        self.reversiones += 1

    async def verificar_conexion(self) -> None:
        if not self.base_disponible:
            raise ErrorBaseDatos("Base de datos no disponible (simulado)")


class AuditoriaRepositoryFalso(IAuditoriaRepository):
    """Guarda en una lista los registros de auditoría que agrega el servicio."""

    def __init__(self) -> None:
        self.registros: list[Auditoria] = []

    def agregar(self, registro: Auditoria) -> None:
        self.registros.append(registro)


class MaterialRepositoryFalso(IMaterialRepository):
    """Materiales en memoria. No simula el rollback: lo agregado queda en ``materiales``
    aunque la unidad de trabajo falle; para eso, verificar ``uow.confirmaciones``."""

    def __init__(self, materiales: Sequence[Material] = ()) -> None:
        self.materiales: dict[str, Material] = {}
        self._secuencia = 0
        self.sembrar(*materiales)

    def sembrar(self, *materiales: Material) -> None:
        """Deja materiales ya registrados (preparación de la prueba, sin pasar por el servicio)."""
        for material in materiales:
            self.materiales[material.id_material] = material
        self._secuencia = len(self.materiales)

    async def listar_pagina(self, filtros: FiltrosMaterial, offset: int, limite: int) -> tuple[list[Material], int]:
        encontrados = [
            m
            for m in self.materiales.values()
            if (filtros.nombre is None or filtros.nombre.lower() in m.nombre.lower())
            and (filtros.categoria is None or filtros.categoria == m.categoria)
            and (filtros.unidad_medida is None or filtros.unidad_medida == m.unidad_medida)
            and (filtros.estado is None or filtros.estado == m.estado)
        ]
        encontrados.sort(key=lambda m: (len(m.id_material), m.id_material))
        return encontrados[offset : offset + limite], len(encontrados)

    async def obtener_por_id(self, id_material: str, *, para_actualizar: bool = False) -> Material | None:
        return self.materiales.get(id_material)

    async def listar(self) -> Sequence[Material]:
        return list(self.materiales.values())

    async def buscar_por_nombre(self, fragmento: str) -> Sequence[Material]:
        return [m for m in self.materiales.values() if fragmento.lower() in m.nombre.lower()]

    async def existe_nombre(self, nombre: str, excluir_id: str | None = None) -> bool:
        return any(m.nombre.lower() == nombre.lower() and m.id_material != excluir_id for m in self.materiales.values())

    async def siguiente_numero(self) -> int:
        self._secuencia += 1
        return self._secuencia

    async def agregar(self, material: Material) -> None:
        self.materiales[material.id_material] = material

    async def eliminar(self, material: Material) -> None:
        self.materiales.pop(material.id_material, None)
