# Design — paso_10g_convivencia
## Módulo: Convivencia (observaciones, comportamiento, notas)

---

## Archivos del scope

```
src/interface/pages/convivencia/
├── __init__.py            (ya existe, vacío — no modificar)
├── observaciones.py       (CREAR)
├── comportamiento.py      (CREAR)
└── notas_convivencia.py   (CREAR)
```

> `seguimiento.py` existente en el directorio es vacío y no es parte del scope de este paso; no se modifica.

---

## Dependencias de importación por archivo

### observaciones.py
```python
from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.tokens import Icons
from src.interface.design.components.buttons import (
    btn_primary, btn_ghost, btn_danger, btn_icon
)
from src.interface.design.components import confirm_dialog, form_dialog
```
Servicio: `Container.convivencia_service()`, `Container.infraestructura_service()`, `Container.periodo_service()`

### comportamiento.py
```python
from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.tokens import Icons
from src.interface.design.components.buttons import (
    btn_primary, btn_ghost, btn_danger, btn_icon
)
from src.interface.design.components import confirm_dialog, form_dialog
```
Servicio: `Container.convivencia_service()`, `Container.infraestructura_service()`, `Container.configuracion_service()`, `Container.periodo_service()`

Dict local para etiquetas de tipo (NO importar TipoRegistro de dominio para lógica de display):
```python
_TIPOS_DISPLAY: dict[str, str] = {
    "fortaleza": "Fortaleza",
    "dificultad": "Dificultad",
    "compromiso": "Compromiso",
    "citacion_acudiente": "Citación acudiente",
    "descargo": "Descargo",
}
```

### notas_convivencia.py
```python
from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.tokens import Icons
from src.interface.design.components.buttons import btn_primary, btn_ghost, btn_icon
```
Servicio: `Container.convivencia_service()`, `Container.infraestructura_service()`

---

## Estructura interna de cada página

### Patrón general (igual en los tres módulos)

```python
@ui.page("/convivencia/<ruta>")
def <nombre>_page() -> None:
    _s = SessionContext.desde_storage()
    if not _s.autenticado:
        ui.navigate.to("/login")
        return

    # estado mutable (dict)
    _estado: dict = { ... }

    def _cargar_estado() -> None: ...
    def _<accion>_handler(...) -> None: ...

    @ui.refreshable
    def _contenido() -> None:
        app_layout(
            _s,
            page_titulo="...",
            page_subtitulo="...",
            page_icono="...",
            on_context_change=_contenido.refresh,
        )
        # widgets de filtros + tabla/grilla

    _cargar_estado()
    _contenido()
```

---

### observaciones.py — estructura detallada

**Estado mutable:**
```python
_estado: dict = {
    "estudiantes": [],      # list del grupo
    "periodos": [],
    "observaciones": [],    # list[ObservacionPeriodo]
    "sel_estudiante_id": None,
    "sel_periodo_id": None,
}
```

**Handlers:**
- `_cargar_estado()` — llama a `infraestructura_service().listar_estudiantes_grupo(grupo_id)` y `listar_periodos()`.
- `_cargar_observaciones()` — llama a `convivencia_service().listar_observaciones(...)`.
- `_crear_observacion(datos: dict) -> bool | None` — construye `NuevaObservacionDTO` y llama al servicio. Retorna `False` en error (mantiene dialog abierto).
- `_toggle_visibilidad(obs_id, es_publica: bool)` — no hay método update directo en el servicio; se elimina y recrea, o se llama `eliminar_observacion` + `registrar_observacion` con el texto existente y visibilidad invertida. Alternativa: si el servicio expone un método de actualización futuro, usarlo.
- `_eliminar_observacion(obs_id)` — llama a `eliminar_observacion(obs_id)` y refresca.

**Columnas aggrid observaciones:**
| Campo | Tipo | Notas |
|---|---|---|
| Estudiante | text | nombre del estudiante |
| Texto | text | primeros 80 chars + "..." |
| Visibilidad | text | "Pública" / "Privada" |
| Fecha | text | fecha_registro formateada |
| Acciones | cellRenderer | botones via `cellRendererFramework` o `actionColumn` |

**Regla de visibilidad de filas:** si rol es `profesor`, filtrar en cliente las observaciones donde `usuario_id != _s.usuario_id` y `es_publica=False`.

---

