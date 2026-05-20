# Requisitos — paso_10l_topbar_pageheader_redesign

## Contexto

El layout actual tiene un `andes-topbar` con glassmorphism ligero (blanco semitransparente)
que muestra solo el título de página, el context_chip y el bloque de usuario. El
`page_header()` es un componente separado que cada página renderiza dentro de su
contenido, produciendo una segunda "cabecera" que duplica el concepto de título.

Además:
- La sidebar muestra "LumEd" hardcodeado sin soporte para logo institucional real
- El topbar blanco no comunica la identidad visual de la institución
- `page_header()` no aporta presencia visual suficiente (solo texto + icono plano)

## Alcance

Módulos afectados:
- `src/interface/design/layout.py`
- `src/interface/design/styles.css`
- `src/interface/design/components/page_header.py` (deprecación + adaptación)
- `src/interface/pages/*.py` — 8 páginas que adoptaron `page_header()` en paso_10j
- `src/domain/models/` — verificar/ampliar `ConfiguracionInstitucion`
- `src/interface/design/theme.py` — añadir `render_logo()`

## Requisitos funcionales

### R1 — Layout adopta el page_header directamente

`app_layout(ctx, contenido)` extiende su firma con parámetros opcionales de cabecera:

```python
def app_layout(
    ctx: SessionContext | None,
    contenido: Callable,
    *,
    page_titulo: str = "",
    page_subtitulo: str = "",
    page_icono: str = "",
    page_acciones: list[dict] | None = None,
) -> None
```

El topbar renderiza estos datos si `page_titulo` está presente. Cuando `page_titulo`
es vacío (páginas sin cabecera formal: `inicio.py`, `tablero_estadisticos.py`),
el topbar muestra solo logo app + context_chip + usuario (comportamiento actual).

### R2 — Topbar unificado con page_header: diseño moderno

El `.andes-topbar` se rediseña visualmente:

**Fondo:** gradiente diagonal primario con efecto glassmorphism
```css
background: linear-gradient(135deg,
    rgba(25, 48, 122, 0.97)  0%,    /* --color-primary-darker */
    rgba(59, 92, 204, 0.93)  60%,   /* --color-primary */
    rgba(78, 117, 255, 0.88) 100%); /* --color-primary-light */
backdrop-filter: blur(20px);
-webkit-backdrop-filter: blur(20px);
border-bottom: 1px solid rgba(255, 255, 255, 0.12);
box-shadow: 0 4px 24px rgba(59, 92, 204, 0.25);
```

**Altura:** 72px (antes 58px) para acomodar subtítulo.

**Layout interno del topbar:**
```
[ brand/logo-área ] [ icono + título + subtítulo ] · · · [ ctx-chip ] [ logo-inst ] [ user-block ]
 └─ sidebar toggle     └─ solo si page_titulo                └─ si ctx      └─ si existe
```

**Textos en el topbar:** todos en colores blancos/claros sobre el gradiente oscuro.

### R3 — Sección izquierda del topbar: brand + page info

El área izquierda del topbar tiene dos sub-secciones:

**Brand area** (visible siempre, compacto):
- Botón de toggle del sidebar (ya existente), rediseñado para fondo oscuro
- Separador visual vertical sutil

**Page info area** (visible solo cuando `page_titulo != ""`):
- Icono de página: `ThemeManager.icono(page_icono, size=20, color="rgba(255,255,255,0.9)")`
- Columna de texto:
  - Título: `font-size: 16px; font-weight: 600; color: white; letter-spacing: -0.01em`
  - Subtítulo: `font-size: 11px; color: rgba(255,255,255,0.65); margin-top: 1px`

### R4 — Sección derecha del topbar: acciones + logo + usuario

El área derecha contiene en orden (derecha a izquierda):
1. **User block**: nombre + rol + logout — colores blancos
2. **Logo institucional** (si existe): `<img>` de max 36px de alto, clic → página inicio
3. **Botones de acción** (`page_acciones`): si la página provee CTAs, se muestran aquí
   — usar variante secondary con colores adaptados para fondo oscuro
   (`btn_outline_light()`: nuevo sub-componente opcional o clase CSS override)
