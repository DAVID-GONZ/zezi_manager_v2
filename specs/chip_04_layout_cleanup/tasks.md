# chip_04 — Cleanup final del chip global

> Referencia: `specs/chip_inline_00_roadmap/chip_04_layout_cleanup.md`
> Este paso es solo eliminación — no añade funcionalidad.

## Orden de ejecución obligatorio

1. T1 — Borrar test obsoleto (evita que init.py falle por imports rotos)
2. T2 — Limpiar `__init__.py` (quitar exports muertos)
3. T3 — Borrar `context_bar.py`
4. T4 — Vaciar `context_selector.py` (dejar módulo mínimo con deprecation notice)
5. T5 — Limpiar `layout.py` (quitar parámetros y bloque del chip)
6. T6 — Eliminar `chips.css` y su `@import` en theme.py
7. T7 — Limpiar las 26 páginas (quitar `mostrar_contexto`, `mostrar_grupo`, `mostrar_asignatura`, `on_context_change` de llamadas a `app_layout`)
8. T8 — Verificación final

---

## T1 — Borrar test obsoleto

Eliminar el archivo completo:
```
tests/unit/interface/design/test_context_selector_dimensiones.py
```
Testa `dimensiones_visibles` y `seleccion_completa` de `context_selector.py`.
Al vaciar ese módulo (T4), el test fallaría con ImportError.
**Borrar ANTES de limpiar context_selector.py.**

---

## T2 — Limpiar `src/interface/design/components/__init__.py`

Eliminar exactamente estas líneas (verificar números reales antes):
```python
from .context_bar import context_bar        # línea ~7
from .context_selector import abrir_selector, context_chip  # línea ~8
```
Y en `__all__` (si existe):
```python
"context_chip",    # eliminar
"abrir_selector",  # eliminar
"context_bar",     # eliminar si está
```

---

## T3 — Borrar `context_bar.py`

Eliminar el archivo completo:
```
src/interface/design/components/context_bar.py
```
Es un shim de 15 líneas que solo llama a `abrir_selector`. Ya no tiene importadores
tras limpiar `__init__.py` en T2.

---

## T4 — Vaciar `context_selector.py`

Reemplazar el contenido completo de
`src/interface/design/components/context_selector.py`
con un módulo mínimo de deprecación:

```python
"""
context_selector.py — DEPRECADO (chip_04, 2026-07-30).

El chip global de contexto fue eliminado en la épica chip_inline.
Los selectores de periodo/grupo/asignatura ahora viven en cada página
vía `src.interface.design.components.inline_selectors`.

Este módulo se conserva vacío para no romper imports legacy
que puedan existir en ramas no mergeadas.
"""
```

No dejar ninguna función, clase ni import activo. El módulo debe importar sin error
pero no exportar nada.

---

## T5 — Limpiar `src/interface/design/layout.py`

### En `_topbar()` (función interna, ~línea 348)

**Eliminar estos 4 parámetros de la firma:**
```python
on_context_change=None,        # ~línea 356
mostrar_contexto: bool = True, # ~línea 357
mostrar_grupo: bool = True,    # ~línea 358
mostrar_asignatura: bool = True, # ~línea 359
```

**Eliminar el bloque completo del chip (~líneas 385-393):**
```python
if ctx is not None and mostrar_contexto:
    from src.interface.design.components.context_selector import context_chip
    context_chip(
        ctx,
        on_change=on_context_change,
        mostrar_grupo=mostrar_grupo,
        mostrar_asignatura=mostrar_asignatura,
    )
```

### En `app_layout()` (~línea 510)

**Eliminar estos 4 parámetros de la firma:**
```python
on_context_change=None,
mostrar_contexto: bool = True,
mostrar_grupo: bool = True,
mostrar_asignatura: bool = True,
```

**Eliminar del docstring** las líneas que describen esos parámetros (~líneas 534-541):
```
on_context_change: Callback al cambiar contexto desde el chip.
mostrar_contexto:  Si False, oculta el chip de contexto...
mostrar_grupo:     Si False, el selector no muestra el paso Grupo...
mostrar_asignatura: Si False, el selector no muestra el paso Asignatura...
```

**Eliminar el forwarding de los 4 kwargs a `_topbar()` (~líneas 714-717):**
```python
on_context_change=on_context_change,
mostrar_contexto=mostrar_contexto,
mostrar_grupo=mostrar_grupo,
mostrar_asignatura=mostrar_asignatura,
```

