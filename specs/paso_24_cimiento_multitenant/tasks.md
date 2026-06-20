# paso_24 — Cimiento multi-tenant: instituciones + scope de usuarios

## Contexto y decisión (aprobada por David)

Primer ladrillo de multi-tenant, **alcance mínimo** (no tocar tablas académicas todavía):
- Entidad/tabla **`instituciones`** (lista + alta) — hoy hay solo `configuracion` (singleton).
- **`institucion_id`** en `usuarios` (FK), backfill de todos los usuarios existentes a la institución actual.
- **Scope** del listado de usuarios: el `director` ve solo los usuarios de SU institución; el `admin` (plataforma) ve todas y puede **filtrar por institución**. Activar el filtro real en `listar_para_ver_como`.

**Fuera de alcance:** `institucion_id` en config/años/grupos/tablas académicas (migración amplia, futura). Aislamiento total por tenant.

Requisito previo: `paso_23` cerrado (no hay conflicto de archivos: paso_23 toca RBAC/recuperación; paso_24 toca el modelo de usuario y schema).

## Tareas

### T1 — Entidad y persistencia de instituciones
- Modelo de dominio `Institucion` (`src/domain/models/`) + DTOs (`NuevaInstitucionDTO`, `InstitucionResumenDTO`), Pydantic v2, validadores.
- DDL `instituciones` en `schema.py` (id, nombre, nit/codigo opcional, activa, fecha_creacion) + índice. La fila inicial se crea desde el seed a partir de `configuracion.nombre_institucion` (institución #1).
- Port `IInstitucionRepository` + repo `SqliteInstitucionRepository` (listar, get, guardar, existe).
- `InstitucionService` (listar, crear, get_activa/por_defecto). Registrar en `container.py` + `diagnostico`.
- Tests de modelo y repo.

### T2 — institucion_id en usuarios (schema + migración + modelo)
- Añadir columna `institucion_id INTEGER REFERENCES instituciones(id)` a `usuarios`. Como `schema.py` usa `CREATE TABLE IF NOT EXISTS`, implementar **migración idempotente**: si la columna no existe (PRAGMA table_info), `ALTER TABLE usuarios ADD COLUMN institucion_id ...` y **backfill** de todos los usuarios a la institución #1. Integrarlo donde `init_db()` aplica el schema (sin romper BDs existentes de desarrollo).
- Actualizar el modelo `Usuario` + `NuevoUsuarioDTO`/`UsuarioResumenDTO` con `institucion_id` (opcional, default = institución por defecto). El repo de usuarios persiste/lee la columna.
- Seed: los usuarios creados se asignan a la institución #1.
- Tests: usuarios nuevos y existentes tienen `institucion_id`; backfill correcto.

### T3 — Scope de usuarios por institución
- `FiltroUsuariosDTO` gana `institucion_id: int | None`.
- `listar_resumenes` / `listar_filtrado` respetan el filtro de institución.
- En la vista `/admin/usuarios`:
  - `director`: el listado se **fuerza** a `ctx`-institución (no puede ver otras). (Hoy `SessionContext` no lleva institución; añadir `institucion_id` al contexto de sesión y poblarlo en el login a partir del usuario.)
  - `admin`: selector/filtro de **institución** (opciones desde `InstitucionService.listar`), "Todas" por defecto.
- Activar el filtro real en `usuario_service.listar_para_ver_como(institucion_id=...)` (ya existe el hook no-op) y conectar el doble filtrado del selector "Ver como" (nivel institución → usuarios de esa institución) con datos reales.

### T4 — Login/sesión: institución del usuario
- En el login, al autenticar, cargar `institucion_id` del usuario en `SessionContext` (`guardar`/`desde_storage`).
- Al impersonar ("Ver como"), el contexto toma la institución del usuario objetivo.

### T5 — (Opcional dentro del paso) Listado de instituciones para admin
- Sección/acción mínima para que el admin **liste** las instituciones (y dé de alta una) — puede ser un panel en el dashboard admin o una página `/admin/instituciones`. Si se añade página, registrar ruta en `main.py` (admin-only) y NAV item bajo Administración (rol admin), manteniendo la invariante de grupos raíz del NAV.

### T6 — Verificación y cierre
- `python init.py` VERDE (corregir fallout; los repos/fakes de tests que listan usuarios deben contemplar `institucion_id`). check_imports domain/infrastructure/services/interface y check_design en verde.
- Verificar a mano la migración: una BD de desarrollo preexistente (sin la columna) debe migrar sin perder datos al arrancar.
- `progress/impl_paso_24.md`.

## Estado de implementación

- [x] **T1** — Entidad/DTOs `Institucion`, port + repo SQLite, `InstitucionService`, DDL + índice, seed institución #1, tests modelo+repo.
- [x] **T2** — `usuarios.institucion_id` (CREATE + micro-migración idempotente + backfill en seed), modelo/DTOs `Usuario`, repo persiste/lee, seed asigna #1, tests.
- [x] **T3** — `FiltroUsuariosDTO.institucion_id`; repo lo respeta; página `/admin/usuarios` (director forzado a su institución, admin con filtro "Todas"); `listar_para_ver_como` filtra real.
- [x] **T4** — `SessionContext.institucion_id` (campo + guardar/desde_storage); login lo carga; impersonación toma la institución del objetivo y restaura la del admin al salir.
- [ ] **T5** — (opcional) página/panel de instituciones para admin. NO implementado (fuera del alcance mínimo).
- [x] **T6** — `python init.py` VERDE (1074 passed, 1 skipped); migración de BD preexistente verificada a mano y en test.

## criterio_done
Existe entidad `instituciones` con su servicio y la institución #1 sembrada; `usuarios` tiene `institucion_id` con migración idempotente + backfill; el director ve solo usuarios de su institución y el admin filtra por institución; el selector "Ver como" filtra por institución con datos reales; `SessionContext` lleva la institución; `python init.py` verde y una BD preexistente migra sin pérdida.