4. **Context chip**: ya existente, rediseñado para fondo oscuro

### R5 — Context_selector no se rompe

El `context_chip()` y el `abrir_selector()` siguen funcionando. Solo cambios visuales:
- El chip en el topbar usa colores adaptados para fondo oscuro:
  fondo `rgba(255,255,255,0.12)`, texto `white`, borde `rgba(255,255,255,0.2)`
- El `context_selector` dialog (que se abre en overlay) no cambia

### R6 — Logo institucional

**Origen:** `ConfiguracionInstitucion.logo_url` — campo de la entidad institucional.

Verificación: si el modelo `ConfiguracionInstitucion` en `src/domain/models/` no tiene
campo `logo_url: str | None = None`, agregarlo. Si el servicio correspondiente
(`infraestructura_service` u otro) no tiene `get_configuracion_institucion()`, el
implementer usa el acceso existente o el servicio que obtiene la config.

**Display:**
- En el **topbar** (R4): `<img>` de max 36px alto, max 120px ancho,
  `object-fit: contain`, redondeado (radius-sm), solo visible cuando `logo_url != None`
- En la **sidebar header**: si `logo_url` existe, mostrar como imagen en lugar del
  texto "LumEd". Si no existe, mantener el texto actual.

**ThemeManager:**
```python
@classmethod
def render_logo(cls, logo_url: str, max_height: int = 36, clases: str = "") -> ui.html:
    """Renderiza la imagen del logo institucional."""
```

**Fallback:** si `logo_url` no existe o falla la carga → no se muestra nada
(no romper el layout).

### R7 — Migración de 8 páginas

Las 8 páginas que adoptaron `page_header()` en paso_10j deben:
1. Eliminar la llamada `page_header(...)` de dentro de `contenido()`
2. Mover los parámetros a `app_layout(ctx, contenido, page_titulo=..., ...)`

Páginas afectadas:
- `admin/grupos.py`, `admin/asignaturas.py`, `admin/asignaciones.py`
- `admin/usuarios.py`, `admin/configuracion_sie.py`, `admin/configuracion_institucion.py`
- `academico/estudiantes.py`, `academico/horarios.py`

Para `usuarios.py` y `estudiantes.py` que tenían `page_acciones` en su `page_header()`,
los botones de acción deben pasarse a `page_acciones` de `app_layout()`.

### R8 — `page_header()` componente: deprecación controlada

El componente `src/interface/design/components/page_header.py` queda disponible
pero se marca como deprecated en su docstring. No se elimina ya que puede ser
necesario en páginas que no usan `app_layout` o en contextos embebidos futuros.

Agregar al inicio del docstring:
```
.. deprecated::
    Usar page_titulo/page_subtitulo/page_icono/page_acciones en app_layout() en su lugar.
```

### R9 — Sidebar header con logo

La sección `.sidebar-header` del layout se adapta:
- Si `logo_url` existe → mostrar `<img>` del logo (max 120px ancho, max 40px alto)
- Si no → mantener `.sidebar-logo-text` ("LumEd") y `.sidebar-sub-text` actuales
- La detección se hace en `_sidebar()` leyendo la config (misma consulta que R6)

### R10 — 0 regresiones

`python init.py` → verde · `pytest tests/ -q` → ≥607 passed · context_chip funcional.

## Criterio de completado

- El topbar muestra el gradiente primario con glassmorphism (visual verificado en browser)
- `grep "page_header(" src/interface/pages/admin/*.py src/interface/pages/academico/*.py`
  → 0 resultados (removido de las páginas)
- `grep "page_titulo" src/interface/pages/admin/*.py src/interface/pages/academico/*.py`
  → presente en las 8 páginas
- `grep "logo_url" src/domain/models/` → campo presente
- `python init.py` → verde
- `pytest tests/ -q` → ≥607 passed
