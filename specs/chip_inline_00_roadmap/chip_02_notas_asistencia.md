# chip_02 — Migrar Notas y Asistencia a selectores inline

> Depende de chip_01. No iniciar sin chip_01 verde en init.py.

## Archivos a modificar

```
src/interface/pages/evaluacion/planilla_notas.py
src/interface/pages/academico/registro_asistencia.py
```

---

## planilla_notas.py

### Código muerto a eliminar (verificar línea exacta antes de tocar)

| Qué | Líneas aprox. | Motivo |
|-----|--------------|--------|
| Docstring del módulo, frases que referencian `context_bar` | 8-10 | El módulo ya no depende del topbar |
| Comentario `# ── Estado — solo lo que no viene del context_bar` | ~78 | Obsoleto |
| `_s["asignacion_id"] = ctx.asignacion_id` | ~80 | El inline selector lo setea |
| `_s["periodo_id"] = ctx.periodo_id` | ~81 | Idem |
| `_s["grupo_id"] = ctx.grupo_id` | ~82 | Idem |
| `def on_context_change() -> None: ui.navigate.reload()` | ~850-851 | Función muerta |
| `on_context_change = on_context_change` en `app_layout(...)` | ~856 | Kwarg muerto |

### Cambios requeridos

1. **Inicialización de `_s`**: reemplazar los tres campos que venían de `ctx` por las
   claves del inline selector:
   ```python
   # ANTES
   "asignacion_id": ctx.asignacion_id,
   "periodo_id":    ctx.periodo_id,
   "grupo_id":      ctx.grupo_id,

   # DESPUÉS
   "sel_periodo_id":       None,
   "sel_periodo_nombre":   "",
   "sel_grupo_id":         None,
   "sel_grupo_nombre":     "",
   "sel_asignacion_id":    None,
   "sel_asignacion_nombre": "",
   ```

2. **Toda referencia a `_s["asignacion_id"]`, `_s["periodo_id"]`, `_s["grupo_id"]`**
   dentro de la página debe migrarse a `_s["sel_asignacion_id"]` etc.
   Buscar y reemplazar exhaustivamente — no dejar referencias huérfanas.

3. **Agregar los selectores inline** al inicio del `contenido()` (antes de la tabla):
   ```python
   from src.interface.design.components.inline_selectors import inline_periodo_grupo_asignatura

   def on_sel_change() -> None:
       _s["periodo_id"]    = _s["sel_periodo_id"]     # alias para el resto de la lógica
       _s["asignacion_id"] = _s["sel_asignacion_id"]
       _s["grupo_id"]      = _s["sel_grupo_id"]
       _cargar_datos()
       panel_vista.refresh()

   inline_periodo_grupo_asignatura(
       _s, on_sel_change,
       usuario_id=ctx.usuario_id,
       institucion_id=ctx.institucion_id,
       usuario_rol=ctx.usuario_rol,
       preselect_periodo=True,
   )
   ```

   > Nota: mantener temporalmente los alias `_s["periodo_id"]` etc. para no
   > refactorizar toda la lógica interna de la página en este paso. El
   > renombrado completo es opcional y puede hacerse como cleanup posterior.

4. **`app_layout`**: eliminar `on_context_change=on_context_change`. No agregar
   `mostrar_contexto=False` explícito — ya no existe ese parámetro (chip_04 lo eliminará).

5. **`ctx`** sigue siendo necesario para `ctx.usuario_id`, `ctx.usuario_rol`,
   `ctx.institucion_id`. NO eliminar la línea `ctx = SessionContext.desde_storage()`.

### Verificar que sigue funcionando

- [ ] Periodo cerrado → campo edición bloqueado (lógica en `_s_cerrado_desde_ctx` o equivalente)
- [ ] Si no hay asignacion_id, la planilla muestra estado vacío (no crash)
- [ ] El `on_sel_change` dispara recarga de actividades y planilla

---

## registro_asistencia.py

### Código muerto a eliminar

| Qué | Líneas aprox. | Motivo |
|-----|--------------|--------|
| Docstring módulo: líneas sobre `context_selector` en 2 puntos | 11-15 | Obsoleto |
| Comentario sobre `on_context_change` en 2 lugares | ~415-416 | Obsoleto |
| `_s["grupo_id"] = ctx.grupo_id` | ~204 | Bleeding eliminado |
| `_s["periodo_id"] = ctx.periodo_id` | ~205 | Bleeding eliminado |
| `def on_context_change() -> None:` con su body | ~443-447 | Función muerta |
| `ctx_actual = SessionContext.desde_storage() or ctx` | ~431 | Patrón muerto |
| `on_context_change = on_context_change` en `app_layout(...)` | ~505 | Kwarg muerto |

### Cambios requeridos

1. **`_cargar_estado(ctx, _s)`**: esta función mezcla lógica legítima (cargar
   `estudiantes`, `asistencias`) con bleeding del chip (setear `grupo_id` y
   `periodo_id` desde `ctx`). Separar:
   - Eliminar las líneas que copian `ctx.grupo_id / ctx.asignacion_id / ctx.periodo_id`
     a `_s`. Esos valores vienen del inline selector.
   - Mantener el resto de la función que usa `_s["grupo_id"]` etc. ya seteados.

2. **`_s_cerrado_desde_ctx(ctx)`** (~línea 168): esta función lee `ctx.periodo_id`
   para verificar si el periodo está cerrado. Migrar para leer de `_s["sel_periodo_id"]`
   en su lugar. Cambiar firma a `_s_cerrado(_s)` o `_s_cerrado(periodo_id)`.

3. **Agregar selectores inline** al inicio del `contenido()`:
   ```python
   from src.interface.design.components.inline_selectors import inline_periodo_grupo_asignatura

   def on_sel_change() -> None:
       _s["grupo_id"]      = _s["sel_grupo_id"]
       _s["asignacion_id"] = _s["sel_asignacion_id"]
       _s["periodo_id"]    = _s["sel_periodo_id"]
       _cargar_estado(_s)
       vista_asistencia.refresh()

   inline_periodo_grupo_asignatura(
       _s, on_sel_change,
       usuario_id=ctx.usuario_id,
       institucion_id=ctx.institucion_id,
       usuario_rol=ctx.usuario_rol,
       preselect_periodo=True,
   )
   ```

4. **`_guardar(_s, ctx)`** (~línea 343): sigue usando `ctx.usuario_id`, `ctx.anio_id`
   etc. para auditoría. Los valores de grupo/asignacion/periodo ahora vienen de `_s`.
   Ajustar las referencias internas.

5. **Verificar que sigue funcionando**:
   - [ ] Periodo cerrado → guardar bloqueado (usa `_s_cerrado(_s)`)
   - [ ] Sin selección completa → no crash, estado vacío
   - [ ] Guardar asistencia graba con el periodo/grupo/asignacion del selector

---

## Restricciones

- ❌ No refactorizar la lógica de dominio ni los servicios.
- ❌ No cambiar el nombre de `_cargar_estado` ni `_guardar` — solo sus cuerpos.
- ✅ Después del paso, `init.py` completamente verde.
- ✅ Los comentarios `context_bar` / `context_selector` en docstrings deben desaparecer.
