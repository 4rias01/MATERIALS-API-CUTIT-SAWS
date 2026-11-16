# API Materiales y Fórmulas · Cutit Saws Ltd.

API REST de la célula 1 de la plataforma backend de Cutit Saws (Desarrollo de Software II, 2026-2).
Implementa el **DAS v1.2** del módulo y el **product backlog V1.3**.

> **Estado: arquetipo + CRUD básico de materiales.** La infraestructura transversal funciona y
> hay un **CRUD básico de `/materiales`** (equivalente al CRUD de profesores del dojo de Java)
> con pruebas unitarias y de integración. **Aún no hay historias de usuario implementadas**:
> cada historia se agrega siguiendo la sección 4.

| Funciona hoy | Pendiente |
|---|---|
| Arquitectura en capas, inyección de dependencias, configuración por variables de entorno | HU-01 a HU-11 (rutas, DTO, servicios, tablas, clientes y pruebas) |
| CRUD básico de materiales: crear, listar, buscar por id o por nombre, actualizar y eliminar | Clientes de Inventario y Patent Sweep (contrato POR ACORDAR, sección 11) |
| Modelos ORM y migraciones Alembic de `auditoria` y `material` | Pruebas del resto de la infraestructura (cobertura < 80 %, sección 3) |
| Unidad de trabajo (commit/rollback, timeout de 5 s), auditoría, eventos de dominio | |
| Cliente HTTP base (timeout de 5 s, circuit breaker, traceId) | |
| traceId, logs JSON, manejador global de errores, `/health`, `/metrics`, Swagger | |
| Dockerfile, Docker Compose, Prometheus, Grafana, node-exporter, GitHub Actions, SonarCloud | |
| Pruebas unitarias (`MaterialService`) y de integración (API de materiales contra PostgreSQL) | |
| Análisis estático de seguridad: reglas de Bandit en ruff (CI), Semgrep OWASP Top 10 y pip-audit | |

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
│   ├── routers/                health.py · materiales.py
│   ├── schemas/                DTO de Pydantic (contratos de entrada y salida, camelCase)
│   ├── middleware.py           traceId por petición (Correlation ID)
│   ├── exception_handlers.py   Manejador global de excepciones
│   └── dependencies.py         Inyección de dependencias (raíz de composición)
├── business/                   Capa de lógica de negocio
│   ├── services/               base.py (transacción, auditoría, errores) · comandos.py · material_service.py · salud_service.py
│   └── domain/                 enums · errores · eventos · mensajes
└── infraestructure/            Capa de acceso a datos
    ├── interfaces/             Contratos que usan los servicios (repositorios, cliente, unidad de trabajo)
    ├── repositories/           Implementaciones con SQLAlchemy
    ├── models/                 Modelos ORM (auditoria y material)
    ├── clients/                Cliente HTTP base + circuit breaker
    ├── unit_of_work.py         Transacción: commit / rollback
    └── database.py             Motor, pool de conexiones y timeouts
