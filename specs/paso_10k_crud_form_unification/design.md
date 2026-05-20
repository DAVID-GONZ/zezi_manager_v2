# Diseño técnico — paso_10k_crud_form_unification

## Arquitectura de referencia

```
src/interface/design/components/
  base_form.py        ← MODIFICAR: nuevos tipos + "valor" pre-población
  form_dialog.py      ← CREAR: wrapper modal para base_form
  __init__.py         ← MODIFICAR: exportar form_dialog

src/interface/design/styles.css
  ← AÑADIR: .form-dialog-card, .form-dialog-title

src/interface/pages/admin/
  grupos.py           ← migrar _abrir_editar
  asignaturas.py      ← migrar _editar_area, _editar_asignatura
  asignaciones.py     ← migrar _abrir_crear_asignacion
  usuarios.py         ← migrar _abrir_crear_usuario, _cambiar_rol

src/interface/pages/academico/
  estudiantes.py      ← migrar _abrir_dialog_matricula, _abrir_dialog_edicion
  horarios.py         ← migrar _abrir_dialog_crear

src/interface/pages/evaluacion/
  configuracion_evaluacion.py ← migrar _editar_categoria
  habilitaciones.py           ← migrar _registrar_nota_dialog
  planilla_notas.py           ← migrar dialog nota
  planes_mejoramiento.py      ← migrar _cerrar_plan_dialog
```

---

## §1 — Extensión de `base_form()`

### Campo dict extendido (especificación completa)

```python
campo = {
    # Obligatorios
    "key":       str,          # clave en el dict de retorno

    # Opcionales con defaults
    "label":     str = key,    # label visible
    "tipo":      str = "text", # "text"|"select"|"textarea"|"password"|
                               # "number"|"checkbox"|"time"|"email"|"readonly"
    "valor":     Any = None,   # valor inicial (para modo edición)
    "requerido": bool = False, # muestra asterisco; base_form NO valida internamente
    "placeholder": str = "",
    "opciones":  dict | list = [],  # para tipo="select"
    "ref":       list = None,  # si se provee, widget se append a esta lista

    # Sólo para tipo="number"
    "min":    int | float = None,
    "max":    int | float = None,
    "step":   int | float = None,
    "format": str = None,       # ej: "%.2f"
}
```

### Nuevos bloques de renderizado en `base_form()`

Insertar después del bloque `elif tipo == "password"`:

```python
elif tipo == "number":
    widget = ui.number(
        label=label_text,
        value=campo.get("valor"),
        min=campo.get("min"),
        max=campo.get("max"),
        step=campo.get("step"),
        format=campo.get("format"),
    ).classes("andes-input w-full")

elif tipo == "checkbox":
    valor_inicial = campo.get("valor", False)
    widget = ui.checkbox(label_text, value=bool(valor_inicial))

elif tipo == "time":
    widget = (
        ui.input(label=label_text, value=campo.get("valor", ""))
        .props("type=time")
        .classes("andes-input w-full")
    )

elif tipo == "email":
    widget = (
        ui.input(label=label_text, placeholder=placeholder, value=campo.get("valor", ""))
        .props("type=email")
        .classes("andes-input w-full")
    )

elif tipo == "readonly":
    # No se añade a _valores — es solo display
    ui.label(str(campo.get("valor", ""))).classes("readonly-field-value text-sm text-grey-7")
    continue  # salta el append a _valores
```

### Pre-población en tipos existentes

Para los tipos ya existentes (`text`, `select`, `textarea`, `password`),
añadir el uso de `campo.get("valor")` donde corresponda:

```python
# text (antes: ui.input(label=label_text, ...))
widget = ui.input(
    label=label_text,
    placeholder=placeholder,
    value=campo.get("valor", ""),
).classes("andes-input w-full")

# select (antes: ui.select(options=opciones, label=label_text))
widget = ui.select(
    options=opciones,
    label=label_text,
    value=campo.get("valor"),
).classes("andes-input w-full")

# textarea (antes: ui.textarea(label=label_text, ...))
widget = ui.textarea(
    label=label_text,
    placeholder=placeholder,
    value=campo.get("valor", ""),
).classes("andes-input w-full")
```

