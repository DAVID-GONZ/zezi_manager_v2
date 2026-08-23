# Patrones canónicos — Capa de interfaz

> Extraídos de `inicio.py` y `registro_asistencia.py`.
> El implementer usa estos patrones como plantilla para todas las páginas nuevas.

---

## 0. Autorización central — la página NO se decora con `@ui.page`

Desde paso_35 la autorización es **deny-by-default y central**. La función de
página es una función normal (sin `@ui.page`) que se **registra** en `main.py`:

```python
# En main.py::registrar_rutas_ui()
from src.interface.auth import registrar_pagina, AUTENTICADO
from src.domain.models.usuario import Rol

registrar_pagina("/asistencia", registro_asistencia_page, roles=_AULA)
registrar_pagina("/inicio", inicio_page, roles=AUTENTICADO)
```

`registrar_pagina` envuelve la página con el guard que aplica **auth + rol**,
fuerza el cambio de contraseña si aplica (A2) y **sincroniza el contexto**
(`SessionContext.desde_storage()`) antes de renderizar. Por eso la página ya no
necesita su propio guard de redirección; sí puede leer el contexto para usarlo:

```python
def registro_asistencia_page() -> None:      # sin @ui.page
    ctx = SessionContext.desde_storage()      # el guard ya autorizó; aquí solo se lee
    _s = _estado_inicial()
    _cargar_estado(ctx, _s)
    # ...
```

El template de §1 conserva el patrón por compatibilidad, pero **el registro y la
autorización van por `registrar_pagina`**, no por un `@ui.page` con guard inline.

---

## 0.5. Presenter — view-model de la página (OBLIGATORIO con estado)

Toda página con estado mutable tiene un **presenter puro** que espeja la ruta de la
página: `pages/admin/salas.py` → `presenters/admin/salas_presenter.py`; página en la
raíz de `pages/` → presenter en la raíz de `presenters/`. Ver `docs/conventions.md`
§2 y §14.

El presenter contiene tres cosas y **nada de negocio**:

1. **Estado** (`self.estado`, el antiguo dict `_s`).
2. **Transiciones**: qué pasa al cambiar un selector — coerción a int, cascada de
   reseteos, flags. Nada de `nicegui`, nada de `Container`.
3. **Consultas/mapeos de vista**: `filtros_completos()`, `resumen(datos)` → tarjetas.
   Los NÚMEROS y umbrales de esos mapeos los calcula el **backend**; el presenter solo
   formatea (ver el split de referencia en `docs/conventions.md` §14).

```python
# src/interface/presenters/informes/estadisticos_presenter.py  (PURO — sin nicegui)
class EstadisticosPresenter:
    def __init__(self, tipos_map: dict) -> None:
        self._tipos = tipos_map
        self.estado: dict = estado_inicial()

    def set_grupo(self, grupo_id) -> None:          # transición
        self.estado["grupo_id"] = int(grupo_id) if grupo_id is not None else None
        self.estado["asignacion_id"] = None          # cascada de reseteo
        self._limpiar_datos()

    def filtros_completos(self) -> bool: ...          # consulta de vista pura
```

```python
# src/interface/pages/informes/estadisticos.py  (adaptador fino)
presenter = EstadisticosPresenter(_TIPOS_MAP)
_s = presenter.estado                                 # misma referencia
def on_grupo_change(grupo_id):
    presenter.set_grupo(grupo_id)                     # decisión → presenter
    _cargar_asignaciones(ctx, _s)                     # carga (Container) → página
    filtros_refreshable.refresh()                     # render/refresh → página
```

**Su test llama al presenter real** (no reimplementa la lógica): un
`tests/unit/interface/presenters/<...>_presenter.py` que instancia el presenter y
verifica transiciones y mapeos. Esto **mata las tautologías** (tests que copiaban la
lógica del handler y hacían assert sobre la copia). La guarda
`tests/unit/interface/presenters/test_presenters_puros.py` verifica que ningún
presenter importe `nicegui`.

**Páginas sin estado** (render puro, o helpers como `parrilla_widget.py`) NO llevan
presenter: se testean sus funciones puras directamente.

---

## 1. Estructura de un archivo de página

