# chip_04 — Limpiar layout, context_selector y directivo

> Depende de chip_03. No iniciar sin chip_03 verde en init.py.
> Este paso no añade funcionalidad — solo elimina código muerto.

## Inventario completo de código muerto

### layout.py — parámetros y lógica del chip

| Qué | Líneas aprox. | Motivo |
|-----|--------------|--------|
| Parámetro `on_context_change=None` en `_topbar()` | ~356 | Ya no hay chip que lo use |
| Parámetro `mostrar_contexto: bool = True` en `_topbar()` | ~357 | Chip eliminado |
| Parámetro `mostrar_grupo: bool = True` en `_topbar()` | ~358 | Chip eliminado |
| Parámetro `mostrar_asignatura: bool = True` en `_topbar()` | ~359 | Chip eliminado |
| Bloque `if ctx is not None and mostrar_contexto:` con la llamada a `context_chip(...)` | ~385-392 | Chip eliminado |
| Parámetro `on_context_change=None` en `app_layout()` | ~516 | Chip eliminado |
| Parámetros `mostrar_contexto/grupo/asignatura` en `app_layout()` | ~517-519 | Chip eliminado |
| Docstring de `app_layout()`: frases sobre `on_context_change` y `mostrar_contexto` | ~534-541 | Stale |
| Forwarding de los 4 kwargs de `_topbar(...)` en `app_layout()` | ~714-717 | Muerto |

**Resultado esperado**: `_topbar()` y `app_layout()` con firmas más limpias sin
parámetros relacionados al chip.

### context_selector.py — módulo completo obsoleto

Después de chip_02 y chip_03, ninguna página llama directamente a funciones de
`context_selector.py`. El único consumidor que queda es `layout.py` (eliminado arriba)
y `context_bar.py` (shim).

| Función | Estado |
|---------|--------|
| `context_chip(ctx, on_change, ...)` | DEAD — eliminar |
| `abrir_selector(ctx, on_change, ...)` | DEAD — eliminar |
| `_texto_chip(ctx)` | DEAD — eliminar |
| `_progreso_periodo(fecha_inicio, fecha_fin)` | DEAD — eliminar |
| `dimensiones_visibles(mostrar_grupo, mostrar_asignatura)` | DEAD — eliminar |
| `seleccion_completa(...)` | DEAD — eliminar |

**Acción**: vaciar `context_selector.py` dejando solo el módulo docstring con
una nota de deprecación, o eliminar el archivo si nada lo importa. Verificar
`__init__.py` del package antes de borrar.

### context_bar.py — shim completo obsoleto

El archivo `src/interface/design/components/context_bar.py` es un shim de compatibilidad
que solo llama a `abrir_selector`. Con `context_selector.py` obsoleto, `context_bar.py`
también muere.

**Acción**: eliminar `context_bar.py` completo.

### components/__init__.py — imports muertos

| Import | Estado |
|--------|--------|
| `from .context_bar import context_bar` | DEAD — eliminar |
| `from .context_selector import abrir_selector, context_chip` | DEAD — eliminar |

### styles/components/chips.css — CSS del chip global

Verificar si `chips.css` contiene estilos exclusivos del chip modal
(clases `.cs-chip-*`, `.cs-dialog-*`, `.cs-step-*`, `.cs-card-*`).
Si todo el CSS es del chip antiguo: **eliminar el archivo completo** y
quitar su `@import` de `main.css`.

Si contiene clases compartidas con otros componentes: conservar solo esas.

### Tests obsoletos

| Archivo | Estado |
|---------|--------|
| `tests/unit/interface/design/test_context_selector_dimensiones.py` | DEAD — eliminar |

Este archivo testea `dimensiones_visibles` y `seleccion_completa` de
`context_selector.py`. Con ambas funciones eliminadas, el test no puede pasar.
Eliminar antes de correr `init.py`.

---

## Páginas de directivo/coordinación — cortar bleeding

Las páginas de directivo ya tienen `mostrar_contexto=False` y sus propios selectores.
Solo hay que:
1. Eliminar el kwarg `mostrar_contexto=False` de cada llamada a `app_layout()` (el
   parámetro ya no existe en la firma).
2. Verificar si alguna página inicializa `_s` con valores de `ctx.periodo_id` o
   `ctx.grupo_id`. Si existe ese bleeding, eliminar esas líneas.

### Páginas a revisar (grep antes de tocar)

```
src/interface/pages/evaluacion/cierre_periodo.py       ~433
src/interface/pages/evaluacion/cierre_anio.py          ~215
src/interface/pages/evaluacion/configuracion_evaluacion.py ~614
src/interface/pages/evaluacion/habilitaciones.py       ~490
src/interface/pages/evaluacion/planes_mejoramiento.py  ~540
src/interface/pages/informes/boletin_periodo.py        ~305
src/interface/pages/informes/boletin_anual.py          ~287
src/interface/pages/informes/consolidado_notas.py      ~237
src/interface/pages/informes/consolidado_asistencia.py ~208
src/interface/pages/informes/estadisticos.py           ~896
src/interface/pages/academico/estudiantes.py           ~962
src/interface/pages/academico/horarios_hub.py          ~2265
src/interface/pages/admin/asignaciones.py              ~810
src/interface/pages/admin/asignaturas.py               ~421
src/interface/pages/admin/auditoria.py                 ~350
src/interface/pages/admin/configuracion_institucion.py ~166
src/interface/pages/admin/configuracion_sie.py         ~788
src/interface/pages/admin/diagnostico.py               ~224
src/interface/pages/admin/disponibilidad_docente.py    ~300
src/interface/pages/admin/grupos.py                    ~484
src/interface/pages/admin/plan_estudios.py             ~415
src/interface/pages/admin/salas.py                     ~274
src/interface/pages/admin/usuarios.py                  ~539
src/interface/pages/convivencia/categorias.py          ~281
src/interface/pages/convivencia/plantillas.py          ~326
src/interface/pages/inicio.py                          ~863, ~919
```

**Acción por página**: buscar y eliminar:
- `mostrar_contexto=False` (parámetro que ya no existe)
- `mostrar_contexto=True` (idem)
- `mostrar_grupo=...` (idem)
- `mostrar_asignatura=...` (idem, donde no ya migrado en chip_02/03)
- Cualquier `_s["periodo_id"] = ctx.periodo_id` o `_s["grupo_id"] = ctx.grupo_id`
  que no sea parte de la lógica propia del selector de esa página.

---

## Orden de ejecución

1. Eliminar `test_context_selector_dimensiones.py`
2. Limpiar `components/__init__.py` (imports muertos)
3. Eliminar `context_bar.py`
4. Vaciar / eliminar `context_selector.py`
5. Limpiar `layout.py` (parámetros y bloque chip)
6. Limpiar `chips.css` (o eliminar)
7. Limpiar kwarg `mostrar_contexto=False` de las ~26 páginas de directivo/admin
8. Correr `init.py` — debe estar completamente verde

## Criterio de done

- `init.py` completamente verde.
- `grep -rn "context_chip\|abrir_selector\|mostrar_contexto\|on_context_change" src/` → cero resultados.
- `grep -rn "context_bar" src/` → cero resultados.
- El parámetro `mostrar_contexto` no existe en ninguna firma de función.
