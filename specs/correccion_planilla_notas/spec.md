# Spec — correccion_planilla_notas

## Módulo: Corrección de Planilla de Notas (`/evaluacion/planilla`)
**Versión:** 1.0 — 2026-05-21  
**Roles:** `profesor`, `coordinador`  
**Tipo:** Corrección funcional + mejora UX  
**Notación:** EARS (Event-Action-Response System)

---

## Diagnóstico de causas raíz

### Bug #1 — CRÍTICO: Planilla siempre vacía al entrar

**Síntoma:** La página carga mostrando "Sin datos de planilla para los selectores
actuales." aunque el usuario tiene contexto activo en el topbar.

**Causa:** El estado `_s` inicializa `asignacion_id=None` y `periodo_id=None`.
La función `_cargar_datos_asignacion()` retorna tempranamente cuando alguno es
`None`, dejando `_s["planilla"] = []`. El `SessionContext` (`ctx`) ya contiene
`ctx.asignacion_id` y `ctx.periodo_id` seleccionados por el context chip del
topbar, pero la página **nunca los lee**.

```python
# ESTADO ACTUAL (roto)
_s: dict = {
    "asignacion_id": None,   # ← nunca se inicializa desde ctx
    "periodo_id":    None,   # ← nunca se inicializa desde ctx
    ...
}

# CORRECCIÓN
_s: dict = {
    "asignacion_id": ctx.asignacion_id,   # ← leer del context
    "periodo_id":    ctx.periodo_id,       # ← leer del context
    "grupo_id":      ctx.grupo_id,
    ...
}
_cargar_datos_asignacion()   # llamar inmediatamente con valores del ctx
```

---

### Bug #2 — CRÍTICO: `registrar_nota` falla silenciosamente

**Síntoma:** El diálogo de nota se cierra sin guardar. La nota nunca aparece
en la planilla.

**Causa:** La llamada actual pasa `ctx=None`:
```python
Container.evaluacion_service().registrar_nota(dto, ctx=None)
```
El método `registrar_nota` llama internamente a
`self._verificar_periodo_abierto(ctx.periodo_id)`, lo que lanza
`AttributeError: 'NoneType' object has no attribute 'periodo_id'`.
Este error es capturado por el `except Exception` genérico y logeado,
pero nunca visible al usuario.

**Corrección:**
```python
Container.evaluacion_service().registrar_nota(
    dto,
    ctx=ctx.to_contexto_academico(),
    usuario_id=ctx.usuario_id,
)
```

---

### Bug #3 — FUNCIONAL: Sin gestión de categorías en la UI

**Síntoma:** El profesor no puede crear categorías (Examen, Taller, etc.) con
sus pesos. Sin categorías, no puede crear actividades. La planilla permanece vacía.

**Causa:** La vista "Actividades" tiene un formulario para actividades pero NO
para categorías. El legacy (`notas.py`) tenía columna 1 = Categorías,
columna 2 = Actividades en el mismo acordeón.

**Corrección:** Revisar si es necesario y funcional agregar panel de gestión de categorías o estas se deben seguir gestionando en configuracion_evaluacion.py(ver §3.2).

---

### Problema de arquitectura — Selectores duplicados

**Síntoma:** La página tiene sus propios `ui.select` para Periodo y Asignación,
independientes del context chip del topbar. El usuario debe seleccionar dos veces
(topbar + página). Al cambiar el contexto en el topbar, la página recarga pero
los selectores internos vuelven a `None`.

**Corrección:** Eliminar los selectores internos de Periodo y Asignación.
La página lee exclusivamente desde `ctx`. Si el contexto está incompleto,
mostrar estado vacío con hint.

---

## Arquitectura objetivo

```
/evaluacion/planilla
├── [Panel de contexto]                ← solo si ctx incompleto: banner de advertencia
│
├── [Panel de configuración — acordeón]  ←  solo si consideras adecuada esta implementación
│   ├── Columna A: Categorías (CRUD)
│   └── Columna B: Actividades (CRUD)
│
└── [Panel de planilla / ag-Grid]      ← con selector de vista
    ├── Vista "Planilla"   → ag-Grid con edición inline de notas
    └── Vista "Actividades" → lista con estado y acciones
```

---

## Requisitos funcionales

### R0 — Contexto de sesión como única fuente de verdad

**R0.1** WHEN la página carga, THE SYSTEM SHALL leer `ctx.asignacion_id`,
`ctx.periodo_id` y `ctx.grupo_id` para inicializar `_s` y llamar
`_cargar_datos_asignacion()` inmediatamente.