migrations/                     Migraciones versionadas (Alembic)
tests/
├── conftest.py                 Fixtures comunes: app, cliente HTTP en memoria, configuración de prueba
├── unit/                       Sin base de datos: test_material_service.py (repositorio simulado con AsyncMock)
├── integration/                Contra PostgreSQL (TEST_DATABASE_URL): test_material_api.py; conftest.py aplica migraciones
├── hu/                         Una o más pruebas por criterio de aceptación (vacío por ahora)
└── dobles/                     Unidad de trabajo y auditoría en memoria (Test Double)
monitoring/                     prometheus.yml y aprovisionamiento + tablero de Grafana
.github/workflows/ci.yml        Integración continua (develop): ruff, mypy, import-linter, pruebas, SonarCloud
.github/workflows/cd.yml        Despliegue continuo (main): imagen en GHCR y despliegue en EC2
pyproject.toml                  Configuración de ruff, mypy e import-linter
```

**Regla de dependencias** (la verifica `lint-imports`):
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
| Prometheus | http://localhost:9520 |

**Puertos.** Ningún servicio usa el puerto por defecto de su producto, para no exponer puertos
predecibles: API 8520, PostgreSQL 5520, Prometheus 9520, Grafana 3820 y node-exporter 9530
(dentro de la red de Docker). En el host solo se publican `API_PUERTO_HOST` (del `.env`),
y Prometheus y Grafana únicamente en `127.0.0.1`. En desarrollo PostgreSQL se publica en
`127.0.0.1:POSTGRES_PUERTO_HOST` (5533 en `.env.example`).

### CRUD de materiales

| Método y ruta | Respuesta |
|---|---|
| `POST /materiales` | 201 con el material creado · 400 datos no válidos · 409 nombre repetido |
| `GET /materiales` | 200 con la lista |
| `GET /materiales/buscar?nombre=` | 200 con los que contienen el texto (sin distinguir mayúsculas) |
| `GET /materiales/{id}` | 200 · 404 si no existe |
| `PUT /materiales/{id}` | 200 con el material actualizado · 404 · 409 nombre de otro material |
| `DELETE /materiales/{id}` | 204 · 404 |

Cuerpo de POST y PUT: `{"nombre", "categoria", "unidadMedida", "densidad", "pureza"}`. El id lo
asigna la base de datos; en PUT va en la ruta, y cualquier campo extra (incluido `id`) se
rechaza con 400.

### API en Python, base de datos en Docker (para desarrollar)

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env                       # completar y descomentar POSTGRES_HOST/POSTGRES_PORT
docker compose up -d postgres              # PostgreSQL en localhost:POSTGRES_PUERTO_HOST
alembic upgrade head
uvicorn app.main:app --reload --port 8520
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

**Análisis estático de seguridad (OWASP Top 10).** `ruff check .` ya incluye las reglas de
Bandit (`S`), así que el CI las aplica en cada PR. Para un análisis completo:

```bash
pip install bandit semgrep pip-audit
bandit -r app migrations                                        # SAST de Python
semgrep scan --metrics=off --config p/owasp-top-ten --config p/python --config p/secrets \
  --config p/dockerfile --config p/docker-compose --config p/github-actions --exclude .venv .
pip-audit -r requirements.txt -r requirements-dev.txt           # dependencias con CVE conocidas (A06)
```

> La cobertura actual (~72 %) está por debajo del 80 % que exige el CI: solo el CRUD de
> materiales tiene pruebas. Hay que agregar pruebas del resto de la infraestructura o ajustar
> el umbral en `.github/workflows/ci.yml`.

Las pruebas de integración usan `TEST_DATABASE_URL` (sin valor por defecto; si no está
definida se omiten), por ejemplo `postgresql+asyncpg://<usuario>:<clave>@127.0.0.1:<POSTGRES_PUERTO_HOST>/materiales_formulas_test`.
En el CI, PostgreSQL se levanta con `docker compose` y las credenciales salen de los secretos `POSTGRES_USER` y `POSTGRES_PASSWORD`.
Al empezar, aplican las migraciones desde cero en esa base: **no la apunten a una base con datos**.

```bash
docker compose exec postgres sh -c 'createdb -U "$POSTGRES_USER" materiales_formulas_test'
```

---

## 4. Cómo implementar una historia de usuario

Cada historia recorre los mismos archivos (ejemplo con HU-01, registrar material):

