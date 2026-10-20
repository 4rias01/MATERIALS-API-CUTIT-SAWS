"""Utilidades transversales: configuración, logging JSON, eventos y paginación."""

import json
import logging

import pytest

from app.core.config import Configuracion
from app.core.contexto import establecer_contexto, restablecer_contexto, trace_id_valido
from app.core.events import BusEventos, EventoDominio
from app.core.logging import FormateadorJson
from app.core.paginacion import Pagina, calcular_desplazamiento


def test_url_de_base_de_datos_desde_las_variables_postgres() -> None:
    config = Configuracion(_env_file=None, postgres_user="u", postgres_password="cl@ve:1", postgres_host="db", postgres_db="mf")  # type: ignore[call-arg]
    assert config.url_base_datos == "postgresql+asyncpg://u:cl%40ve%3A1@db:5432/mf"
    config = Configuracion(_env_file=None, database_url="postgresql+asyncpg://x@y/z")  # type: ignore[call-arg]
    assert config.url_base_datos == "postgresql+asyncpg://x@y/z"


def test_configuracion_lee_variables_de_entorno(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INVENTARIO_URL", "http://inventario:8000")
    monkeypatch.setenv("HTTP_TIMEOUT_S", "3")
    config = Configuracion(_env_file=None)  # type: ignore[call-arg]
    assert (config.inventario_url, config.http_timeout_s) == ("http://inventario:8000", 3.0)


def test_log_en_json_con_trace_id_y_datos_adicionales() -> None:
    registro = logging.LogRecord("app.prueba", logging.INFO, __file__, 1, "Hola %s", ("mundo",), None)
    registro.materialId = "mat-001"
    tokens = establecer_contexto("traza-1234567890", "pruebas")
    try:
        linea = json.loads(FormateadorJson().format(registro))
    finally:
        restablecer_contexto(tokens)
    assert linea["mensaje"] == "Hola mundo"
    assert (linea["traceId"], linea["origen"], linea["materialId"]) == ("traza-1234567890", "pruebas", "mat-001")
    assert linea["nivel"] == "INFO"


@pytest.mark.parametrize(("valor", "valido"), [("abc12345", True), ("a" * 64, True), ("corto", False), ("con espacio 123", False), (None, False)])
def test_trace_id_recibido_valido(valor: str | None, valido: bool) -> None:
    assert trace_id_valido(valor) is valido


def test_bus_de_eventos_entrega_a_los_suscriptores_y_aisla_fallos() -> None:
    bus = BusEventos()
    todos: list[str] = []
    solo_uno: list[str] = []

    def falla(_: EventoDominio) -> None:
        raise RuntimeError("suscriptor roto")

    bus.suscribir(falla)
    bus.suscribir(lambda e: todos.append(e.nombre))
    bus.suscribir(lambda e: solo_uno.append(e.nombre), evento="MaterialRegistrado")
    bus.publicar(EventoDominio("MaterialRegistrado", {"materialId": "mat-001"}))
    bus.publicar(EventoDominio("FormulaRegistrada"))
    assert todos == ["MaterialRegistrado", "FormulaRegistrada"]
    assert solo_uno == ["MaterialRegistrado"]


@pytest.mark.parametrize(("total", "tamano", "paginas"), [(0, 10, 0), (10, 10, 1), (11, 10, 2), (101, 50, 3)])
def test_total_de_paginas(total: int, tamano: int, paginas: int) -> None:
    assert Pagina([], 1, tamano, total).total_paginas == paginas


def test_desplazamiento() -> None:
    assert calcular_desplazamiento(1, 10) == 0
    assert calcular_desplazamiento(3, 50) == 100
