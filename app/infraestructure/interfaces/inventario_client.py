"""Contrato del cliente de la API de Inventario (célula 4)."""

from abc import ABC, abstractmethod


class NombreDuplicadoEnInventarioError(Exception):
    """Inventario rechazó la solicitud porque ya tiene un artículo con ese nombre (HU-01 c5, HU-03 c5)."""

    def __init__(self, mensaje_recibido: str | None = None) -> None:
        super().__init__(mensaje_recibido or "Inventario ya tiene un artículo con ese nombre")
        self.mensaje_recibido = mensaje_recibido


class IInventarioClient(ABC):
    """Operaciones que este módulo pide a Inventario (request-reply síncrono, timeout 5 s).

    Los fallos de comunicación (sin respuesta, error interno, más de 5 s o circuito
    abierto) se lanzan como ``app.core.exceptions.ErrorServicioExterno``.
    """

    @abstractmethod
    async def registrar_materia_prima(self, nombre: str, unidad_medida: str) -> str:
        """Registra el material como materia prima y devuelve el Código de artículo
        (SKU, formato MP-00000) que asigna Inventario (HU-01 c4)."""

    @abstractmethod
    async def modificar_nombre_articulo(self, codigo: str, nombre: str) -> None:
        """Cambia el nombre del artículo cuyo código es el SKU del material (HU-03 c4)."""

    @abstractmethod
    def estado_circuito(self) -> str:
        """Estado del circuit breaker: CERRADO, ABIERTO o SEMIABIERTO."""
