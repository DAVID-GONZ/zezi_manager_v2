# Tasks: mejora_09a — Admin crea institución + director + seed

**Fase 1 de 3.** Prerrequisitos: mejora_06 ✓, mejora_07 ✓, mejora_08 ✓.

---

## T1 — Constantes compartidas

**Archivo nuevo:** `src/domain/catalogos_estandar.py`

Crear con `AREAS_ESTANDAR_CO`, `CATEGORIAS_BASE_CO`, `PREF_DEFAULTS` (ver design.md §1).
Módulo puro, sin imports de infraestructura. `__all__` con los 3 nombres.

**Archivo:** `src/infrastructure/db/seed.py`
- Importar las constantes desde `src.domain.catalogos_estandar`.
- Eliminar las declaraciones locales `_AREAS_ESTANDAR_CO`, `_CATEGORIAS_BASE_CO`, `_PREF_DEFAULTS`.
- Ajustar los cuerpos de `_seed_catalogos_institucion` y `_seed_preferencias_institucion`
  para usar los nombres importados (`AREAS_ESTANDAR_CO`, etc.).
- Verificar que no queden referencias colgantes a los nombres viejos.

---

## T2 — Schema

**Archivo:** `src/infrastructure/db/schema.py`

Añadir al `CREATE TABLE IF NOT EXISTS instituciones`, después de `calendario TEXT`:
```sql
        calendario             TEXT,
        configuracion_inicial_completa BOOLEAN NOT NULL DEFAULT 0
```
(Coma tras `calendario`.) Sin `_migrate_*`.

---

## T3 — Modelo de dominio

**Archivo:** `src/domain/models/institucion.py`
1. Añadir a `Institucion`: `configuracion_inicial_completa: bool = False` (junto a `activa`).
2. Crear `NuevaInstitucionConDirectorDTO` (ver design.md §3) con validación de `nombre`
   reutilizando el patrón existente; `director_usuario` y `director_nombre_completo`
   requeridos; resto opcional.
3. Crear `ResultadoAprovisionamientoDTO` (institucion, director_usuario, password_temporal).
   - `model_config = ConfigDict(arbitrary_types_allowed=False)` no necesario; `Institucion`
     es BaseModel, se anida sin problema.
4. Actualizar `__all__`.

---

## T4 — Repositorio: flag + siembra de tenant

**Archivo:** `src/domain/ports/institucion_repo.py`
- Añadir abstractmethod `sembrar_defaults_tenant(self, institucion_id: int) -> None`.

**Archivo:** `src/infrastructure/db/repositories/sqlite_institucion_repo.py`
- `_COLS` / `_row_to_institucion`: incluir `configuracion_inicial_completa`
  (int 0/1 → bool). Si el mapper usa dict-comprehension genérica, castear el bool.
- `guardar()` e `actualizar()`: incluir la columna en INSERT/UPDATE (bool → int).
- Implementar `sembrar_defaults_tenant()` reutilizando `_seed_catalogos_institucion` y
  `_seed_preferencias_institucion` de `seed.py` con la conexión del repo (ver design.md §4).
  Commit solo si la conexión no es inyectada (mismo patrón que los demás métodos del repo).

---

## T5 — Servicio de aprovisionamiento

**Archivo nuevo:** `src/services/aprovisionamiento_institucion_service.py`

Implementar `AprovisionamientoInstitucionService` con
`crear_institucion_con_director(dto, actor_rol=None)` (ver design.md §5):
1. Unicidad de nombre (`self._repo.existe_nombre`).
2. `self._repo.guardar(Institucion(..., configuracion_inicial_completa=False))`.
3. `self._repo.sembrar_defaults_tenant(inst.id)`.
4. `Container.usuario_service().crear_usuario(NuevoUsuarioDTO(rol=Rol.DIRECTOR, institucion_id=inst.id, ...), actor_rol=actor_rol)`.
5. Retornar `ResultadoAprovisionamientoDTO`.

Decorar con `@requiere_escritura`. Import de `Container` local dentro del método.
No importar `src.db`. No instanciar repos.

**Archivo:** `container.py`
- Añadir `aprovisionamiento_service()` reutilizando `cls.institucion_service()._repo`
  (ver design.md §5).

---

## T6 — Seed: marcar institución #1 configurada

**Archivo:** `src/infrastructure/db/seed.py`

En `_seed_institucion()`, después de sembrar catálogos/preferencias de #1 y antes del
`return institucion_id`, añadir:
```python
conn.execute(
    "UPDATE instituciones SET configuracion_inicial_completa = 1 WHERE id = ?",
    (institucion_id,),
)
```

