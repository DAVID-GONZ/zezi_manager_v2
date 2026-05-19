# Patrones canónicos — Capa de interfaz

> Extraídos de `inicio.py` y `registro_asistencia.py`.
> El implementer usa estos patrones como plantilla para todas las páginas nuevas.

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

## 2. Gestión de estado con `_s`

**Siempre un dict mutable**, nunca variables sueltas. Las closures de NiceGUI capturan por referencia — el dict permite mutación sin `nonlocal`.

```python
# ✅
_s: dict = {"registros": {}, "periodo_cerrado": False}
def handler():
    _s["registros"][id] = valor  # funciona

# ❌
periodo_cerrado = False
def handler():
    nonlocal periodo_cerrado   # frágil
    periodo_cerrado = True
```

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
except ValueError as exc:
    ui.notify(f"Error de validación: {exc}", type="warning")
except Exception as exc:
    logger.error("Error guardando nota: %s", exc, exc_info=True)
    ui.notify("Error al guardar. Intenta de nuevo.", type="negative")
```

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