| Paso | Dónde |
|---|---|
| 1. Mensajes literales del backlog | `app/business/domain/mensajes.py` (`HU01_*`) |
| 2. Reglas del dominio (objetos de valor, enums) | `app/business/domain/` (p. ej. `value_objects.py`, `enums.py`) |
| 3. Tabla y migración (si hace falta) | `infraestructure/models/<tabla>.py` (importarla en `models/__init__.py`) + `alembic revision --autogenerate` |
| 4. Contrato del repositorio y su implementación | `infraestructure/interfaces/` y `infraestructure/repositories/` |
| 5. Cliente de otra célula (si hace falta) | Interfaz que hereda de `IClienteExterno` + clase que hereda de `ClienteHttpBase`; registrarlo en `app.state.clientes_externos` (`main.py`) |
| 6. Comando de entrada del caso de uso | `app/business/services/comandos.py` |
| 7. Servicio | `app/business/services/<recurso>_service.py`, heredando de `ServicioBase` |
| 8. DTO de entrada y salida | `app/api/schemas/<recurso>.py`, heredando de `EsquemaEntrada` / `EsquemaSalida` |
| 9. Ruta | `app/api/routers/<recurso>.py` + `include_router` en `main.py` + etiqueta en `core/openapi.py` |
| 10. Inyección de dependencias | `obtener_<recurso>_service` en `app/api/dependencies.py` |
| 11. Pruebas de aceptación | `tests/hu/test_huXX_*.py` (y los dobles que haga falta en `tests/dobles`) |

**Validación de entrada (400).** En el DTO, la tabla `mensajes_error` asocia cada
`(campo en camelCase, tipo de error de Pydantic)` con su mensaje (`"*"` = cualquier error del
campo) y los `@field_validator` usan los objetos de valor y lanzan `error_de_negocio(mensaje)`.
El manejador global responde 400 con ese texto y el traceId.

**Servicio.** Patrón general:

```python
class MaterialService(ServicioBase):
    @operacion_de_negocio("REGISTRAR_MATERIAL", "material", mensaje_error_bd=mensajes.HU01_C8,
                          mensaje_servicio_externo=mensajes.HU01_C6)
    async def registrar(self, comando: RegistrarMaterialComando) -> Resultado[Material]:
        async with self._uow:                                   # Unit of Work: una transacción
            if await self._materiales.existe_nombre(comando.nombre):
                raise ConflictoError(formatear(mensajes.HU01_C3, Nombre=comando.nombre))
        ...
        async with self._uow:
            self._materiales.agregar(material)
            self._auditar("REGISTRAR_MATERIAL", "material", material.id_material, 201)
            await self._uow.commit()
        self._publicar(TipoEvento.MATERIAL_REGISTRADO, materialId=material.id_material)
        return Resultado(material, formatear(mensajes.HU01_C7, Nombre=comando.nombre, SKU=sku))
```

No hace falta capturar los fallos de base de datos ni de las APIs externas: el decorador
`@operacion_de_negocio` los traduce al 500 o al 503 con el mensaje de la HU y registra los
rechazos en la auditoría. Mientras una ruta exista sin su lógica, el servicio puede lanzar
`NoImplementadoError("HU-XX")` (responde 501).

**Pruebas.** `tests/hu/test_huXX_*.py` con una prueba por criterio (código HTTP y mensaje).
Para probar sin base de datos, reemplazar el servicio o sus dependencias con
`app.dependency_overrides` y los dobles de `tests/dobles`. Al agregar una tabla, sumarla a
`TABLAS` en `tests/integration/conftest.py`. `pytest` en
verde y Pull Request con la plantilla.

---

## 5. Base de datos

```bash
alembic upgrade head                          # aplicar migraciones (el contenedor lo hace al arrancar)
alembic revision --autogenerate -m "cambio"   # nueva migración después de cambiar un modelo
alembic check                                 # falla si modelos y migraciones difieren
```

- Tablas: `auditoria` (0001) y `material` (0002, CRUD básico). Las del MER se agregan con
  nuevas migraciones cuando se implementen sus historias.
- `material`: id `BIGINT GENERATED ALWAYS AS IDENTITY`, nombre único sin distinguir
  mayúsculas (índice `lower(nombre)`), restricciones CHECK de categoría, unidad de medida,
  densidad (> 0) y pureza (0 a 100).
- Fechas `TIMESTAMP WITH TIME ZONE` (UTC), devueltas en ISO 8601.

> La migración `0001` se reescribió para dejar solo la tabla `auditoria`. Si tienen una base
> local creada con una versión anterior, recréenla: `docker compose down -v` y
> `docker compose up` (borra los datos del volumen).

---

## 6. Integración con otras células

