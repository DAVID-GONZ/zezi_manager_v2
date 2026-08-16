# convivencia_30_notas_lista_y_crea_observaciones — Spec

## Contexto

`notas_convivencia.py` (post `convivencia_24_notas_limpieza`) quedó reducida a
un grid editable de nota + `observacion_boletin`. La observación de boletín es
un texto corto asociado a la NOTA (`NotaComportamiento.observacion`), NO es una
`ObservacionPeriodo` — son entidades distintas y salen a boletín por caminos
distintos:

- `NotaComportamiento.observacion` → aparece como párrafo bajo la nota en el
  boletín (via `convivencia_boletin` → `nota_observacion`).
- `ObservacionPeriodo` con `es_publica=True` → aparece como viñetas en la
  sección de observaciones del boletín (via `convivencia_boletin` →
  `observaciones`).

David define que el director de curso (que es quien escribe la nota
consolidada del periodo) debe **poder ver desde Notas** las observaciones
públicas ya escritas por los profesores de asignatura de ese estudiante, y
**crear nuevas observaciones** desde aquí sin cambiar de módulo. Esto
consolida el flujo del boletín en una sola pantalla para el director de curso.

Esta spec revive parcialmente lo que `convivencia_24` retiró, pero con
delimitación clara para no volver a duplicar el módulo Observaciones:

- Notas mantiene grid de nota + observacion_boletin (dueño de la NOTA).
- Notas AÑADE un panel lateral/inferior con **dos sub-secciones claramente
  separadas** para el estudiante seleccionado (decisión de David 2026-08-12):
  1. **Observaciones individuales** — lista de `ObservacionPeriodo` del
     periodo (por asignatura), en solo lectura, con categoría, autor y flag
     `es_publica`. Es el material que se usa para armar el boletín.
  2. **Historial de convivencia** — lista de `RegistroComportamiento` del
     periodo (fortaleza, dificultad, compromiso, citación, descargo), en
     solo lectura, con fecha, tipo y descripción. Es el timeline de eventos
     puntuales, distinto de las observaciones narrativas.
  Las dos sub-secciones se rotulan explícitamente para que el director de
  curso entienda que son fuentes distintas.
- Notas AÑADE botón "Nueva observación" que usa el helper compartido
  `abrir_crear_observacion_dialog` (extraído en T3), aplicando el
  `NuevaObservacionDTO` a UN solo estudiante (el seleccionado en el grid),
  NO al multi-select — el módulo Observaciones sigue siendo el que gestiona
  la creación masiva.

Scope:
- `src/interface/pages/convivencia/notas_convivencia.py` (MODIFICAR)
- `src/interface/pages/convivencia/observaciones.py` (SIN cambios funcionales;
  este spec sí extrae los helpers de creación de observación a un módulo
  compartido — T3)
- `src/interface/design/components/` (posible componente `obs_list_readonly`
  si aporta reutilización)

## Requisitos (EARS)

- **R1** — La página DEBE conservar el grid editable de notas y la observación
  de boletín (comportamiento actual, gated a director de curso/coord/dir).
- **R2** — Al seleccionar UN estudiante en el grid, la página DEBE mostrar un
  panel con DOS sub-secciones claramente rotuladas:
  - "Observaciones individuales" — `ObservacionPeriodo` del periodo activo,
    ordenadas por fecha desc, con categoría, autor y flag público.
  - "Historial de convivencia" — `RegistroComportamiento` del periodo activo,
    ordenados por fecha desc, con fecha, tipo (display) y descripción.
  Cada sub-sección tiene su propio empty_state y su badge de conteo.
- **R3** — La página DEBE ofrecer un botón "Nueva observación" cuando hay UN
  solo estudiante seleccionado. Invoca el helper compartido
  `abrir_crear_observacion_dialog` (T3). El diálogo pide asignatura
  (dropdown de las asignaciones del grupo), categoría, texto y `es_publica`,
  y crea una única `ObservacionPeriodo`.
- **R4** — Con cero o >1 estudiantes seleccionados, las dos sub-secciones
  muestran empty_state ("Selecciona un estudiante") y el botón "Nueva
  observación" queda deshabilitado o oculto.