**R0.2** IF `ctx.asignacion_id is None OR ctx.periodo_id is None`,
THE SYSTEM SHALL mostrar un banner de estado vacío:
```
⚠️ Contexto incompleto
Selecciona un periodo y asignación en el menú de contexto superior.
```
con la clase `tablero-empty` + `tablero-empty-hint`. No renderizar planilla.

**R0.3** THE SYSTEM SHALL eliminar los selectores internos de Periodo y Asignación.
Solo mantener el selector de Vista (Planilla / Actividades).

**R0.4** `on_context_change` sigue siendo `ui.navigate.reload()`. Correcto — el
reload carga el nuevo ctx desde storage y `_s` se inicializa con los valores
actualizados.

---

### R1 — Estado mutable corregido

```python
def _estado_inicial(ctx: SessionContext) -> dict:
    return {
        "asignacion_id":   ctx.asignacion_id,
        "periodo_id":      ctx.periodo_id,
        "grupo_id":        ctx.grupo_id,
        "categorias":      [],
        "actividades":     [],
        "planilla":        [],   # list[ResultadoEstudianteDTO]
        "modo":            "planilla",
        # form nueva categoría
        "cat_nombre":      "",
        "cat_peso":        30.0,   # en porcentaje (0-100)
        # form nueva actividad
        "act_nombre":      "",
        "act_categoria_id": None,
        "act_valor_max":   100.0,
    }
```

---

### R2 — Carga de datos corregida

**R2.1** `_cargar_datos_asignacion()` llama al servicio solo si ambos
`_s["asignacion_id"]` y `_s["periodo_id"]` son no-None.

**R2.2** Llamadas de servicio:
```python
svc = Container.evaluacion_service()
_s["categorias"]  = svc.listar_categorias(_s["asignacion_id"], _s["periodo_id"])
_s["actividades"] = svc.listar_actividades(_s["asignacion_id"], _s["periodo_id"])
_s["planilla"]    = svc.obtener_planilla(
    _s["asignacion_id"],
    _s["periodo_id"],
    ctx=ctx.to_contexto_academico(),   # ← CORRECCIÓN Bug #2
)
```

---

### R3 — Panel de categorías (nuevo)

**R3.1** WHEN la vista "Actividades" está activa, THE SYSTEM SHALL mostrar
un acordeón con dos columnas: Categorías (izquierda) y Actividades (derecha).

**R3.2** Sección de Categorías:
- Listar categorías existentes con nombre y peso (ej. "Examen — 40%")
- Botón editar (abre diálogo con `nombre` + `peso %`)
- Botón eliminar (con advertencia: "Se eliminarán sus actividades y notas")
- Formulario agregar: `nombre` + `peso %` + botón Agregar

**R3.3** WHEN el usuario agrega/edita una categoría, THE SYSTEM SHALL llamar:
```python
# Agregar
svc.agregar_categoria(
    NuevaCategoriaDTO(
        nombre=nombre,
        peso=peso_pct / 100.0,   # convertir a decimal
        asignacion_id=_s["asignacion_id"],
        periodo_id=_s["periodo_id"],
    ),
    ctx=ctx.to_contexto_academico(),
    usuario_id=ctx.usuario_id,
)

# Actualizar
svc.actualizar_categoria(
    cat_id=cat.id,
    dto=ActualizarCategoriaDTO(nombre=nombre, peso=peso_pct / 100.0),
    usuario_id=ctx.usuario_id,
)

# Eliminar
svc.eliminar_categoria(cat_id=cat.id, usuario_id=ctx.usuario_id)
```

**R3.4** IF el servicio lanza `ValueError` (suma de pesos > 100%, periodo
cerrado, etc.), THE SYSTEM SHALL mostrar `ui.notify` de tipo `warning` con el
mensaje exacto de la excepción.

**R3.5** Mostrar la suma actual de pesos en el encabezado de la sección:
`f"Categorías — Total: {suma_pesos_pct:.0f}%"`. Si la suma es 100%, indicar
con color verde. Si es menor, indicar con color naranja.

---

### R4 — Planilla con ag-Grid e edición inline

**R4.1** WHEN `_s["modo"] == "planilla"`, THE SYSTEM SHALL renderizar un
`ui.aggrid` en lugar de la tabla HTML actual.

**R4.2** Estructura de columnas del ag-Grid:

| Columna | `field` | Editable | Notas |
|---|---|---|---|
| Estudiante | `nombre_completo` | No | Pinned left, width 220 |
| [Por cada categoría → grupo de columnas children] | | | |
| — [Por cada actividad de la cat.] | `act_{act_id}` | Sí, si publicada y periodo abierto | width 80 |
| — PROM cat. | `cat_avg_{cat_id}` | No | width 70, calculado |
| Definitiva | `definitiva` | No | Pinned right, width 80 |

