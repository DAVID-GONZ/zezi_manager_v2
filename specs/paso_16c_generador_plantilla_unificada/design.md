# Diseño: Plantilla integrada y robusta en el generador (paso_16c_generador_plantilla_unificada)

> Depende de `paso_16a` (motor operativo) y `paso_16b` (contexto robusto +
> integración). Este es el paso de mayor alcance estructural de los tres.

## 0. Decisión de arquitectura

La gestión de plantillas se **integra** en `/academico/generar-horario` como una
sección/pestaña, reutilizando los servicios que ya existen (no se crea lógica de
dominio nueva). La página `/admin/plantillas-franja` se **conserva intacta** como
acceso administrativo (R9): ambos consumen los mismos métodos de
`infraestructura_service`, así que no hay duplicación de lógica, sólo dos puntos
de entrada de UI a las mismas capacidades.

La página de generación pasa a tener tres zonas:

```
┌─ /academico/generar-horario ───────────────────────────────┐
│ [ Plantillas ] [ Configuraciones ] [ Resultado ]   (tabs)   │
│                                                             │
│  Plantillas:      lista + crear/editar/eliminar + preview   │
│  Configuraciones: lista + crear (elige o crea plantilla)    │
│  Resultado:       generar + métricas + incidencias + preview│
└─────────────────────────────────────────────────────────────┘
```

## 1. Archivos a modificar / crear

- `src/interface/pages/academico/horario_generar.py` — añadir la sección de
  plantillas (lista, alta, edición de franjas, preview, borrado con guardas) y el
  selector "elige o crea plantilla" en el diálogo de configuración.
- `src/interface/pages/academico/plantilla_editor_widget.py` *(nuevo)* — helper de
  interfaz reutilizable que renderiza el editor de franjas de una plantilla
  (formulario de plantilla + tabla de franjas) y su vista previa de rejilla. Lo
  consumen tanto el generador como, opcionalmente, `plantillas_franja.py` en un
  paso posterior (en este paso sólo lo usa el generador).

**No se modifica `parrilla_widget.py` (el renderizado de horarios funcional no se
toca). No se modifica ningún servicio ni modelo de dominio.**

## 2. Métodos de Container a usar (todos ya existentes)

Plantillas:
- `infraestructura_service().listar_plantillas()` → `list[PlantillaFranja]`.
- `infraestructura_service().crear_plantilla_simple(nombre, jornada, dias)` → plantilla.
- `infraestructura_service().guardar_franjas(plantilla_id, filas)` → int (reemplaza
  el conjunto de franjas; `filas` = dicts `{orden, hora_inicio, hora_fin, tipo, etiqueta}`).
- `infraestructura_service().listar_franjas(plantilla_id)` → `list[Franja]`.
- `infraestructura_service().activar_plantilla(plantilla_id)`.
- `infraestructura_service().eliminar_plantilla(plantilla_id)`.

Configuraciones (sin cambios respecto a hoy):
- `infraestructura_service().crear_config_generacion(nombre, periodo_id, anio_id, plantilla_id, grupos, pesos)`.
- `infraestructura_service().listar_configs_generacion(periodo_id)`.

Validación de "plantilla generable" (R5) y de "plantilla en uso" (R7) se calcula
en la interfaz a partir de los datos ya disponibles:
- R5: `listar_franjas(plantilla_id)` → existe alguna con `es_lectiva` True, y la
  plantilla tiene `dias_activos` no vacío.
- R7: una plantilla está en uso si algún `config` de
  `listar_configs_generacion(periodo_id)` tiene `plantilla_id == p.id`.

## 3. Estructura de estado `_s` (claves añadidas a horario_generar.py)

```python
_s["tab"]            = "configuraciones"   # "plantillas" | "configuraciones" | "resultado"
_s["plantilla_sel"]  = None                # PlantillaFranja en edición/preview
_s["franjas_sel"]    = []                  # list[Franja] de plantilla_sel
# (las claves de paso_16b: anio_id, periodo_id, error_contexto, ya presentes)
```

## 4. Editor de plantilla (nuevo widget) — contrato

`plantilla_editor_widget.py` expone:

```python
def render_plantilla_form(
    plantilla,                  # PlantillaFranja | None (None = creación)
    on_guardar_plantilla,       # Callable[[dict], None]  -> {nombre, jornada, dias}
) -> None: ...

def render_franjas_editor(
    franjas: list,              # list[Franja]
    on_guardar_franjas,         # Callable[[list[dict]], None]  -> filas para guardar_franjas
) -> None: ...

def render_plantilla_preview(
    plantilla,                  # PlantillaFranja
    franjas: list,              # list[Franja]
) -> None: ...   # rejilla franjas × dias_activos, marca lectiva/no lectiva
```

