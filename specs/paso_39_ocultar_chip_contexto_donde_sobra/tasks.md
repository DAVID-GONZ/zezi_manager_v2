# paso_39 — Ocultar el chip de contexto en las páginas que no lo usan

## Contexto y decisión (David)

El chip de contexto de la topbar (selector año/periodo/grupo/asignatura) se muestra hoy en casi todas las páginas, pero **muchas no usan ninguna dimensión de contexto** → el chip ahí es ruido (y en `configuracion_sie` el selector de año es engañoso, porque la página usa `get_activa()`, no `ctx.anio_id`). Ya existe el flag `mostrar_contexto: bool = True` de `app_layout`/`_topbar` (paso_25); basta usarlo.

**Audit (objetivo, por uso real de `ctx.anio_id/periodo_id/grupo_id/asignacion_id`):**
- **Mantienen el chip** (leen contexto): inicio, horarios_hub, registro_asistencia, tablero_estadisticos, admin/asignaciones, convivencia/* (3), evaluacion/* (cierre_anio, cierre_periodo, configuracion_evaluacion, habilitaciones, planes_mejoramiento, planilla_notas), informes/* (boletin_anual, boletin_periodo, consolidado_asistencia, consolidado_notas, estadisticos). NO TOCAR.
- **Apagar el chip** (no leen contexto): las 9 de abajo.

## Tareas

### T1 — `mostrar_contexto=False` en las 9 páginas sin uso de contexto
En la llamada a `app_layout(...)` de cada una, añadir `mostrar_contexto=False` (sin tocar nada más de la página):
- `src/interface/pages/academico/estudiantes.py`
- `src/interface/pages/admin/grupos.py`
- `src/interface/pages/admin/asignaturas.py`
- `src/interface/pages/admin/salas.py`
- `src/interface/pages/admin/plan_estudios.py`
- `src/interface/pages/admin/disponibilidad_docente.py`
- `src/interface/pages/admin/configuracion_institucion.py`
- `src/interface/pages/admin/configuracion_sie.py`
- `src/interface/pages/admin/auditoria.py`

(Ya están apagadas `usuarios` y `diagnostico` — no tocar.)

NOTA: verificar que ninguna de estas 9 pasa `on_context_change` a `app_layout` (no deberían, según el audit). Si alguna lo hiciera, NO apagarla y reportarlo.

### T2 — Verificación
- `python init.py` VERDE (baseline 1178 passed, 1 skipped). check_design + check_imports interface en verde.
- (Opcional) un test que afirme que esas rutas se construyen con `mostrar_contexto=False` o, más simple, dejar constancia en el progress.
- `progress/impl_paso_39.md` (lista de páginas tocadas + confirmación de que las que usan contexto no se tocaron).

## criterio_done
Las 9 páginas listadas (que no leen ninguna dimensión de contexto) ya no muestran el chip (`mostrar_contexto=False`); las páginas que sí usan contexto lo conservan; `python init.py` verde; sin otros cambios de comportamiento.
