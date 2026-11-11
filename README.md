# API Materiales y Fórmulas · Cutit Saws Ltd.

API REST de la célula 1 de la plataforma backend de Cutit Saws (Desarrollo de Software II, 2026-2).
Implementa el **DAS v1.2** del módulo y el **product backlog V1.3**.

> **Estado (sprint 0):** la infraestructura transversal funciona y está probada, y hay **un
> solo flujo implementado de punta a punta como ejemplo: HU-01, registrar material**
> (`POST /materiales`). Las demás historias se agregan en los siguientes sprints siguiendo
> ese mismo flujo (sección 4).

| Funciona hoy | Pendiente |
|---|---|
| Arquitectura en capas, inyección de dependencias, configuración por variables de entorno | HU-02 a HU-11 (rutas, DTO, servicios, tablas y pruebas) |
| HU-01 completa: DTO con los mensajes del criterio 2, servicio, repositorio y alta en Inventario | Contrato POR ACORDAR con Inventario (sección 11) |
| Modelo ORM de `material` y `auditoria`, migración Alembic | |
| Unidad de trabajo (commit/rollback, timeout de 5 s), auditoría, eventos de dominio | |
| Cliente de Inventario (timeout de 5 s, circuit breaker, traceId) | |
| traceId, logs JSON, manejador global de errores, `/health`, `/metrics`, Swagger | |
| Dockerfile, Docker Compose, Prometheus, Grafana, node-exporter, GitHub Actions, SonarCloud | |
| Pruebas unitarias, de integración y de aceptación de HU-01 (`tests/hu`) | |

---

## 1. Estructura

```
app/
├── main.py                     Arranque: crea la app, pool de BD, cliente HTTP compartido, middleware, routers
├── core/                       Utilidades transversales (las usan las tres capas)
│   ├── config.py               Configuración por variables de entorno (pydantic-settings)
│   ├── contexto.py             traceId y origen de la petición en curso
│   ├── logging.py              Logs en JSON con traceId
│   ├── exceptions.py           Errores para el cliente (con código HTTP) y fallos técnicos
│   ├── events.py               Bus de eventos de dominio (Observer)
│   ├── metrics.py              Métricas de Prometheus y /metrics
│   └── openapi.py              Documentación del contrato (/docs)
├── api/                        Capa de presentación (API REST)
│   ├── routers/                materiales.py · health.py
│   ├── schemas/                DTO de Pydantic (contratos de entrada y salida, camelCase)
│   ├── middleware.py           traceId por petición (Correlation ID)
│   ├── exception_handlers.py   Manejador global de excepciones
│   └── dependencies.py         Inyección de dependencias (raíz de composición)
├── business/                   Capa de lógica de negocio
│   ├── services/               MaterialService (casos de uso) · base.py (transacción, auditoría, errores)
│   └── domain/                 enums · value_objects · errores · eventos · mensajes
└── infraestructure/            Capa de acceso a datos
    ├── interfaces/             Contratos que usan los servicios (repositorios, cliente, unidad de trabajo)
    ├── repositories/           Implementaciones con SQLAlchemy
    ├── models/                 Modelos ORM (material y auditoria)
    ├── clients/                Cliente HTTP de Inventario + circuit breaker
    ├── unit_of_work.py         Transacción: commit / rollback
    └── database.py             Motor, pool de conexiones y timeouts
migrations/                     Migraciones versionadas (Alembic)
tests/
├── unit/                       Sin base de datos ni APIs externas
├── integration/                Contra PostgreSQL (TEST_DATABASE_URL)
├── hu/                         Una o más pruebas por criterio de aceptación (hoy, HU-01)
├── dobles/                     Repositorios y cliente en memoria (Test Double)
└── fabricas.py                 Objetos de prueba con valores válidos
monitoring/                     prometheus.yml y aprovisionamiento + tablero de Grafana
.github/workflows/ci.yml        Integración continua (develop): ruff, mypy, import-linter, pruebas, SonarCloud
.github/workflows/cd.yml        Despliegue continuo (main): imagen en GHCR y despliegue en EC2
pyproject.toml                  Configuración de ruff, mypy e import-linter
```

