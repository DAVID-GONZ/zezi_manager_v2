# chip_03 — Migrar páginas de Convivencia a selectores inline

> Depende de chip_02. No iniciar sin chip_02 verde en init.py.

## Páginas incluidas

| Archivo | Selectores | Notas |
|---------|-----------|-------|
| `observaciones.py` | periodo + grupo + asignatura | |
| `comportamiento.py` | periodo + grupo + asignatura | actualmente usa `mostrar_asignatura=False` — CORREGIR |
| `seguimiento.py` | periodo + grupo + asignatura | actualmente usa `mostrar_asignatura=False` — CORREGIR |
| `notas_convivencia.py` | periodo + grupo | grupo dirigido; sin asignatura |
| `tablero_estadisticos.py` | periodo + grupo + asignatura | |
| `reporte_periodo.py` | periodo + grupo + asignatura | tiene helpers de carga propios |

---

## observaciones.py

### Código muerto identificado

| Qué | Líneas aprox. | Motivo |
|-----|--------------|--------|
| `_cargar_estado(ctx, _s)`: líneas `if ctx.grupo_id:` y `if ctx.periodo_id and _s["sel_periodo_id"] is None:` | ~64-65, ~89-90 | Bleeding del chip; inline selector reemplaza esto |
| `def on_context_change()` con su body completo | ~272-292 | Función muerta |
| Toda aparición de `ctx_actual = SessionContext.desde_storage() or ctx` | múltiples | Patrón muerto — usar `_s` directamente |
| `nuevo_ctx = SessionContext.desde_storage()` dentro de on_context_change | ~273 | Muerto |
| `on_context_change=on_context_change` en `app_layout(...)` | ~637 | Kwarg muerto |

### Cambios requeridos

1. **`_cargar_estado(ctx, _s)`**: eliminar las líneas que leen de `ctx` para setear
   `_s["estudiantes"]` y `_s["sel_periodo_id"]`. El inline selector ya habrá seteado
   `_s["sel_*"]` antes de que la página cargue datos.

2. **`_cargar_observaciones(_s, ctx)`**: conservar `ctx.usuario_id` y `ctx.usuario_rol`
   porque se necesitan para RBAC. No eliminar la función ni cambiar esos parámetros.

3. **Agregar selector inline** al inicio del contenido:
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

4. **`ctx_actual`**: cada lugar que hace `ctx_actual = SessionContext.desde_storage() or ctx`
   y luego usa solo `ctx_actual.usuario_id` / `ctx_actual.usuario_rol` puede simplificarse
   a usar el `ctx` original (que ya tiene esos valores y no cambia sin reload).

---

## comportamiento.py

### Código muerto identificado

| Qué | Líneas aprox. | Motivo |
|-----|--------------|--------|
| `_cargar_estado(ctx, _s)`: líneas `if ctx.grupo_id...` y `if ctx.periodo_id...` | ~131-134 | Bleeding |
| `if es_profesor and ctx.grupo_id: _s["filtro_grupo_id"] = ctx.grupo_id` | ~235-236 | Bleeding duplicado |
| `def on_context_change()` con su body | ~241-245 | Función muerta |
| `nuevo_ctx = SessionContext.desde_storage()` dentro de on_context_change | ~242 | Muerto |
| `ctx_actual = SessionContext.desde_storage() or ctx` | múltiples | Patrón muerto |
| `mostrar_asignatura=False` en `app_layout(...)` | ~578 | Kwarg muerto (chip desaparece) |
| `on_context_change=on_context_change` en `app_layout(...)` | ~577 | Kwarg muerto |

### Corrección de comportamiento (importante)

Esta página actualmente usaba `mostrar_asignatura=False` en el chip, lo que significa
que **no filtraba por asignatura**. Según la decisión de David, convivencia SÍ debe
filtrar por asignatura porque un profesor puede tener varias. El inline selector debe
ser `inline_periodo_grupo_asignatura` (con las 3 dimensiones).

Verificar que el servicio de comportamiento acepta `asignacion_id` como parámetro de
filtro. Si no lo acepta, agregar en chip_03 el filtro en la capa de página (no en el
servicio), o diferir a un paso separado con nota explícita en `progress/impl_chip_03.md`.

---

## seguimiento.py

### Código muerto identificado

| Qué | Líneas aprox. | Motivo |
|-----|--------------|--------|
| `_cargar_estado(ctx, _s)`: líneas de bleeding `ctx.grupo_id / ctx.periodo_id` | ~86-89 | Bleeding |
| `def on_context_change()` con su body | ~188-192 | Función muerta |
| `ctx_actual = SessionContext.desde_storage() or ctx` | múltiples | Patrón muerto |
| `mostrar_asignatura=False` en `app_layout(...)` | ~492 | Kwarg muerto |
| `mostrar_contexto=True` en `app_layout(...)` | ~491 | Kwarg muerto (chip desaparece) |
| `on_context_change=on_context_change` en `app_layout(...)` | ~490 | Kwarg muerto |

