# chip_03 — Migrar 6 páginas de convivencia a selectores inline

> Referencia: `specs/chip_inline_00_roadmap/chip_03_convivencia.md`
> Componente disponible: `src/interface/design/components/inline_selectors.py`
> Patrón de referencia ya aplicado: `planilla_notas.py` y `registro_asistencia.py`

## Archivos a modificar (solo estos 6)

```
src/interface/pages/convivencia/observaciones.py
src/interface/pages/convivencia/comportamiento.py
src/interface/pages/convivencia/seguimiento.py
src/interface/pages/convivencia/notas_convivencia.py
src/interface/pages/convivencia/reporte_periodo.py
src/interface/pages/academico/tablero_estadisticos.py
```

## Patrón estándar (repetir en cada archivo)

```python
# 1. Import (a nivel módulo, junto a los demás imports)
from src.interface.design.components.inline_selectors import inline_periodo_grupo_asignatura
# o inline_periodo_grupo para notas_convivencia

# 2. Añadir claves sel_* al dict _s si no existen ya
"sel_periodo_id":        None,
"sel_periodo_nombre":    "",
"sel_grupo_id":          None,
"sel_grupo_nombre":      "",
"sel_asignacion_id":     None,   # solo para inline_periodo_grupo_asignatura
"sel_asignacion_nombre": "",     # solo para inline_periodo_grupo_asignatura

# 3. Al inicio de contenido(), antes de cualquier otro elemento:
def on_sel_change(s: dict) -> None:
    # copiar sel_* a los alias internos de la página
    ...
    vista.refresh()

inline_periodo_grupo_asignatura(_s, on_sel_change,
    usuario_id=ctx.usuario_id,
    institucion_id=ctx.institucion_id,
    usuario_rol=ctx.usuario_rol,
    preselect_periodo=True,
)

# 4. Eliminar on_context_change y su kwarg en app_layout
# 5. Eliminar bleeding ctx.grupo_id / ctx.periodo_id / ctx.asignacion_id → _s
# 6. Eliminar patrón ctx_actual = SessionContext.desde_storage() or ctx
#    (reemplazar por ctx directamente donde solo se usa para usuario_id/rol)
```

---

## T1 — observaciones.py

**Estado actual**: ya tiene `"sel_periodo_id": None` en `_s` (línea ~55). El chip seteaba
`sel_periodo_id` desde `ctx.periodo_id`. Ahora el inline selector maneja el periodo.
El grupo venía del chip via `ctx.grupo_id` (líneas ~64-65).

**Código muerto a eliminar:**
- `_cargar_estado(ctx, _s)` líneas ~64-65: `if ctx.grupo_id: _s["estudiantes"] = ...`
  — esta carga de estudiantes debe moverse a `on_sel_change` (se llama cuando grupo cambia)
- `_cargar_estado` líneas ~89-90: `if ctx.periodo_id and _s["sel_periodo_id"] is None:` — bleeding
- `def on_context_change()` completa (línea ~272) con su body
- Todas las apariciones de `ctx_actual = SessionContext.desde_storage() or ctx`
  donde `ctx_actual` se usa para `usuario_id`/`usuario_rol`: reemplazar por `ctx`
- `on_context_change=on_context_change` en `app_layout(...)`

**Claves internas de observaciones**: usa `sel_periodo_id` (ya existente). Añadir:
```python
"sel_grupo_id":          None,
"sel_grupo_nombre":      "",
"sel_asignacion_id":     None,
"sel_asignacion_nombre": "",
```

**on_sel_change**:
```python
def on_sel_change(s: dict) -> None:
    _s["sel_periodo_id"]  = s["sel_periodo_id"]
    _s["sel_grupo_id"]    = s["sel_grupo_id"]
    _s["sel_asignacion_id"] = s["sel_asignacion_id"]
    if s["sel_grupo_id"]:
        _s["estudiantes"] = Container.estudiante_service().listar_por_grupo(s["sel_grupo_id"])
    else:
        _s["estudiantes"] = []
    lista_observaciones.refresh()   # verificar el nombre real del refreshable
```

**Verificar que `_cargar_observaciones` lee de `_s["sel_periodo_id"]`** — ya lo hace
(línea ~99: `periodo_id = _s["sel_periodo_id"]`). Añadir también lectura de
`_s.get("sel_grupo_id")` y `_s.get("sel_asignacion_id")` si el servicio los consume.