**R4.3** Construcción de `rowData`: para cada `ResultadoEstudianteDTO` en
`_s["planilla"]` construir un dict plano:
```python
{
    "estudiante_id":     resultado.estudiante_id,
    "nombre_completo":   resultado.nombre_completo,
    # Una clave por actividad:
    f"act_{act.id}": resultado.notas.get(act.id),
    # Una clave por promedio de categoría — calcular desde las notas:
    f"cat_avg_{cat.id}": _calcular_promedio_cat(resultado.notas, acts_de_cat),
    "definitiva":        resultado.definitiva,
}
```

**R4.4** Color de celdas por rango (aplicar con `cellClassRules` globales):
```python
{
    "grade-bajo":     "x != null && x < 60",
    "grade-basico":   "x != null && x >= 60 && x < 80",
    "grade-alto":     "x != null && x >= 80 && x < 90",
    "grade-superior": "x != null && x >= 90",
}
```
Los estilos `grade-bajo`, `grade-basico`, `grade-alto`, `grade-superior`
deben estar definidos en `styles.css` (reutilizar del legacy).

**R4.5** Opciones del ag-Grid:
```python
{
    "columnDefs": col_defs,
    "rowData": row_data,
    "defaultColDef": {"sortable": True, "resizable": True},
    "singleClickEdit": True,
    "stopEditingWhenCellsLoseFocus": True,
}
```

**R4.6** WHEN el usuario edita una celda (`cellValueChanged`), THE SYSTEM SHALL:
1. Verificar que el `field` empieza con `act_` → extraer `act_id`.
2. Verificar que el valor es numérico y está entre 0 y 100. Si no → `ui.notify` warning + recargar grid.
3. Si el valor está vacío (`""` / `None`) → borrar la nota (`Container.evaluacion_service()` no tiene método delete-nota directo; usar `registrar_nota` con valor 0 o el repo directamente; **ver nota de implementación**).
4. Construir `RegistrarNotaDTO(estudiante_id, actividad_id, valor, usuario_registro_id=ctx.usuario_id)`.
5. Llamar `Container.evaluacion_service().registrar_nota(dto, ctx=ctx.to_contexto_academico(), usuario_id=ctx.usuario_id)`.
6. IF ok → recalcular el promedio de categoría y la definitiva de esa fila en el ag-Grid (actualizar rowData en memoria + llamar `grid.run_row_method()`).
7. IF excepción → `ui.notify` tipo `negative` con el mensaje.

> **Nota de implementación (celda vacía):** Si el implementer encuentra que
> `EvaluacionService` no tiene `eliminar_nota()`, puede guardar un valor `None`
> o simplemente no actualizar cuando el campo queda vacío. Documentar la decisión
> en el progress file.

**R4.7** WHEN `_periodo_abierto() == False`, THE SYSTEM SHALL:
- Mostrar un banner `🔒 Período CERRADO — Modo solo lectura` sobre la planilla.
- Deshabilitar la edición inline (todas las columnas `act_*` con `editable: False`).
- No registrar el listener `cellValueChanged`.

**R4.8** Verificación de periodo abierto:
```python
def _periodo_abierto() -> bool:
    per_id = _s["periodo_id"]
    if not per_id:
        return False
    for p in _s["periodos"]:
        if p.id == per_id:
            estado_val = p.estado.value if hasattr(p.estado, "value") else str(p.estado)
            return estado_val not in ("cerrado", "closed")
    return True  # si no encontrado, asumir abierto
```

---

### R5 — Gestión de actividades (mantener, mejorar integración)

**R5.1** La vista de actividades sigue funcionando igual que el código actual,
con una corrección: `agregar_actividad` requiere que haya categorías. Si
`_s["categorias"]` está vacío → mostrar `"⚠️ Crea categorías primero"`.

**R5.2** El formulario de nueva actividad usa:
```python
svc.agregar_actividad(dto, usuario_id=ctx.usuario_id)
```
(el `agregar_actividad` del servicio NO requiere ctx — correcto).

---

### R6 — Refreshables

Tres `@ui.refreshable`:
- `panel_categorias_actividades()` — contiene el acordeón con categorías + actividades
- `vista_planilla()` — ag-Grid (existente, re-implementar)
- `_header_contexto()` — opcional: chip con info del contexto activo (asignación + periodo)

No hay `contenido_actividades` separado del acordeón: el acordeón reemplaza
la vista "Actividades" actual.

---

### R7 — Modo de vista

