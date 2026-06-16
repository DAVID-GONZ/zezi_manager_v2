# Diseño: Robustez de contexto e integración del generador (paso_16b_generador_robustez)

> Depende de `paso_16a_fix_generador_timer` (el motor debe ejecutarse antes de
> poder integrar su resultado con la vista de horarios).

## 1. Archivos a modificar

- `src/interface/pages/academico/horario_generar.py`
  - Sustituir el guard rígido por derivación robusta de año/periodo.
  - Mostrar estados vacíos explicativos (sin año, sin periodo, sin plantilla).
  - Añadir acción «Ver en horarios» tras una generación válida.
- `src/interface/pages/academico/horarios.py`
  - Aceptar un parámetro de consulta opcional `escenario` para preseleccionar el
    escenario indicado al cargar la página.

**No se crean archivos nuevos. No se modifica `parrilla_widget.py` ni ningún
servicio.**

## 2. Métodos de Container a usar

- `Container.configuracion_service().get_activa()` → año lectivo activo (o `None`).
  Expone `.id`.
- `Container.periodo_service().get_activo(anio_id)` → periodo activo del año
  (o `None`). Alternativa de listado: `periodo_service().listar_por_anio(anio_id)`.
- `Container.infraestructura_service().listar_plantillas()` → lista de plantillas.
- `Container.infraestructura_service().listar_escenarios(anio_id)` → escenarios
  (ya usado por `horarios.py` para preseleccionar).
- `Container.generador_horario_service().generar(...)` y
  `Container.horario_service().datos_parrilla(...)` (sin cambios).

## 3. Derivación robusta de contexto (reemplaza el guard de horario_generar.py:82)

Patrón calcado del que ya usa `horarios.py:130` (que sí es robusto):

```python
# En vez de exigir ctx.anio_id / ctx.periodo_id del storage:
anio = Container.configuracion_service().get_activa()
if anio is None:
    _s["error_contexto"] = "No hay un año lectivo activo. Actívalo en Configuración."
    anio_id = periodo_id = None
else:
    anio_id = anio.id
    periodo = Container.periodo_service().get_activo(anio_id)
    if periodo is None:
        # fallback: primer periodo no cerrado, o el primero
        periodos = Container.periodo_service().listar_por_anio(anio_id)
        activos = [p for p in periodos if not getattr(p, "cerrado", False)]
        periodo = activos[0] if activos else (periodos[0] if periodos else None)
    periodo_id = periodo.id if periodo else None
    if periodo_id is None:
        _s["error_contexto"] = "No hay periodos en el año activo. Crea uno en Configuración."

# Preferir el contexto de sesión si ya viene fijado (no romper el flujo actual):
anio_id = ctx.anio_id or anio_id
periodo_id = ctx.periodo_id or periodo_id
```

El guard sólo redirige si el rol no tiene permiso (R7 deja de exigir grupo). La
ausencia de año/periodo/plantilla ya **no** redirige: se renderiza un estado
vacío explicativo (R2, R3, R4).

## 4. Estructura de estado `_s` (claves añadidas)

Sobre el `_s` existente en `horario_generar.py`, añadir:

```python
_s["anio_id"]         = anio_id          # int | None — derivado, no solo de ctx
_s["periodo_id"]      = periodo_id        # int | None — derivado, no solo de ctx
_s["error_contexto"]  = None             # str | None — mensaje de estado vacío
```

Todas las llamadas que hoy usan `ctx.periodo_id` / `ctx.anio_id` en este archivo
pasan a usar `_s["periodo_id"]` / `_s["anio_id"]`.

## 5. Refreshables y handlers — orden de definición

```
1. derivación de contexto (anio_id/periodo_id/error_contexto)   ← antes del render
2. _cargar_plantillas / _cargar_grupos / _cargar_configs
3. @ui.refreshable contenido_refreshable()                       ← ya existente
4. handlers (_generar_config, _activar_escenario, _ver_en_horarios, ...)
5. app_layout(...)
```

`contenido_refreshable` debe, al inicio, cortocircuitar con un `empty_state`
cuando `_s["error_contexto"]` no es `None`:

```python
@ui.refreshable
def contenido_refreshable() -> None:
    if _s["error_contexto"]:
        empty_state(icono=Icons.WARNING, titulo="No se puede generar todavía",
                    descripcion=_s["error_contexto"])
        return
    if not _s["plantillas"]:
        empty_state(icono=Icons.SCHEDULE, titulo="Sin plantillas horarias",
                    descripcion="Crea una plantilla horaria antes de configurar una generación.",
                    cta_label="Ir a plantillas horarias",
                    cta_on_click=lambda: ui.navigate.to("/admin/plantillas-franja"))
        return
    _render_lista()
    _render_detalle()
```

(R4: el CTA a plantillas es provisional; `paso_16c` lo sustituye por edición
embebida.)

## 6. Acción «Ver en horarios» (R5, R6)

En `_render_detalle()`, cuando la última corrida fue válida y existe
`resultado.escenario_id`, añadir junto a «Activar este escenario»:

```python
btn_secondary("Ver en horarios", icon="calendar_today",
              on_click=lambda eid=escenario_id: ui.navigate.to(f"/horarios?escenario={eid}"))
```

### Preselección en horarios.py (R6)

`horarios.py` ya preselecciona el escenario activo en `_cargar_escenarios()`.
Añadir lectura del query param para forzar la preselección del escenario recién
generado aunque no esté activo:

```python
from nicegui import context  # o app.storage.request — usar el patrón ya presente
# Tras _cargar_escenarios():
try:
    esc_q = context.client.request.query_params.get("escenario")
except Exception:
    esc_q = None
if esc_q:
    try:
        esc_id = int(esc_q)
        forzado = next((e for e in _s["escenarios"] if e.id == esc_id), None)
        if forzado:
            _s["escenario_sel"] = forzado
            _cargar_bloques_escenario()
    except (ValueError, TypeError):
        pass
```

El implementer debe verificar el modo exacto de leer query params disponible en
la versión de NiceGUI del proyecto (`ui.page` recibe el request; comprobar el
patrón ya usado en otras páginas antes de elegir API).

## 7. Manejo de errores

```python
try:
    anio = Container.configuracion_service().get_activa()
except Exception as exc:
    logger.error("Error derivando contexto del generador: %s", exc)
    _s["error_contexto"] = "No se pudo cargar el contexto académico."
```

Toda derivación de contexto va envuelta; un fallo se convierte en estado vacío
explicativo, nunca en redirección silenciosa ni en excepción sin capturar.

## 8. Alternativa descartada

Forzar al usuario a fijar año/periodo en el selector de contexto del topbar antes
de entrar. Se descarta porque rompe la experiencia (el usuario ya está en la
página) y porque `horarios.py` demuestra que la derivación automática desde
`configuracion_service().get_activa()` es suficiente y consistente.
