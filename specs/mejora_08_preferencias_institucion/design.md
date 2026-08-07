# Design: mejora_08 — Preferencias de institución

> **Revisión 2 — 2026-08-07**  
> Principios: sin migraciones (dev → schema + seed directo), diseño heredado configurable,
> logs de auditoría funcionales para lectura admin.

---

## 0. Correcciones de auditoría previas (bloqueante para admin)

Dos defectos introducidos en mejora_07-T7 que impiden que el módulo admin lea los
logs correctamente:

### Bug 1 — `registrar_cambios_masivos()` no escribe `institucion_id`

`sqlite_auditoria_repo.py` línea ~257: el `executemany` del batch INSERT omite la
columna `institucion_id`. Los registros masivos quedan sin institución.

**Fix:** añadir `institucion_id` a la tupla y al SQL del INSERT masivo.
`institucion_id` se obtiene de cada `r.institucion_id`.

### Bug 2 — `FiltroAuditoriaDTO` no filtra por institución

El admin necesita listar eventos/cambios de su tenant. Sin filtro `institucion_id` en
el DTO y en las queries, el admin ve todos los logs del sistema.

**Fix en `auditoria.py`:**
```python
class FiltroAuditoriaDTO(BaseModel):
    ...
    institucion_id: int | None = None  # ← añadir
```

**Fix en `sqlite_auditoria_repo.py`** — `listar_eventos()` y `listar_cambios()`:
```python
if filtro.institucion_id is not None:
    sql += " AND institucion_id = ?"
    params.append(filtro.institucion_id)
```

---

## 1. Tabla `preferencias_institucion`

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

Índice: `idx_pref_inst ON preferencias_institucion(institucion_id)`.

Sin función `_migrate_*`. La tabla se crea desde cero en schema.py; el seed la puebla.
Para dev: borrar la BD y relanzar `python init.py`.

---

## 2. Catálogo predeterminado (heredado, editable)

Los colores heredan el design system Aula Serena como valores reales (no null):

| categoría    | clave                          | valor_default | tipo  |
|---|---|---|---|
| academicas   | nota_minima_aprobacion_default | 60.0          | float |
| academicas   | nota_minima_escala_default     | 0.0           | float |
| academicas   | nota_maxima_escala_default     | 100.0         | float |
| academicas   | numero_periodos_default        | 4             | int   |
| convivencia  | modulo_convivencia_activo      | true          | bool  |
| convivencia  | modulo_alertas_activo          | true          | bool  |
| apariencia   | color_primario                 | #2E3192       | str   |
| apariencia   | color_secundario               | #8B90F0       | str   |

Seed: `INSERT OR IGNORE` por clave → si ya existe no sobreescribe (editable en runtime).

---

## 3. Modelo de dominio

```python
# src/domain/models/preferencia_institucion.py

class CategoriaPreferencia(str, Enum):
    ACADEMICAS   = "academicas"
    CONVIVENCIA  = "convivencia"
    APARIENCIA   = "apariencia"

class TipoValor(str, Enum):
    STR   = "str"
    INT   = "int"
    FLOAT = "float"
    BOOL  = "bool"
    JSON  = "json"

class PreferenciaInstitucion(BaseModel):
    id:             int | None = None
    institucion_id: int
    categoria:      CategoriaPreferencia
    clave:          str
    valor:          str | None = None
    tipo_valor:     TipoValor  = TipoValor.STR

    def valor_tipado(self) -> bool | int | float | str | dict | None:
        if self.valor is None:
            return None
        match self.tipo_valor:
            case TipoValor.BOOL:  return self.valor.lower() in ("true","1","yes")
            case TipoValor.INT:   return int(self.valor)
            case TipoValor.FLOAT: return float(self.valor)
            case TipoValor.JSON:  import json; return json.loads(self.valor)
            case _:               return self.valor

class PreferenciasDTO(BaseModel):
    """Vista plana de las preferencias de una institución."""
    nota_minima_aprobacion_default: float      = 60.0
    nota_minima_escala_default:     float      = 0.0
    nota_maxima_escala_default:     float      = 100.0
    numero_periodos_default:        int        = 4
    modulo_convivencia_activo:      bool       = True
    modulo_alertas_activo:          bool       = True
    color_primario:                 str | None = "#2E3192"
    color_secundario:               str | None = "#8B90F0"

class ActualizarPreferenciaDTO(BaseModel):
    clave: str
    valor: str | None
```

---

## 4. Puerto

```python
class IPreferenciasRepository(ABC):
    @abstractmethod
    def get(self, institucion_id: int, clave: str) -> PreferenciaInstitucion | None: ...

    @abstractmethod
    def get_all(self, institucion_id: int) -> list[PreferenciaInstitucion]: ...

    @abstractmethod
    def set(self, pref: PreferenciaInstitucion) -> PreferenciaInstitucion: ...
    # UPSERT — INSERT OR REPLACE

    @abstractmethod
    def seed_defaults(self, institucion_id: int, defaults: list[PreferenciaInstitucion]) -> None: ...
    # INSERT OR IGNORE por cada item
```

