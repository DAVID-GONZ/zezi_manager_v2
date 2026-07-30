# chip_01 — Componente `inline_selectors`

> Paso aprobado: ⏳ pendiente confirmación de David.

## Objetivo

Crear `src/interface/design/components/inline_selectors.py` con dos funciones
públicas que renderizan pills de selección en cascada dentro del contenido de
la página (no en el topbar). Este componente reemplaza el rol del chip global
en todas las páginas que usan `on_context_change`.

---

## Comportamiento esperado

```
[2025-1  ▾]  [10A  ▾]  [Matemáticas  ▾]
```

- Cada dimensión es un pill independiente con icono `expand_more`.
- Click abre un `ui.menu` con las opciones disponibles.
- Cascada estricta: grupo no carga hasta tener periodo; asignatura no carga hasta tener grupo.
- Pill siguiente aparece deshabilitado/gris si el anterior no está seleccionado.
- Al cambiar periodo, grupo y asignatura se limpian (cascada hacia abajo).
- Al cambiar grupo, asignatura se limpia.
- `on_change` se llama SOLO cuando la selección es completa (todas las dimensiones requeridas tienen valor).

---

## API pública

```python
def inline_periodo_grupo_asignatura(
    s: dict,                    # estado local de la página (se modifica in-place)
    on_change: Callable,        # llamado cuando la selección completa cambia
    usuario_id: int,
    institucion_id: int,
    usuario_rol: str,           # "profesor" filtra grupos/asignaturas propios
    preselect_periodo: bool = True,  # True para profesor; False para directivo
) -> None: ...

def inline_periodo_grupo(
    s: dict,
    on_change: Callable,
    institucion_id: int,
    preselect_periodo: bool = True,
) -> None: ...
```

### Claves de `s` que el componente lee y escribe

| Clave | Tipo | Semántica |
|-------|------|-----------|
| `sel_periodo_id` | int \| None | ID del periodo actualmente seleccionado |
| `sel_periodo_nombre` | str | Nombre para mostrar en el pill |
| `sel_grupo_id` | int \| None | ID del grupo seleccionado |
| `sel_grupo_nombre` | str | Nombre para mostrar |
| `sel_asignacion_id` | int \| None | ID de la asignación seleccionada |
| `sel_asignacion_nombre` | str | Nombre para mostrar |

Las páginas que actualmente usan `ctx.periodo_id / ctx.grupo_id / ctx.asignacion_id`
migrarán esas claves a `_s["sel_periodo_id"]` etc. La función `on_change` recibe
el `_s` actualizado y puede copiar los valores donde la página los necesite.

### Pre-selección de periodo

Cuando `preselect_periodo=True`:
1. Llama `Container.periodo_service().listar_por_anio(anio_id_activo)` donde
   `anio_id_activo` se obtiene del año calendario actual.
2. Filtra el primer periodo con `estado == 'abierto'`.
3. Si hay uno, lo escribe en `s["sel_periodo_id"]` y `s["sel_periodo_nombre"]`
   antes de renderizar y dispara la carga de grupos.
4. Si no hay ninguno abierto, deja el pill vacío (no pre-selecciona).

---

## Estructura interna del componente

```
inline_selectors_container  (div.inline-sel-row)
  ├── _pill_periodo(s, menus, on_change, ...)
  ├── _pill_grupo(s, menus, on_change, ...)       # disabled si no hay periodo
  └── _pill_asignatura(s, menus, on_change, ...)  # disabled si no hay grupo
                                                  # (solo en inline_periodo_grupo_asignatura)
```

Cada `_pill_*` es una función interna que renderiza:
- `ui.button` con clase CSS `inline-sel-pill` (label + icono `expand_more`)
- `ui.menu` anclado al botón con `ui.menu_item` por cada opción

El pill usa `@ui.refreshable` para actualizarse cuando cambia su valor en `s`.

---

## Carga de datos