---

## T2 — comportamiento.py

**Estado actual**: usa `filtro_grupo_id` y `filtro_periodo_id` como claves internas
(no `grupo_id`/`periodo_id`). El chip era la única fuente de esos valores al inicio.

**Código muerto a eliminar:**
- `_cargar_estado` líneas ~131-134: bleeding de `ctx.grupo_id` → `filtro_grupo_id`
  y `ctx.periodo_id` → `filtro_periodo_id`
- Líneas ~235-236: `if es_profesor and ctx.grupo_id: _s["filtro_grupo_id"] = ctx.grupo_id`
  — doble bleeding
- `def on_context_change()` (línea ~241) con body completo (~líneas 242-245)
- `nuevo_ctx = SessionContext.desde_storage()` dentro de on_context_change
- `ctx_actual = SessionContext.desde_storage() or ctx` (líneas ~278, ~453)
  — reemplazar usos por `ctx` directamente
- `on_context_change=on_context_change` en `app_layout(...)`
- `mostrar_asignatura=False` en `app_layout(...)` — eliminar (chip desaparece)

**Claves sel_* a añadir en `_s`:**
```python
"sel_periodo_id":        None,
"sel_periodo_nombre":    "",
"sel_grupo_id":          None,
"sel_grupo_nombre":      "",
"sel_asignacion_id":     None,
"sel_asignacion_nombre": "",
```

**on_sel_change** (mapea sel_* → filtro_*):
```python
def on_sel_change(s: dict) -> None:
    _s["filtro_grupo_id"]    = s["sel_grupo_id"]
    _s["filtro_periodo_id"]  = s["sel_periodo_id"]
    # asignacion: verificar si el servicio de comportamiento la consume
    # Si no hay método con asignacion_id, guardar para uso futuro:
    _s["sel_asignacion_id"]  = s["sel_asignacion_id"]
    lista_comportamiento.refresh()  # verificar nombre real del refreshable
```

**Nota**: el servicio de comportamiento actualmente filtra por `grupo_id` y `periodo_id`.
Si no tiene filtro por `asignacion_id`, el pill de asignatura igual se muestra pero
el filtro real es por grupo. No cambiar la firma del servicio — eso es scope de otra épica.

---

## T3 — seguimiento.py

**Estado actual**: ya tiene `"sel_periodo_id": None` en `_s` (línea ~66) y tiene su
propio selector de periodo inline que escribe en `sel_periodo_id` (línea ~201).
El grupo venía del chip (`ctx.grupo_id` líneas ~75-76). Tiene `mostrar_asignatura=False`
y `mostrar_contexto=True` → ambos se eliminan.

**Código muerto a eliminar:**
- `_cargar_estado` líneas ~75-76: `if ctx.grupo_id: _s["estudiantes"] = ...` — bleeding
- `_cargar_estado` líneas ~100-101: auto-selección del primer periodo desde `_s["periodos"]`
  (ya no carga lista de periodos aquí, lo hace el inline selector)
- El mecanismo interno actual de selector de periodo (un ui.select o similar que
  escribe en `sel_periodo_id` con el handler `on_periodo_cambio`): REEMPLAZAR por
  el pill inline. Verificar qué líneas lo implementan y eliminarlas.
- `def on_context_change()` (línea ~188) con su body
- `ctx_actual = SessionContext.desde_storage() or ctx` (líneas ~206, ~230, ~338)
  — reemplazar por `ctx`
- `on_context_change=on_context_change` en `app_layout(...)`
- `mostrar_contexto=True` y `mostrar_asignatura=False` en `app_layout(...)` — eliminar ambos

**Claves a añadir** (sel_periodo_id ya existe, añadir las demás):
```python
"sel_grupo_id":          None,
"sel_grupo_nombre":      "",
"sel_asignacion_id":     None,
"sel_asignacion_nombre": "",
```

**on_sel_change**:
```python
def on_sel_change(s: dict) -> None:
    _s["sel_periodo_id"]    = s["sel_periodo_id"]
    _s["sel_grupo_id"]      = s["sel_grupo_id"]
    _s["sel_asignacion_id"] = s["sel_asignacion_id"]
    if s["sel_grupo_id"]:
        _s["estudiantes"] = Container.estudiante_service().listar_por_grupo(s["sel_grupo_id"])
    else:
        _s["estudiantes"] = []
    vista_seguimiento.refresh()  # verificar nombre real
```

