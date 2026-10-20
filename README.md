# API Materiales y Fórmulas · Cutit Saws Ltd.

API REST de la célula 1 de la plataforma backend de Cutit Saws (Desarrollo de Software II, 2026-2).
Implementa el **DAS v1.2** del módulo y el **product backlog V1.3** (HU-01 a HU-11).

> **Estado:** base lista para la fase de codificación. La infraestructura transversal
> funciona y está probada; cada historia de usuario tiene su ruta, su DTO, su servicio y sus
> pruebas pendientes, y responde **501** hasta que se implemente.

| Funciona hoy | Pendiente (por HU) |
|---|---|
| Arquitectura en capas, inyección de dependencias, configuración por variables de entorno | Lógica de cada servicio (`raise NoImplementadoError`) con sus pasos documentados en `TODO(HU-XX)` |
| Modelos ORM del MER, migración Alembic, repositorios con paginación y filtros en SQL | Mapeo de cada error de validación a su mensaje del backlog en los DTO (`TODO(HU-XX)`) |
| Unidad de trabajo (commit/rollback, timeout de 5 s), auditoría, eventos de dominio | 83 pruebas de criterios de aceptación en `tests/hu` (con `skip`) |
| Clientes de Inventario y Patent Sweep (timeout de 5 s, circuit breaker, traceId) | Contratos POR ACORDAR con Inventario y Patent Sweep |
| traceId, logs JSON, manejador global de errores, `/health`, `/metrics`, Swagger | |
| Dominio: objetos de valor, especificaciones, estados de la fórmula, 96 mensajes del backlog | |
| Dockerfile, Docker Compose, Prometheus, Grafana, node-exporter, GitHub Actions, SonarCloud | |
| 194 pruebas unitarias y de integración (incluida una que vigila la regla de capas) | |

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
│   ├── paginacion.py           Página de resultados (LIMIT/OFFSET)
│   └── openapi.py              Documentación del contrato (/docs)
├── presentation/               Capa de presentación (API REST)
│   ├── routers/                materiales.py · formulas.py · evaluacion_patente.py · health.py
│   ├── schemas/                DTO de Pydantic (contratos de entrada y salida, camelCase)
│   ├── middleware.py           traceId por petición (Correlation ID)
│   ├── exception_handlers.py   Manejador global de excepciones
│   └── dependencies.py         Inyección de dependencias (raíz de composición)
├── business/                   Capa de lógica de negocio
│   ├── services/               MaterialService · FormulaService · EvaluacionPatenteService (casos de uso)
│   └── domain/                 enums · value_objects · specifications · formula_states · mensajes
└── data_access/                Capa de acceso a datos
    ├── interfaces/             Contratos que usan los servicios (repositorios, clientes, unidad de trabajo)
    ├── repositories/           Implementaciones con SQLAlchemy
    ├── models/                 Modelos ORM (tablas del MER)
    ├── clients/                Clientes HTTP de Inventario y Patent Sweep + circuit breaker
    ├── unit_of_work.py         Transacción: commit / rollback
    └── database.py             Motor, pool de conexiones y timeouts
migrations/                     Migraciones versionadas (Alembic)
tests/
├── unit/                       Sin base de datos ni APIs externas
├── integration/                Contra PostgreSQL (TEST_DATABASE_URL)
├── hu/                         Una prueba por criterio de aceptación (pendientes)
├── dobles/                     Repositorios y clientes en memoria (Test Double)
└── fabricas.py                 Objetos de prueba con valores válidos
monitoring/                     prometheus.yml y aprovisionamiento + tablero de Grafana
.github/workflows/ci-cd.yml     Pipeline: build, pruebas, SonarCloud, imagen en GHCR y despliegue en EC2
```

**Regla de dependencias** (la verifica `tests/unit/test_arquitectura.py`):
`presentation → business → data_access`, y todas pueden usar `core`. Ninguna capa importa de
una capa superior. Los servicios no importan FastAPI, Pydantic, SQLAlchemy ni httpx: reciben
interfaces. Solo `app/main.py` y `app/presentation/dependencies.py` conocen las clases
concretas, porque arman los objetos que se inyectan.

---

## 2. Puesta en marcha

Requisitos: Python 3.12 y Docker con el plugin Compose.

### Todo con Docker Compose

```bash
cp .env.example .env          # completar claves; para pruebas locales las URLs de otras células pueden quedar así
docker compose up --build     # usa docker-compose.yml + docker-compose.override.yml
```

| Servicio | URL |
|---|---|
| Swagger (contrato) | http://localhost:8000/docs |
| Estado | http://localhost:8000/health |
| Métricas | http://localhost:8000/metrics |
| Grafana | http://localhost:3000 (usuario y clave del `.env`) |
| Prometheus | http://localhost:9090 |

### API en Python, base de datos en Docker (para desarrollar)

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env                       # agregar POSTGRES_HOST=localhost
docker compose up -d postgres              # PostgreSQL en localhost:5432
alembic upgrade head
uvicorn app.main:app --reload
```

