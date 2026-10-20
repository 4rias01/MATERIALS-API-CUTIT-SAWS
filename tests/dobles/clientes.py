"""Clientes de Inventario y Patent Sweep simulados."""

from app.core.exceptions import ErrorServicioExterno
from app.data_access.interfaces import (
    IInventarioClient,
    IPatentSweepClient,
    NombreDuplicadoEnInventarioError,
    SolicitudEvaluacionPatente,
)


class InventarioClientFalso(IInventarioClient):
    """Responde con ``sku`` o con el fallo configurado (``nombre_duplicado`` o ``caido``)."""

    def __init__(self, sku: str = "MP-00001", nombre_duplicado: bool = False, caido: bool = False) -> None:
        self.sku = sku
        self.nombre_duplicado = nombre_duplicado
        self.caido = caido
        self.altas: list[tuple[str, str]] = []
        self.cambios_de_nombre: list[tuple[str, str]] = []

    def _verificar(self) -> None:
        if self.caido:
            raise ErrorServicioExterno("inventario", ErrorServicioExterno.TIMEOUT)
        if self.nombre_duplicado:
            raise NombreDuplicadoEnInventarioError("Ya existe un artículo con ese nombre")

    async def registrar_materia_prima(self, nombre: str, unidad_medida: str) -> str:
        self._verificar()
        self.altas.append((nombre, unidad_medida))
        return self.sku

    async def modificar_nombre_articulo(self, codigo: str, nombre: str) -> None:
        self._verificar()
        self.cambios_de_nombre.append((codigo, nombre))

    def estado_circuito(self) -> str:
        return "ABIERTO" if self.caido else "CERRADO"


class PatentSweepClientFalso(IPatentSweepClient):
    """Acepta las solicitudes (las guarda en ``solicitudes``) o falla si ``caido``."""

    def __init__(self, caido: bool = False) -> None:
        self.caido = caido
        self.solicitudes: list[SolicitudEvaluacionPatente] = []

    async def solicitar_evaluacion(self, solicitud: SolicitudEvaluacionPatente) -> None:
        if self.caido:
            raise ErrorServicioExterno("patent_sweep", ErrorServicioExterno.CONEXION)
        self.solicitudes.append(solicitud)

    def estado_circuito(self) -> str:
        return "ABIERTO" if self.caido else "CERRADO"
