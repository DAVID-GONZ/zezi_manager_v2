# paso_22 — Diferenciar a fondo el dashboard: profesor vs directivo

## Contexto y decisión

Cierre de la línea de "vistas diferenciadas por rol". `paso_21` ya redefinió el dashboard de **admin** (plataforma). Este paso diferencia el **contenido** (no solo etiquetas/enlaces) del dashboard de `/inicio` entre **profesor** y **directivo (director/coordinador)**, que hoy comparten estructura y métricas de un solo grupo del chip.

Principio:
- **Directivo** = vista **institucional / de gestión** (agregado de todos los grupos del periodo).
- **Profesor** = vista **personal / accionable** (sus grupos y sus pendientes).

**Fuera de alcance:**
- NO tocar la rama **admin** del dashboard (quedó en paso_21).
- NO romper "Ver como": estas vistas se renderizan cuando un admin impersona a un profesor/directivo, así que deben funcionar en **solo lectura** (usar SOLO métodos de lectura; nada de escritura).
- Multi-tenancy real.

Reusar servicios existentes (verificar firmas antes de usar — protocolo implementer): `estadisticos_service.metricas_institucionales(periodo_id, anio_id)`, `estadisticos_service.metricas_dashboard(grupo_id, periodo_id, anio_id)`, `estadisticos_service.ranking_grupo(...)`, `estadisticos_service.estudiantes_en_riesgo_academico(...)`, `cierre_service.estado_cierres_por_asignaciones(...)`, `habilitacion_service.listar_habilitaciones(...)`, `periodo_service.listar_hitos_proximos(...)`. Si falta un agregado, añadir un método de **solo lectura** en la capa de servicios (no computar en la página); NO meter lógica de negocio en la vista.

Archivo principal: `src/interface/pages/inicio.py`. Solo las ramas `profesor` / `director` / `coordinador` (helpers `_seccion_*`).

---

## Tareas

### T1 — Rama DIRECTIVO: stats institucionales (no de un solo grupo)
- Para `director`/`coordinador`, las stat-cards deben mostrar **agregados institucionales del periodo** (todos los grupos), vía `estadisticos_service.metricas_institucionales(periodo_id, anio_id)` — NO `metricas_dashboard` de un único grupo del chip.
- Métricas sugeridas: total estudiantes (institución), promedio general, % asistencia global, nº estudiantes en riesgo. Si `metricas_institucionales` no cubre algún dato, agregarlo como método de lectura en el servicio.
- Si no hay periodo/datos: empty states claros (no "—" mudo).

### T2 — Rama DIRECTIVO: sección "Grupos que requieren atención"
- Nueva sección (solo directivo): ranking de los grupos con más estudiantes en riesgo / por debajo del mínimo, usando `ranking_grupo` / `estudiantes_en_riesgo_academico` / el desglose por grupo de `metricas_institucionales` (lo que exista; verificar firmas). Top N (p.ej. 5), cada fila clickable → `/academico/tablero` (o informe pertinente).
- Empty state si no hay grupos en riesgo.

### T3 — Rama DIRECTIVO: sección "Pendientes institucionales"
- Nueva sección (solo directivo): resumen de pendientes a nivel institución:
  - Estado de cierres por grupo del periodo (`cierre_service.estado_cierres_por_asignaciones(...)`): cuántos cerrados / pendientes.
  - Habilitaciones / planes de mejoramiento pendientes (conteo, vía `habilitacion_service.listar_habilitaciones(...)` y plan_mejoramiento).
- Cada item enlaza a su módulo. Empty state si no hay pendientes.
- (coordinador puede inclinarse a convivencia; mantener la vista institucional compartida y dejar la diferencia fina de coordinador en sus accesos rápidos, que ya difieren. No sobre-ingeniar.)

### T4 — Rama PROFESOR: sección "Tus pendientes" (accionable)
- Para `profesor`, mantener las stat-cards actuales del grupo del chip, y añadir una sección **"Tus pendientes"** orientada a acción:
  - Actividades sin calificar / cortes pendientes de sus asignaciones.
  - Asistencia sin registrar hoy (si aplica al grupo/asignación activos).
  - Alertas de SUS estudiantes (ya filtra por `usuario_id`).
- Reusar métodos de lectura existentes; si hace falta un agregado "pendientes del docente", añadirlo como método de lectura en el servicio correspondiente (filtrado por `usuario_id`).
- Cada item enlaza a la pantalla que resuelve el pendiente (planilla, asistencia, etc.).

### T5 — Verificación y cierre
- `python init.py` VERDE (baseline previa: 1015 passed, 1 skipped). Corregir fallout; añadir tests de los nuevos métodos de servicio de lectura si se crean.
- `python scripts/check_design.py --file src/interface/pages/inicio.py` exit 0; `check_imports --layer interface` y `--layer services` exit 0.
- Confirmar que la rama admin del dashboard NO cambió y que las vistas profesor/directivo funcionan en solo lectura (no llaman métodos de escritura — relevante para "Ver como").
- Escribir `progress/impl_paso_22.md` (archivos, verificación por tarea, decisiones de diseño, output de `python init.py`).

## criterio_done
El dashboard de directivo muestra datos **institucionales agregados** (no de un solo grupo) + secciones "Grupos que requieren atención" y "Pendientes institucionales"; el de profesor mantiene sus métricas y añade "Tus pendientes" accionable; la rama admin queda intacta; todas las vistas funcionan en solo lectura (compatibles con "Ver como"); `python init.py` verde; check_design/check_imports verdes.