---

## §2 — `form_dialog()` — implementación completa

```python
# src/interface/design/components/form_dialog.py
"""
form_dialog.py — Modal de formulario CRUD del design system Andes Minimal.
"""
from __future__ import annotations
from typing import Callable
from nicegui import ui
from src.interface.design.components.base_form import base_form


def form_dialog(
    titulo: str,
    campos: list[dict],
    on_submit: Callable[[dict], bool | None],
    texto_submit: str = "Guardar",
    on_cancelar: Callable | None = None,
    max_width: str = "max-w-md",
    columnas: int = 1,
) -> None:
    """
    Abre un diálogo modal con un formulario estandarizado del design system.

    Args:
        titulo:        Título del diálogo (cabecera visual del card).
        campos:        Lista de dicts de campo; ver base_form() para schema.
        on_submit:     Callback(datos: dict) → bool | None.
                       Return False para mantener el dialog abierto (error);
                       None / True para cerrarlo (éxito).
        texto_submit:  Etiqueta del botón de confirmación.
        on_cancelar:   Callback adicional al cerrar con Cancelar.
        max_width:     Clase Tailwind de ancho máximo (ej: "max-w-md", "max-w-lg").
        columnas:      Número de columnas del grid de campos.
    """
    with ui.dialog() as dlg, ui.card().classes(f"andes-card form-dialog-card {max_width}"):
        ui.label(titulo).classes("font-h3 form-dialog-title")

        def _cancelar():
            if on_cancelar:
                on_cancelar()
            dlg.close()

        def _submit(datos: dict):
            result = on_submit(datos)
            if result is not False:
                dlg.close()

        base_form(
            campos=campos,
            on_submit=_submit,
            texto_submit=texto_submit,
            texto_cancelar="Cancelar",
            on_cancelar=_cancelar,
            columnas=columnas,
        )

    dlg.open()


__all__ = ["form_dialog"]
```

---

## §3 — Patron de migración por dialog

### Patrón general

```python
# ──── ANTES ────────────────────────────────────────────────────────────────
def _abrir_editar(grupo: Grupo) -> None:
    with ui.dialog() as dlg, ui.card().classes("w-full max-w-md"):
        ui.label("Editar grupo").classes("text-lg font-bold mb-2")
        cod_inp = ui.input("Código", value=grupo.codigo).classes("w-full")
        grd_inp = ui.number("Grado", value=grupo.grado, min=1, max=13).classes("w-full")
        jor_sel = ui.select({v: k for k, v in _JORNADAS.items()},
                             value=..., label="Jornada").classes("w-full")
        cap_inp = ui.number("Capacidad", value=grupo.capacidad_maxima, min=1).classes("w-full")

        def _guardar_edicion() -> None:
            try:
                Container.infraestructura_service().actualizar_grupo(...)
                ui.notify(f"Grupo actualizado", type="positive")
                dlg.close()
                _cargar_estado(); tabla.refresh()
            except ValueError as exc:
                ui.notify(str(exc), type="warning")
            except Exception as exc:
                logger.error(...); ui.notify("Error...", type="negative")

        with ui.row().classes("gap-2 mt-4 justify-end"):
            btn_ghost("Cancelar", on_click=dlg.close)
            btn_primary("Guardar", on_click=_guardar_edicion)
    dlg.open()

# ──── DESPUÉS ──────────────────────────────────────────────────────────────
def _abrir_editar(grupo: Grupo) -> None:
    def _guardar(datos: dict) -> bool | None:
        try:
            Container.infraestructura_service().actualizar_grupo(
                grupo.id,
                codigo=datos["codigo"],
                grado=int(datos["grado"]),
                jornada=datos["jornada"],
                capacidad=int(datos["capacidad"]),
            )
            ui.notify(f"Grupo {datos['codigo']} actualizado", type="positive")
            _cargar_estado()
            tabla.refresh()
            # return None → dialog closes automatically
        except ValueError as exc:
            ui.notify(str(exc), type="warning")
            return False
        except Exception as exc:
            logger.error("Error al actualizar grupo: %s", exc)
            ui.notify("Error al actualizar el grupo", type="negative")
            return False

    form_dialog(
        titulo    = "Editar grupo",
        campos    = [
            {"key": "codigo",    "label": "Código *",   "tipo": "text",
             "valor": grupo.codigo,            "requerido": True},
            {"key": "grado",     "label": "Grado",      "tipo": "number",
             "valor": grupo.grado or 1,        "min": 1, "max": 13},
            {"key": "jornada",   "label": "Jornada",    "tipo": "select",
             "valor": ...,                     "opciones": {v: k for k, v in _JORNADAS.items()}},
            {"key": "capacidad", "label": "Capacidad",  "tipo": "number",
             "valor": grupo.capacidad_maxima,  "min": 1},
        ],
        on_submit    = _guardar,
        texto_submit = "Guardar",
        max_width    = "max-w-md",
        columnas     = 2,
    )
```