---

## T4 — notas_convivencia.py

**Selector**: `inline_periodo_grupo` (2 dimensiones — sin asignatura).

**Código muerto a eliminar:**
- Líneas ~86-89: bleeding `ctx.grupo_id` → `_s["grupo_id"]` y `ctx.periodo_id` → `_s["periodo_id"]`
- `def on_context_change()` (línea ~291) con body completo
- `ctx_actual = SessionContext.desde_storage() or ctx` (línea ~309 y demás)
  — reemplazar por `ctx`
- `on_context_change=on_context_change` en `app_layout(...)` (línea ~455)
- `mostrar_asignatura=False` en `app_layout(...)` (línea ~456) — eliminar

**Claves sel_* a añadir en `_s`:**
```python
"sel_periodo_id":     None,
"sel_periodo_nombre": "",
"sel_grupo_id":       None,
"sel_grupo_nombre":   "",
```

**on_sel_change** (mapea a las claves internas `grupo_id` y `periodo_id`):
```python
def on_sel_change(s: dict) -> None:
    _s["grupo_id"]   = s["sel_grupo_id"]
    _s["periodo_id"] = s["sel_periodo_id"]
    tabla_notas.refresh()   # verificar nombre real
```

**Inline selector** (2D, sin usuario_id ni usuario_rol):
```python
from src.interface.design.components.inline_selectors import inline_periodo_grupo

inline_periodo_grupo(
    _s, on_sel_change,
    institucion_id=ctx.institucion_id,
    preselect_periodo=True,
)
```

**`ctx_actual`**: las referencias a `ctx_actual.usuario_id` y `ctx_actual.usuario_rol`
(líneas ~311, ~384, ~393) — reemplazar por `ctx.usuario_id` y `ctx.usuario_rol`.

---

## T5 — reporte_periodo.py

**Selector**: `inline_periodo_grupo_asignatura` (3 dimensiones).

**Código muerto a eliminar — dos funciones completas:**
- `def _cargar_grupos(ctx, _s)` (línea ~85) — función entera, el inline selector hace esto
- `def _cargar_periodos(ctx, _s)` (línea ~106) — función entera, ídem
- Líneas ~204-205: `_s["grupo_id"] = ctx.grupo_id` y `_s["periodo_id"] = ctx.periodo_id`
- `ctx_actual = SessionContext.desde_storage() or ctx` (línea ~222)
  — reemplazar `ctx_actual` por `ctx`
- `mostrar_asignatura=False` en `app_layout(...)` (línea ~301) — eliminar

**Verificar también**: si hay llamadas a `_cargar_grupos(ctx, _s)` o `_cargar_periodos(ctx, _s)`
en el cuerpo de la página → eliminar esas llamadas también.

**Claves sel_* a añadir:**
```python
"sel_periodo_id":        None,
"sel_periodo_nombre":    "",
"sel_grupo_id":          None,
"sel_grupo_nombre":      "",
"sel_asignacion_id":     None,
"sel_asignacion_nombre": "",
```

**on_sel_change**:
```python
def on_sel_change(s: dict) -> None:
    _s["grupo_id"]       = s["sel_grupo_id"]
    _s["periodo_id"]     = s["sel_periodo_id"]
    _s["asignacion_id"]  = s["sel_asignacion_id"]   # si la página usa asignacion
    vista_reporte.refresh()   # verificar nombre real
```

Si `_s` no tenía `asignacion_id` antes, añadirlo inicializado en None.

---

## T6 — tablero_estadisticos.py (el más complejo)

**Estructura**: tiene CONTEXTO PRINCIPAL (`periodo_id`, `grupo_id`, `asignacion_id`, `anio_id`)
y DRILL-DOWN INTERNO (`drill_grupo_id`, `drill_asig_id`).
- El inline selector alimenta el CONTEXTO PRINCIPAL.
- El drill-down tiene sus propios selectores UI internos (ui.select) — NO tocarlos.

**Código muerto a eliminar:**
- Líneas ~926-929: bleeding de las 4 claves desde ctx:
  `ctx.periodo_id`, `ctx.anio_id`, `ctx.grupo_id`, `ctx.asignacion_id` → `_s[*]`
  — inicializar en None en su lugar
- Líneas ~937-938: `"drill_grupo_id": ctx.grupo_id` y `"drill_asig_id": ctx.asignacion_id`
  — inicializar en None
