# chip_02 — Migrar planilla_notas y registro_asistencia a selectores inline

> Referencia completa: `specs/chip_inline_00_roadmap/chip_02_notas_asistencia.md`
> Componente ya disponible: `src/interface/design/components/inline_selectors.py`

## Contexto crítico antes de empezar

El componente `inline_periodo_grupo_asignatura(s, on_change, usuario_id, institucion_id, usuario_rol, preselect_periodo=True)` ya existe. Los pills se renderizan en el contenido de la página, NO en el topbar.

El componente escribe en `s` estas claves: `sel_periodo_id`, `sel_periodo_nombre`, `sel_grupo_id`, `sel_grupo_nombre`, `sel_asignacion_id`, `sel_asignacion_nombre`.

El callback `on_change(s)` se llama solo cuando las 3 dimensiones tienen valor.

## Archivos a modificar

```
src/interface/pages/evaluacion/planilla_notas.py
src/interface/pages/academico/registro_asistencia.py
```

NO tocar ningún otro archivo.

---

## Tasks

### T1 — planilla_notas.py

Leer el archivo completo antes de tocar nada. Luego:

**Código muerto a eliminar (buscar la línea exacta antes de borrar):**
- Líneas del docstring del módulo que referencian `context_bar` o `context_selector`
- Comentario `# ── Estado — solo lo que no viene del context_bar`
- Las tres líneas de inicialización de `_s` desde `ctx`: `ctx.asignacion_id`, `ctx.periodo_id`, `ctx.grupo_id`
- La función completa `def on_context_change() -> None: ui.navigate.reload()`
- El kwarg `on_context_change=on_context_change` en la llamada a `app_layout(...)`

**Cambios a realizar:**

1. En el dict `_s`, reemplazar las tres claves que venían de `ctx`:
   ```python
   # ANTES (aproximadamente líneas 80-82)
   "asignacion_id": ctx.asignacion_id,
   "periodo_id":    ctx.periodo_id,
   "grupo_id":      ctx.grupo_id,

   # DESPUÉS — agregar estas claves en su lugar
   "sel_periodo_id":        None,
   "sel_periodo_nombre":    "",
   "sel_grupo_id":          None,
   "sel_grupo_nombre":      "",
   "sel_asignacion_id":     None,
   "sel_asignacion_nombre": "",
   ```

2. Las referencias internas a `_s["asignacion_id"]`, `_s["periodo_id"]`, `_s["grupo_id"]` deben mantenerse funcionando. La estrategia más segura: añadir alias en `on_sel_change` que copian los valores sel_* a las claves originales, para no renombrar toda la lógica interna de la página:
   ```python
   def on_sel_change(s: dict) -> None:
       _s["asignacion_id"] = s["sel_asignacion_id"]
       _s["periodo_id"]    = s["sel_periodo_id"]
       _s["grupo_id"]      = s["sel_grupo_id"]
       _cargar_datos()
       panel_vista.refresh()
   ```

3. Al inicio de `contenido()`, ANTES de renderizar la tabla o cualquier otro elemento, insertar:
   ```python
   from src.interface.design.components.inline_selectors import inline_periodo_grupo_asignatura
   inline_periodo_grupo_asignatura(
       _s, on_sel_change,
       usuario_id=ctx.usuario_id,
       institucion_id=ctx.institucion_id,
       usuario_rol=ctx.usuario_rol,
       preselect_periodo=True,
   )
   ```
   El import debe estar al nivel del módulo (no dentro de la función), junto a los otros imports.

4. En `app_layout(...)`: eliminar `on_context_change=on_context_change`. Verificar que no quede ese kwarg.

5. `ctx` sigue siendo necesario para `ctx.usuario_id`, `ctx.usuario_rol`, `ctx.institucion_id`, `ctx.usuario_nombre`. NO eliminar `ctx = SessionContext.desde_storage()`.

**Verificar que no se rompe:**
- Si `_s["asignacion_id"]` o `_s["periodo_id"]` son None al inicio, `_cargar_datos()` debe retornar vacío sin crash (ya tiene este guard en las primeras líneas: `if not asig_id or not per_id: return`). Con la nueva inicialización ambos empiezan en None, que es el estado correcto.
- La lógica de periodo cerrado: buscar `_s_cerrado_desde_ctx` o similar. Si lee `ctx.periodo_id`, migrar para que lea `_s["periodo_id"]`. Si lanza excepción cuando `periodo_id` es None, añadir guard: `if not _s["periodo_id"]: return False`.

---

### T2 — registro_asistencia.py

