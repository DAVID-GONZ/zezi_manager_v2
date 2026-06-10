# paso_13b — Toast Adoption: spec

**Fecha:** 2026-06-08
**Status sugerido:** spec_ready
**Prerequisito:** paso_12b (componente toast existe)

## Problema

`src/interface/design/components/toast.py` (creado en paso_12b) define el wrapper unificado
`toast_info / toast_success / toast_warning / toast_error` sobre `ui.notify`. Pero la
auditoría de paso_13a revela:

- **329 ocurrencias de `ui.notify()`** en 24 archivos de `src/interface/pages/`.
- **0 importaciones** de `toast_*` en pages.

Consecuencia: las notificaciones usan colores Quasar (`positive/negative/warning/info`)
en lugar del design system, sin iconografía consistente, sin estándar de duración.

## Objetivo

Migrar todas las llamadas a `ui.notify()` en `src/interface/pages/` al wrapper `toast_*`
correspondiente. **Sin cambiar el wording de los mensajes** — solo el mecanismo de invocación.

## Mapeo

| Patrón `ui.notify()` actual | Wrapper destino |
|---|---|
| `ui.notify(msg, color="positive")` | `toast_success(msg)` |
| `ui.notify(msg, type="positive")` | `toast_success(msg)` |
| `ui.notify(msg, color="negative")` | `toast_error(msg)` |
| `ui.notify(msg, type="negative")` | `toast_error(msg)` |
| `ui.notify(msg, color="warning")` | `toast_warning(msg)` |
| `ui.notify(msg, type="warning")` | `toast_warning(msg)` |
| `ui.notify(msg, color="info")` | `toast_info(msg)` |
| `ui.notify(msg)` sin color | `toast_info(msg)` |
| `ui.notify(msg, type="ongoing", timeout=0)` | `toast_info(msg, duracion_ms=0)` |

## Alcance

24 archivos en `src/interface/pages/` (todas las páginas con ≥1 `ui.notify()`).

Excluido: cualquier `ui.notify()` dentro de `src/interface/design/components/` — esos
son parte del wrapper mismo.

## Implementación

1. Por archivo: añadir import `from src.interface.design.components import toast_*`
   (solo los wrappers usados en ese archivo).
2. Reemplazar `ui.notify(...)` → `toast_*(...)` siguiendo el mapeo.
3. Mantener el primer argumento posicional (mensaje) intacto.
4. Eliminar `color=` y `type=` redundantes.
5. Conservar `position=` y otros kwargs que el wrapper acepta (verificar firma).

## Criterio done

- `grep -rE "ui\.notify\(" src/interface/pages/` → 0 ocurrencias.
- `grep -rE "toast_(info|success|warning|error)\(" src/interface/pages/` → ≥ 329 ocurrencias.
- `python -m pytest tests/ -q` → 740 passed (sin regresiones).
- `python init.py` → verde.

## Tareas

| # | Tarea | Archivos |
|---|---|---|
| T1 | Migrar pages admin/ (6 archivos) | configuracion_institucion, configuracion_sie, grupos, asignaturas, asignaciones, usuarios |
| T2 | Migrar pages academico/ (4) | estudiantes, horarios, registro_asistencia, tablero_estadisticos |
| T3 | Migrar pages evaluacion/ (6) | configuracion_evaluacion, planilla_notas, cierre_periodo, cierre_anio, habilitaciones, planes_mejoramiento |
| T4 | Migrar pages convivencia/ (3) | observaciones, comportamiento, notas_convivencia |
| T5 | Migrar pages informes/ (5) | boletin_periodo, boletin_anual, consolidado_notas, consolidado_asistencia, estadisticos |
| T6 | Tests + init.py verde | — |