**Importación a añadir en cada página migrada:**
```python
from src.interface.design.components import form_dialog
```

---

## §4 — Tabla completa de migración

### `admin/grupos.py` — T1

| Campo | `key` | `tipo` | `valor` | extras |
|---|---|---|---|---|
| Código * | `"codigo"` | `"text"` | `grupo.codigo` | `requerido: True` |
| Grado | `"grado"` | `"number"` | `grupo.grado or 1` | `min:1, max:13` |
| Jornada | `"jornada"` | `"select"` | `jornada_val` | `opciones: {v:k for k,v in _JORNADAS.items()}` |
| Capacidad | `"capacidad"` | `"number"` | `grupo.capacidad_maxima` | `min:1` |

columnas=2, max_width="max-w-md"

---

### `admin/asignaturas.py` — T2a (`_editar_area`)

| Campo | `key` | `tipo` | `valor` |
|---|---|---|---|
| Nombre * | `"nombre"` | `"text"` | `area.nombre` |
| Código | `"codigo"` | `"text"` | `area.codigo or ""` |

columnas=1, max_width="max-w-md"

### `admin/asignaturas.py` — T2b (`_editar_asignatura`)

| Campo | `key` | `tipo` | `valor` | extras |
|---|---|---|---|---|
| Nombre * | `"nombre"` | `"text"` | `asig.nombre` | `requerido: True` |
| Código | `"codigo"` | `"text"` | `asig.codigo or ""` | |
| Área | `"area_id"` | `"select"` | `asig.area_id` | `opciones: {a.id: a.nombre for a in _s["areas"]}` |
| Horas semanales | `"horas_semanales"` | `"number"` | `asig.horas_semanales` | `min:1` |

columnas=2, max_width="max-w-md"

---

### `admin/asignaciones.py` — T3 (`_abrir_crear_asignacion`)

Opciones cargadas antes de abrir el dialog desde `_s["docentes"]`, `_s["grupos"]`, etc.

| Campo | `key` | `tipo` | extras |
|---|---|---|---|
| Docente * | `"usuario_id"` | `"select"` | `opciones: docentes_opts, requerido: True` |
| Grupo * | `"grupo_id"` | `"select"` | `opciones: grupos_opts, requerido: True` |
| Asignatura * | `"asignatura_id"` | `"select"` | `opciones: asigs_opts, requerido: True` |
| Periodo * | `"periodo_id"` | `"select"` | `opciones: periodos_opts, requerido: True` |

columnas=1, max_width="max-w-lg", texto_submit="Crear"

**Guard previo al `form_dialog()`:**
```python
if not docentes_opts or not grupos_opts or ...:
    ui.notify("...", type="warning"); return
```

---

### `admin/usuarios.py` — T4a (`_abrir_crear_usuario`)

| Campo | `key` | `tipo` | extras |
|---|---|---|---|
| Nombre completo * | `"nombre_completo"` | `"text"` | `requerido: True, placeholder: "Carlos López García"` |
| Nombre de usuario * | `"usuario"` | `"text"` | `requerido: True, placeholder: "c.lopez"` |
| Contraseña inicial | `"password"` | `"password"` | `placeholder: "dejar vacío = usa username"` |
| Rol | `"rol"` | `"select"` | `opciones: _ROLES_OPCIONES, valor: "profesor"` |
| Email | `"email"` | `"email"` | `placeholder: "usuario@institucion.edu.co"` |