Leer el archivo completo antes de tocar nada. Luego:

**Código muerto a eliminar:**
- Líneas del docstring del módulo que referencian `context_selector` (menciona "2 puntos")
- Comentarios sobre `on_context_change` en la función principal (~líneas 415-416)
- Las líneas de bleeding: `_s["grupo_id"] = ctx.grupo_id` y `_s["periodo_id"] = ctx.periodo_id`
- La función completa `def on_context_change() -> None:` con todo su body
- El patrón `ctx_actual = SessionContext.desde_storage() or ctx` donde solo se usa para leer grupo/periodo/asignacion — reemplazar por `ctx` directamente (ctx tiene usuario_id, usuario_rol que no cambian)
- El kwarg `on_context_change=on_context_change` en `app_layout(...)`

**Cambios a realizar:**

1. En el dict `_s`, inicializar las claves sel_* (si no existen ya):
   ```python
   "sel_periodo_id":        None,
   "sel_periodo_nombre":    "",
   "sel_grupo_id":          None,
   "sel_grupo_nombre":      "",
   "sel_asignacion_id":     None,
   "sel_asignacion_nombre": "",
   ```
   Y eliminar las líneas que hacían `_s["grupo_id"] = ctx.grupo_id` / `_s["periodo_id"] = ctx.periodo_id`.

2. Función `_cargar_estado(ctx, _s)`: esta función mezcla lógica legítima con bleeding. Eliminar las líneas que copian `ctx.grupo_id`, `ctx.asignacion_id`, `ctx.periodo_id` a `_s`. El resto de la función (que carga estudiantes, asistencias usando `_s["grupo_id"]` etc.) debe mantenerse intacto.

3. Función `_s_cerrado_desde_ctx(ctx)` (o equivalente que lee `ctx.periodo_id` para verificar el estado del periodo): migrar para leer de `_s`. Cambiar la firma a `_s_cerrado(periodo_id: int | None) -> bool`. Si `periodo_id` es None, retornar False. Actualizar todos los llamadores de esa función.

4. Función `_guardar(_s, ctx)`: sigue necesitando `ctx.usuario_id`, `ctx.anio_id` etc. para auditoría. Los valores `grupo_id/asignacion_id/periodo_id` ahora vienen de `_s` (que ya tiene esos valores vía alias). No cambiar la firma si se puede evitar.

5. Al inicio de `contenido()`, antes de renderizar la tabla, insertar:
   ```python
   def on_sel_change(s: dict) -> None:
       _s["grupo_id"]      = s["sel_grupo_id"]
       _s["asignacion_id"] = s["sel_asignacion_id"]
       _s["periodo_id"]    = s["sel_periodo_id"]
       _cargar_estado(ctx, _s)
       vista_asistencia.refresh()

   inline_periodo_grupo_asignatura(
       _s, on_sel_change,
       usuario_id=ctx.usuario_id,
       institucion_id=ctx.institucion_id,
       usuario_rol=ctx.usuario_rol,
       preselect_periodo=True,
   )
   ```
   Verificar el nombre real del `@ui.refreshable` de la vista antes de llamar `.refresh()`.

6. Verificar que el guard de datos vacíos funciona: si `_s["grupo_id"]` es None al cargar, `_cargar_estado` debe retornar temprano sin crash.

---

### T3 — Verificación final

```bash
python -X utf8 init.py
python -X utf8 scripts/check_imports.py --layer interface
python -X utf8 scripts/check_design.py --file src/interface/pages/evaluacion/planilla_notas.py
python -X utf8 scripts/check_design.py --file src/interface/pages/academico/registro_asistencia.py
```

Validaciones adicionales con grep:
```bash
# Debe retornar 0 resultados en los dos archivos:
grep -n "on_context_change" src/interface/pages/evaluacion/planilla_notas.py
grep -n "on_context_change" src/interface/pages/academico/registro_asistencia.py
grep -n "context_bar\|context_selector\|context_chip" src/interface/pages/evaluacion/planilla_notas.py
grep -n "context_bar\|context_selector\|context_chip" src/interface/pages/academico/registro_asistencia.py
```

## Restricciones

- ❌ No tocar ningún archivo fuera de los dos de este paso
- ❌ No renombrar funciones de dominio ni cambiar firmas de servicios
- ✅ `ctx = SessionContext.desde_storage()` permanece en ambas páginas (se usa para usuario_id, rol, institucion_id)
- ✅ La lógica de periodo cerrado debe seguir bloqueando edición
- ✅ Ambas páginas deben mostrar estado vacío (sin crash) cuando no hay selección completa