### Corrección igual que comportamiento

`mostrar_asignatura=False` → migrar a `inline_periodo_grupo_asignatura` (con las 3 dimensiones).

---

## notas_convivencia.py

### Código muerto identificado

| Qué | Líneas aprox. | Motivo |
|-----|--------------|--------|
| `_cargar_estado(ctx, _s)`: bleeding `ctx.grupo_id / ctx.periodo_id` | ~86-89 | Bleeding |
| `def on_context_change()` con su body | ~291-292 | Función muerta |
| `ctx_actual = SessionContext.desde_storage() or ctx` | múltiples | Patrón muerto |
| `mostrar_asignatura=False` en `app_layout(...)` | ~456 | Kwarg muerto |
| `on_context_change=on_context_change` en `app_layout(...)` | ~455 | Kwarg muerto |

### Selector correcto: `inline_periodo_grupo` (sin asignatura)

Esta página gestiona el grupo dirigido. Usar:
```python
from src.interface.design.components.inline_selectors import inline_periodo_grupo

inline_periodo_grupo(
    _s, on_sel_change,
    institucion_id=ctx.institucion_id,
    preselect_periodo=True,
)
```

---

## tablero_estadisticos.py

### Código muerto identificado (el más contaminado)

| Qué | Líneas aprox. | Motivo |
|-----|--------------|--------|
| `_s["periodo_id"] = ctx.periodo_id` en init de `_s` | ~926 | Bleeding |
| `_s["anio_id"] = ctx.anio_id` en init de `_s` | ~927 | Bleeding |
| `_s["grupo_id"] = ctx.grupo_id` en init de `_s` | ~928 | Bleeding |
| `_s["asignacion_id"] = ctx.asignacion_id` en init de `_s` | ~929 | Bleeding |
| `"drill_grupo_id": ctx.grupo_id` en init de `_s` | ~937 | Bleeding |
| `"drill_asig_id": ctx.asignacion_id` en init de `_s` | ~938 | Bleeding |
| `ctx_actual = SessionContext.desde_storage()` | ~1070 | Patrón muerto |
| `def on_context_change()` con su body completo | ~1119-1125 | Función muerta |
| `on_context_change = on_context_change` en `app_layout(...)` | ~1169 | Kwarg muerto |

### Cambio en `_s` drill fields

Los campos `drill_grupo_id` y `drill_asig_id` ya no arrancan con valores de `ctx`
— arrancan en `None`. El inline selector los poblará cuando el usuario seleccione.

---

## reporte_periodo.py

### Código muerto identificado

| Qué | Líneas aprox. | Motivo |
|-----|--------------|--------|
| `_cargar_grupos(ctx, _s)` — función completa | ~85-104 | El inline selector hace esto internamente |
| `_cargar_periodos(ctx, _s)` — función completa | ~106-120 | Idem |
| `_s["grupo_id"] = ctx.grupo_id` | ~204 | Bleeding |
| `_s["periodo_id"] = ctx.periodo_id` | ~205 | Bleeding |
| `ctx_actual = SessionContext.desde_storage() or ctx` | múltiples | Patrón muerto |
| `mostrar_asignatura=False` en `app_layout(...)` | ~301 | Kwarg muerto |

### Nota especial

`reporte_periodo.py` tiene sus propios helpers `_cargar_grupos` y `_cargar_periodos`.
Son funcionalmente equivalentes a lo que el inline selector hará. Al migrar, ELIMINAR
esas funciones completamente — no dejarlas como dead code. El inline selector los reemplaza.

---

## Reglas transversales para este paso

- ✅ En todas las páginas: `ctx` sigue siendo necesario para `ctx.usuario_id`,
  `ctx.usuario_rol`, `ctx.institucion_id`. No eliminar la línea de `SessionContext.desde_storage()`.
- ✅ El patrón `ctx_actual = SessionContext.desde_storage() or ctx` desaparece en todos
  los lugares donde solo se usaba para leer `ctx_actual.grupo_id / .periodo_id / .asignacion_id`.
  Si algún lugar usaba `ctx_actual` para datos de identidad (usuario_id, rol), reemplazar
  directamente con `ctx` (que no cambia sin reload).
- ❌ No modificar `context_selector.py` ni `layout.py` — eso es chip_04.
- ✅ `init.py` completamente verde al terminar.

## Código muerto en tests

Al terminar chip_03, revisar:
- `tests/unit/interface/design/test_context_selector_dimensiones.py` — este archivo
  testa `dimensiones_visibles` y `seleccion_completa` de `context_selector.py`.
  Esas funciones se volverán dead en chip_04. **No eliminar en chip_03** — hacerlo en chip_04
  junto con el resto del cleanup de context_selector.
