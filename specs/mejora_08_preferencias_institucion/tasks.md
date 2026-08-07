# Tasks: mejora_08 — Preferencias de institución (Rev. 2)

**Principios:** sin `_migrate_*`, schema directo, seed al final, diseño heredado.  
**Prerrequisito:** mejora_06 ✓, mejora_07 ✓

---

## T0 — Corrección audit log (bloqueante)

### T0a — `sqlite_auditoria_repo.py`: `registrar_cambios_masivos()`

Bug: el INSERT masivo no escribe `institucion_id`.

Cambiar el `executemany` para incluir la columna:
```python
conn.executemany(
    """
    INSERT INTO audit_log
        (usuario_id, accion, tabla, registro_id,
         valor_anterior, valor_nuevo, timestamp, hash_cadena,
         institucion_id)
    VALUES (?,?,?,?,?,?,?,?,?)
    """,
    params,
)
```

Y añadir `r.institucion_id` como último elemento de cada tupla en el loop:
```python
params.append((
    r.usuario_id, r.accion.value, r.tabla, r.registro_id,
    r.valor_anterior, r.valor_nuevo, r.timestamp.isoformat(),
    hash_cadena,
    r.institucion_id,   # ← añadir
))
```

### T0b — `src/domain/models/auditoria.py`: `FiltroAuditoriaDTO`

Añadir campo:
```python
institucion_id: int | None = None
```
(después de `hasta`; antes de `pagina`)

### T0c — `sqlite_auditoria_repo.py`: `listar_eventos()` y `listar_cambios()`

En ambos métodos, después de los filtros existentes y antes de `ORDER BY`, añadir:
```python
if filtro.institucion_id is not None:
    sql += " AND institucion_id = ?"
    params.append(filtro.institucion_id)
```

---

## T1 — Schema

**Archivo:** `src/infrastructure/db/schema.py`

Añadir a la lista `TABLAS` (después de `configuracion_grado_institucion`):

```sql
CREATE TABLE IF NOT EXISTS preferencias_institucion (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    institucion_id INTEGER NOT NULL REFERENCES instituciones(id) ON DELETE CASCADE,
    categoria      TEXT    NOT NULL,
    clave          TEXT    NOT NULL,
    valor          TEXT,
    tipo_valor     TEXT    NOT NULL DEFAULT 'str'
                   CHECK(tipo_valor IN ('str','int','float','bool','json')),
    UNIQUE(institucion_id, clave)
)
```

Añadir a `INDICES`:
```python
"CREATE INDEX IF NOT EXISTS idx_pref_inst ON preferencias_institucion(institucion_id)",
```

Sin función `_migrate_*`.

---

## T2 — Modelo de dominio

**Archivo nuevo:** `src/domain/models/preferencia_institucion.py`

Crear con:
- `CategoriaPreferencia(str, Enum)`: ACADEMICAS, CONVIVENCIA, APARIENCIA
- `TipoValor(str, Enum)`: STR, INT, FLOAT, BOOL, JSON
- `PreferenciaInstitucion(BaseModel)` con `valor_tipado()` (match/case sobre TipoValor)
- `PreferenciasDTO(BaseModel)` — 8 campos con defaults del catálogo
  - `color_primario: str | None = "#2E3192"` (Aula Serena light primary)
  - `color_secundario: str | None = "#8B90F0"` (Aula Serena dark primary)
- `ActualizarPreferenciaDTO(BaseModel)` — clave + valor
- `__all__` con todos los nombres

---

## T3 — Puerto abstracto

**Archivo nuevo:** `src/domain/ports/preferencias_repo.py`

`IPreferenciasRepository(ABC)` con:
- `get(institucion_id, clave) -> PreferenciaInstitucion | None`
- `get_all(institucion_id) -> list[PreferenciaInstitucion]`
- `set(pref: PreferenciaInstitucion) -> PreferenciaInstitucion`
- `seed_defaults(institucion_id, defaults: list[PreferenciaInstitucion]) -> None`

---

## T4 — Repositorio SQLite

**Archivo nuevo:** `src/infrastructure/db/repositories/sqlite_preferencias_repo.py`

`SqlitePreferenciasRepository(IPreferenciasRepository)`:
- `_row_to_pref(row) -> PreferenciaInstitucion`
- `get()` — `WHERE institucion_id=? AND clave=?`
- `get_all()` — `WHERE institucion_id=?`
- `set()` — `INSERT OR REPLACE INTO preferencias_institucion(...) VALUES(...)`
- `seed_defaults()` — loop de `INSERT OR IGNORE`

Mismo patrón de `_get_conn()` que los otros repos (context manager o conn inyectada).

---

## T5 — Servicio

**Archivo nuevo:** `src/services/preferencias_institucion_service.py`

```python
CLAVES_CONOCIDAS: frozenset[str] = frozenset({
    "nota_minima_aprobacion_default", "nota_minima_escala_default",
    "nota_maxima_escala_default", "numero_periodos_default",
    "modulo_convivencia_activo", "modulo_alertas_activo",
    "color_primario", "color_secundario",
})
```

Métodos:
- `get_dto(institucion_id) -> PreferenciasDTO` — construye el DTO; si falta una clave usa el default de `PreferenciasDTO`
- `get(institucion_id, clave) -> Any` — `valor_tipado()` o None
- `set(institucion_id, dto: ActualizarPreferenciaDTO) -> PreferenciaInstitucion` (`@requiere_escritura`; `ValueError` si clave desconocida)
- `modulo_activo(institucion_id, nombre_modulo) -> bool` — fail-open