---

## 3. Pruebas

```bash
pytest                                     # todo (las de integración se omiten si no hay PostgreSQL)
pytest tests/unit                          # rápidas, sin base de datos
pytest -m integracion                      # requiere TEST_DATABASE_URL
pytest --cov --cov-report=term-missing     # cobertura
```

Las pruebas de integración usan `TEST_DATABASE_URL`
(por defecto `postgresql+asyncpg://materiales:materiales@127.0.0.1:5432/materiales_formulas_test`).
Al empezar, aplican las migraciones desde cero en esa base: **no la apunten a una base con datos**.

```bash
docker compose exec postgres createdb -U materiales materiales_formulas_test
```

---

## 4. Cómo implementar una historia de usuario

Ejemplo con HU-04 (inhabilitar material); el resto sigue el mismo camino.

1. **Leer el `TODO(HU-04)`** del servicio (`app/business/services/material_service.py`). Tiene
   los pasos en el orden del backlog, el criterio de cada uno y la constante del mensaje.
2. **Validación de entrada** (si la HU tiene cuerpo o parámetros): completar `mensajes_error`
   y los validadores del DTO según su `TODO`. Cada error de validación debe terminar en el
   mensaje literal del backlog (`app/business/domain/mensajes.py`); el manejador global responde
   400 con ese texto y el traceId.
3. **Servicio**: reemplazar `raise NoImplementadoError("HU-04")` por la lógica. Patrón general:

   ```python
   async with self._uow:                                   # Unit of Work: una transacción
       material = await self._materiales.obtener_por_id(id_material)
       if material is None:
           raise RecursoNoEncontradoError(formatear(mensajes.HU04_C4, id_material=id_material))
       ...                                                 # reglas: especificaciones y estados del dominio
       self._auditar("INHABILITAR_MATERIAL", RECURSO, id_material, 200)
       await self._uow.commit()
   self._publicar(TipoEvento.MATERIAL_INHABILITADO, materialId=id_material)
   return Resultado(material, formatear(mensajes.HU04_C2, id_material=id_material))
   ```

   No hace falta capturar los fallos de base de datos ni de las APIs externas: el decorador
   `@operacion_de_negocio` los traduce al 500 o al 503 con el mensaje de la HU y registra los
   rechazos en la auditoría.
4. **Router y DTO de salida**: ya están hechos; revisar que la respuesta tenga los campos del criterio.
5. **Pruebas**: en `tests/hu/test_hu04_inhabilitar_material.py`, quitar el `skip` de cada
   criterio implementado y escribir la prueba (código HTTP y mensaje). Para probar el servicio
   sin base de datos usar `tests/dobles`; para la ruta, ver `tests/unit/test_rutas.py`.
6. `pytest` en verde y Pull Request con la plantilla.

---

## 5. Base de datos

```bash
alembic upgrade head                          # aplicar migraciones (el contenedor lo hace al arrancar)
alembic revision --autogenerate -m "cambio"   # nueva migración después de cambiar un modelo
alembic check                                 # falla si modelos y migraciones difieren (lo prueba la suite)
```

- Tablas del MER: `material`, `formula`, `componente_formula`, `evaluacion_patente`,
  `patente_conflicto` y `auditoria`.
- IDs `mat-NNN`, `form-NNN` y `tck-NNN` desde secuencias de PostgreSQL (mínimo 3 dígitos;
  una transacción revertida deja un salto en la numeración).
- Nombre único sin distinguir mayúsculas: índices `lower(nombre)` en material y fórmula.
- A lo sumo un trámite de patente abierto por fórmula: índice único parcial.
- Fechas `TIMESTAMP WITH TIME ZONE` (UTC), devueltas en ISO 8601.

---

## 6. Integración con otras células

| | Inventario (célula 4) | Patent Sweep (célula 2) |
|---|---|---|
| Este módulo llama | `POST /inventario/materias-primas` (HU-01) y `PATCH /inventario/articulos/{codigo}` (HU-03) | Solicitud de evaluación (HU-09), ruta **POR ACORDAR** |
| Este módulo recibe | — | `GET /formulas/aprobadas` (HU-11) y `POST /formulas/{id}/dictamen-patente` (HU-10) |
| Configuración | `INVENTARIO_URL`, `INVENTARIO_RUTA_*` | `PATENT_SWEEP_URL`, `PATENT_SWEEP_RUTA_EVALUACION` |
| Contrato por acordar | Nombres de los campos JSON y código HTTP del nombre repetido: constantes en `app/data_access/clients/inventario_client.py` | Ruta y código de aceptación: `app/data_access/clients/patent_sweep_client.py` |

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
| `DependenciaNoDisponibleError` (Inventario o Patent Sweep) | 503 |