- **R5** — Notas NO DEBE ofrecer creación masiva multi-estudiante (esa es la
  responsabilidad de `observaciones.py`). Notas NO DEBE ofrecer eliminación
  ni promoción a plantilla/comportamiento (esas viven en Seguimiento).
  Notas NO DEBE ofrecer creación de RegistroComportamiento — el "historial"
  aquí es solo lectura; su creación vive en `observaciones.py` con RBAC.
- **R6** — Al crear una observación desde Notas, la sub-sección "Observaciones
  individuales" debe refrescarse sin recargar toda la página.

## Diseño

### Estado

Añadir a `_estado_inicial`:
- `sel_estudiante_id: int | None` (el único seleccionado; None si 0 o >1).
- `observaciones_estudiante: list[ObservacionPeriodo]` (individuales).
- `registros_estudiante: list[RegistroComportamiento]` (historial).
- `asignaciones_grupo: list` (cache para el dropdown del form; se carga al
  cambiar de grupo/periodo).

Añadir en `_estado_inicial` el mismo esqueleto para categorías/plantillas si
David decide permitir plantillas aquí (por defecto NO — Notas es express).

### Handlers

**`on_grid_selection`** (existente): además de guardar
`sel_estudiante_ids`, computar `sel_estudiante_id` = único id si `len==1`
sino `None`. Si cambió, llamar a `_cargar_convivencia_estudiante(_s)` y
refrescar solo el panel (nuevo `@ui.refreshable panel_convivencia()`).

**`_cargar_convivencia_estudiante(_s)`** — carga las dos fuentes:
```
if not _s["sel_estudiante_id"] or not _s["sel_periodo_id"]:
    _s["observaciones_estudiante"] = []
    _s["registros_estudiante"]     = []
    return
svc = Container.convivencia_service()
_s["observaciones_estudiante"] = svc.listar_observaciones(
    _s["sel_estudiante_id"], _s["sel_periodo_id"],
    usuario_id=ctx.usuario_id, usuario_rol=ctx.usuario_rol,
)
_s["registros_estudiante"] = svc.listar_registros(
    FiltroConvivenciaDTO(
        estudiante_id=_s["sel_estudiante_id"],
        periodo_id=_s["sel_periodo_id"],
    )
)
```
Nota:
- `listar_observaciones` ya filtra por rol de profesor a sus asignaciones;
  director/coordinador ve todas. Respeta RBAC sin código nuevo.
- `listar_registros` no expone hoy filtro por rol; el historial se muestra
  íntegro para el estudiante seleccionado. Si en el futuro se quiere gate
  por rol para el historial en Notas, se extiende el servicio, no la página.
- Importar `FiltroConvivenciaDTO` desde el servicio (no de dominio) siguiendo
  la regla de capas de `notas_convivencia.py`.

**`_cargar_asignaciones_grupo(_s)`** (invocado en `on_sel_change` tras cambiar
grupo/periodo):
```
_s["asignaciones_grupo"] = (
    Container.asignacion_service()
    .listar_por_grupo_periodo(_s["sel_grupo_id"], _s["sel_periodo_id"])
)
```
(Verificar nombre exacto del método; usar el existente si difiere.)

**`_abrir_crear_observacion()`**:
- Invoca `abrir_crear_observacion_dialog(estudiante_ids=[sel_id], ...)` del
  helper compartido (ver `Extracción compartida`).
- `on_success` recibe `(exitos, errores)` y llama
  `_cargar_convivencia_estudiante(_s)` + `panel_convivencia.refresh()`.

### Layout

`contenido()` pasa a un layout de dos secciones apiladas:

1. `panel_grid()` — grid editable de notas (arriba, sin cambios).
2. `panel_convivencia()` — panel del estudiante seleccionado, dividido en
   dos sub-secciones tituladas con `andes-card`:
   - **"Observaciones individuales"** — header con nombre del estudiante,
     contador (badge con `len(observaciones_estudiante)`) y botón "Nueva
     observación" (icono `add`) a la derecha; cuerpo: lista de `panel-card`
     por observación con `badge_*` para `es_publica`/`es_privada` y nombre
     de categoría.
   - **"Historial de convivencia"** — header con contador
     (`len(registros_estudiante)`); cuerpo: lista de filas
     `fecha · <badge tipo> · descripción` (sin botones — solo lectura).