El editor de franjas reutiliza el patrón ya probado en
`plantillas_franja.py::_dialogo_franja` (tipo, orden, hora_inicio, hora_fin,
etiqueta) y produce `filas` con el shape que espera `guardar_franjas`. La
validación de solapes y orden de horas (R8) la aplica el dominio
(`NuevaFranjaDTO`/`Franja`); la UI sólo captura el `ValueError` y lo muestra.

## 5. Selector "elige o crea plantilla" en el diálogo de configuración (R3)

En `_config_dialog` de `horario_generar.py`, el `ui.select` de plantilla gana una
opción "➕ Crear plantilla nueva…" que, al elegirse, abre el editor de plantilla
(sección Plantillas) en modo creación; al guardar, vuelve al diálogo de
configuración con la nueva plantilla preseleccionada. Si no hay ninguna plantilla,
el diálogo de configuración guía directamente a crear una (en vez del toast
actual "ve a Ajustes → Plantillas horarias").

## 6. Refreshables y handlers — orden de definición

```
1. derivación de contexto (de paso_16b)
2. _cargar_plantillas / _cargar_franjas / _cargar_grupos / _cargar_configs
3. helpers de validación (_plantilla_generable, _plantilla_en_uso)
4. @ui.refreshable contenido_refreshable()      ← enruta según _s["tab"]
       ├─ _render_tab_plantillas()
       ├─ _render_tab_configuraciones()  (lista + detalle actuales)
       └─ _render_tab_resultado()
5. handlers de plantilla (_crear_plantilla, _guardar_franjas, _eliminar_plantilla, _preview_plantilla)
6. handlers de config y generación (ya existentes, de paso_16a/16b)
7. app_layout(...)
```

**Crítico (regla del proyecto):** todos los `@ui.refreshable` se declaran antes de
cualquier handler que invoque su `.refresh()`.

## 7. Guardas de borrado y de generación

```python
def _eliminar_plantilla(p):
    usos = [c for c in _s["configs"] if getattr(c, "plantilla_id", None) == p.id]
    if usos:
        nombres = ", ".join(getattr(c, "nombre", "?") for c in usos)
        toast_warning(f"No se puede eliminar: la usan las configuraciones: {nombres}")
        return
    confirm_dialog(titulo="Eliminar plantilla", variante="danger", ...,
                   on_confirm=lambda: _confirmar_eliminar_plantilla(p))

def _plantilla_generable(p) -> tuple[bool, str]:
    if not getattr(p, "dias_activos", None):
        return False, "La plantilla no tiene días activos."
    franjas = Container.infraestructura_service().listar_franjas(p.id)
    if not any(f.es_lectiva for f in franjas):
        return False, "La plantilla no tiene franjas lectivas."
    return True, ""
```

Antes de habilitar «Generar horario» (R5), se evalúa `_plantilla_generable` de la
plantilla de la config seleccionada; si es falso, el botón se deshabilita y se
muestra el motivo.

## 8. Manejo de errores

```python
try:
    Container.infraestructura_service().guardar_franjas(pid, filas)
    toast_success("Franjas guardadas")
    _cargar_franjas(); contenido_refreshable.refresh()
except ValueError as exc:        # solape / orden de horas / datos inválidos
    toast_warning(str(exc))
except Exception as exc:
    logger.error("Error guardando franjas: %s", exc)
    toast_error("No se pudieron guardar las franjas")
```

## 9. Alternativa descartada

Mover por completo la administración de plantillas dentro del generador y eliminar
`/admin/plantillas-franja`. Se descarta: rompería el acceso administrativo
existente (R9) y los bookmarks/menú actuales, y obligaría a migrar el editor en un
solo golpe. Integrar reutilizando los mismos servicios (un widget compartido) da
el mismo beneficio al usuario con mucho menor riesgo y sin duplicar dominio.

## 10. Nota de alcance / riesgo

Este paso **no toca el renderizado de la parrilla de horarios** (`parrilla_widget.py`
ni la sección unificada de `horarios.py`). Sólo añade UI de plantillas en el
generador y un widget nuevo. El estado funcional de la visualización de horarios
queda intacto.