---

## T6 — Container

**Archivo:** `container.py`

Añadir:
```python
@classmethod
def preferencias_service(cls):
    from src.infrastructure.db.repositories.sqlite_preferencias_repo import SqlitePreferenciasRepository
    from src.services.preferencias_institucion_service import PreferenciasInstitucionService
    return cls._get_or_create(
        "preferencias_service",
        lambda: PreferenciasInstitucionService(SqlitePreferenciasRepository(cls._db())),
    )
```

---

## T7 — Seed

**Archivo:** `src/infrastructure/db/seed.py`

Añadir constante `_PREF_DEFAULTS` y función `_seed_preferencias_institucion(conn, institucion_id)`.

En `_seed_institucion(conn)`, añadir la llamada después de `_seed_catalogos_institucion`:
```python
_seed_preferencias_institucion(conn, institucion_id)
return institucion_id
```

Sin función `_migrate_*`. Directo al INSERT.

---

## T8 — `configuracion_service.crear_anio()`

**Archivo:** `src/services/configuracion_service.py`

Reemplazar la línea:
```python
self._repo.guardar_numero_periodos(config.id, 4, pesos_iguales=True)
```
por:
```python
_num_periodos = 4
try:
    from container import Container
    _num_periodos = int(
        Container.preferencias_service().get(institucion_id, "numero_periodos_default") or 4
    )
except Exception:
    pass
self._repo.guardar_numero_periodos(config.id, _num_periodos, pesos_iguales=True)
```

Después de ese bloque (antes del auto-snapshot de mejora_06), añadir best-effort de escala:
```python
try:
    from container import Container
    prefs = Container.preferencias_service().get_dto(institucion_id)
    _upd: dict = {}
    if config.nota_minima_aprobacion is None:
        _upd["nota_minima_aprobacion"] = prefs.nota_minima_aprobacion_default
    if config.nota_minima_escala is None:
        _upd["nota_minima_escala"] = prefs.nota_minima_escala_default
    if config.nota_maxima_escala is None:
        _upd["nota_maxima_escala"] = prefs.nota_maxima_escala_default
    if _upd:
        config = self._repo.actualizar(config.model_copy(update=_upd))
except Exception:
    pass
```

---

## T9 — `layout.py` — toggles de módulo

**Archivo:** `src/interface/design/layout.py`

1. Añadir `"requiere_modulo": "convivencia"` al dict de primer nivel de Convivencia en `NAV_ITEMS`.

2. Añadir función helper (al nivel de módulo, cerca de `_usuario_puede_ver`):
```python
def _modulo_visible(item: dict) -> bool:
    modulo = item.get("requiere_modulo")
    if modulo is None:
        return True
    try:
        from container import Container
        from src.services.contexto_tenant import institucion_actual
        inst_id = institucion_actual()
        if inst_id is None:
            return True
        return Container.preferencias_service().modulo_activo(inst_id, modulo)
    except Exception:
        return True
```

3. En el loop `for idx, item in enumerate(NAV_ITEMS):` dentro de `app_layout()`:
```python
if not _modulo_visible(item):
    continue
```
como primera línea dentro del loop.

---

## T10 — `route_guard.py` — bloqueo de rutas por módulo

**Archivo:** `src/interface/auth/route_guard.py`

1. Añadir después de los sentinels:
```python
RUTAS_POR_MODULO: dict[str, list[str]] = {
    "convivencia": [
        "/convivencia/observaciones",
        "/convivencia/comportamiento",
        "/convivencia/notas",
        "/convivencia/categorias",
        "/convivencia/plantillas",
        "/convivencia/seguimiento",
    ],
    "alertas": [],
}
```

2. Añadir función:
```python
def _modulo_permitido(ruta: str) -> bool:
    try:
        from container import Container
        from src.services.contexto_tenant import institucion_actual
        inst_id = institucion_actual()
        if inst_id is None:
            return True
        for modulo, rutas in RUTAS_POR_MODULO.items():
            if ruta in rutas:
                return Container.preferencias_service().modulo_activo(inst_id, modulo)
    except Exception:
        pass
    return True
```

3. En el wrapper generado por `registrar_pagina`, después del check de rol y antes del render:
```python
if not _modulo_permitido(ruta):
    ui.navigate.to("/inicio")
    return
```

---

## Tests esperados

**Archivo nuevo:** `tests/unit/services/test_preferencias_service.py`

- `test_get_dto_defaults` — sin preferencias en BD → DTO con valores por defecto del catálogo
- `test_set_y_get_round_trip` — set + get tipado retorna el valor correcto
- `test_modulo_activo_sin_clave_es_true` — clave inexistente → True (fail-open)
- `test_modulo_inactivo_devuelve_false` — set `modulo_convivencia_activo=false` → False
- `test_clave_desconocida_rechazada` — ValueError al hacer set con clave no en CLAVES_CONOCIDAS
- `test_crear_anio_lee_num_periodos_desde_prefs` — preferencia en 3 → año creado con 3 periodos
- `test_audit_filtro_institucion` — listar_eventos con `institucion_id` filtra correctamente

---

## Orden de verificación

Después de cada tarea:
```
$env:PYTHONIOENCODING="utf-8"; python -m pytest tests/ -q --tb=short
```
≥ 1439 passed, 0 failed.

Al finalizar: `progress/impl_mejora_08.md` con archivos modificados y conteo de tests.