- Logs: una línea JSON por evento en la salida estándar (`docker compose logs api`), con
  `traceId` y `origen`. Buscar un error por su traceId: `docker compose logs api | grep <traceId>`.
- Auditoría (tabla `auditoria`, solo inserción): cada escritura exitosa (en la misma
  transacción) y cada rechazo o fallo de una escritura (en una transacción propia), con fecha,
  operación, recurso, código HTTP, origen y traceId. Las consultas no se auditan.

---

## 8. Monitoreo

- `GET /health`: 200 si la API alcanza su base de datos, 503 si no; incluye el estado de los
  circuit breakers. Lo usan el `HEALTHCHECK` de Docker y el pipeline después de desplegar.
- `GET /metrics`: peticiones por ruta y código, latencia, memoria del proceso, llamadas a otras
  células, circuit breakers y eventos de negocio.
- Prometheus recoge la API y node-exporter (CPU, memoria y disco de la EC2) cada 15 s.
- Grafana carga sola la fuente de datos y el tablero **API Materiales y Fórmulas**
  (`monitoring/grafana/dashboards/materiales-api.json`).

---

## 9. CI/CD y despliegue

**Pipeline** (`.github/workflows/ci-cd.yml`):

1. En cada Pull Request hacia `main`: build, pruebas (unitarias e integración con PostgreSQL) y
   análisis de SonarCloud con quality gate.
2. Al fusionar el PR en `main`: lo mismo y, solo si se aprueba el quality gate, se publica la
   imagen en GHCR (`ghcr.io/<propietario>/materiales-formulas-api:<commit>` y `:latest`) y se
   despliega en la EC2 por SSH; al final se verifica `/health`.

**Configuración única en GitHub**

1. *Settings → Branches*: regla para `main` con "Require a pull request before merging",
   1 aprobación y el check obligatorio **Build, pruebas y SonarCloud**.
2. *Settings → Secrets and variables → Actions*: `SONAR_TOKEN`, `EC2_HOST`, `EC2_USUARIO`,
   `EC2_LLAVE_SSH` (y opcionalmente la variable `EC2_DIRECTORIO`).

**SonarCloud**: importar el repositorio, desactivar *Automatic Analysis* (el análisis lo hace
el pipeline), generar el token y poner la organización y la llave del proyecto en
`sonar-project.properties`.

**EC2 (una sola vez)**

```bash
# Docker Engine y el plugin Compose instalados; el usuario SSH en el grupo docker.
mkdir -p ~/materiales-formulas && cd ~/materiales-formulas
nano .env      # copiar .env.example y completar: claves, API_IMAGEN en minúsculas, URLs de las otras células
```

Grupo de seguridad: 22 (SSH del pipeline), 8000 (API, para las otras células) y 3000
(Grafana, para el equipo). PostgreSQL y node-exporter no se publican; Prometheus solo escucha
en localhost de la EC2 (`ssh -L 9090:localhost:9090 ...` para verlo).

**Volver a una versión anterior** (en la EC2):
`API_TAG=<commit anterior> docker compose up -d api`.

---

## 10. Patrones del DAS en el código

| Patrón / táctica | Dónde |
|---|---|
| Layered Architecture | `app/presentation`, `app/business`, `app/data_access`, `app/core` + `tests/unit/test_arquitectura.py` |
| DTO · Canonical Schema | `app/presentation/schemas/` (camelCase, `extra="forbid"`) |
| Soft Delete | `estado = INACTIVO` en `MaterialService.inhabilitar` (HU-04) |
| Tabla de auditoría | `app/data_access/models/auditoria.py`, `repositories/auditoria_repository.py`, `ServicioBase._auditar` |
| Observer | `app/core/events.py` (suscriptores: log y métricas) |
| Correlation ID | `app/presentation/middleware.py`, `app/core/contexto.py`, `app/data_access/clients/base.py` |
| Unit of Work | `app/data_access/unit_of_work.py` |
| Transaction Script | Cada método de servicio + `@operacion_de_negocio` (`app/business/services/base.py`) |
| Global Exception Handler | `app/presentation/exception_handlers.py` |
| Timeout | `app/data_access/database.py` (BD) y `app/data_access/clients/base.py` (HTTP) |
| Circuit Breaker | `app/data_access/clients/circuit_breaker.py` |
| Pagination | `app/core/paginacion.py` y repositorios (`LIMIT/OFFSET` en SQL) |
| Dependency Injection | `app/presentation/dependencies.py` (`Depends`) |
| Object Pool | Pool de conexiones (`database.py`) y un `httpx.AsyncClient` compartido (`main.py`) |
| Gateway | `app/data_access/clients/` |
| Repository | `app/data_access/interfaces/` + `app/data_access/repositories/` |
| Value Object · Specification | `app/business/domain/value_objects.py`, `specifications.py` |
| State | `app/business/domain/formula_states.py` |
| Domain Service · Service Layer | `app/business/services/` |
| Externalized Configuration | `app/core/config.py`, `.env.example`, `docker-compose.yml`, secretos de GitHub |
| Application Metrics · Health Endpoint | `app/core/metrics.py`, `/metrics`, `app/presentation/routers/health.py` |
| Contenerización · límites de recursos | `Dockerfile`, `docker-compose.yml` |
| Test Double | `tests/dobles/` |