**Verificar** que la llamada a `_topbar(...)` restante compila sin esos kwargs.

---

## T6 — Eliminar `chips.css`

El archivo `src/interface/design/styles/components/chips.css` contiene exclusivamente
CSS del chip global (clases `.cs-chip`, `.cs-chip-empty`, `.cs-dialog-*`, `.cs-step-*`,
`.cs-card-*`, `.cs-bar-*`). Ninguna de esas clases se usa en páginas tras este paso.

**Verificar primero** con grep que ningún archivo fuera de context_selector.py usa clases `.cs-`:
```
grep -rn "cs-chip\|cs-dialog\|cs-step\|cs-card\|cs-bar" src/interface/pages/ src/interface/design/components/
```
Si el resultado es vacío (o solo aparece en context_selector.py que ya fue vaciado):

1. Eliminar el archivo `src/interface/design/styles/components/chips.css`
2. En `src/interface/design/theme.py`, eliminar la línea del CSS_LOAD_ORDER que lo importa:
   ```python
   "components/chips.css",  # eliminar esta entrada
   ```

---

## T7 — Limpiar las 26 páginas

En cada página de la lista, buscar la llamada a `app_layout(...)` y eliminar
exactamente los kwargs muertos que aparezcan. Solo tocar la llamada a `app_layout`,
no la lógica de la página.

**Kwargs a eliminar donde aparezcan:**
- `mostrar_contexto=False`
- `mostrar_contexto=True`
- `mostrar_grupo=True` / `mostrar_grupo=False`
- `mostrar_asignatura=True` / `mostrar_asignatura=False`
- `on_context_change=...` (si queda alguno residual)

### Lista de archivos

```
src/interface/pages/academico/estudiantes.py
src/interface/pages/academico/horarios_hub.py
src/interface/pages/admin/asignaciones.py
src/interface/pages/admin/asignaturas.py
src/interface/pages/admin/auditoria.py
src/interface/pages/admin/configuracion_institucion.py
src/interface/pages/admin/configuracion_sie.py
src/interface/pages/admin/diagnostico.py
src/interface/pages/admin/disponibilidad_docente.py
src/interface/pages/admin/grupos.py
src/interface/pages/admin/plan_estudios.py
src/interface/pages/admin/salas.py
src/interface/pages/admin/usuarios.py
src/interface/pages/convivencia/categorias.py
src/interface/pages/convivencia/plantillas.py
src/interface/pages/evaluacion/cierre_anio.py
src/interface/pages/evaluacion/cierre_periodo.py
src/interface/pages/evaluacion/configuracion_evaluacion.py
src/interface/pages/evaluacion/habilitaciones.py
src/interface/pages/evaluacion/planes_mejoramiento.py
src/interface/pages/informes/boletin_anual.py
src/interface/pages/informes/boletin_periodo.py
src/interface/pages/informes/consolidado_asistencia.py
src/interface/pages/informes/consolidado_notas.py
src/interface/pages/informes/estadisticos.py
src/interface/pages/inicio.py
```

**Estrategia**: para cada archivo, leer la llamada a `app_layout(...)`, identificar
qué kwargs muertos tiene, y eliminarlos. No tocar ningún otro código del archivo.

---

## T8 — Verificación final

```bash
python -X utf8 init.py
```

**Grep de validación — todos deben retornar 0 resultados:**
```bash
grep -rn "context_chip\|abrir_selector\|mostrar_contexto\|on_context_change" src/
grep -rn "context_bar" src/
grep -rn "cs-chip\|cs-dialog\|cs-step" src/interface/pages/ src/interface/design/components/
grep -rn "from .context_bar\|from .context_selector" src/interface/design/components/__init__.py
grep -rn "mostrar_asignatura\|mostrar_grupo" src/interface/pages/
```

**Verificar que `app_layout` sigue siendo llamable** — al menos una página debe importar y llamar a `app_layout` sin los kwargs eliminados.

---

## Restricciones

- ❌ No tocar lógica de ninguna página — solo eliminar kwargs de la llamada a `app_layout`
- ❌ No eliminar `SessionContext` ni `Container` de ninguna página
- ❌ No modificar CSS de `inline_selectors.css` ni ningún otro CSS del design system
- ✅ `context_selector.py` se vacía pero NO se borra (por si hay branches que lo importan)
- ✅ El orden T1→T8 es obligatorio para evitar ImportError durante la ejecución