| Paso | Servicio | Filtros |
|------|----------|---------|
| Periodos | `Container.periodo_service().listar_por_anio(anio_id)` | Sin filtro de rol |
| Grupos | `Container.infraestructura_service().listar_grupos_por_periodo(periodo_id)` | Si `usuario_rol == "profesor"`: solo grupos con asignaciones de `usuario_id` |
| Asignaciones | `Container.catalogo_academico_service().listar_asignaciones_por_grupo_periodo(grupo_id, periodo_id)` | Si `usuario_rol == "profesor"`: filtra por `usuario_id` |

---

## CSS (a agregar en `styles/components/forms.css` o nuevo `inline_selectors.css`)

```css
.inline-sel-row {
  display: flex;
  gap: var(--space-2);
  align-items: center;
  flex-wrap: wrap;
  padding: var(--space-3) 0 var(--space-4);
}

.inline-sel-pill {
  /* pill base: borde, fondo, texto compact */
  border: 1px solid var(--color-border);
  border-radius: 999px;
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-sm);
  color: var(--color-text);
  background: var(--color-surface);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  transition: border-color 0.15s, background 0.15s;
}

.inline-sel-pill:hover {
  border-color: var(--color-primary);
  background: var(--color-primary-lighter);
}

.inline-sel-pill.sel-active {
  border-color: var(--color-primary);
  background: var(--color-primary-lighter);
  color: var(--color-primary-dark);
  font-weight: 500;
}

.inline-sel-pill:disabled,
.inline-sel-pill[disabled] {
  opacity: 0.4;
  cursor: not-allowed;
}
```

---

## Tests requeridos (unit, sin BD)

Archivo: `tests/unit/interface/test_inline_selectors.py`

| Test | Qué verifica |
|------|-------------|
| `test_preselect_false_no_modifica_s` | Con `preselect_periodo=False`, `s` permanece vacío al init |
| `test_preselect_true_selecciona_primer_abierto` | Con `preselect_periodo=True` y un periodo abierto, `s["sel_periodo_id"]` se asigna |
| `test_preselect_true_sin_abiertos_deja_none` | Sin periodos abiertos, `s["sel_periodo_id"]` queda None |
| `test_cambio_periodo_limpia_grupo_y_asignacion` | Al cambiar periodo, `sel_grupo_id` y `sel_asignacion_id` se ponen a None |
| `test_cambio_grupo_limpia_asignacion` | Al cambiar grupo, `sel_asignacion_id` se pone a None |
| `test_on_change_solo_cuando_completa_3d` | `on_change` no se llama con solo periodo; se llama con los 3 valores |
| `test_on_change_solo_cuando_completa_2d` | Para `inline_periodo_grupo`, `on_change` se llama con periodo+grupo |

Los tests verifican la **lógica pura** (pre-selección, cascada, disparo de `on_change`)
sin renderizar UI. El renderizado NiceGUI no se testea en unit.

---

## Restricciones

- ❌ No importar desde `src.domain` ni `src.infrastructure` directamente.
  Solo vía `Container`.
- ❌ No escribir a `SessionContext` (solo lectura para obtener `anio_id` activo
  si es necesario, o usar año calendario de `datetime.date.today().year`).
- ❌ No usar `ui.select` nativo — los pills deben ser `ui.button` + `ui.menu`
  para control total del estilo.
- ✅ Toda lógica pura (pre-selección, cascada, disparo on_change) separable y testeable.
- ✅ CSS en archivo de estilos, no inline.

---

## Archivos a crear/modificar

| Archivo | Acción |
|---------|--------|
| `src/interface/design/components/inline_selectors.py` | **CREAR** |
| `src/interface/design/styles/components/inline_selectors.css` | **CREAR** |
| `src/interface/design/styles/main.css` | **MODIFICAR** — importar el nuevo CSS |
| `tests/unit/interface/test_inline_selectors.py` | **CREAR** |

---

## Criterio de done

- `init.py` completamente verde.
- Los 7 tests pasan.
- No se modifica ninguna página existente (eso es chip_02 y chip_03).
- El componente se puede importar sin errores.