RBAC no está implementado: el DAS excluye la autenticación del alcance, así que no hay roles
que verificar. El callback del dictamen (HU-10) queda abierto, como riesgo documentado.

---

## 11. Decisiones y pendientes

### POR ACORDAR con otras células

1. **Inventario**: nombres de los campos JSON del alta y del cambio de nombre, campo con el
   Código de artículo en la respuesta y código HTTP con que rechaza un nombre repetido
   (se asumió 409; constantes en `inventario_client.py`).
2. **Patent Sweep**: ruta de su API para la solicitud de evaluación (`PATENT_SWEEP_RUTA_EVALUACION`).
3. URLs de las EC2 de ambas células y uso de las cabeceras `X-Trace-Id` y `X-Servicio-Origen`.

### Vacíos del backlog (confirmar con el PO)

1. HU-01: no hay mensaje para Densidad o Pureza con valor no válido (solo para "obligatorio").
2. HU-01 y HU-03: cómo contar "máximo 4 / 3 caracteres" de un número (se cuenta el número sin
   ceros sobrantes: 7.850 → "7.85" → 4).
3. HU-02 c3: el listado `GET /materiales` no tiene definidos filtros, tamaño de página ni orden.
4. HU-02, HU-03, HU-06, HU-07, HU-09 y HU-10: un ID con formato inválido no tiene mensaje 400;
   se responde 404 (no existe). Solo HU-04 y HU-08 validan el formato (400).
5. HU-03 c4: si el nombre solo cambia en mayúsculas o minúsculas, ¿se envía a Inventario?
6. HU-03: no hay mensaje si el cuerpo incluye el ID (solo para SKU y Unidad de medida).
7. HU-05 y HU-07: no hay mensajes para nombre de más de 80 caracteres, nombre no alfabético,
   aplicación técnica de más de 200 caracteres, la misma línea de material repetida ni Unidad
   de medida enviada por el cliente (hoy: 400 con el mensaje genérico).
8. HU-05: unicidad del nombre de la fórmula sin distinguir mayúsculas (supuesto del MER).
9. HU-07: el backlog no dice qué pasa si el nuevo nombre ya existe en otra fórmula.
10. HU-06: nombres de los parámetros de consulta, parámetro de página y zona horaria de las
    fechas DD/MM/AAAA (UTC o America/Bogota).
11. HU-09: no hay mensaje 500 para un fallo de la base de datos (se usa el genérico).
12. HU-10: no hay mensaje si falta `patentesEnConflicto`; en el backlog los mensajes del
    criterio 6 están numerados 5.1 y 5.2 (en el código: `HU10_C6_1` y `HU10_C6_2`).
13. Respuestas de HU-04 y HU-08: el backlog solo define el mensaje; se devuelve además el ID y
    el estado (igual que HU-10 c2).

### Decisiones tomadas en este código

- Validaciones de contrato → **400** (no el 422 por defecto de FastAPI); 422 solo para reglas de
  negocio (HU-05, HU-07 y HU-09). HU pendiente → 501.
- Mensajes genéricos fuera del backlog: ruta inexistente (404), método no permitido (405) y
  error no controlado (500), en `mensajes.py`.
- Fechas `TIMESTAMPTZ` en lugar de `TIMESTAMP` (la figura del MER), para devolver UTC en ISO 8601.
- Imagen `postgres:16` (Debian) en lugar de Alpine, para que `lower()` trate bien las tildes.
- Los rechazos por validación del DTO (400) quedan en el log, no en la tabla de auditoría
  (no llegan a la capa de negocio).
- `/health` responde 503 solo si falla la base de datos propia; si Inventario o Patent Sweep
  fallan, la API sigue sana y esas operaciones responden 503.
- Un solo proceso de Uvicorn (las métricas viven en memoria del proceso).
- Diferencias con la tabla de atributos del DAS: el código usa `app/presentation/routers`,
  `app/business/services` y `app/presentation/exception_handlers.py` (secciones 1.5 y 2); en la
  tabla aún aparecen `v1/endpoints`, `use_cases` y el manejador en `app/core`.
