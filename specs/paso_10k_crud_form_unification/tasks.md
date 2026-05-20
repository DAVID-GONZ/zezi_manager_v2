# Tasks — paso_10k_crud_form_unification

## Resumen de tareas

| ID | Descripción | Archivos | Verificación |
|---|---|---|---|
| T0 | Extender `base_form()` + crear `form_dialog()` + CSS | base_form.py, form_dialog.py, __init__.py, styles.css | R1–R6 |
| T1 | Migrar `admin/grupos.py` | grupos.py | 0 inline dialogs |
| T2 | Migrar `admin/asignaturas.py` (×2) | asignaturas.py | 0 inline dialogs |
| T3 | Migrar `admin/asignaciones.py` | asignaciones.py | 0 inline dialogs |
| T4 | Migrar `admin/usuarios.py` (×2) | usuarios.py | 0 inline dialogs |
| T5 | Migrar `academico/estudiantes.py` (×2) | estudiantes.py | 0 inline dialogs |
| T6 | Migrar `academico/horarios.py` | horarios.py | 0 inline dialogs |
| T7 | Migrar `evaluacion/configuracion_evaluacion.py` | configuracion_evaluacion.py | 0 inline dialogs |
| T8 | Migrar `evaluacion/habilitaciones.py` | habilitaciones.py | 0 inline dialogs |
| T9 | Migrar `evaluacion/planilla_notas.py` | planilla_notas.py | 0 inline dialogs |
| T10 | Migrar `evaluacion/planes_mejoramiento.py` | planes_mejoramiento.py | 0 inline dialogs |
| T11 | Verificación final | — | R7 |

---

## T0 — Extender base_form + crear form_dialog

**Prerequisito:** ninguno.

### T0a — `src/interface/design/components/base_form.py`

**Lee el archivo completo antes de editar.**

1. Agregar soporte de `"valor"` para pre-poblar widgets en los tipos ya existentes:
   - `"text"`: `value=campo.get("valor", "")`
   - `"select"`: `value=campo.get("valor")`
   - `"textarea"`: `value=campo.get("valor", "")`
   - `"password"`: `value=campo.get("valor", "")`

2. Agregar los nuevos tipos de campo (insertar en el bloque `if/elif` de tipos):
   - `"number"`: `ui.number(label=label_text, value=campo.get("valor"), min=campo.get("min"), max=campo.get("max"), step=campo.get("step"), format=campo.get("format")).classes("andes-input w-full")`
   - `"checkbox"`: `ui.checkbox(label_text, value=bool(campo.get("valor", False)))`
   - `"time"`: `ui.input(label=label_text, value=campo.get("valor", "")).props("type=time").classes("andes-input w-full")`
   - `"email"`: `ui.input(label=label_text, placeholder=placeholder, value=campo.get("valor", "")).props("type=email").classes("andes-input w-full")`
   - `"readonly"`: `ui.label(str(campo.get("valor", ""))).classes("readonly-field-value text-sm")` + `continue` (no añadir a `_valores`)

**Nota sobre `number` con `None` values:** `ui.number` en NiceGUI acepta `None` para `min`, `max`, `step` — simplemente los ignora. Verificar que el comportamiento es correcto o filtrar con: `min=campo.get("min") if campo.get("min") is not None else None`

**Verificación T0a:**
```bash
grep -n "def stat_card\|\"number\"\|\"checkbox\"\|\"time\"\|\"email\"\|\"readonly\"" src/interface/design/components/base_form.py
# → debe mostrar las 5 ramas nuevas
```

### T0b — Crear `src/interface/design/components/form_dialog.py`

Crear el archivo completo según design.md §2. Ver la implementación exacta en ese documento.

**Verificación T0b:**
```bash
python -c "from src.interface.design.components import form_dialog; print('OK')"
# → OK
```

### T0c — Actualizar `src/interface/design/components/__init__.py`

Agregar:
```python
from .form_dialog import form_dialog
```
Y en `__all__`:
```python
"form_dialog",
```

### T0d — Agregar CSS en `src/interface/design/styles.css`

Agregar en la sección de components (junto a `.base-form-card`):
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