**Regla de dependencias** (la verifican `lint-imports` y `tests/unit/test_arquitectura.py`):
`api → business → infraestructure`, y todas pueden usar `core`. Ninguna capa importa de una
capa superior. Los servicios no importan FastAPI, Pydantic, SQLAlchemy ni httpx: reciben
interfaces. Solo `app/main.py` y `app/api/dependencies.py` conocen las clases concretas,
porque arman los objetos que se inyectan.

---

## 2. Puesta en marcha

Requisitos: Python 3.12 y Docker con el plugin Compose.

### Todo con Docker Compose

```bash
cp .env.example .env          # completar usuarios y claves; las URLs de otras células pueden quedar vacías
docker compose up --build     # usa docker-compose.yml + docker-compose.override.yml
```

| Servicio | URL |
|---|---|
| Swagger (contrato) | http://localhost:API_PUERTO_HOST/docs |
| Estado | http://localhost:API_PUERTO_HOST/health |
| Métricas | http://localhost:API_PUERTO_HOST/metrics |
| Grafana | http://localhost:3820 (usuario y clave del `.env`) |
| Prometheus | http://localhost:9090 |

### API en Python, base de datos en Docker (para desarrollar)

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env                       # completar y descomentar POSTGRES_HOST/POSTGRES_PORT
docker compose up -d postgres              # PostgreSQL en localhost:POSTGRES_PUERTO_HOST
alembic upgrade head
uvicorn app.main:app --reload
```

---

## 3. Pruebas

```bash
pytest                                     # todo (las de integración se omiten si no hay PostgreSQL)
pytest tests/unit                          # rápidas, sin base de datos
pytest -m integracion                      # requiere TEST_DATABASE_URL
pytest --cov --cov-report=term-missing     # cobertura (el CI exige 80 %)
ruff check .                               # linter
mypy                                       # type checker
lint-imports                               # arquitectura: api -> business -> infraestructure -> core
```

Las pruebas de integración usan `TEST_DATABASE_URL` (sin valor por defecto; si no está
definida se omiten), por ejemplo `postgresql+asyncpg://<usuario>:<clave>@127.0.0.1:<POSTGRES_PUERTO_HOST>/materiales_formulas_test`.
En el CI, PostgreSQL se levanta con `docker compose` y las credenciales salen de los secretos `POSTGRES_USER` y `POSTGRES_PASSWORD`.
Al empezar, aplican las migraciones desde cero en esa base: **no la apunten a una base con datos**.

```bash
docker compose exec postgres sh -c 'createdb -U "$POSTGRES_USER" materiales_formulas_test'
```

---

## 4. Cómo implementar una historia de usuario

HU-01 es el ejemplo de referencia: cada historia nueva recorre los mismos archivos.

| Paso | HU-01 (ejemplo) |
|---|---|
| 1. Mensajes literales del backlog | `app/business/domain/mensajes.py` (`HU01_*`) |
| 2. Reglas del dominio (objetos de valor, enums) | `NombreMaterial`, `Densidad`, `Pureza`, `Sku` en `value_objects.py` |
| 3. Tabla y migración (si hace falta) | `models/material.py` + `alembic revision --autogenerate` |
| 4. Contrato del repositorio y su implementación | `interfaces/material_repository.py`, `repositories/material_repository.py` |
| 5. Comando de entrada del caso de uso | `RegistrarMaterialComando` en `services/comandos.py` |
| 6. Servicio | `MaterialService.registrar` en `services/material_service.py` |
| 7. DTO de entrada y salida | `MaterialCrearSolicitud` / `MaterialRespuesta` en `api/schemas/materiales.py` |
| 8. Ruta | `api/routers/materiales.py` (y `include_router` en `main.py` si es un router nuevo) |
| 9. Inyección de dependencias | `obtener_material_service` en `api/dependencies.py` |
| 10. Pruebas de aceptación | `tests/hu/test_hu01_registrar_material.py` |

**Validación de entrada (400).** En el DTO, la tabla `mensajes_error` asocia cada
`(campo en camelCase, tipo de error de Pydantic)` con su mensaje (`"*"` = cualquier error del
campo) y los `@field_validator` usan los objetos de valor y lanzan `error_de_negocio(mensaje)`.
El manejador global responde 400 con ese texto y el traceId.

**Servicio.** Patrón general (ver `MaterialService.registrar`):

