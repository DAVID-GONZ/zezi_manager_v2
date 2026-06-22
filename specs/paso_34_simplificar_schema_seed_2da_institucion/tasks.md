# paso_34 — Quitar migraciones del schema + sembrar 2ª institución de prueba

## Contexto y decisión (David)

El proyecto es pre-producción: **no hay BDs que migrar** (la de desarrollo se recrea borrando el `.db` y dejando que el seed la regenere). Por tanto todo el andamiaje de migración que añadieron los pasos 24/27/29/30/32/33 sobra: los `CREATE TABLE` de `schema.py` ya traen el schema correcto (`institucion_id` + uniques compuestos). Hay que **eliminar los `ALTER TABLE` y los rebuilds**, dejando el `CREATE TABLE` como única fuente de verdad. Y **sembrar una 2ª institución** en el seed de desarrollo para probar el aislamiento y la desambiguación de login.

Estado actual a limpiar en `src/infrastructure/db/schema.py`:
- 7 funciones `_migrar_*_por_institucion` (configuracion_anio, grupos, asignaturas, estudiantes, salas, plantillas_franja, usuarios) — usan `... _new` + `INSERT…SELECT` + `ALTER TABLE … RENAME`.
- Mecanismo de **micro-migraciones** en `init_db`: lista `(tabla, columna, ddl)` + bucle con `ALTER TABLE … ADD COLUMN`, y el helper `_columna_existe`.
- Las llamadas a todo eso dentro de `init_db`.

## Tareas

### T1 — Verificación previa (load-bearing, NO destructiva)
- ANTES de borrar nada: confirmar que **cada columna/constraint** que hoy añade una migración (rebuild o micro-migración ADD COLUMN) **ya está presente en el `CREATE TABLE` correspondiente**. Lista a verificar (al menos): `institucion_id` en usuarios/configuracion_anio/grupos/asignaturas/estudiantes/salas/plantillas_franja; uniques compuestos `(institucion_id, …)`; y las columnas de micro-migraciones (sala_id, carga_horaria_max, horas_extra, columnas de escala, etc.).
- Si alguna columna existe SOLO vía migración y NO está en el `CREATE TABLE`, **añadirla al `CREATE TABLE`** antes de borrar la migración (para que una BD fresca quede completa). Documentar el cross-check.

### T2 — Eliminar el andamiaje de migración de schema.py
- Borrar las 7 funciones `_migrar_*_por_institucion`, el mecanismo de micro-migraciones (lista + bucle `ALTER TABLE ADD COLUMN`) y `_columna_existe` (si solo lo usaban las migraciones).
- `init_db` queda reducido a: crear tablas (DDL), índices y triggers. SIN ningún `ALTER TABLE`.
- Verificar que **no queda ningún `ALTER TABLE` en `schema.py`**.
- Eliminar/ajustar los tests que probaban las migraciones de BD preexistente (p.ej. `TestMigracion*`, `test_migra_sin_perder_datos`, los `TestMigracionPreexistente`): ya no aplican; quitarlos o reconvertirlos a tests de que el `CREATE TABLE` fresco trae el schema correcto (columnas + uniques compuestos).

### T3 — Sembrar 2ª institución en seed_dev (casos de uso)
- En `seed_dev` (NO en `seed_base`, que queda mínimo/1 institución), crear una **2ª institución** ("Institución de Prueba" o similar) con datos mínimos pero suficientes para ejercitar el multi-tenant:
  - Su propio `director` (usar **el mismo username** que un director de la institución #1, p.ej. `director`, para probar la **desambiguación de login** ambiguo) + su contraseña conocida.
  - Su propio `configuracion_anio` activo (año académico).
  - Al menos un `grupo` **reutilizando un `codigo`** de la institución #1 (p.ej. `601`) y un `estudiante` **reutilizando un `numero_documento`** de la #1 — para demostrar que la unicidad compuesta lo permite.
  - Una asignatura propia.
- El objetivo es poder, a mano en la app: loguearse como director de cada institución y ver que **cada uno solo ve lo suyo**; y comprobar que el login con `director` pide elegir institución.
- Mantener `seed_dev` idempotente/coherente con su patrón actual (no romper el resto del dataset de desarrollo).

### T4 — Verificación
- `python init.py` VERDE (corregir todo el fallout de los tests de migración eliminados; baseline 1148 passed, 1 skipped — el número bajará por los tests de migración retirados y/o subirá por tests nuevos del seed). check_imports + check_design en verde.
- Arrancar una BD **fresca** (borrar el `.db` de test/dev y dejar que `init_db`+seed la creen) y confirmar: schema correcto sin ALTER, la 2ª institución sembrada, uniques compuestos funcionando (mismo codigo/documento/username en dos instituciones conviven).
- Tests nuevos: el seed_dev crea 2 instituciones; un director de la #2 no ve datos de la #1 (aislamiento vía `institucion_actual()`); el username compartido es ambiguo en login.
- `progress/impl_paso_34.md` (cross-check de columnas, qué se eliminó, qué se sembró, output de init.py).

## criterio_done
`schema.py` no contiene ningún `ALTER TABLE` ni funciones de migración/rebuild; los `CREATE TABLE` son la única fuente de verdad y una BD fresca queda completa y correcta; `seed_dev` siembra una 2ª institución con username/codigo/documento compartidos para probar aislamiento y login ambiguo; tests de migración obsoletos retirados; `python init.py` verde.