---

## T7 — UI: página catálogo de instituciones

**Archivo nuevo:** `src/interface/pages/admin/catalogo_instituciones.py`
**Ruta lógica:** `/admin/instituciones` (registro en main.py, T8).

Seguir el patrón de `configuracion_institucion.py` / otras páginas admin:
- `catalogo_instituciones_page()` que lee `SessionContext.desde_storage()`.
- `app_layout(ctx, contenido, page_titulo="Instituciones", page_icono="apartment", ...)`.
- Lista `Container.institucion_service().listar()` (o un listado que incluya el flag —
  si `listar()` devuelve solo resumen, usar `get()` por id o ampliar; preferible mostrar
  el badge leyendo la entidad completa vía un listado de entidades. Si hace falta, añadir
  al servicio un `listar_entidades()` que devuelva `list[Institucion]` — decisión del
  implementer, documentar en el progreso).
- Badge de estado por institución (Configurada / Pendiente).
- Botón "Crear institución" → `form_dialog` con campos de institución + director.
- Submit → `Container.aprovisionamiento_service().crear_institucion_con_director(dto, actor_rol=ctx.usuario_rol)`.
  - Éxito: diálogo que muestra usuario + password temporal (una sola vez, botón copiar),
    `toast_success`, refresca la lista.
  - `ValueError`: `toast_warning`.
- Usar componentes existentes: `btn_primary`, `btn_ghost`, `form_dialog`/`custom_dialog`,
  `toast_*`, `empty_state` si no hay instituciones (no aplica: siempre existe #1).
- Colores del tema (sin hex literales nuevos en la página; usar clases/tokens existentes).

---

## T8 — Navegación y ruta

**Archivo:** `src/interface/design/layout.py`
- Añadir ítem "Instituciones" en la sección admin de `NAV_ITEMS`
  (`"label": "Instituciones", "icon": "apartment", "ruta": "/admin/instituciones", "rol": ["admin"]`).
  Ubicarlo junto a "Usuarios" / "Auditoría".

**Archivo:** `main.py`
- Importar `catalogo_instituciones_page` y registrar:
  `registrar_pagina("/admin/instituciones", catalogo_instituciones_page, roles=_ADMIN)`.

---

## T9 — Tests

**Archivo nuevo:** `tests/unit/services/test_aprovisionamiento_service.py`
Con `MagicMock` para el repo y monkeypatch de `Container.usuario_service` (ver design.md §9):
- `test_crear_institucion_con_director_ok`
- `test_flag_inicial_false`
- `test_siembra_defaults_llamada`
- `test_nombre_duplicado_rechazado`
- `test_director_en_tenant_correcto`

**Test de integración** (en `tests/integration/` siguiendo el patrón de los existentes):
- Crear institución vía repo real + `sembrar_defaults_tenant` sobre BD de test →
  verificar 12 áreas, 4 categorías, 8 preferencias para el nuevo `institucion_id`.

---

## Verificación

Tras cada tarea:
```
$env:PYTHONIOENCODING="utf-8"; python -m pytest tests/ -q --tb=short
```
≥ 1446 passed + nuevos, 0 failed.

Al finalizar, además:
```
$env:PYTHONIOENCODING="utf-8"; python init.py
```
Debe quedar verde (salvo el falso positivo pre-existente de `login.py:16` — no introducir nuevos).

Escribir `progress/impl_mejora_09a.md` con archivos, conteo de tests y desviaciones.

---

## Riesgos / notas para el implementer

- **Bool ↔ int en SQLite**: `configuracion_inicial_completa` se guarda como 0/1;
  el mapper debe castear a `bool` explícitamente (un `1` de SQLite ya es truthy, pero
  Pydantic con `bool` lo acepta; validar en test).
- **`listar()` devuelve `InstitucionResumenDTO`** (sin el flag). Para el badge se necesita
  la entidad; el implementer decide si usar un nuevo `listar_entidades()` o `get()` por id.
  Mantener el cambio mínimo y documentarlo.
- **`sembrar_defaults_tenant` importa de `seed.py`**: es infra→infra, permitido. No mover
  esa llamada a un servicio.
- **RBAC del director**: `crear_usuario(actor_rol="admin")` debe permitir crear rol
  director; verificar que `roles_asignables("admin")` incluye `director` (si no, es un
  hallazgo a reportar, no forzar).