```python
@operacion_de_negocio("REGISTRAR_MATERIAL", RECURSO, mensaje_error_bd=mensajes.HU01_C8,
                      mensaje_servicio_externo=mensajes.HU01_C6)
async def registrar(self, comando):
    async with self._uow:                                   # Unit of Work: una transacción
        if await self._materiales.existe_nombre(nombre):
            raise ConflictoError(formatear(mensajes.HU01_C3, Nombre=nombre))
    ...
    async with self._uow:
        self._materiales.agregar(material)
        self._auditar("REGISTRAR_MATERIAL", RECURSO, material.id_material, 201)
        await self._uow.commit()
    self._publicar(TipoEvento.MATERIAL_REGISTRADO, materialId=material.id_material)
    return Resultado(material, formatear(mensajes.HU01_C7, Nombre=nombre, SKU=sku))
```

No hace falta capturar los fallos de base de datos ni de las APIs externas: el decorador
`@operacion_de_negocio` los traduce al 500 o al 503 con el mensaje de la HU y registra los
rechazos en la auditoría. Mientras una ruta exista sin su lógica, el servicio puede lanzar
`NoImplementadoError("HU-XX")` (responde 501).

**Pruebas.** `tests/hu/test_huXX_*.py` con una prueba por criterio (código HTTP y mensaje).
Para probar sin base de datos, reemplazar el servicio con `app.dependency_overrides` y los
dobles de `tests/dobles` (como el fixture `escenario` de HU-01). `pytest` en verde y Pull
Request con la plantilla.

---

## 5. Base de datos

```bash
alembic upgrade head                          # aplicar migraciones (el contenedor lo hace al arrancar)
alembic revision --autogenerate -m "cambio"   # nueva migración después de cambiar un modelo
alembic check                                 # falla si modelos y migraciones difieren (lo prueba la suite)
```

- Tablas: `material` y `auditoria` (las del resto del MER se agregan con nuevas migraciones
  cuando se implementen sus historias).
- ID `mat-NNN` desde la secuencia `seq_material` de PostgreSQL (mínimo 3 dígitos; una
  transacción revertida deja un salto en la numeración).
- Nombre único sin distinguir mayúsculas: índice `lower(nombre)` en `material`.
- Fechas `TIMESTAMP WITH TIME ZONE` (UTC), devueltas en ISO 8601.

> La migración `0001` se reescribió en el sprint 0 para dejar solo estas dos tablas. Si tienen
> una base local creada con la versión anterior, recréenla: `docker compose down -v` y
> `docker compose up` (borra los datos del volumen).

---

## 6. Integración con otras células

| | Inventario (célula 4) |
|---|---|
| Este módulo llama | `POST /inventario/materias-primas` (HU-01 c4) |
| Configuración | `INVENTARIO_URL`, `INVENTARIO_RUTA_MATERIAS_PRIMAS` |
| Contrato por acordar | Nombres de los campos JSON y código HTTP del nombre repetido: constantes en `app/infraestructure/clients/inventario_client.py` |

Todas las llamadas salientes tienen timeout total de 5 s, circuit breaker (5 fallos seguidos
lo abren por 30 s; configurable) y envían las cabeceras `X-Trace-Id` y `X-Servicio-Origen`.
Pedimos a las otras células que nos envíen las mismas cabeceras: el traceId se reutiliza y el
origen queda en la auditoría.

---

## 7. Errores, logs y auditoría

- Éxito: campos del recurso en camelCase y `mensaje` cuando el backlog lo define.
- Error: `{"mensaje": "...", "traceId": "..."}` y cabecera `X-Trace-Id`.

| Excepción (`app/core/exceptions.py`) | HTTP |
|---|---|
| Error de validación del DTO / `SolicitudInvalidaError` | 400 |
| `RecursoNoEncontradoError` | 404 |
| `ConflictoError` | 409 |
| `ReglaDeNegocioError` | 422 |
| `ErrorInterno` (BD caída o timeout) / cualquier error no controlado | 500 |
| `NoImplementadoError` (HU pendiente) | 501 |
| `DependenciaNoDisponibleError` (Inventario) | 503 |

- Logs: una línea JSON por evento en la salida estándar (`docker compose logs api`), con
  `traceId` y `origen`. Buscar un error por su traceId: `docker compose logs api | grep <traceId>`.
