# paso_13d — Empty State + Skeleton Loader Adoption: spec

**Fecha:** 2026-06-08
**Status sugerido:** spec_ready
**Prerequisito:** paso_12b (empty_state + skeleton_loader existen)

## Problema

Componentes creados en paso_12b nunca adoptados:
- `empty_state` — estados vacíos con icono + título + CTA opcional.
- `skeleton_table` / `skeleton_cards` / `skeleton_form` — placeholders con shimmer.

Hoy las páginas con listados vacíos muestran tablas vacías sin contexto, y las páginas
de carga lenta no dan feedback al usuario.

## Objetivo

Adoptar los componentes en páginas con buen caso de uso, mejorando la percepción de
performance y la claridad de estados vacíos.

## API

### `empty_state`

```python
from src.interface.design.components import empty_state

empty_state(
    titulo="No hay estudiantes en este grupo",
    mensaje="Cuando matricules estudiantes, aparecerán aquí.",
    icono="school",
    cta_label="Matricular estudiante",
    on_cta_click=lambda: dlg.open(),
)
```

### `skeleton_*`

```python
from src.interface.design.components import skeleton_table, skeleton_cards

skeleton_table(filas=8, columnas=5)
skeleton_cards(n=4)
```

## Tareas

### T1 — empty_state en listados

| Página | Cuando aplicar | Texto sugerido |
|---|---|---|
| `estudiantes.py` | `len(estudiantes_filtrados) == 0` | "No hay estudiantes con esos filtros" + CTA "Limpiar filtros" |
| `horarios.py` | grupo sin horario | "Este grupo aún no tiene horario" + CTA "Agregar bloque" (solo admin) |
| `planilla_notas.py` | sin estudiantes o sin actividades | "Configura una actividad para empezar a calificar" |
| `habilitaciones.py` | sin habilitaciones | "No hay habilitaciones registradas" + CTA "Crear habilitación" |
| `planes_mejoramiento.py` | sin planes | "No hay planes activos" |
| `observaciones.py` | sin observaciones | "Sin observaciones para este estudiante" + CTA "Agregar observación" |

### T2 — skeleton_loader durante carga

| Página | Punto de inserción |
|---|---|
| `tablero_estadisticos.py` | Mientras se calculan los KPIs (skeleton_cards n=4) |
| `estadisticos.py` | Antes de la primera previsualización (skeleton_table) |
| `boletin_periodo.py` | Durante generación de boletines masivos (skeleton_cards) |
| `boletin_anual.py` | Idem |
| `planilla_notas.py` | Carga inicial de la planilla (skeleton_table filas=15 cols=8) |

### T3 — Validación

- Cada empty_state respeta los permisos del rol (no mostrar CTA si no tiene permiso).
- Los skeletons reemplazan completamente el área de carga (no se ven encima).
- Soporte `prefers-reduced-motion`: el shimmer debe respetar la media query (ya está
  en `styles/components/skeleton.css`).

## Criterio done

- `grep -E "empty_state\(" src/interface/pages/` → ≥ 6 ocurrencias.
- `grep -E "skeleton_(table|cards|form)\(" src/interface/pages/` → ≥ 5 ocurrencias.
- Smoke manual: forzar filtros sin resultados en estudiantes → empty_state visible.
- Smoke manual: tablero_estadisticos antes/después → skeleton visible durante 1 ciclo.
- 740 tests verdes; init.py verde.

## Notas

- No reemplazar mensajes de error con empty_state — los errores siguen usando `toast_error`.
- Si una página ya tiene un mensaje "Sin resultados" custom, migrarlo a empty_state
  preservando el texto original.