Aún no hay clientes concretos: se crean con la primera historia que llame a otra célula.
Las URLs base ya se configuran con `INVENTARIO_URL` y `PATENT_SWEEP_URL`.

Todo cliente hereda de `ClienteHttpBase` (`app/infraestructure/clients/base.py`), así que sus
llamadas salientes tienen timeout total de 5 s, circuit breaker (5 fallos seguidos
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
| `DependenciaNoDisponibleError` (API de otra célula) | 503 |

- Logs: una línea JSON por evento en la salida estándar (`docker compose logs api`), con
  `traceId` y `origen`. Buscar un error por su traceId: `docker compose logs api | grep <traceId>`.
- Auditoría (tabla `auditoria`, solo inserción): cada escritura exitosa (en la misma
  transacción) y cada rechazo o fallo de una escritura (en una transacción propia), con fecha,
  operación, recurso, código HTTP, origen y traceId. Las consultas no se auditan.

---

## 8. Monitoreo

- `GET /health`: 200 si la API alcanza su base de datos, 503 si no; incluye el estado del
  circuit breaker de cada cliente registrado en `app.state.clientes_externos`. Lo usan el `HEALTHCHECK` de Docker y el pipeline después de desplegar.
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
la EC2 (`ssh -L 9520:localhost:9520 -L 3820:localhost:3820 ...` para verlos).

**Volver a una versión anterior** (en la EC2):
`API_IMAGEN=ghcr.io/<propietario>/materiales-formulas-api API_TAG=<commit anterior> docker compose up -d api`.

---

## 10. Patrones del DAS en el código

| Patrón / táctica | Dónde |
|---|---|
| Layered Architecture | `app/api`, `app/business`, `app/infraestructure`, `app/core` + `lint-imports` |
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
| Service Layer | `app/business/services/` |
| Externalized Configuration | `app/core/config.py`, `.env.example`, `docker-compose.yml`, secretos de GitHub |
| Application Metrics · Health Endpoint | `app/core/metrics.py`, `/metrics`, `app/api/routers/health.py` |
| Contenerización · límites de recursos | `Dockerfile`, `docker-compose.yml` |
| Test Double | `tests/dobles/` |

Los patrones que dependen de historias aún no implementadas (Value Object, Soft Delete en
HU-04, Pagination, Specification y State en las fórmulas) se agregan junto con esas historias.

RBAC no está implementado: el DAS excluye la autenticación del alcance, así que no hay roles
que verificar.

---

## 11. Decisiones y pendientes

### POR ACORDAR con otras células

1. **Inventario**: rutas, nombres de los campos JSON y códigos HTTP de las operaciones que
   use cada historia.
2. **Patent Sweep** (HU-09): ruta y contrato de la solicitud de evaluación.
3. URLs de las EC2 de ambas células y uso de las cabeceras `X-Trace-Id` y `X-Servicio-Origen`.

### Decisiones tomadas en este código

- Validaciones de contrato → **400** (no el 422 por defecto de FastAPI); 422 se reserva para
  reglas de negocio. HU pendiente → 501.
- Mensajes genéricos fuera del backlog: solicitud no válida sin mensaje propio (400), ruta
  inexistente (404), método no permitido (405) y error no controlado (500), en `mensajes.py`.
- Fechas `TIMESTAMPTZ` en lugar de `TIMESTAMP` (la figura del MER), para devolver UTC en ISO 8601.
- Imagen `postgres:16` (Debian) en lugar de Alpine, para que `lower()` trate bien las tildes.
- Los rechazos por validación del DTO (400) quedan en el log, no en la tabla de auditoría
  (no llegan a la capa de negocio).
- `/health` responde 503 solo si falla la base de datos propia; si otra célula falla, la API
  sigue sana y las operaciones que la usan responden 503.
- Un solo proceso de Uvicorn (las métricas viven en memoria del proceso).
- Diferencias con la tabla de atributos del DAS: el código usa `app/api/routers`,
  `app/business/services` y `app/api/exception_handlers.py` (secciones 1.5 y 2); en la tabla
  aún aparecen `v1/endpoints`, `use_cases` y el manejador en `app/core`.
