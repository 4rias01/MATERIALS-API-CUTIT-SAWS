## Tipo de cambio

- [ ] Historia de usuario
- [ ] Corrección
- [ ] Infraestructura, CI/CD o configuración
- [ ] Documentación

## Historia de usuario

HU-XX · (título) <!-- o "No aplica" -->

## Qué cambia

-

## Criterios de aceptación cubiertos

<!-- Solo si es una historia de usuario. -->

- [ ] c1:
- [ ] c2:

## Pruebas

- [ ] Cada criterio implementado tiene su prueba en `tests/hu/test_huXX_*.py` (código HTTP y mensaje).
- [ ] `pytest` pasa completo (unitarias, integración y aceptación) con cobertura de al menos 80 %.
- [ ] `ruff check .`, `mypy` y `lint-imports` pasan.
- [ ] Los mensajes al cliente salen de `app/business/domain/mensajes.py` (texto literal del backlog).

## Revisión de arquitectura

- [ ] Cada capa usa solo la de abajo (`api` → `business` → `infraestructure`) y `app/core`.
- [ ] Los servicios reciben interfaces (`app/infraestructure/interfaces`), no clases concretas.
- [ ] Si cambié un modelo ORM, agregué la migración (`alembic revision --autogenerate`) y `alembic check` no muestra diferencias.
- [ ] Si cambié el contrato de la API, lo acordé con las células que lo consumen.

## Despliegue

<!-- Al fusionar en main se despliega en la EC2 (cd.yml). -->

- [ ] Si agregué o cambié variables de entorno, actualicé `.env.example`, `docker-compose.yml` y `app/core/config.py`.
- [ ] La migración no borra ni altera datos existentes (o lo explico en las notas).

**Notas para el despliegue** (cambios en el `.env` de la EC2, bases que haya que recrear, pasos manuales):

- Ninguna.