### comportamiento.py — estructura detallada

**Estado mutable:**
```python
_estado: dict = {
    "estudiantes": [],
    "periodos": [],
    "registros": [],        # list[RegistroComportamiento]
    "filtro_grupo_id": None,
    "filtro_periodo_id": None,
    "filtro_tipo": "",      # string vacío = todos
    "filtro_solo_negativos": False,
    "anio_id": None,
}
```

**Handlers:**
- `_cargar_estado()` — carga grupos, periodos, `anio_id` desde `configuracion_service().get_activa()`.
- `_aplicar_filtros()` — construye `FiltroConvivenciaDTO` y llama a `listar_registros(filtro)`.
- `_crear_registro(datos: dict) -> bool | None` — construye `NuevoRegistroComportamientoDTO`. El campo `tipo` se pasa como string (el servicio/DTO hace la conversión a enum). Llama a `registrar_comportamiento(dto, usuario_id, anio_id)`.
- `_notificar_acudiente(registro_id)` — llama a `notificar_acudiente(registro_id)` y refresca.
- `_agregar_seguimiento_handler(registro_id, texto) -> bool | None` — llama a `agregar_seguimiento(registro_id, texto)`.
- `_eliminar_registro(registro_id)` — muestra `confirm_dialog` y luego llama al servicio.

**Columnas aggrid comportamiento:**
| Campo | Tipo | Notas |
|---|---|---|
| Fecha | text | |
| Estudiante | text | |
| Tipo | text | con cellClass `badge-<tipo>` |
| Descripción | text | |
| Requiere firma | text | "Sí" / "No" |
| Notificado | text | "Sí" / "Pendiente" |
| Seguimiento | text | ícono si tiene |
| Acciones | — | botones contextuales |

**Clases CSS para badges de tipo (se añaden a `styles.css`):**
```
.badge-fortaleza       → verde
.badge-dificultad      → rojo
.badge-compromiso      → amarillo/ámbar
.badge-citacion        → naranja
.badge-descargo        → gris azulado
```

---

### notas_convivencia.py — estructura detallada

**Estado mutable:**
```python
_estado: dict = {
    "estudiantes": [],       # del grupo
    "periodos": [],
    "notas": [],             # list[NotaComportamiento]
    "periodo_cerrado": False,
    "cambios_pendientes": {},  # {estudiante_id: {"valor": float, "observacion": str}}
}
```

**Handlers:**
- `_cargar_estado()` — carga periodos y llama a `listar_notas_grupo(grupo_id, periodo_id)`.
- `_verificar_periodo(periodo_id)` — llama a `periodo_service()` para verificar si está cerrado.
- `_guardar_nota(estudiante_id, valor, observacion)` — construye `NuevaNotaComportamientoDTO` y llama a `registrar_nota_comportamiento(dto, usuario_id)`.
- `_guardar_todo()` — itera `_estado["cambios_pendientes"]` y guarda cada uno, acumulando errores.

**Aggrid notas:**
- `columnDefs` se construye dinámicamente. Si `periodo_cerrado=True`, todas las columnas tienen `editable: False`.
- Evento `cellValueChanged` de aggrid se captura para actualizar `_estado["cambios_pendientes"]`.

---

## Alternativa descartada

**Alternativa: tres páginas en un único archivo `convivencia.py` con tabs de NiceGUI.**

Se descartó porque:
1. Viola la convención del proyecto de un archivo por ruta.
2. Dificulta el enrutamiento — cada funcionalidad tiene una URL propia para permitir navegación directa y bookmarking.
3. Las tres páginas tienen estados independientes y cargas de datos distintas; combinarlas en un solo módulo aumenta el acoplamiento y la superficie de errores sin beneficio UX.

---

## CSS a agregar en `styles.css`

Las clases de badges de tipo de registro se añaden a `styles.css` (el implementer verifica que no existan antes de añadir):

```css
/* Convivencia — badges tipo registro */
.badge-fortaleza       { ... }  /* verde */
.badge-dificultad      { ... }  /* rojo */
.badge-compromiso      { ... }  /* ámbar */
.badge-citacion        { ... }  /* naranja */
.badge-descargo        { ... }  /* gris azulado */
```

Los valores exactos de color usan variables CSS ya definidas (`--color-success`, `--color-error`, `--color-warning`, `--color-info`, `--color-neutral`).