- Auditoría (tabla `auditoria`, solo inserción): cada escritura exitosa (en la misma
  transacción) y cada rechazo o fallo de una escritura (en una transacción propia), con fecha,
  operación, recurso, código HTTP, origen y traceId. Las consultas no se auditan.

---

## 8. Monitoreo

- `GET /health`: 200 si la API alcanza su base de datos, 503 si no; incluye el estado del
  circuit breaker de Inventario. Lo usan el `HEALTHCHECK` de Docker y el pipeline después de desplegar.
- `GET /metrics`: peticiones por ruta y código, latencia, memoria del proceso, llamadas a otras
  células, circuit breakers y eventos de negocio.
- Prometheus recoge la API y node-exporter (CPU, memoria y disco de la EC2) cada 15 s.
- Grafana carga sola la fuente de datos y el tablero **API Materiales y Fórmulas**
  (`monitoring/grafana/dashboards/materiales-api.json`).

---

## 9. CI/CD y despliegue

**Integración continua** (`.github/workflows/ci.yml`), en cada Pull Request y push a `develop`:

1. Calidad: linter (`ruff`), type checker (`mypy`) y validación de arquitectura (`import-linter`).
2. Pruebas unitarias y de integración contra PostgreSQL (levantado con `docker compose`),
   cobertura mínima del 80 % y análisis de SonarCloud con quality gate.
3. Build de la imagen Docker (sin publicarla).

**Despliegue continuo** (`.github/workflows/cd.yml`), en cada push a `main` (al fusionar `develop`):
se publica la imagen en GHCR (`ghcr.io/<propietario>/materiales-formulas-api:<commit>` y `:latest`)
y se despliega en la EC2 por SSH; al final se verifica `/health`.

**Configuración única en GitHub**

1. *Settings → Branches*: regla para `develop` con "Require a pull request before merging",
   1 aprobación y los checks obligatorios **Linter, type checker y arquitectura**,
   **Pruebas, cobertura y SonarCloud** y **Build de la imagen Docker**; regla para `main` con
   "Require a pull request before merging" (solo se fusiona `develop`).
2. *Settings → Secrets and variables → Actions*: `SONAR_TOKEN`, `EC2_HOST`, `EC2_USUARIO`,
   `EC2_LLAVE_SSH`, `POSTGRES_USER` y `POSTGRES_PASSWORD` (BD de pruebas del CI), y opcionalmente
   la variable `EC2_DIRECTORIO`.

**SonarCloud**: importar el repositorio, desactivar *Automatic Analysis* (el análisis lo hace
el pipeline), generar el token y poner la organización y la llave del proyecto en
`sonar-project.properties`.

**EC2 (una sola vez)**

```bash
# Docker Engine y el plugin Compose instalados; el usuario SSH en el grupo docker.
mkdir -p ~/materiales-formulas && cd ~/materiales-formulas
nano .env      # copiar .env.example y completar: usuarios, claves y URLs de las otras células
```

Grupo de seguridad: 22 (SSH del pipeline) y `API_PUERTO_HOST` (API), abierto solo a las IP de
las EC2 de las otras células.
PostgreSQL y node-exporter no se publican; Prometheus y Grafana solo escuchan en localhost de
la EC2 (`ssh -L 9090:localhost:9090 -L 3820:localhost:3820 ...` para verlos).

**Volver a una versión anterior** (en la EC2):
`API_IMAGEN=ghcr.io/<propietario>/materiales-formulas-api API_TAG=<commit anterior> docker compose up -d api`.

---

## 10. Patrones del DAS en el código

