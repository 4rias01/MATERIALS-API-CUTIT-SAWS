"""Cliente de Inventario simulado."""

from app.core.exceptions import ErrorServicioExterno
from app.infraestructure.interfaces import IInventarioClient, NombreDuplicadoEnInventarioError


class InventarioClientFalso(IInventarioClient):
    """Responde con ``sku`` o con el fallo configurado (``nombre_duplicado`` o ``caido``)."""

    def __init__(self, sku: str = "MP-00001", nombre_duplicado: bool = False, caido: bool = False) -> None:
        self.sku = sku
        self.nombre_duplicado = nombre_duplicado
        self.caido = caido
        self.altas: list[tuple[str, str]] = []

    async def registrar_materia_prima(self, nombre: str, unidad_medida: str) -> str:
        if self.caido:
            raise ErrorServicioExterno("inventario", ErrorServicioExterno.TIMEOUT)
        if self.nombre_duplicado:
            raise NombreDuplicadoEnInventarioError(f"Ya existe un artículo con el nombre {nombre}")
        self.altas.append((nombre, unidad_medida))
        return self.sku

    def estado_circuito(self) -> str:
        return "ABIERTO" if self.caido else "CERRADO"