```python
"""
src/interface/pages/<modulo>/<nombre>.py
========================================
<Una línea de descripción>

Regla de capas:
  Esta página NO importa ningún símbolo de src.domain.models.*.
  Solo usa Container (servicios) e imports de la capa de interfaz.

Flujo:
  1. <paso 1>
  2. <paso 2>
  ...

Refreshables:
  <nombre>_refreshable()  — re-renderiza <qué>
"""
from __future__ import annotations

import logging
from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.theme import ThemeManager
from src.interface.design.tokens import Icons

logger = logging.getLogger("<NOMBRE_MODULO>")


# ── Constantes de UI ──────────────────────────────────────────────────────────
# Si la página usa ECharts, el bloque _EC_* va aquí
# _EC_PRIMARY = Colors.PRIMARY
# _EC_SUCCESS = Colors.SUCCESS

# ── Helpers ───────────────────────────────────────────────────────────────────
# Funciones puras de cálculo/formateo — sin NiceGUI, testeable en aislamiento


# ── Estado ────────────────────────────────────────────────────────────────────
def _estado_inicial() -> dict:
    return {
        "datos": [],
        "cargando": False,
        # ...
    }

def _cargar_estado(ctx: SessionContext, _s: dict) -> None:
    """Carga datos desde servicios. No lanza excepciones al exterior."""
    try:
        _s["datos"] = Container.<servicio>().<método>(...)
    except Exception as exc:
        logger.error("Error cargando datos: %s", exc)
        _s["datos"] = []


# ── Secciones de UI ───────────────────────────────────────────────────────────
def _<seccion>(_s: dict, ...) -> None:
    """Renderiza <qué>."""
    with ui.element("div").classes("<clase-contenedor>"):
        # ...


# ── Página ────────────────────────────────────────────────────────────────────
@ui.page("/<ruta>")
def <nombre>_page() -> None:
    # Guard
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    # Estado
    _s = _estado_inicial()
    _cargar_estado(ctx, _s)

    # Refreshables
    @ui.refreshable
    def <seccion>_refreshable() -> None:
        _<seccion>(_s)

    # Handlers
    def on_<accion>(...) -> None:
        # Mutar _s
        <seccion>_refreshable.refresh()

    # Contenido
    def contenido() -> None:
        with ui.element("div").classes("page-stack"):
            <seccion>_refreshable()

    # Layout
    app_layout(
        titulo_pagina="<Título>",
        usuario_nombre=ctx.usuario_nombre,
        usuario_rol=ctx.usuario_rol,
        ruta_activa="/<ruta>",
        contenido=contenido,
        ctx=ctx,
        on_context_change=on_context_change,  # solo si la página es sensible al contexto
    )


__all__ = ["<nombre>_page"]
```

---

## 2. Gestión de estado con `_s` — vía presenter

**Siempre un dict mutable**, nunca variables sueltas. Las closures de NiceGUI capturan por referencia — el dict permite mutación sin `nonlocal`.

**El dict lo posee un presenter** (ver §0.5). La página hace `_s = presenter.estado`
(misma referencia) para que `bind_value` y los `refreshables` sigan leyendo `_s`, y las
**transiciones** (mutaciones con lógica) pasan por métodos del presenter, no por
escritura directa en los handlers:

```python
# ✅ El estado lo posee el presenter; el handler llama a una transición
presenter = RegistroAsistenciaPresenter()
_s = presenter.estado
def on_estado(est_id, estado):
    presenter.marcar(est_id, estado)   # coerción/flag pendiente viven en el presenter
    grilla_refreshable.refresh()

# ❌ Lógica de estado embebida en el handler de la página
def on_estado(est_id, estado):
    _s["registros"][est_id] = estado
    _s["pendiente"] = True             # ← esto es view-state; va al presenter

# ❌ Variables sueltas
periodo_cerrado = False
def handler():
    nonlocal periodo_cerrado   # frágil
```

> La **carga de datos** (llamadas a `Container.*`) puede seguir escribiendo `_s[...]`
> en la página (o pasar por setters del presenter). Lo que NUNCA se queda en la página
> son las **decisiones de view-state** (coerción a int, cascadas de reseteo, flags,
> `filtros_completos`, mapeo a tarjetas): eso es el presenter.

---

## 3. Refreshables — granularidad

Una sección por `@ui.refreshable`. La regla: si el usuario puede desencadenar un cambio que afecta solo a esa sección, necesita su propio refreshable.

```python
@ui.refreshable
def stats_refreshable() -> None:
    """Solo los contadores — se refresca en cada cambio de estado individual."""
    _stats_panel(_s)

@ui.refreshable
def grilla_refreshable() -> None:
    """La tabla completa — se refresca en cambio de fecha o contexto."""
    _grilla(_s, on_estado=on_estado)
```

`ctx_refreshable` es opcional — usarlo solo si el panel de contexto es visible inline en la página (no aplica si el contexto solo está en el topbar).

---

## 4. Handlers — nombrados, nunca lambdas complejas

```python
# ✅ Handler nombrado — legible en el callback
def on_fecha_cambio(valor: str) -> None:
    try:
        _s["fecha"] = date.fromisoformat(valor)
    except ValueError:
        return
    _cargar_estado(ctx, _s)
    grilla_refreshable.refresh()

ui.input(on_change=lambda e: on_fecha_cambio(e.value))

# ❌ Lógica compleja inline
ui.input(on_change=lambda e: (
    setattr(_s, 'fecha', date.fromisoformat(e.value)),
    grilla_refreshable.refresh()
))
```

