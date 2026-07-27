# convivencia_06 — Reporte de notas + observaciones del periodo (director de grupo)

> Fase 2 (`convivencia_00_roadmap`). Depende de `convivencia_04` (RBAC), `convivencia_04b` (enforcement) y `convivencia_05` (DTO consolidado).

## Contexto y decisión (David)

Prioridad explícita de la épica: **"que el director de grupo asigne notas y genere el reporte de notas y observaciones por periodo"**. Convivencia_04/04b/05 dejaron el terreno listo. Ahora se añade la pantalla y la exportación.

Estado actual (herramientas disponibles):
- `ConvivenciaService.listar_conceptos_grupo(grupo_id, periodo_id)` — devuelve `ConceptoComportamientoDTO` por estudiante (nota + nivel + concepto).
- `ConvivenciaService.listar_observaciones(estudiante_id, periodo_id, solo_publicas=False)` — todas las observaciones del estudiante en el periodo.
- `catalogo_academico_service.puede_gestionar_comportamiento_en_grupo(rol, uid, gid)` — autorización por objeto.
- Exportadores en `src/infrastructure/exporters/` (PDF, Excel, CSV) — usados por informe_service.

## Puerta de aprobación
No toca esquema ni modelo. Añade pantalla nueva de interfaz + método consolidador en `ConvivenciaService` que combina lecturas ya existentes. **No requiere puerta**.

## Tareas

### T1 — Método consolidador en servicio
- En `ConvivenciaService`, añadir:
  - `reporte_periodo_grupo(grupo_id: int, periodo_id: int) -> list[ReporteConvivenciaFilaDTO]`
    - Combina `listar_conceptos_grupo(grupo_id, periodo_id)` con `listar_observaciones(est_id, periodo_id)` por estudiante.
    - Cada fila: `{estudiante_id, nombre, valor, nivel_nombre, concepto, observaciones: list[str]}`.
- Añadir DTO `ReporteConvivenciaFilaDTO` en `src/domain/models/convivencia.py` (aditivo puro; exportado en __all__).
- Resolución de nombres de estudiantes: reutilizar `estudiante_svc_provider` ya inyectado (convivencia_05).

### T2 — Ruta y RBAC
- En `main.py`, registrar `/convivencia/reporte-periodo` con `roles=_AULA` (director/coordinador/profesor). El gating por-objeto se hace **en la página** con `puede_gestionar_comportamiento_en_grupo`.

### T3 — Página `reporte_periodo.py`
- Crear `src/interface/pages/convivencia/reporte_periodo.py` con `reporte_periodo_page()`.
- Selectores: **grupo** (todos si es dir/coord; solo el que dirige si es profesor director de grupo) y **periodo**.
- Si el usuario no está autorizado para el grupo activo → `empty_state` con mensaje claro; no muestra datos ni acciones.
- Autorizado → tabla por estudiante con: nombre, nota, nivel, concepto, número de observaciones (con detalle expandible o listado debajo).
- Botón "Exportar PDF" y "Exportar Excel" (usa los exporters existentes vía `informe_service` o un helper mínimo dentro del servicio).
- **CUMPLIMIENTO DEL DESIGN SYSTEM** (endurecido 2026-07-27): usa **exclusivamente** clases del design system (`.panel-card`, `.panel-toolbar`, `.section-title-lg`, `.row-actions`, `.form-row-*`, `.divider-row*`, `stat-card`, `status_badge`, `empty_state`, `toast_*`, `btn_*`, `custom_dialog`, `form_dialog`, `confirm_dialog`); PROHIBIDO apilar 3+ utilidades atómicas Tailwind o llamar `ui.notify`/`ui.dialog`/`ui.badge` directamente. Corre `scripts/check_design.py --file src/interface/pages/convivencia/reporte_periodo.py` y debe salir verde.

### T4 — Tests
- Servicio: `reporte_periodo_grupo` combina notas + observaciones correctamente para un grupo/periodo dado; incluye estudiantes sin nota y sin observaciones.
- Página (opcional si el proyecto lo permite): smoke import + estructura de estado.

### T5 — Verificación
- `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_imports.py --layer domain / services / interface`
- `... scripts/check_design.py --file src/interface/pages/convivencia/reporte_periodo.py` VERDE.
- `... -m pytest tests/unit/ -q --tb=short`
- `... init.py` VERDE.
- `progress/impl_convivencia_06.md`.

## criterio_done
Existe la página `/convivencia/reporte-periodo` accesible al director de grupo + dirección + coordinación (gating por objeto), que muestra por estudiante la nota+concepto+observaciones del periodo y permite exportar a PDF/Excel. Método `reporte_periodo_grupo` en el servicio combina las lecturas. Tests verdes, `check_design --file` verde, `init.py` verde. Cero utilidades Tailwind atómicas apiladas (regla L) y cero `ui.dialog/notify/badge` (regla M) en la página nueva.
