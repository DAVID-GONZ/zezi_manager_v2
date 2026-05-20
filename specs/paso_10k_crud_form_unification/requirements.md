# Requisitos — paso_10k_crud_form_unification

## Contexto

Tras paso_10j, los componentes del design system están adoptados en páginas para
headers, badges y stat cards. Sin embargo, **todos los CRUD dialogs (crear/editar)
siguen siendo inline**: cada página declara su propio `with ui.dialog() as dlg,
ui.card():` con widgets individuales. Esto genera:

- 13 dialogs con el mismo patrón visual pero código duplicado
- Inconsistencia en sizing, spacing, botón order, y feedback de error
- `base_form()` creado en paso_10i pero con 0 usos en páginas
- Tipos de campo faltantes en `base_form()`: `number`, `checkbox`, `time`, `email`,
  `readonly`

## Alcance

Módulo afectado: `src/interface/design/components/` + `src/interface/pages/`

## Requisitos funcionales

### R1 — `base_form()` extendido con nuevos tipos de campo

Agregar soporte para:

| `tipo` | Widget NiceGUI | Params adicionales en campo dict |
|---|---|---|
| `"number"` | `ui.number()` | `min`, `max`, `step`, `format`, `valor` |
| `"checkbox"` | `ui.checkbox()` | `valor` (bool, default False) |
| `"time"` | `ui.input().props("type=time")` | `valor` (str "HH:MM") |
| `"email"` | `ui.input().props("type=email")` | `placeholder` |
| `"readonly"` | `ui.label()` styled | `valor` (str mostrado); **no** se incluye en `_recoger_datos()` |

Tipos existentes que se mantienen sin cambio: `"text"`, `"select"`,
`"textarea"`, `"password"`.

### R2 — Campo dict ampliado con `valor` (pre-población para edición)

Todos los tipos de campo aceptan un key `"valor"` en el dict para pre-popular
el widget. Esto habilita el patrón edit:

```python
{"key": "nombre", "label": "Nombre *", "tipo": "text",
 "valor": grupo.codigo, "requerido": True}
```

Para select: `"valor"` es la key/value del ítem pre-seleccionado.
Para checkbox: `"valor"` es `True` / `False`.
Para number: `"valor"` es el número inicial.

### R3 — Nueva función `form_dialog()`

Nuevo componente en `src/interface/design/components/form_dialog.py`:

```python
def form_dialog(
    titulo: str,
    campos: list[dict],
    on_submit: Callable[[dict], bool | None],
    texto_submit: str = "Guardar",
    on_cancelar: Callable | None = None,
    max_width: str = "max-w-md",
    columnas: int = 1,
) -> None
```

Comportamiento:
- Abre un `ui.dialog()` con `ui.card()` estandarizado (clase `andes-card form-dialog-card`)
- Título del dialog: `ui.label(titulo).classes("font-h3 form-dialog-title")`
- Cuerpo: `base_form(...)` sin título propio (`titulo=""`) ni botón cancelar propio
- El botón "Cancelar" cierra el dialog y llama a `on_cancelar` si se proveyó
- `on_submit(datos: dict) → bool | None`:
  - Si retorna `False` → el dialog permanece abierto (validación fallida, el
    handler ya llamó `ui.notify`)
  - Si retorna `None` / `True` (o no retorna nada) → el dialog se cierra

### R4 — `form_dialog()` exportado desde `__init__.py`

`from src.interface.design.components import form_dialog`

### R5 — Migración de CRUD dialogs existentes

Los 13 dialogs listados abajo deben reemplazarse con `form_dialog()`. El criterio
de migración es: `with ui.dialog()` sin lógica que requiera widgets reactivos
inter-dependientes (ej: campos cuyo contenido cambia según otro campo).

**Páginas y funciones a migrar:**

| Página | Función / dialog | Campos | `max_width` |
|---|---|---|---|
| `admin/grupos.py` | `_abrir_editar(grupo)` | código(text), grado(number), jornada(select), capacidad(number) | `max-w-md` |
| `admin/asignaturas.py` | `_editar_area(area)` | nombre(text,req), código(text) | `max-w-md` |
| `admin/asignaturas.py` | `_editar_asignatura(asig)` | nombre(text,req), código(text), área(select), horas(number) | `max-w-md` |
| `admin/asignaciones.py` | `_abrir_crear_asignacion()` | docente(select,req), grupo(select,req), asignatura(select,req), periodo(select,req) | `max-w-lg` |
| `admin/usuarios.py` | `_abrir_crear_usuario()` | nombre(text,req), usuario(text,req), password(password), rol(select), email(email) | `max-w-lg` |
| `admin/usuarios.py` | `_cambiar_rol(usuario_id, nombre, rol_actual)` | rol(select,req) | `max-w-sm` |
| `academico/estudiantes.py` | `_abrir_dialog_matricula()` | tipo_doc(select), num_doc(text,req), nombre(text,req), apellido(text,req), grupo_id(select), genero(select), posee_piar(checkbox) | `max-w-lg` |
| `academico/estudiantes.py` | `_abrir_dialog_edicion(fila)` | nombre(text,req), apellido(text,req), estado(select), grupo_id(select), genero(select), posee_piar(checkbox) | `max-w-lg` |
| `academico/horarios.py` | `_abrir_dialog_crear()` | asignacion_id(select,req), dia(select,req), hora_inicio(time), hora_fin(time), sala(text) | `max-w-lg` |
| `evaluacion/configuracion_evaluacion.py` | `_editar_categoria(cat)` | nombre(text,req), peso(number,0.01–1.0), pct_actual(readonly) | `max-w-md` |
| `evaluacion/habilitaciones.py` | `_registrar_nota_dialog(hab)` | header_info(readonly), nota(number,0–100,step=0.5), observacion(text) | `max-w-sm` |
| `evaluacion/planilla_notas.py` | dialog nota | nota(number,0–100,step=0.5) | `max-w-sm` |
| `evaluacion/planes_mejoramiento.py` | `_cerrar_plan_dialog(plan)` | estado(select,req), observacion(textarea,req) | `max-w-md` |

**Funciones confirmadoras a refactorizar:**
Para cada dialog migrado, la función confirmadora (ej: `_guardar_edicion()`)
que era closure interno se transforma en función externa nombrada que:
- Recibe `datos: dict` con las claves según los `"key"` del campo dict
- Realiza la llamada al servicio y `ui.notify()`
- Si falla → `ui.notify(msg, type="warning/negative")` + `return False`
- Si exitosa → retorna `None` (dialog se cierra automáticamente)

### R6 — CSS para `form-dialog-card` y `form-dialog-title`

Agregar en `styles.css`:
```css
.form-dialog-card {
  width: 100%;
  min-width: 320px;
}
.form-dialog-title {
  margin-bottom: var(--space-sm);
  color: var(--color-text-primary);
  border-bottom: 1px solid var(--color-divider);
  padding-bottom: var(--space-sm);
}
```

### R7 — 0 regresiones

`python init.py` verde · `pytest tests/ -q` ≥607 passed · 0 failed.

## Criterio de completado

- `grep -rn "with ui.dialog() as dlg, ui.card" src/interface/pages/` → solo dialogs
  que son confirm_dialog o tienen lógica reactiva inter-campo justificada
- `grep -rn "form_dialog" src/interface/pages/` → ≥13 resultados
- `python init.py` → verde
- `pytest tests/ -q` → ≥607 passed
