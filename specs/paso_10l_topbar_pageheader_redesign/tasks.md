# Tasks — paso_10l_topbar_pageheader_redesign

## Resumen de tareas

| ID | Descripción | Archivos | Verificación |
|---|---|---|---|
| T1 | CSS variables y topbar redesign | styles.css | Visual |
| T2 | Modelo: campo logo_url | src/domain/models/… | grep logo_url |
| T3 | ThemeManager: render_logo() | theme.py | import OK |
| T4 | Layout: nueva firma + _topbar + _sidebar | layout.py | init.py verde |
| T5 | 8 páginas: migrar page_header → app_layout params | admin/*.py, academico/*.py | grep 0 page_header( |
| T6 | page_header.py: deprecation notice | page_header.py | docstring |
| T7 | Verificación final | — | R10 |

---

## T1 — CSS: variables y topbar redesign

**Prerequisito:** ninguno.

**Lee `src/interface/design/styles.css` (secciones `:root` y `.andes-topbar`) antes de editar.**

### T1a — Actualizar variable `--topbar-height` en `:root`

```css
/* Antes: */
--topbar-height: 58px;
/* Después: */
--topbar-height: 72px;
```

### T1b — Reemplazar `.andes-topbar`

Reemplazar el bloque CSS existente de `.andes-topbar` con el nuevo según design.md §5.
El nuevo bloque usa el gradiente primario + glassmorphism + nueva altura.

### T1c — Agregar nuevas clases del topbar

Agregar todas las clases nuevas del diseño §5:
- `.topbar-brand`
- `.topbar-page-info`, `.topbar-page-title`, `.topbar-page-sub`
- `.topbar-user-name`, `.topbar-user-role` (actualizar colores a blancos)
- `.topbar-logo-inst`, `.topbar-logo-img`
- `.topbar-action-btn`, `.topbar-action-primary`, `.topbar-action-secondary`, `.topbar-action-danger`
- `.topbar-actions`
- Override `.andes-topbar .q-btn[flat]` para iconos claros
- Override de context chip: `.andes-topbar .context-chip` (verificar nombre de clase real en context_selector.py)

### T1d — Agregar `.sidebar-logo-img`

```css
.sidebar-logo-img {
  max-width: 120px;
  max-height: 40px;
  object-fit: contain;
  border-radius: var(--radius-sm);
  opacity: 0.9;
}
```

**Verificación T1:**
```bash
grep -n "topbar-height\|topbar-page-title\|topbar-action-btn\|sidebar-logo-img" src/interface/design/styles.css
# → debe aparecer cada uno
```

---

## T2 — Modelo ConfiguracionInstitucion: campo `logo_url`

**Localizar** el modelo en `src/domain/models/`. Buscar un archivo con
`ConfiguracionInstitucion` (puede llamarse `configuracion.py`, `institucion.py`, etc.).

```bash
grep -rln "ConfiguracionInstitucion" src/domain/models/
```

**Leer el archivo** y verificar si tiene `logo_url: str | None`.

Si NO existe → agregar campo:
```python
logo_url: str | None = None
```

Ubicarlo después del último campo existente del modelo (probablemente `email`,
`telefono`, `direccion` u otro campo de contacto).

**Verificación T2:**
```bash
grep -rn "logo_url" src/domain/models/
# → al menos 1 resultado
```

---

## T3 — `ThemeManager.render_logo()` en `theme.py`

**Lee `src/interface/design/theme.py` completo antes de editar.**

Agregar el método de clase `render_logo()` según design.md §6.

Ubicar junto a `ThemeManager.icono()` (después del método existente).

**Verificación T3:**
```bash
python -c "from src.interface.design.theme import ThemeManager; print(hasattr(ThemeManager, 'render_logo'))"
# → True
```

---

## T4 — `layout.py`: nueva firma + topbar + sidebar

**Lee `src/interface/design/layout.py` completo antes de editar.**

### T4a — Agregar helper `_get_logo_institucional()`

Agregar función privada en layout.py (antes de `app_layout`):
```python
def _get_logo_institucional() -> str | None:
    try:
        config = Container.infraestructura_service().get_configuracion_institucion()
        if config and hasattr(config, "logo_url") and config.logo_url:
            return config.logo_url
    except Exception:
        pass
    return None
