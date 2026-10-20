## Historia de usuario

HU-XX · (título)

## Qué cambia

-

## Criterios de aceptación cubiertos

- [ ] cX:
- [ ] cY:

## Pruebas

- [ ] Quité el `skip` de las pruebas de `tests/hu/` de los criterios implementados y pasan.
- [ ] `pytest` pasa completo (unitarias e integración).
- [ ] Los mensajes al cliente salen de `app/business/domain/mensajes.py` (texto literal del backlog).

## Revisión de arquitectura

- [ ] Cada capa usa solo la de abajo (presentation → business → data_access) y `app/core`.
- [ ] Los servicios reciben interfaces (`app/data_access/interfaces`), no clases concretas.
- [ ] Si cambié un modelo ORM, agregué la migración (`alembic revision --autogenerate`) y `alembic check` no muestra diferencias.
- [ ] Si cambié el contrato de la API, lo acordé con las células que lo consumen.
