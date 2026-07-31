# Requisitos: Verificación multi-tenant en Postgres + ORM (seguridad_web_07)

> **Nivel:** N0 — Bloqueante de deploy
> **Dificultad:** Código-Bajo (verificación + tests; la lógica ya existe)
> **Depende de:** backend_00 Fase 1 (SQLAlchemy + Postgres disponible)
> **Relacionado con:** S05 (throttle en Postgres)

## Contexto del problema

El scope multi-tenant existe y funciona en SQLite: `src/services/contexto_tenant.py`
inyecta el `institucion_id` y `verificar_pertenencia` protege las operaciones por ID.
Al migrar a SQLAlchemy + Postgres surgen riesgos nuevos:

1. El ORM puede omitir el filtro de tenant si un query se construye sin el scope.
2. Las migraciones de schema pueden introducir tablas sin columna `institucion_id`.
3. Los tests en-memoria con `FakeRepository` no prueban el filtro real en SQL.

Una brecha en el aislamiento de tenants es el peor fallo posible en una app
multi-institución: datos de una escuela visibles para otra.

## Requisitos

R1: CADA TABLA que contenga datos específicos de una institución DEBE tener una
    columna `institucion_id` con clave foránea a la tabla de instituciones. La ausencia
    de esta columna en una tabla de datos de negocio es un bug de schema.

R2: EL SISTEMA DEBE tener un test de integración por cada repositorio que acceda a
    datos multi-tenant, verificando que un query ejecutado con `institucion_id=A`
    no devuelve ningún registro de `institucion_id=B`, incluso si el ID del objeto
    solicitado existe en B.

R3: EL SISTEMA DEBE verificar que `verificar_pertenencia` se llama antes de toda
    operación mutadora (update, delete) sobre entidades con scope de tenant. Esta
    verificación DEBE hacerse a nivel de servicio, no solo a nivel de repositorio.

R4: EL ORM (SQLAlchemy) DEBE aplicar el filtro de `institucion_id` en el repositorio,
    no en el servicio. El servicio pasa el `institucion_id` como parámetro; el repo
    lo aplica en el WHERE. Esto previene que una llamada al repo sin pasar el tenant
    devuelva todos los registros.

R5: EL USUARIO DE POSTGRES con el que corre la app DEBE tener permisos solo sobre
    las tablas de la app. No debe poder acceder a tablas de sistema ni a otras bases
    de datos en el mismo servidor Postgres.

R6: DEBE existir un test de regresión que simule el escenario de "tenant incorrecto":
    un usuario autenticado como institución A que intenta acceder a un recurso de
    institución B debe recibir un error de autorización, no el recurso.

R7: EL ADMIN tiene acceso cross-tenant por diseño (`admin → sin scope`). Este
    privilegio DEBE estar documentado y DEBE requerir autenticación de dos factores
    (o equivalente) en producción. *(2FA puede diferirse; la documentación no.)*

R8: LOS TESTS de repositorio que corren contra Postgres (post Fase 1 de backend_00)
    DEBEN incluir los casos multi-tenant (R2, R6) como parte del suite `pytest -m repo`.

## Criterio de done

- `pytest -m multitenant` verde en SQLite y Postgres.
- Ningún repositorio de datos de negocio tiene queries sin filtro de `institucion_id`
  (verificable con grep en los adaptadores SQLAlchemy).
- Test de "cruce de tenant" falla con error de autorización, no con datos del otro tenant.