```

Verificar el nombre exacto del método del servicio que obtiene la configuración
institucional. Si el servicio se llama diferente, ajustar.

### T4b — Modificar `app_layout()`

Cambiar la firma para aceptar los nuevos parámetros opcionales (keyword-only con `*`)
según design.md §1. Pasar `logo_url` a `_sidebar()` y `_topbar()`.

### T4c — Reescribir `_topbar()`

Reescribir la función interna `_topbar()` según design.md §2.
Incluir los helpers `_btn_topbar_accion()` y `_user_block_topbar()` como funciones
privadas adicionales en layout.py.

**Puntos críticos:**
- Mantener la llamada a `context_chip()` con los mismos parámetros que tenía antes
- Mantener la llamada a `_toggle_sidebar` o al handler de colapso del sidebar
- El botón de toggle sidebar (si existe en el topbar actual) debe mantenerse en `.topbar-brand`
- Si el topbar actual usa `topbar-title` (label de texto), eliminarlo → reemplazado por `.topbar-page-info`

### T4d — Modificar `_sidebar()` para logo condicional

Modificar la función interna `_sidebar()` para aceptar `logo_url: str | None = None`
y mostrar `<img>` condicional según design.md §4.

**Verificación T4:**
```powershell
$env:PYTHONIOENCODING = "utf-8"; python init.py
# → verde (0 errores)
python -c "from src.interface.design.layout import app_layout; print('OK')"
# → OK
```

---

## T5 — Migrar 8 páginas

**Prerequisito:** T4 completado y `python init.py` verde.

Para cada página, sigue el patrón de design.md §8. Para cada archivo:

1. **Leer el archivo** completo (o al menos la función `@ui.page` principal)
2. Localizar la llamada `page_header(...)` dentro de `contenido()`
3. Extraer los argumentos (`titulo`, `subtitulo`, `icono`, `acciones`)
4. Eliminar la llamada `page_header(...)` de `contenido()`
5. Mover los argumentos como params keyword a `app_layout(...)`
6. Eliminar el import `from src.interface.design.components import page_header` si ya no se usa

**T5-1: `admin/grupos.py`**
- titulo="Gestión de Grupos", subtitulo="Crea y administra los grupos académicos de la institución", icono=Icons.GROUPS

**T5-2: `admin/asignaturas.py`**
- titulo="Gestión de Asignaturas", subtitulo="Áreas de conocimiento y asignaturas del currículo", icono=Icons.SUBJECTS

**T5-3: `admin/asignaciones.py`**
- titulo="Asignaciones Docentes", subtitulo="Asignación de docentes a grupos y asignaturas por periodo", icono="assignment_ind"

**T5-4: `admin/usuarios.py`**
- titulo="Gestión de Usuarios", subtitulo="Cuentas de usuario y roles del sistema", icono=Icons.TEACHERS
- acciones: el botón "Nuevo usuario" condicional en `es_admin` (ver design.md §8)

**T5-5: `admin/configuracion_sie.py`**
- titulo="Configuración del SIE", subtitulo="Periodos académicos y configuración del año escolar", icono="settings"

**T5-6: `admin/configuracion_institucion.py`**
- titulo="Información Institucional", subtitulo="Datos básicos y generales de la institución educativa", icono="business"

**T5-7: `academico/estudiantes.py`**
- titulo="Gestión de Estudiantes", subtitulo="Matrícula, estado y PIAR de estudiantes", icono=Icons.STUDENTS
- acciones: [Matricular, Carga CSV] (ver design.md §8)

**T5-8: `academico/horarios.py`**
- titulo="Horarios", subtitulo="Grilla semanal de bloques de clase por grupo", icono=Icons.SCHEDULE

**Verificación T5:**
```bash
grep -rn "page_header(" src/interface/pages/admin/ src/interface/pages/academico/estudiantes.py src/interface/pages/academico/horarios.py
# → 0 resultados

grep -rn "page_titulo" src/interface/pages/admin/ src/interface/pages/academico/
# → 8 resultados (uno por archivo)
```

---

## T6 — `page_header.py`: deprecation notice

**Lee `src/interface/design/components/page_header.py`.**

Al inicio del docstring de la función `page_header()`, agregar:

```python
"""
.. deprecated::
    Usar los parámetros page_titulo/page_subtitulo/page_icono/page_acciones
    en app_layout() en su lugar. Este componente se mantiene por compatibilidad.

[resto del docstring existente...]
"""
```

No cambiar nada más del componente.

---

## T7 — Verificación final

```powershell
$env:PYTHONIOENCODING = "utf-8"; python init.py
```
→ 100% verde.

```powershell
python -m pytest tests/ -q 2>&1 | Select-Object -Last 5
```
→ ≥607 passed, 0 failed.

**Greps de comprobación:**
```bash
# 0 llamadas a page_header() en páginas migradas:
grep -rn "page_header(" src/interface/pages/admin/ src/interface/pages/academico/estudiantes.py src/interface/pages/academico/horarios.py
# → 0 resultados

# page_titulo presente en app_layout de 8 páginas:
grep -rn "page_titulo" src/interface/pages/admin/ src/interface/pages/academico/
# → ≥8 resultados

# logo_url en dominio:
grep -rn "logo_url" src/domain/models/
# → ≥1 resultado

# topbar gradient en CSS:
grep -n "rgba(25, 48, 122" src/interface/design/styles.css
# → ≥1 resultado
```

**Verificación visual (si hay server disponible):**
- Navegar a `/admin/grupos`: topbar azul gradiente, título "Gestión de Grupos" + subtítulo visibles
- Navegar a `/inicio`: topbar azul gradiente sin título de página (solo brand + user)
- Con rol no-admin: context_chip visible y funcional con estilo claro sobre fondo oscuro
- Si `logo_url` está configurado: imagen visible en topbar derecho y en sidebar

El implementer escribe resultado en `progress/impl_paso_10l.md`.
El reviewer escribe veredicto en `progress/review_paso_10l.md`.
Solo tras reviewer PASS el leader actualiza `step_list.json` a `done`.