/* base_form — campo readonly */
.readonly-field-value {
  background: var(--color-surface-alt);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: var(--space-xs) var(--space-sm);
  font-size: var(--font-size-body);
  color: var(--color-text-secondary);
  display: block;
  width: 100%;
}
```

---

## T1 — `admin/grupos.py`

**Agregar import:**
```python
from src.interface.design.components import form_dialog
```

**Migrar `_abrir_editar(grupo: Grupo)`:**

Ver design.md §3 para el patrón completo. La función `_guardar_edicion()` se extrae
como `_guardar_edicion_grupo(datos: dict) -> bool | None` dentro de `_abrir_editar()`.

Campos: `codigo`(text,req), `grado`(number,1-13), `jornada`(select), `capacidad`(number,min=1)

Para el campo `jornada`, el valor pre-población es:
```python
"valor": grupo.jornada.value if hasattr(grupo.jornada, "value") else str(grupo.jornada)
```

**Verificación:**
```bash
grep -n "with ui.dialog" src/interface/pages/admin/grupos.py
# → solo debe aparecer UNA vez: el de _eliminar_grupo (confirm_dialog llama dlg internamente)
# → 0 veces en _abrir_editar
```

---

## T2 — `admin/asignaturas.py`

**Agregar import:** `form_dialog`

**Migrar `_editar_area(area: AreaConocimiento)`:**
Campos: `nombre`(text,req), `codigo`(text), columnas=1, max_width="max-w-md"

Handler:
```python
def _guardar(datos: dict) -> bool | None:
    try:
        nombre = str(datos["nombre"]).strip()
        if not nombre:
            ui.notify("El nombre es obligatorio", type="warning"); return False
        area_act = AreaConocimiento(id=area.id, nombre=nombre,
                                    codigo=str(datos.get("codigo","")).strip() or None)
        Container.infraestructura_service().actualizar_area(area_act)
        ui.notify(f"Área '{area_act.nombre}' actualizada", type="positive")
        _cargar_areas(); _cargar_asignaturas()
        tabla_areas.refresh(); filtro_area.refresh(); tabla_asignaturas.refresh()
    except ValueError as exc:
        ui.notify(str(exc), type="warning"); return False
    except Exception as exc:
        logger.error(...); ui.notify("Error al actualizar el área", type="negative"); return False
```

**Migrar `_editar_asignatura(asig: Asignatura)`:**
Campos: `nombre`(text,req), `codigo`(text), `area_id`(select), `horas_semanales`(number,min=1), columnas=2, max_width="max-w-md"

Opciones para `area_id`: `{a.id: a.nombre for a in _s["areas"]}`

---

## T3 — `admin/asignaciones.py`

**Agregar import:** `form_dialog`

**Migrar `_abrir_crear_asignacion()`:**

El guard de validación de opciones disponibles se mantiene ANTES del `form_dialog()`:
```python
def _abrir_crear_asignacion() -> None:
    docentes_opts = {u.id: u.nombre_completo for u in _s["docentes"] if u.activo}
    grupos_opts   = {g.id: g.codigo          for g in _s["grupos"]}
    asigs_opts    = {a.id: a.nombre          for a in _s["asignaturas"]}
    periodos_opts = {p.id: p.nombre          for p in _s["periodos"]}

    if not docentes_opts:
        ui.notify("No hay docentes disponibles", type="warning"); return
    if not grupos_opts:
        ui.notify("No hay grupos disponibles", type="warning"); return
    if not asigs_opts:
        ui.notify("No hay asignaturas disponibles", type="warning"); return
    if not periodos_opts:
        ui.notify("No hay periodos disponibles para el año activo", type="warning"); return

    def _crear(datos: dict) -> bool | None:
        try:
            if not all([datos.get("usuario_id"), datos.get("grupo_id"),
                        datos.get("asignatura_id"), datos.get("periodo_id")]):
                ui.notify("Todos los campos son obligatorios", type="warning"); return False
            dto = NuevaAsignacionDTO(...)
            Container.asignacion_service().crear_asignacion(dto)
            ui.notify("Asignación creada", type="positive")
            _cargar_asignaciones(); tabla.refresh()
        except ValueError as exc:
            ui.notify(str(exc), type="warning"); return False
        except Exception as exc:
            logger.error(...); ui.notify("Error al crear la asignación", type="negative"); return False

    form_dialog(
        titulo="Nueva asignación",
        campos=[
            {"key": "usuario_id",    "label": "Docente *",    "tipo": "select", "opciones": docentes_opts, "requerido": True},
            {"key": "grupo_id",      "label": "Grupo *",      "tipo": "select", "opciones": grupos_opts,   "requerido": True},
            {"key": "asignatura_id", "label": "Asignatura *", "tipo": "select", "opciones": asigs_opts,    "requerido": True},
            {"key": "periodo_id",    "label": "Periodo *",    "tipo": "select", "opciones": periodos_opts, "requerido": True},
        ],
        on_submit=_crear,
        texto_submit="Crear",
        max_width="max-w-lg",
    )