---

## 5. Servicio

```python
CLAVES_CONOCIDAS: frozenset[str] = frozenset({
    "nota_minima_aprobacion_default", "nota_minima_escala_default",
    "nota_maxima_escala_default", "numero_periodos_default",
    "modulo_convivencia_activo", "modulo_alertas_activo",
    "color_primario", "color_secundario",
})

class PreferenciasInstitucionService:
    def get_dto(self, institucion_id: int) -> PreferenciasDTO:
        """Lee todas las preferencias y construye el DTO. Usa defaults si faltan claves."""

    def get(self, institucion_id: int, clave: str) -> Any:
        """Valor tipado o None."""

    @requiere_escritura
    def set(self, institucion_id: int, dto: ActualizarPreferenciaDTO) -> PreferenciaInstitucion:
        """UPSERT. Rechaza claves fuera de CLAVES_CONOCIDAS con ValueError."""

    def modulo_activo(self, institucion_id: int, nombre_modulo: str) -> bool:
        """True si el módulo está activo; fail-open (True) ante cualquier error."""
```

`modulo_activo` mapea: `"convivencia"` → `modulo_convivencia_activo`, `"alertas"` → `modulo_alertas_activo`.

---

## 6. Seed (directo, sin migración)

```python
_PREF_DEFAULTS = [
    ("academicas",  "nota_minima_aprobacion_default", "60.0",    "float"),
    ("academicas",  "nota_minima_escala_default",     "0.0",     "float"),
    ("academicas",  "nota_maxima_escala_default",     "100.0",   "float"),
    ("academicas",  "numero_periodos_default",        "4",       "int"),
    ("convivencia", "modulo_convivencia_activo",      "true",    "bool"),
    ("convivencia", "modulo_alertas_activo",          "true",    "bool"),
    ("apariencia",  "color_primario",                 "#2E3192", "str"),
    ("apariencia",  "color_secundario",               "#8B90F0", "str"),
]

def _seed_preferencias_institucion(conn: sqlite3.Connection, institucion_id: int) -> None:
    for categoria, clave, valor, tipo in _PREF_DEFAULTS:
        conn.execute(
            "INSERT OR IGNORE INTO preferencias_institucion"
            "(institucion_id, categoria, clave, valor, tipo_valor) VALUES (?,?,?,?,?)",
            (institucion_id, categoria, clave, valor, tipo),
        )
```

Posición en `_seed_institucion()` — al final, después de `_seed_catalogos_institucion`:
```python
_seed_catalogos_institucion(conn, institucion_id)    # mejora_07
_seed_preferencias_institucion(conn, institucion_id) # mejora_08
return institucion_id
```

---

## 7. `crear_anio()` — best-effort desde preferencias

```python
# Lee número de periodos desde preferencias (en vez del hardcoded 4)
_num_periodos = 4
try:
    from container import Container
    _num_periodos = int(
        Container.preferencias_service().get(institucion_id, "numero_periodos_default") or 4
    )
except Exception:
    pass
self._repo.guardar_numero_periodos(config.id, _num_periodos, pesos_iguales=True)

# Aplica defaults académicos (nota_minima, escala) desde preferencias
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

## 8. `layout.py` — toggles de módulo

Añadir `"requiere_modulo": "convivencia"` al ítem de primer nivel de Convivencia.

Función helper `_modulo_visible(item: dict) -> bool` — fail-open.

En el loop de render: `if not _modulo_visible(item): continue`.

---

## 9. `route_guard.py` — bloqueo por módulo inactivo

Diccionario `RUTAS_POR_MODULO` con las rutas `/convivencia/*`.

Función `_modulo_permitido(ruta: str) -> bool` — fail-open.

En el wrapper de `registrar_pagina`, después del check de rol: redirigir a `/inicio` si `not _modulo_permitido(ruta)`.

---

## Notas de compatibilidad

- **Sin migraciones**: en desarrollo, borrar `data/*.db` y relanzar. Schema + seed crean todo desde cero.
- **Colores reales como defaults**: la UI en mejora_09 puede leer `get_dto().color_primario` directamente; si la institución no ha editado nada, ya tiene los colores del design system.
- **Fail-open en toggles**: si el servicio de preferencias falla (BD corrupta, error de arranque), la UI muestra todo y el guard deja pasar — el sistema es navegable aunque las preferencias fallen.
- **Audit scope**: con el fix del `FiltroAuditoriaDTO`, el admin module puede llamar `listar_eventos(FiltroAuditoriaDTO(institucion_id=...))` y recibir solo los logs de su tenant.
