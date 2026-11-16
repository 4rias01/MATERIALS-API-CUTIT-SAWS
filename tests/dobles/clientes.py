"""Clientes de otras células simulados."""

from app.infraestructure.interfaces import IClienteExterno


class ClienteExternoFalso(IClienteExterno):
    """Cliente mínimo que solo informa el estado de su circuito (para /health)."""

    def __init__(self, estado: str = "CERRADO") -> None:
        self.estado = estado

    def estado_circuito(self) -> str:
        return self.estado