| Patrón / táctica | Dónde |
|---|---|
| Layered Architecture | `app/api`, `app/business`, `app/infraestructure`, `app/core` + `lint-imports` y `tests/unit/test_arquitectura.py` |
| DTO · Canonical Schema | `app/api/schemas/` (camelCase, `extra="forbid"`) |
| Tabla de auditoría | `app/infraestructure/models/auditoria.py`, `repositories/auditoria_repository.py`, `ServicioBase._auditar` |
| Observer | `app/core/events.py` (suscriptores: log y métricas) |
| Correlation ID | `app/api/middleware.py`, `app/core/contexto.py`, `app/infraestructure/clients/base.py` |
| Unit of Work | `app/infraestructure/unit_of_work.py` |
| Transaction Script | Cada método de servicio + `@operacion_de_negocio` (`app/business/services/base.py`) |
| Global Exception Handler | `app/api/exception_handlers.py` |
| Timeout | `app/infraestructure/database.py` (BD) y `app/infraestructure/clients/base.py` (HTTP) |
| Circuit Breaker | `app/infraestructure/clients/circuit_breaker.py` |
| Dependency Injection | `app/api/dependencies.py` (`Depends`) |
| Object Pool | Pool de conexiones (`database.py`) y un `httpx.AsyncClient` compartido (`main.py`) |
| Gateway | `app/infraestructure/clients/` |
| Repository | `app/infraestructure/interfaces/` + `app/infraestructure/repositories/` |
| Value Object | `app/business/domain/value_objects.py` |
| Service Layer | `app/business/services/` |
| Externalized Configuration | `app/core/config.py`, `.env.example`, `docker-compose.yml`, secretos de GitHub |
| Application Metrics · Health Endpoint | `app/core/metrics.py`, `/metrics`, `app/api/routers/health.py` |
| Contenerización · límites de recursos | `Dockerfile`, `docker-compose.yml` |
| Test Double | `tests/dobles/` |

Los patrones que dependen de historias aún no implementadas (Soft Delete en HU-04,
Pagination, Specification y State en las fórmulas) se agregan junto con esas historias.

RBAC no está implementado: el DAS excluye la autenticación del alcance, así que no hay roles
que verificar.

---

## 11. Decisiones y pendientes

### POR ACORDAR con otras células

1. **Inventario**: nombres de los campos JSON del alta, campo con el Código de artículo en la
   respuesta y código HTTP con que rechaza un nombre repetido (se asumió 409; constantes en
   `inventario_client.py`).
2. **Patent Sweep** (HU-09, aún sin implementar): URL y ruta de su API para la solicitud de
   evaluación (`PATENT_SWEEP_URL` y `PATENT_SWEEP_RUTA_EVALUACION`, ya definidas en
   `.env.example`, `docker-compose.yml` y `config.py`).
3. URLs de las EC2 de ambas células y uso de las cabeceras `X-Trace-Id` y `X-Servicio-Origen`.

### Vacíos del backlog en HU-01 (confirmar con el PO)

1. Un campo enviado con `null`, o un Nombre vacío o solo con espacios, se trata como omitido
   (mensaje "es obligatorio").
2. Un Nombre que no es texto (p. ej. un número JSON) responde "contiene caracteres no permitidos".
3. Si Inventario devuelve un Código de artículo que no tiene el formato MP-00000, se trata como
   una falla de Inventario (503 con el mensaje de c6) y no se guarda el material.
4. Si dos peticiones registran el mismo nombre a la vez, el índice único rechaza la segunda y
   se responde 409 con el mensaje de c3 (Inventario ya habrá registrado el artículo; queda en
   el log con su SKU).

### Decisiones tomadas en este código

- Validaciones de contrato → **400** (no el 422 por defecto de FastAPI); 422 se reserva para
  reglas de negocio. HU pendiente → 501.
- Mensajes genéricos fuera del backlog: solicitud no válida sin mensaje propio (400), ruta
  inexistente (404), método no permitido (405) y error no controlado (500), en `mensajes.py`.
- Fechas `TIMESTAMPTZ` en lugar de `TIMESTAMP` (la figura del MER), para devolver UTC en ISO 8601.
- Imagen `postgres:16` (Debian) en lugar de Alpine, para que `lower()` trate bien las tildes.
- Los rechazos por validación del DTO (400) quedan en el log, no en la tabla de auditoría
  (no llegan a la capa de negocio).
- `/health` responde 503 solo si falla la base de datos propia; si Inventario falla, la API
  sigue sana y las operaciones que lo usan responden 503.
- Un solo proceso de Uvicorn (las métricas viven en memoria del proceso).
- Diferencias con la tabla de atributos del DAS: el código usa `app/api/routers`,
  `app/business/services` y `app/api/exception_handlers.py` (secciones 1.5 y 2); en la tabla
  aún aparecen `v1/endpoints`, `use_cases` y el manejador en `app/core`.
