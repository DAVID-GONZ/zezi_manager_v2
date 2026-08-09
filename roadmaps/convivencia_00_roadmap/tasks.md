# convivencia_00 — Roadmap: separación de Convivencia en 3 módulos

## Contexto y decisión (David)

Hoy existe **un solo módulo "Convivencia"** (1 modelo `convivencia.py`, 1 puerto, 1 repo, 1 servicio, 3 páginas bajo `interface/pages/convivencia/`). David pidió separarlo conceptualmente en **tres módulos** con reglas distintas, conectarlo con boletines, y añadir lo que falta. La separación se implementará en **pasos pequeños**, cada uno dejando `python init.py` VERDE.

### Visión de los 3 módulos
- **Observaciones** — bitácora colaborativa: cualquier profesor **con asignación activa en el grupo** ve/crea; texto manual o desde **catálogo** predefinido (editable por coordinador/director) que **se retroalimenta**; observaciones **categorizadas** (categorías predefinidas, editables por coordinación); las de categoría comportamental se pueden **promover** a Comportamiento.
- **Comportamiento** — restringido a **director de grupo + director + coordinador**; **cuantitativo (nota) + cualitativo (concepto)**; **conectado a boletines**. Prioridad: el director de grupo asigna notas y **genera el reporte de notas + observaciones del periodo**.
- **Seguimiento** — **visualización 360°** (todas las notas + observaciones del estudiante) + genera **alertas a profesores** (manual + automática por umbral); esas alertas aparecen en el **dashboard**.

### Decisiones confirmadas (2026-07-26)
1. Director de grupo = FK `grupos.director_grupo_id` (NO un Rol nuevo); autorización a nivel de objeto.
2. Lo asignan **director y coordinador** desde `/admin/grupos`, que pasa de `_DIRECTOR` a **`_DIR_COORD` con acceso pleno** (en el contexto real colombiano el coordinador gestiona grupos).
3. Separar **bitácora (Observaciones)** de la **narrativa oficial de boletín** (consolidada por el director de grupo en Comportamiento).
4. Alertas de seguimiento: **manual (director/coordinador → profesor) + automática por umbral**.

## Reglas duras aplicables (leader.md)
- Todo código en `src/` lo escribe el subagente `implementer`; verifica el `reviewer`.
- Pasos que **tocan el modelo `Grupo`/`Usuario` o el esquema de BD** (crear tablas/columnas, ampliar enums/CHECK) → **puerta de aprobación explícita de David** antes de lanzar el implementer.
- Ningún paso se declara `done` sin `python init.py` VERDE (usar `.venv/Scripts/python.exe`, no el `python` global 3.9).
- No `.dict()` (usar `model_dump()`); no importar `src.infrastructure.db` fuera de infraestructura; repos solo vía `Container`.

## Mapa de pasos (subdivisión)

> ✍️ = spec completa ya redactada en su carpeta. 🕓 = a expandir just-in-time (objetivo + criterio_done abajo).

### Fase 1 — Director de grupo (cimiento de todo lo demás)
- **convivencia_01_director_grupo_schema** ✍️ — `grupos.director_grupo_id` (schema + modelo `Grupo` + repo). Backend puro, sin UI. *(toca schema+modelo → puerta de aprobación)*
- **convivencia_02_director_grupo_ui** ✍️ — `/admin/grupos` → `_DIR_COORD` acceso pleno; selector "Director de grupo" por grupo (candidatos = docentes con asignación en el grupo); método de servicio.
- **convivencia_03_autz_director_grupo** ✍️ — helper de autorización por objeto `es_director_de_grupo(usuario_id, grupo_id)` / `...por_estudiante(...)`, reutilizable, con tests.

### Fase 2 — RBAC de Comportamiento + reporte del director de grupo
- **convivencia_04_rbac_comportamiento** 🕓
  - Objetivo: restringir `/convivencia/comportamiento` y `/convivencia/notas` a **director de grupo (de ese grupo) + director + coordinador**; quitar el profesor genérico. Observaciones queda en profesor-con-asignación. Enforcement por objeto en servicio + gating en vista.
  - criterio_done: un profesor sin dirección de grupo no accede a comportamiento/notas (ruta y servicio lo niegan); director de grupo sí, solo en su grupo; `init.py` verde.
- **convivencia_05_concepto_comportamiento** 🕓 *(toca modelo/BD → puerta de aprobación)*
  - Objetivo: añadir el **concepto cualitativo de periodo** por estudiante (campo/entidad junto a `NotaComportamiento`: nota cuant + concepto cualit), que será lo que baje al boletín.
  - criterio_done: se puede guardar/leer nota + concepto por estudiante/grupo/periodo; tests de dominio y repo; `init.py` verde.
- **convivencia_06_reporte_periodo_grupo** 🕓
  - Objetivo: pantalla del director de grupo para **generar el reporte de notas + observaciones del periodo** de su grupo (consolidado imprimible/exportable).
  - criterio_done: el director de grupo genera el reporte del periodo con notas de comportamiento + observaciones; `init.py` verde.