**R7.1** Mantener el selector de Vista (Planilla / Actividades/Config) con
`ui.select(_MODOS)` pero renombrar la clave `"actividades"` a `"config"` y el
label a `"Configuración"` para mayor claridad.

**R7.2** Cuando el usuario cambia de vista → refresh del refreshable correspondiente.

---

## Imports necesarios

```python
from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.tokens import Icons
from src.interface.design.components.buttons import (
    btn_primary, btn_danger, btn_ghost, btn_icon
)
from src.interface.design.components import status_badge, form_dialog
from src.services.evaluacion_service import (
    NuevaActividadDTO,
    RegistrarNotaDTO,
    EstadoActividad,
)
from src.domain.models.evaluacion import (
    NuevaCategoriaDTO,
    ActualizarCategoriaDTO,
)
```

> DTOs de `src.domain.models.evaluacion` son permitidos como excepción de
> anti-corrupción (son structs sin lógica de dominio, definidos en el shared kernel).

---

## CSS requerido — añadir a `styles.css`

Agregar las clases de color de celda para ag-Grid al final del archivo
(o verificar si ya existen antes de agregar):

```css
/* Planilla de notas — colores de desempeño en ag-Grid */
.ag-theme-quartz .grade-bajo     { background-color: #fee2e2 !important; color: #DC2626; !important; }
.ag-theme-quartz .grade-basico   { background-color: #fef3c7 !important; color: #FFCB47; !important; }
.ag-theme-quartz .grade-alto     { background-color: #dbeafe !important; color: #0284C7; !important; }
.ag-theme-quartz .grade-superior { background-color: #dcfce7 !important; color: #47FF59 !important; }
```

---

## Archivos a modificar

| Archivo | Cambio |
|---|---|
| `src/interface/pages/evaluacion/planilla_notas.py` | Corrección completa (reescritura parcial) |
| `src/interface/design/styles.css` | Agregar clases `grade-*` para ag-Grid si no existen |

No se requieren cambios en servicios, repositorios ni domain models.

---

## Tests de aceptación

**T1** La página carga inmediatamente con datos si `ctx.asignacion_id` y
`ctx.periodo_id` son no-nulos.

**T2** La página muestra el banner de contexto incompleto si alguno de esos
campos es `None`.

**T3** Al cambiar el contexto desde el topbar, el reload recarga la planilla
con los nuevos valores sin mostrar el estado vacío (asumiendo contexto completo).

**T4** Un profesor con categorías y actividades creadas ve la planilla con
columnas agrupadas por categoría.

**T5** Editar una celda de nota en ag-Grid guarda la nota correctamente
(verificar en DB que la nota existe).

**T6** Intentar editar una nota con período cerrado → no se llama al servicio,
banner de solo lectura visible.

**T7** Agregar una categoría con peso que supere el 100% → `ui.notify` de
error con el mensaje del servicio.

**T8** Agregar una actividad sin haber creado categorías → mensaje de advertencia.

**T9** La suma de pesos en el encabezado de Categorías refleja el total actual.

**T10** `pytest -x -q` pasa sin regresiones (607+ tests).

---

## Referencia al legacy

Del archivo `app/gestor_docente/src/pages/notas.py` se toman como referencia:

| Patrón del legacy | Adaptación en v2 |
|---|---|
| `refresh_grid()` como función que reconstruye rowData | `vista_planilla.refresh()` con `@ui.refreshable` |
| ag-Grid `singleClickEdit` + `cellValueChanged` | Igual en v2 |
| Columnas agrupadas por categoría con `children` | Igual en v2 |
| `color_rules` con `cellClassRules` | Igual en v2 con clases CSS en lugar de inline |
| Validación de rango 0-100 en `on_edit` | `on_cell_edit` en v2 |
| `ContextBar` con callback | Context chip del topbar con `on_context_change → reload()` |
| `_periodo_esta_cerrado()` + banner amber | `_periodo_abierto()` + banner CSS |
| Acordeón con Categorías + Actividades en columnas | Panel `panel_categorias_actividades` |

**NO se traslada del legacy:**
- `puntos_extra` (positivos/negativos) — no está en el schema v2 o es feature separada
- `from src.db import fetch_df, execute` — violación de arquitectura v2
- `from src.state import AppState` — reemplazado por `SessionContext`
- `from src.audit import registrar_cambio` — la auditoría la hace el servicio internamente
- `guardar_cierre()` como botón manual — en v2 el cierre es un paso separado en `cierre_periodo.py`
- Estilos inline `ui.add_head_html(...)` — usar clases CSS del design system

---

*Spec listo para ejecución. Paso: `correccion_planilla_notas`.*
