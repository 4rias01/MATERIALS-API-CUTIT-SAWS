"""Utilidades transversales: configuración, logging JSON, contexto y eventos."""

import json
import logging
import secrets
import sys
from urllib.parse import quote

import pytest

from app.core.config import Configuracion
from app.core.contexto import establecer_contexto, restablecer_contexto, trace_id_valido
from app.core.events import BusEventos, EventoDominio, registrar_evento_en_log
from app.core.logging import FormateadorJson, configurar_logging


def test_url_de_base_de_datos_desde_las_variables_postgres() -> None:
    # Clave aleatoria con caracteres que deben codificarse en la URL (@ y :).
    clave = f"cl@ve:{secrets.token_hex(4)}"
    config = Configuracion(_env_file=None, postgres_user="u", postgres_password=clave, postgres_host="db", postgres_db="mf")  # type: ignore[call-arg]
    assert config.url_base_datos == f"postgresql+asyncpg://u:{quote(clave, safe='')}@db:5520/mf"
    config = Configuracion(_env_file=None, database_url="postgresql+asyncpg://x@y/z")  # type: ignore[call-arg]
    assert config.url_base_datos == "postgresql+asyncpg://x@y/z"


def test_sin_credenciales_no_hay_url_de_base_de_datos(monkeypatch: pytest.MonkeyPatch) -> None:
    for variable in ("DATABASE_URL", "POSTGRES_USER", "POSTGRES_PASSWORD"):
        monkeypatch.delenv(variable, raising=False)
    with pytest.raises(ValueError, match="POSTGRES_USER"):
        _ = Configuracion(_env_file=None).url_base_datos  # type: ignore[call-arg]


def test_configuracion_lee_variables_de_entorno(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INVENTARIO_URL", "http://inventario.prueba")
    monkeypatch.setenv("HTTP_TIMEOUT_S", "3")
    config = Configuracion(_env_file=None)  # type: ignore[call-arg]
    assert (config.inventario_url, config.http_timeout_s) == ("http://inventario.prueba", 3.0)


def test_log_en_json_con_trace_id_y_datos_adicionales() -> None:
    registro = logging.LogRecord("app.prueba", logging.INFO, __file__, 1, "Hola %s", ("mundo",), None)
    registro.materialId = 1
    tokens = establecer_contexto("traza-1234567890", "pruebas")
    try:
        linea = json.loads(FormateadorJson().format(registro))
    finally:
        restablecer_contexto(tokens)
    assert linea["mensaje"] == "Hola mundo"
    assert (linea["traceId"], linea["origen"], linea["materialId"]) == ("traza-1234567890", "pruebas", 1)
    assert linea["nivel"] == "INFO"


def test_log_incluye_la_excepcion() -> None:
    try:
        raise ValueError("falló")
    except ValueError:
        registro = logging.LogRecord("app.prueba", logging.ERROR, __file__, 1, "Error", (), sys.exc_info())
    linea = json.loads(FormateadorJson().format(registro))
    assert "ValueError: falló" in linea["excepcion"]


def test_configurar_logging_no_duplica_el_manejador() -> None:
    configurar_logging("WARNING")
    configurar_logging("WARNING")
    propios = [m for m in logging.getLogger().handlers if type(m).__name__ == "_ManejadorConsola"]
    assert len(propios) == 1
    filtro = logging.getLogger("uvicorn.error").filters[0]
    duplicado = logging.LogRecord("uvicorn.error", logging.ERROR, __file__, 1, "Exception in ASGI application", (), None)
    assert not filtro.filter(duplicado)  # type: ignore[union-attr]


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
    bus.suscribir(lambda e: solo_uno.append(e.nombre), evento="MaterialCreado")
    bus.suscribir(registrar_evento_en_log)
    bus.publicar(EventoDominio("MaterialCreado", {"materialId": 1}))
    bus.publicar(EventoDominio("OtroEvento"))
    assert todos == ["MaterialCreado", "OtroEvento"]
    assert solo_uno == ["MaterialCreado"]