- `def on_context_change()` (línea ~1119) con body completo (líneas ~1120-1130+)
- `ctx_actual = SessionContext.desde_storage()` (línea ~1070) y las referencias
  a `ctx_actual.asignacion_id`, `ctx_actual.periodo_id`, `ctx_actual.grupo_id`,
  `ctx_actual.anio_id` (líneas ~1083-1086) → reemplazar por `_s["asignacion_id"]`,
  `_s["periodo_id"]`, `_s["grupo_id"]`, `_s["anio_id"]`
- La condición `if not ctx_actual or not ctx_actual.contexto_completo` (línea ~1071)
  → reemplazar por `if not _s.get("periodo_id") or not _s.get("grupo_id")`
- `on_context_change = on_context_change` en `app_layout(...)` (línea ~1169)

**Claves sel_* a añadir:**
```python
"sel_periodo_id":        None,
"sel_periodo_nombre":    "",
"sel_grupo_id":          None,
"sel_grupo_nombre":      "",
"sel_asignacion_id":     None,
"sel_asignacion_nombre": "",
```

**on_sel_change** (mapea sel_* → claves internas del tablero):
```python
def on_sel_change(s: dict) -> None:
    _s["periodo_id"]    = s["sel_periodo_id"]
    _s["grupo_id"]      = s["sel_grupo_id"]
    _s["asignacion_id"] = s["sel_asignacion_id"]
    # anio_id: el inline selector no lo provee directamente.
    # Obtenerlo desde el periodo seleccionado si es necesario, o dejar None.
    # Verificar si _s["anio_id"] se usa en la lógica de la página.
    _s["drill_grupo_id"] = None   # reset drill al cambiar contexto
    _s["drill_asig_id"]  = None
    tablero.refresh()   # verificar nombre real del refreshable principal
```

**Nota sobre `anio_id`**: verificar en el código si `_s["anio_id"]` se pasa a servicios.
Si sí, obtenerlo desde la configuración activa igual que hace `_preseleccionar_periodo`
en el componente. Si solo se usaba para rellenar el inline selector legacy, se puede
eliminar esa clave de `_s`.

---

## T7 — Verificación final

```
python -X utf8 init.py
python -X utf8 scripts/check_imports.py --layer interface
python -X utf8 scripts/check_design.py --file src/interface/pages/convivencia/observaciones.py
python -X utf8 scripts/check_design.py --file src/interface/pages/convivencia/comportamiento.py
python -X utf8 scripts/check_design.py --file src/interface/pages/convivencia/seguimiento.py
python -X utf8 scripts/check_design.py --file src/interface/pages/convivencia/notas_convivencia.py
python -X utf8 scripts/check_design.py --file src/interface/pages/convivencia/reporte_periodo.py
python -X utf8 scripts/check_design.py --file src/interface/pages/academico/tablero_estadisticos.py
```

**Grep de validación — debe retornar 0 líneas en todos los archivos:**
```
grep -n "on_context_change" src/interface/pages/convivencia/observaciones.py src/interface/pages/convivencia/comportamiento.py src/interface/pages/convivencia/seguimiento.py src/interface/pages/convivencia/notas_convivencia.py src/interface/pages/convivencia/reporte_periodo.py src/interface/pages/academico/tablero_estadisticos.py

grep -n "mostrar_asignatura\|mostrar_contexto" src/interface/pages/convivencia/comportamiento.py src/interface/pages/convivencia/seguimiento.py src/interface/pages/convivencia/notas_convivencia.py src/interface/pages/convivencia/reporte_periodo.py

grep -n "_cargar_grupos\|_cargar_periodos" src/interface/pages/convivencia/reporte_periodo.py
```

## Restricciones

- ❌ No tocar archivos fuera de estos 6
- ❌ No cambiar firmas de servicios de dominio
- ❌ No agregar `mostrar_asignatura` o `mostrar_contexto` a ningún `app_layout` (esos params aún existen en layout.py pero ya no se usan — chip_04 los eliminará)
- ✅ `ctx = SessionContext.desde_storage()` permanece en cada página (necesario para usuario_id, rol, institucion_id)
- ✅ El patrón `ctx_actual = SessionContext.desde_storage() or ctx` desaparece; sus usos de usuario_id/rol se reemplazan por `ctx` directamente
- ✅ init.py completamente verde al final