```

---

## T4 — `admin/usuarios.py`

**Agregar import:** `form_dialog`

**Migrar `_abrir_crear_usuario()`:**
Guard: `if not es_admin: ui.notify(...); return`

Campos: `nombre_completo`(text,req), `usuario`(text,req), `password`(password), `rol`(select,valor="profesor"), `email`(email)
columnas=2, max_width="max-w-lg", texto_submit="Crear"

Handler: construir `NuevoUsuarioDTO` desde `datos["nombre_completo"]`, `datos["usuario"]`, etc.

**Migrar `_cambiar_rol(usuario_id, nombre, rol_actual)`:**
Guard: `if not es_admin: ui.notify(...); return`

Campos: `rol`(select, opciones=_ROLES_OPCIONES, valor=rol_actual si está en opciones else "profesor")
columnas=1, max_width="max-w-sm", texto_submit="Cambiar rol"

---

## T5 — `academico/estudiantes.py`

**Agregar import:** `form_dialog`

**Migrar `_abrir_dialog_matricula()`:**
Ver design.md §4 tabla T5a. columnas=2, max_width="max-w-lg", texto_submit="Matricular"

El handler debe construir el DTO de matrícula desde `datos["tipo_documento"]`, etc.
Verificar si los campos del DTO coinciden con las keys del campo dict.

**Migrar `_abrir_dialog_edicion(fila: dict)`:**
Ver design.md §4 tabla T5b. El `est_id` se toma de `fila["id"]`.

---

## T6 — `academico/horarios.py`

**Agregar import:** `form_dialog`

**Migrar `_abrir_dialog_crear()`:**
Guard previo: `if not asig_opts: ui.notify("No hay asignaciones disponibles"); return`

Campos: ver design.md §4 tabla T6. columnas=2, max_width="max-w-lg"

Handler: construir DTO con `asignacion_id=int(datos["asignacion_id"])`, `dia=datos["dia"]`, `hora_inicio=datos["hora_inicio"]`, `hora_fin=datos["hora_fin"]`, `sala=datos["sala"]`.

---

## T7 — `evaluacion/configuracion_evaluacion.py`

**Agregar import:** `form_dialog`

**Migrar `_editar_categoria(cat)`:**
El campo `pct_info` de tipo `"readonly"` muestra `f"{cat.peso_porcentaje:.1f}%"` como
contexto visual. No llega al handler.

Handler valida que `datos["nombre"].strip()` no esté vacío y `datos["peso"]` sea un float.

---

## T8 — `evaluacion/habilitaciones.py`

**Agregar import:** `form_dialog`

**Migrar `_registrar_nota_dialog(hab)`:**
El campo `hab_info` de tipo `"readonly"` muestra `f"Tipo: {hab.tipo.value} | Estado: {hab.estado.value}"`.

Handler construye `RegistrarNotaHabilitacionDTO(nota=float(datos["nota"]), usuario_id=ctx.usuario_id, observacion=datos.get("observacion"))`.

---

## T9 — `evaluacion/planilla_notas.py`

**Agregar import:** `form_dialog`

**Localizar** los dialogs de nota en el archivo (probablemente `_registrar_nota_dialog` o similar).
Verificar que NO son aggrids JS — son renderizados Python (`ui.dialog()`).
Migrar los que sean Python NiceGUI.

---

## T10 — `evaluacion/planes_mejoramiento.py`

**Agregar import:** `form_dialog`

**Migrar `_cerrar_plan_dialog(plan)`:**
Añadir el campo `readonly` con info del plan si se desea contexto:
```python
{"key": "plan_info", "tipo": "readonly",
 "valor": f"Estudiante: {plan.estudiante_id} — Iniciado: {plan.fecha_inicio}"}
```

La validación de observación no vacía se hace en el handler:
```python
if not str(datos.get("observacion","")).strip():
    ui.notify("La observación es obligatoria", type="warning"); return False
```

---

## T11 — Verificación final

```powershell
# PowerShell
$env:PYTHONIOENCODING = "utf-8"
python init.py
```
→ 100% verde.

```powershell
python -m pytest tests/ -q 2>&1 | Select-Object -Last 5
```
→ ≥607 passed, 0 failed.

```bash
# Greps
grep -rln "form_dialog" src/interface/pages/
# → ≥11 archivos

grep -rn "with ui.dialog() as dlg, ui.card" src/interface/pages/ --include="*.py"
# → SOLO los que son justificables (cierre_periodo, cierre_anio, y confirm_dialog internal)
```

El implementer escribe resultado en `progress/impl_paso_10k.md`.
El reviewer escribe veredicto en `progress/review_paso_10k.md`.
Solo tras reviewer PASS el leader actualiza `step_list.json` a `done`.