columnas=2, max_width="max-w-lg", texto_submit="Crear"

Guard: `if not es_admin: ui.notify(...); return`

### `admin/usuarios.py` — T4b (`_cambiar_rol`)

| Campo | `key` | `tipo` | extras |
|---|---|---|---|
| Nuevo rol * | `"rol"` | `"select"` | `opciones: _ROLES_OPCIONES, valor: rol_actual, requerido: True` |

columnas=1, max_width="max-w-sm", texto_submit="Cambiar rol"

Guard: `if not es_admin: ui.notify(...); return`

---

### `academico/estudiantes.py` — T5a (`_abrir_dialog_matricula`)

| Campo | `key` | `tipo` | extras |
|---|---|---|---|
| Tipo documento | `"tipo_documento"` | `"select"` | `opciones: {"TI":"TI","CC":"CC","CE":"CE","NUIP":"NUIP"}, valor:"TI"` |
| Número documento * | `"numero_documento"` | `"text"` | `requerido: True` |
| Nombre * | `"nombre"` | `"text"` | `requerido: True` |
| Apellido * | `"apellido"` | `"text"` | `requerido: True` |
| Grupo | `"grupo_id"` | `"select"` | `opciones: {g.id: g.codigo for g in _s["grupos"]}` |
| Género | `"genero"` | `"select"` | `opciones: {None:"—","M":"Masculino","F":"Femenino","OTRO":"Otro"}` |
| Posee PIAR | `"posee_piar"` | `"checkbox"` | `valor: False` |

columnas=2, max_width="max-w-lg", texto_submit="Matricular"

### `academico/estudiantes.py` — T5b (`_abrir_dialog_edicion`)

| Campo | `key` | `tipo` | extras |
|---|---|---|---|
| Nombre * | `"nombre"` | `"text"` | `valor: est.nombre, requerido: True` |
| Apellido * | `"apellido"` | `"text"` | `valor: est.apellido, requerido: True` |
| Estado | `"estado"` | `"select"` | `opciones: {...}, valor: est.estado.value` |
| Grupo | `"grupo_id"` | `"select"` | `opciones: {g.id: g.codigo for g in _s["grupos"]}, valor: grupo_id_actual` |
| Género | `"genero"` | `"select"` | `opciones: {...}, valor: est.genero or None` |
| Posee PIAR | `"posee_piar"` | `"checkbox"` | `valor: est.posee_piar` |

columnas=2, max_width="max-w-lg"

---

### `academico/horarios.py` — T6 (`_abrir_dialog_crear`)

| Campo | `key` | `tipo` | extras |
|---|---|---|---|
| Asignación * | `"asignacion_id"` | `"select"` | `opciones: asig_opts, requerido: True` |
| Día * | `"dia"` | `"select"` | `opciones: {d.value: d.value for d in DiaSemana}, requerido: True` |
| Hora inicio | `"hora_inicio"` | `"time"` | `valor: "07:00"` |
| Hora fin | `"hora_fin"` | `"time"` | `valor: "07:55"` |
| Sala | `"sala"` | `"text"` | `valor: "Aula", placeholder: "Aula, Lab. Química..."` |

columnas=2, max_width="max-w-lg"

Guard: `if not asig_opts: ui.notify("..."); return`

---

### `evaluacion/configuracion_evaluacion.py` — T7 (`_editar_categoria`)

| Campo | `key` | `tipo` | extras |
|---|---|---|---|
| Nombre * | `"nombre"` | `"text"` | `valor: cat.nombre, requerido: True` |
| Peso (0.01–1.0) * | `"peso"` | `"number"` | `valor: cat.peso, min:0.01, max:1.0, step:0.01, format:"%.2f"` |
| Porcentaje actual | `"pct_info"` | `"readonly"` | `valor: f"{cat.peso_porcentaje:.1f}%"` |

columnas=1, max_width="max-w-md"

**Nota:** el campo `readonly` `pct_info` no aparece en `datos` del callback.
Se muestra solo para contexto visual.

---