### Fase 3 — Boletín ↔ Convivencia
- **convivencia_07_informe_lee_convivencia** 🕓
  - Objetivo: `informe_service` (datos del boletín) incluye nota de comportamiento + concepto + observaciones públicas del periodo.
  - criterio_done: los datos del boletín contienen la sección de convivencia; tests de servicio; `init.py` verde.
- **convivencia_08_boletin_pdf_convivencia** 🕓
  - Objetivo: `boletin_pdf.py` rellena la caja "OBSERVACIONES Y RECOMENDACIONES" (hoy vacía) con esos datos.
  - criterio_done: el PDF del boletín muestra comportamiento + observaciones; `init.py` verde.

### Fase 4 — Categorías + catálogo + promoción de Observaciones
- **convivencia_09_categorias_schema_seed** 🕓 *(toca BD → puerta de aprobación)*
  - Objetivo: tabla `categorias_observacion` (con `es_comportamental`) + modelo + repo + seed de categorías predefinidas.
  - criterio_done: existen categorías predefinidas legibles vía servicio; `init.py` verde.
- **convivencia_10_categorias_ui** 🕓
  - Objetivo: UI para que **coordinación/dirección** editen categorías (crear/editar/desactivar).
  - criterio_done: coordinador/director gestionan categorías desde la UI; `init.py` verde.
- **convivencia_11_observaciones_categoria_autz** 🕓 *(toca modelo/BD → puerta de aprobación)*
  - Objetivo: `observaciones_periodo` gana `categoria_id` y `origen`; la página de observaciones usa categorías; **autorización por objeto** (profesor con asignación en el grupo) y **eliminar el filtrado en cliente**.
  - criterio_done: crear observación exige categoría; solo profesores con asignación en el grupo acceden; visibilidad resuelta en servidor; `init.py` verde.
- **convivencia_12_catalogo_plantillas** 🕓 *(toca BD → puerta de aprobación)*
  - Objetivo: tabla `plantillas_observacion` + modelo + repo + seed; opción "usar plantilla" en el formulario de observación.
  - criterio_done: el profesor puede crear una observación desde una plantilla del catálogo; `init.py` verde.
- **convivencia_13_catalogo_retroalimentacion** 🕓
  - Objetivo: retroalimentar el catálogo — promover una observación libre a plantilla / sugerir las más usadas.
  - criterio_done: una observación libre puede convertirse en plantilla reutilizable; `init.py` verde.
- **convivencia_14_promocion_a_comportamiento** 🕓 *(toca modelo/BD → puerta de aprobación)*
  - Objetivo: `observaciones_periodo.registro_comportamiento_id`; acción "promover a comportamiento" para observaciones de categoría comportamental (crea `RegistroComportamiento` con trazabilidad).
  - criterio_done: promover una observación comportamental genera el registro y queda enlazada; `init.py` verde.

### Fase 5 — Seguimiento + alertas + dashboard
- **convivencia_15_alerta_seguimiento_schema** 🕓 *(toca modelo/BD/enum+CHECK → puerta de aprobación)*
  - Objetivo: `TipoAlerta.SEGUIMIENTO_REQUERIDO` (enum + CHECK de `alertas` y `configuracion_alertas`) + `alertas.usuario_destino_id` (destinatario profesor).
  - criterio_done: se puede crear/leer una alerta de seguimiento dirigida a un usuario; migración idempotente; `init.py` verde.
- **convivencia_16_alerta_manual** 🕓
  - Objetivo: creación manual de alerta de seguimiento (director/coordinador → profesor) desde la UI.
  - criterio_done: un directivo crea una alerta dirigida a un profesor; `init.py` verde.
- **convivencia_17_alerta_automatica_umbral** 🕓
  - Objetivo: generación automática por umbral configurable; **reemplazar el hack** actual de `PLAN_MEJORAMIENTO_VENCIDO` en `convivencia_service`.
  - criterio_done: al superar el umbral se genera la alerta de seguimiento (sin duplicar pendientes); el hack queda eliminado; `init.py` verde.
- **convivencia_18_vista_seguimiento_360** 🕓
  - Objetivo: página nueva "Seguimiento" (solo lectura) con notas académicas + comportamiento + observaciones + alertas del estudiante.
  - criterio_done: la vista 360° muestra el consolidado por estudiante con RBAC correcto; `init.py` verde.
- **convivencia_19_dashboard_alertas_seguimiento** 🕓
  - Objetivo: el dashboard (`inicio.py`) muestra las alertas de seguimiento dirigidas al profesor (reutilizar panel de alertas / "Tus pendientes").
  - criterio_done: el profesor ve en inicio las alertas de seguimiento que le fueron dirigidas; `init.py` verde.

## criterio_done (del roadmap)
Este documento existe como plan maestro aprobado; las specs de la **Fase 1** (convivencia_01..03) están redactadas y listas para la puerta de aprobación. Las fases 2–5 se expanden a `tasks.md` completos just-in-time, en orden, cada una respetando su puerta de aprobación cuando toque modelo/esquema.
