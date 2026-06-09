# Requisitos — paso_12b_design_components

## Contexto

El design system actual cubre componentes CRUD (formularios, tablas, diálogos,
botones, badges, KPI cards), pero le faltan tres patrones que aparecen una y otra
vez en las páginas reales:

1. **Estado vacío.** Hoy una página sin datos muestra una tabla vacía o nada. No
   hay un mensaje uniforme que oriente al usuario ("¿Está cargando? ¿No hay datos
   aún? ¿Algo falló?").
2. **Carga (skeleton).** Las páginas que disparan consultas pesadas (planilla,
   informes, estadísticos) muestran un instante de UI vacía antes del render.
   No hay un placeholder unificado.
3. **Notificaciones (toast).** Se usa `ui.notify(...)` directamente con
   parámetros distintos en cada llamada: `type="positive"`, `color="warning"`,
   `position="top"`, posición/colores variables. No hay un wrapper que aplique
   el design system de forma consistente.

## Alcance

NUEVOS archivos en `src/interface/design/components/`:

- `empty_state.py`
- `skeleton_loader.py`
- `toast.py`

CSS asociado en `src/interface/design/styles/components/` (depende de paso 12a estar
hecho — este paso es bloqueado por 12a):

- `empty_state.css`
- `skeleton_loader.css`
- `toast.css`

Actualización del registro de componentes:

- `src/interface/design/components/__init__.py`
- `src/interface/design/styles/index.css` (si se usa @import; o `theme.py` si se usa
  concatenación de lista) — para incluir los nuevos CSS.

**Fuera de scope:**
- Migrar páginas existentes para usar los nuevos componentes. Esa adopción se
  agenda como ticket separado `paso_12b_followup_adoption` y se aplica en pasos
  posteriores o cuando se toque cada página por otro motivo.

## Requisitos funcionales

### R1 — Componente `empty_state(...)`

API:

```python
def empty_state(
    *,
    icono: str = "inbox",          # nombre Material Symbols
    titulo: str,                   # ej. "Sin estudiantes en este grupo"
    descripcion: str = "",         # texto explicativo opcional
    cta_label: str | None = None,  # texto del botón de acción
    cta_on_click: Callable | None = None,
    cta_icono: str | None = None,
    variante: str = "default",     # "default" | "search" | "error"
) -> None:
    """Renderiza un estado vacío centrado con icono grande, título y CTA opcional."""
```

**Casos de uso típicos:**

```python
# 1. Lista sin datos aún cargados
empty_state(
    icono="folder_open",
    titulo="Aún no hay grupos",
    descripcion="Crea el primer grupo para comenzar a registrar estudiantes.",
    cta_label="Crear grupo",
    cta_icono="add",
    cta_on_click=lambda: dialog_crear.open(),
)

# 2. Filtro sin resultados
empty_state(
    icono="search_off",
    titulo="Ningún estudiante coincide con tu búsqueda",
    descripcion="Prueba ajustando los filtros.",
    variante="search",
)

# 3. Error
empty_state(
    icono="error",
    titulo="No pudimos cargar los informes",
    descripcion="Verifica tu conexión y vuelve a intentarlo.",
    cta_label="Reintentar",
    cta_on_click=recargar,
    variante="error",
)
```

### R2 — Componente `skeleton_loader(...)`

Tres presets pensados para los patrones reales de la app:

```python
def skeleton_table(rows: int = 8, cols: int = 5) -> None:
    """Skeleton para tablas: N filas × M columnas con barras animadas."""

def skeleton_cards(count: int = 4) -> None:
    """Skeleton para grids de tarjetas (stat_card, informes)."""

def skeleton_form(fields: int = 6) -> None:
    """Skeleton para formularios: label + input por campo."""
```

Cada uno produce un placeholder con animación shimmer (CSS keyframes). El color
es el neutro de `--color-border` y `--color-divider`. No se reusa lo del estado
vacío.

### R3 — Sistema `toast(...)` unificado

API:

```python
def toast(
    mensaje: str,
    *,
    tipo: str = "info",         # "info" | "success" | "warning" | "error"
    duracion_ms: int = 4000,    # 0 = persistente con botón cerrar
    accion: dict | None = None, # {"label": "Deshacer", "on_click": ...}
    titulo: str | None = None,  # subtítulo opcional sobre el mensaje
) -> None:
    """Wrapper sobre ui.notify con estilo del design system."""
```

Atajos:

```python
def toast_info(mensaje: str, **kw) -> None
def toast_success(mensaje: str, **kw) -> None
def toast_warning(mensaje: str, **kw) -> None
def toast_error(mensaje: str, **kw) -> None
```

Comportamiento:

- Posición fija: `bottom-right` (configurable globalmente, no por llamada).
- Icono según tipo (`info`, `check_circle`, `warning`, `error`).
- Colores: usa variables `--color-info`, `--color-success`, `--color-warning`,
  `--color-error` y sus *-light* para fondo.
- Z-index alto (encima de modales si es success/error crítico).
- Si `accion` está presente, renderiza botón a la derecha del mensaje.

### R4 — Registro en `__init__.py`

Exportar:

```python
from .empty_state import empty_state
from .skeleton_loader import skeleton_table, skeleton_cards, skeleton_form
from .toast import toast, toast_info, toast_success, toast_warning, toast_error
```

Y añadir a `__all__`.

### R5 — Tests

Tests unitarios mínimos en `tests/unit/interface/design/`:

- `test_empty_state.py`: smoke (importa, instancia sin error con NiceGUI mock).
- `test_skeleton_loader.py`: idem para los 3 presets.
- `test_toast.py`: idem + verifica que `toast_success("X")` llama a `ui.notify`
  con `type="positive"` u otro mapeo esperado.

### R6 — Sin regresión

`python init.py` sigue verde. 715 + 3 tests nuevos = 718 mínimo.

## Requisitos no funcionales

- **Sin dependencias externas.** Todo se construye sobre NiceGUI 3.x existente.
- **Sin emojis.** Iconos solo vía Material Symbols Rounded.
- **Sin estilos inline.** Toda CSS en los nuevos `*.css`.
- **Accesibilidad:** los toasts deben tener `role="status"` para lectores de pantalla.
- **Animación shimmer:** respetar `prefers-reduced-motion` — desactivar animación
  si el usuario lo prefiere.