### `evaluacion/habilitaciones.py` — T8 (`_registrar_nota_dialog`)

| Campo | `key` | `tipo` | extras |
|---|---|---|---|
| Info habilitación | `"hab_info"` | `"readonly"` | `valor: f"Tipo: {hab.tipo.value} | Estado: {hab.estado.value}"` |
| Nota (0–100) * | `"nota"` | `"number"` | `valor: 0.0, min:0.0, max:100.0, step:0.5, requerido: True` |
| Observación | `"observacion"` | `"text"` | `placeholder: "Opcional"` |

columnas=1, max_width="max-w-sm", texto_submit="Registrar nota"

---

### `evaluacion/planilla_notas.py` — T9 (dialog nota)

Localizar el dialog existente (probablemente usa `ui.number` para nota).

| Campo | `key` | `tipo` | extras |
|---|---|---|---|
| Nota (0–100) * | `"nota"` | `"number"` | `valor: 0.0, min:0.0, max:100.0, step:0.5, requerido: True` |

columnas=1, max_width="max-w-sm"

---

### `evaluacion/planes_mejoramiento.py` — T10 (`_cerrar_plan_dialog`)

| Campo | `key` | `tipo` | extras |
|---|---|---|---|
| Estado de cierre * | `"estado"` | `"select"` | `opciones: _ESTADOS_CIERRE, valor: EstadoPlanMejoramiento.CUMPLIDO.value, requerido: True` |
| Observación de cierre * | `"observacion"` | `"textarea"` | `placeholder: "Describa el resultado...", requerido: True` |

columnas=1, max_width="max-w-md", texto_submit="Cerrar plan"

**Validación en on_submit:**
```python
def _guardar_cierre(datos: dict) -> bool | None:
    obs = str(datos.get("observacion", "")).strip()
    if not obs:
        ui.notify("La observación es obligatoria", type="warning")
        return False
    ...
```

---

## §5 — CSS nuevo

```css
/* form_dialog.py */
.form-dialog-card {
  width: 100%;
  min-width: 320px;
}

.form-dialog-title {
  margin-bottom: var(--space-sm);
  padding-bottom: var(--space-sm);
  border-bottom: 1px solid var(--color-divider);
  color: var(--color-text-primary);
}

/* base_form — readonly field */
.readonly-field-value {
  background: var(--color-surface-alt);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: var(--space-xs) var(--space-sm);
  font-size: var(--font-size-body);
  color: var(--color-text-secondary);
}
```

---

## §6 — Orden de implementación

```
T0  →  base_form.py: nuevos tipos + "valor" en todos los tipos
T0b →  form_dialog.py: crear componente
T0c →  __init__.py: exportar form_dialog
T0d →  styles.css: .form-dialog-card, .form-dialog-title, .readonly-field-value

T1  →  grupos.py: _abrir_editar
T2  →  asignaturas.py: _editar_area + _editar_asignatura
T3  →  asignaciones.py: _abrir_crear_asignacion
T4  →  usuarios.py: _abrir_crear_usuario + _cambiar_rol
T5  →  estudiantes.py: _abrir_dialog_matricula + _abrir_dialog_edicion
T6  →  horarios.py: _abrir_dialog_crear
T7  →  configuracion_evaluacion.py: _editar_categoria
T8  →  habilitaciones.py: _registrar_nota_dialog
T9  →  planilla_notas.py: dialog nota
T10 →  planes_mejoramiento.py: _cerrar_plan_dialog

T11 →  python init.py + pytest + greps de verificación
```

---

## §7 — Verificación final

```bash
# Sin dialogs inline residuales (solo confirms y dialogs con lógica reactiva):
grep -rn "with ui.dialog() as dlg, ui.card" src/interface/pages/ --include="*.py"
# → debe retornar solo: cierre_periodo.py, cierre_anio.py, horarios._abrir_editar_*
#   (si existen dialogs complejos de editar horario con lógica reactiva)

# form_dialog adoptado:
grep -rln "form_dialog" src/interface/pages/
# → ≥11 archivos distintos

# Tests:
python init.py  # verde
pytest tests/ -q  # ≥607 passed, 0 failed
```