---

## 5. Pasar primitivos al servicio, recibir entidades

```python
# ✅ La página no importa EstadoAsistencia ni Asistencia
conteo = Container.asistencia_service().guardar_asistencia_masiva(
    grupo_id=ctx.grupo_id,
    fecha=_s["fecha"],
    lista=[
        {"estudiante_id": est.id, "estado": _s["registros"][est.id]}
        for est in _s["estudiantes"]
    ],
    usuario_id=ctx.usuario_id,
)

# ❌ La página construye DTOs de dominio
from src.domain.models.asistencia import RegistroAsistenciaDTO  # prohibido en páginas
dto = RegistroAsistenciaDTO(...)
```

---

## 6. Acceso a atributos de entidades — defensivo con getattr

Las entidades devueltas por los servicios pueden cambiar. En páginas, preferir `getattr` con valor por defecto para atributos que no son críticos:

```python
# ✅
nivel  = str(getattr(alerta, "nivel", "info")).lower()
tipo   = getattr(alerta, "tipo_alerta", "alerta")
tiempo = getattr(cambio, "timestamp", None)

# ✅ Atributos esenciales — acceso directo (falla explícito si el contrato cambia)
est.id
est.nombre_completo
periodo.cerrado
```

---

## 7. Manejo de errores — visible al usuario, silencioso en logs

```python
# ✅ Error esperado → ui.notify; error inesperado → log + ui.notify genérico
try:
    Container.evaluacion_service().guardar_nota(...)
    ui.notify("Nota guardada", type="positive", timeout=3000)
except OperacionSoloLecturaError:
    # Modo "Ver como" (impersonación admin): no se permiten cambios.
    ui.notify("Estás en modo solo lectura (Ver como).", type="warning")
except ValueError as exc:
    ui.notify(f"Error de validación: {exc}", type="warning")
except Exception as exc:
    logger.error("Error guardando nota: %s", exc, exc_info=True)
    ui.notify("Error al guardar. Intenta de nuevo.", type="negative")
```

> `OperacionSoloLecturaError` (de `src/services/solo_lectura.py`) hereda de
> `PermissionError` y la lanzan los mutadores de servicio cuando la sesión está
> impersonando en solo lectura. Captúrala **antes** que `ValueError`/`Exception`
> para dar un mensaje claro. Idealmente, la página además oculta/deshabilita los
> controles de edición cuando `ctx.solo_lectura` es `True`.

---

## 8. Periodo cerrado — modo solo lectura

Todas las páginas del módulo de evaluación y asistencia deben verificar cierre del periodo antes de renderizar controles de edición:

```python
def _cargar_estado(ctx, _s):
    try:
        periodo = Container.periodo_service().get_by_id(ctx.periodo_id)
        _s["periodo_cerrado"] = bool(getattr(periodo, "cerrado", False))
    except Exception as exc:
        logger.warning("No se pudo verificar cierre: %s", exc)
        _s["periodo_cerrado"] = False  # fallback seguro: permitir edición

# En la grilla de notas o asistencia:
if _s["periodo_cerrado"]:
    ui.element("div").classes("asis-banner-cerrado")  # banner visual
    # Renderizar en modo lectura — sin botones de edición
else:
    # Renderizar en modo edición
```

---

## 9. Confirm dialog para operaciones destructivas

Para cierres de periodo, eliminaciones y otras operaciones irreversibles:

```python
from src.interface.design.components.confirm_dialog import confirm_dialog

def on_cerrar_periodo() -> None:
    confirm_dialog(
        titulo="Cerrar periodo",
        mensaje="Esta acción es irreversible. ¿Confirmar cierre del periodo activo?",
        on_confirm=_ejecutar_cierre,
        variante="danger",
    )
```

---

## 10. ag-Grid editable — patrón de columnas dinámicas

Para la planilla de notas (columnas por actividad):

```python
column_defs = [
    {"field": "nombre_estudiante", "headerName": "Estudiante",
     "pinned": "left", "editable": False},
]
for actividad in actividades:
    column_defs.append({
        "field": f"act_{actividad.id}",
        "headerName": actividad.nombre,
        "editable": not _s["periodo_cerrado"],  # ← respeta cierre
        "cellClassRules": {
            "tablero-promedio-superior": "params.value >= 4.6",
            "tablero-promedio-alto":     "params.value >= 3.8",
            "tablero-promedio-basico":   "params.value >= 3.0",
            "tablero-promedio-riesgo":   "params.value < 3.0",
        },
    })

grid = ui.aggrid({
    "columnDefs": column_defs,
    "rowData": filas,
    "defaultColDef": {"resizable": True, "sortable": False},
})
```
