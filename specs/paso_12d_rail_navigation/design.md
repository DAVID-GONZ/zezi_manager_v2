# Diseño — paso_12d_rail_navigation

## Dependencias

12a (modular) + 12c (paleta clara).

## 1. Anatomía visual del rail

```
┌────┐
│ 🅡 │  ← Logo / monograma (top, 56px alto)
├────┤
│    │
│ 🏠 │  ← Inicio (item sin hijos)
│    │
│ 📚 │  ← Aula (item con hijos)
│    │
│ 🎓 │  ← Académico (con hijos)
│    │
│ 📐 │  ← Evaluación (con hijos)
│    │
│ 📊 │  ← Informes (con hijos)
│    │
├────┤  ← divider (margen)
│    │
│ ⚙ │  ← Admin (solo admin/director)
│    │
└────┘

Estado activo (Aula):
│┃📚 │  ← barra accent-600 izquierda, fondo ink-100, icono ink-700
```

Cada item es:
- Container `<div>` clickeable de 60 × 48 px (rail width × item height).
- Padding lateral para centrar el icono de 24 px en 60 px de ancho.
- 4 px de margen vertical entre items.

## 2. Anatomía del flyout

```
                  ┌─────────────────────────────┐
                  │  Aula                       │ ← header en serif
                  ├─────────────────────────────┤
              📚→ │ 📓 Planilla de Notas    ●   │ ← activo
                  │ ✅ Asistencia                │
                  │ 💬 Observaciones             │
                  │ 📋 Comportamiento            │
                  │ 📝 Seguimiento               │
                  └─────────────────────────────┘
```

Items del flyout:
- Padding vertical 10 px, horizontal 14 px.
- Icono Material 18 px + label en Inter 13 px.
- Hover: fondo `var(--ink-050)`.
- Activo: fondo `var(--ink-100)` + barra accent-600 izquierda 3 px + label bold.
- Pending: opacidad 0.5 + icono lock.

## 3. Implementación de `_rail()` en layout.py

Reemplaza a `_sidebar()`:

```python
def _rail(
    usuario_rol: str,
    ruta_activa: str,
    *,
    logo_url: str | None = None,
) -> ui.element:
    """Renderiza el rail icon-only con flyouts contextuales."""

    rail_el = ui.element("nav").classes("andes-rail").props("role=navigation")

    with rail_el:
        # ── Logo / monograma ──
        with ui.element("div").classes("rail-brand"):
            if logo_url:
                ui.html(f'<img src="{logo_url}" alt="Logo" class="rail-logo-img">')
            else:
                # Monograma (iniciales en serif)
                ui.html('<span class="rail-monogram">ZM</span>')

        # ── Items ──
        for item in NAV_ITEMS:
            if "divider" in item:
                if _usuario_puede_ver(item, usuario_rol):
                    ui.element("div").classes("rail-divider")
                continue

            if not _usuario_puede_ver(item, usuario_rol):
                continue

            tiene_hijos = "children" in item
            es_activo = _calcular_activo(item, ruta_activa)

            clase = "rail-item"
            if es_activo:
                clase += " is-active"
            if tiene_hijos:
                clase += " has-children"

            item_el = ui.element("div").classes(clase)
            with item_el:
                ThemeManager.icono(item["icon"], size=22, clases="rail-icon")
                # Tooltip nativo CSS via data-attr
                item_el.props(f'data-tooltip="{item["label"]}"')

            if tiene_hijos:
                item_el.on(
                    "click",
                    lambda e, it=item: _toggle_flyout(it, e),
                )
            else:
                item_el.on(
                    "click",
                    lambda e, r=item["ruta"]: ui.navigate.to(r),
                )

    # Flyout vivo (uno solo, reutilizable)
    _flyout_container = ui.element("div").classes("rail-flyout-container hidden")

    return rail_el
```

### Estado del flyout

Una única instancia del flyout. Su contenido se reconstruye al abrir:

```python
_flyout_state: dict = {"open_item_id": None, "anchor_top": 0}

def _toggle_flyout(item, event):
    target_id = id(item)
    if _flyout_state["open_item_id"] == target_id:
        _cerrar_flyout()
        return
    _abrir_flyout(item, event)

def _abrir_flyout(item, event):
    container = _flyout_container
    container.clear()
    with container:
        ui.label(item["label"]).classes("flyout-header")
        for child in item["children"]:
            if not _usuario_puede_ver(child, usuario_rol):
                continue
            is_active = ruta_activa == child.get("ruta")
            clase = "flyout-item" + (" is-active" if is_active else "")
            it = ui.element("div").classes(clase)
            with it:
                ThemeManager.icono(child["icon"], size=18, clases="flyout-icon")
                ui.label(child["label"]).classes("flyout-label")
            it.on("click", lambda e, r=child["ruta"]: (ui.navigate.to(r), _cerrar_flyout()))
    # Calcula top anchor desde el evento
    container.style(f'top: {event.args["pageY"] - 20}px')
    container.classes(remove="hidden")
    _flyout_state["open_item_id"] = id(item)

def _cerrar_flyout():
    _flyout_container.classes(add="hidden")
    _flyout_state["open_item_id"] = None
```

Para cerrar al click fuera, el flyout escucha global JS:

```python
ui.add_body_html("""
<script>
document.addEventListener('click', function(e) {
  const flyout = document.querySelector('.rail-flyout-container');
  const rail   = document.querySelector('.andes-rail');
  if (!flyout || !rail) return;
  if (flyout.contains(e.target) || rail.contains(e.target)) return;
  flyout.classList.add('hidden');
});
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    document.querySelector('.rail-flyout-container')?.classList.add('hidden');
  }
});
</script>
""")
```