Reutilizar `badge_*` para flags/tipos y `empty_state` cuando no hay selección
o cuando una sub-sección está vacía. Los dos sub-paneles son visualmente
distintos (fondos/bordes o iconografía) para reforzar la diferencia entre
observaciones (materia del boletín) e historial (timeline operativo).

### Extracción compartida (T3 — confirmada por David 2026-08-12)

El form de creación de observación individual es esencialmente el mismo que
en `observaciones.py`. Se extrae un helper reutilizable en:
`src/interface/pages/convivencia/_shared_observacion_form.py`:
```
def abrir_crear_observacion_dialog(
    *,
    ctx,
    estudiante_ids: list[int],           # 1 elemento desde notas, n desde observaciones
    periodo_id: int,
    asignaciones: list,                  # opciones para el selector de asignatura
    on_success: Callable[[int, int], None],   # (exitos, errores)
    plantilla_id: int | None = None,     # si viene, usa registrar_observacion_desde_plantilla
    texto_prefill: str = "",
    categoria_id_prefill: int | None = None,
) -> None: ...
```

Tanto `notas_convivencia.py` (llama con `estudiante_ids=[sel_estudiante_id]`)
como `observaciones.py` (llama con la lista completa del multi-select)
consumen el mismo helper. El helper encapsula:
- Construcción del `NuevaObservacionDTO`.
- Llamada a `registrar_observacion` o `registrar_observacion_desde_plantilla`
  según `plantilla_id`.
- Manejo de `PermissionError` / `ValueError` con toasts.
- Iteración por `estudiante_ids` y agregación de éxitos/errores.

Riesgo controlado: la refactorización de `observaciones.py` es solo cambiar
las llamadas internas — no cambia el contrato del `form_dialog` ni la firma
del servicio. Se cubre con los tests smoke de ambas páginas.

## Tareas

- **T1** — Estado + handlers: añadir `sel_estudiante_id`,
  `observaciones_estudiante`, `registros_estudiante`, `asignaciones_grupo` y
  la función `_cargar_convivencia_estudiante`.
- **T2** — Nuevo refreshable `panel_convivencia()` con las dos sub-secciones
  ("Observaciones individuales" + "Historial de convivencia") y el botón
  "Nueva observación" gated a selección única.
- **T3** — Extraer `abrir_crear_observacion_dialog` a
  `src/interface/pages/convivencia/_shared_observacion_form.py` y usarlo
  desde `observaciones.py` (multi) y `notas_convivencia.py` (uno).
- **T4** — Ajustar `on_sel_change` para cargar `asignaciones_grupo` al
  cambiar contexto y limpiar `observaciones_estudiante` +
  `registros_estudiante` cuando se pierde selección única.
- **T5** — Layout: apilado grid + panel dos sub-secciones, con `empty_state`
  por sub-sección.
- **T6** — Tests smoke de página (import, render sin datos, render con 1
  estudiante seleccionado); no se testea la UI aggrid.

## Verificación

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_design.py --file src/interface/pages/convivencia/notas_convivencia.py
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_imports.py --layer interface
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe init.py
```

Como director de curso:
1. Selecciono grupo y periodo → veo el grid de notas.
2. Selecciono UN estudiante → aparece el panel con dos sub-secciones:
   sus observaciones individuales del periodo y su historial de convivencia
   (registros) del periodo.
3. Botón "Nueva observación" → diálogo con asignatura del grupo, categoría,
   texto, es_publica → guardar → la sub-sección "Observaciones individuales"
   se refresca con la nueva; el "Historial de convivencia" no cambia.
4. Con 0 o >1 estudiantes → ambas sub-secciones muestran empty_state; botón
   deshabilitado.
5. Como profesor no-director del grupo: la sub-sección de observaciones
   filtra a sus asignaciones (RBAC en `listar_observaciones`); el historial
   se ve completo (registros son responsabilidad de dirección/coord — solo
   lectura); el grid queda en solo lectura (autz por objeto).

`check_design` y `init.py` verdes.

## Nota de política

Este spec **revierte parcialmente** `convivencia_24_notas_limpieza`. La
diferencia: aquí la creación es individual (por estudiante seleccionado, no
multi-select), y el listado es de solo lectura (sin acciones de gestión).
`observaciones.py` sigue siendo el módulo de creación masiva; Seguimiento
sigue siendo el hub de gestión (edición, promoción, eliminación).