## 4. CSS — `styles/layout/sidebar.css` (renombrado conceptualmente a rail)

Reemplazar el contenido de la sección sidebar:

```css
/* ── Rail principal ── */
:root {
  --rail-width: 60px;
}

.andes-rail {
  position: fixed;
  top: var(--topbar-height);
  left: 0;
  bottom: 0;
  width: var(--rail-width);
  background: var(--nav-sidebar-bg);
  border-right: 1px solid var(--nav-sidebar-border);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-md) 0;
  gap: 6px;
  z-index: 900;
}

.rail-brand {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--space-md);
}

.rail-logo-img {
  width: 36px;
  height: 36px;
  object-fit: contain;
  border-radius: var(--radius-md);
}

.rail-monogram {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 18px;
  color: var(--ink-700);
  letter-spacing: -0.02em;
}

/* ── Items ── */
.rail-item {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  cursor: pointer;
  position: relative;
  transition: background 0.15s ease;
  color: var(--graphite-700);
}

.rail-item:hover {
  background: var(--nav-sidebar-hover);
  color: var(--ink-700);
}

.rail-item.is-active {
  background: var(--ink-100);
  color: var(--ink-700);
}

.rail-item.is-active::before {
  content: "";
  position: absolute;
  left: -8px;          /* la barra cuelga del borde del rail */
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  background: var(--accent-600);
}

.rail-icon {
  font-size: 22px;
}

/* ── Tooltip nativo ── */
.rail-item[data-tooltip]:hover::after {
  content: attr(data-tooltip);
  position: absolute;
  left: calc(100% + 12px);
  top: 50%;
  transform: translateY(-50%);
  background: var(--graphite-900);
  color: #FFFFFF;
  font-size: var(--font-size-small);
  padding: 6px 10px;
  border-radius: var(--radius-md);
  white-space: nowrap;
  pointer-events: none;
  z-index: 950;
  box-shadow: var(--shadow-md);
}

.rail-divider {
  width: 24px;
  height: 1px;
  background: var(--paper-200);
  margin: 8px 0;
}

/* ── Flyout ── */
.rail-flyout-container {
  position: fixed;
  left: calc(var(--rail-width) + 8px);
  width: 240px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  padding: 8px;
  z-index: 940;
  transform-origin: left center;
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.rail-flyout-container.hidden {
  opacity: 0;
  pointer-events: none;
  transform: scale(0.95);
}

.flyout-header {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: var(--font-size-h4);
  color: var(--ink-700);
  padding: 8px 12px 12px 12px;
  border-bottom: 1px solid var(--color-divider);
  margin-bottom: 6px;
}

.flyout-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--graphite-700);
  position: relative;
}

.flyout-item:hover {
  background: var(--ink-050);
}

.flyout-item.is-active {
  background: var(--ink-100);
  color: var(--ink-700);
  font-weight: 600;
}

.flyout-item.is-active::before {
  content: "";
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  background: var(--accent-600);
}

.flyout-icon {
  flex-shrink: 0;
}

.flyout-label {
  font-size: var(--font-size-body);
}

@media (prefers-reduced-motion: reduce) {
  .rail-flyout-container,
  .rail-item { transition: none; }
}
```

## 5. Cambios en `.andes-main`

El rail tiene ancho fijo. El contenido principal se desplaza:

```css
.andes-main {
  margin-left: var(--rail-width);
  /* sin transición porque el rail no se mueve */
}
```

Elimina `.andes-main.sidebar-collapsed` (ya no aplica).

## 6. Eliminación del toggle del topbar

En `_topbar()` (layout.py), quitar el bloque del `topbar-toggle-btn`:

```python
# Antes
if toggle_callback:
    toggle_btn_inner = ui.element("div").classes("topbar-toggle-btn")
    ...

# Después: BORRADO completo. brand area no incluye toggle.
```

El parámetro `toggle_callback` se elimina de la firma de `_topbar()` y de
`app_layout()`. Esto es breaking change interno; no hay callers fuera del módulo
que lo usen (verificar con grep).

## 7. Mecanismo activo para grupos

```python
def _calcular_activo(item: dict, ruta_activa: str) -> bool:
    if "ruta" in item:
        return item["ruta"] == ruta_activa
    if "children" in item:
        return any(
            c.get("ruta") == ruta_activa
            for c in item["children"]
        )
    return False
```

## 8. Alternativa descartada

**Rail con expansión-on-hover (hover sobre el rail revela labels en su mismo
espacio).** Descartada: empuja contenido en cuanto el cursor entra al rail, que
es prácticamente siempre cuando vas a la izquierda. Frustrante y dañino para
planilla de notas. El flyout solo aparece cuando hay intención (click), no por
trayectoria del cursor.

## 9. Orden de tareas

1. T1: Variables CSS (`--rail-width`) + estructura base `.andes-rail`.
2. T2: Items del rail + tooltip + estado activo.
3. T3: Flyout container + estilos + animación.
4. T4: JS para cerrar al click-fuera + ESC.
5. T5: Reescribir `_sidebar()` → `_rail()` en layout.py.
6. T6: Eliminar toggle del topbar.
7. T7: Ajustar `.andes-main` (margin-left fijo).
8. T8: Smoke visual + reporte.
9. T9: Verificación final.
