# Tasks — paso_12d_rail_navigation

## Resumen

| ID | Descripción | Archivos | Verificación |
|---|---|---|---|
| T1 | Var --rail-width + `.andes-rail` base | tokens.css, sidebar.css | grep |
| T2 | `.rail-item` + tooltip + estado activo | sidebar.css | smoke visual |
| T3 | `.rail-flyout-container` + animación | sidebar.css | smoke visual |
| T4 | Script JS de cierre click-fuera + ESC | layout.py (add_body_html) | manual |
| T5 | Reescribir _sidebar() → _rail() | layout.py | init.py |
| T6 | Quitar toggle del topbar | layout.py | grep |
| T7 | .andes-main con margin fijo | content.css | grep |
| T8 | Smoke visual completo | progress/impl_12d.md | manual |
| T9 | Verificación final | — | init.py + tests |

---

## T1 — Base CSS del rail

En `styles/tokens.css` añadir:

```css
--rail-width: 60px;
```

En `styles/layout/sidebar.css`, eliminar todo el bloque actual de
`.andes-sidebar*` (queda obsoleto) y poner el bloque base del rail según
design.md §4 hasta `.rail-monogram` inclusive.

**Verificación:**
```
grep -c "andes-rail\|rail-brand\|rail-monogram" src/interface/design/styles/layout/sidebar.css
# >= 3
```

---

## T2 — Items del rail

Añadir las reglas `.rail-item`, `.rail-item:hover`, `.rail-item.is-active`,
`.rail-item.is-active::before` (barra accent), `.rail-icon`,
`.rail-item[data-tooltip]:hover::after` (tooltip), `.rail-divider`.

**Verificación visual:** una vez T5 esté hecho, al hover sobre un item aparece
tooltip a la derecha. Item activo muestra barra accent.

---

## T3 — Flyout

Añadir reglas `.rail-flyout-container`, `.rail-flyout-container.hidden`,
`.flyout-header`, `.flyout-item`, `.flyout-item:hover`, `.flyout-item.is-active`,
`.flyout-icon`, `.flyout-label`.

Incluir bloque `@media (prefers-reduced-motion: reduce)`.

---

## T4 — Script JS de cierre

En `layout.py`, dentro de `app_layout()` antes de renderizar el rail, añadir:

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

**Importante:** este script se inyecta una sola vez por página. Si `app_layout`
se invoca múltiples veces en la misma sesión, evitar reinjección (usar bandera
en `app.storage` o `shared=True` si NiceGUI lo soporta).

---

## T5 — Reescribir _sidebar() → _rail()

En `src/interface/design/layout.py`:

1. Borrar la función `_sidebar()` completa.
2. Crear `_rail(usuario_rol, ruta_activa, *, logo_url=None)` según design.md §3.
3. Implementar `_calcular_activo(item, ruta_activa)` (helper).
4. Implementar `_abrir_flyout`, `_cerrar_flyout`, `_toggle_flyout`.
5. En `app_layout()`, reemplazar la llamada a `_sidebar()` por `_rail()` y
   eliminar el código de estado de colapso (`_s = {"collapsed": ...}`, toggle).

**Verificación:**
```
grep "_sidebar\|def _rail" src/interface/design/layout.py
# Debe aparecer _rail; _sidebar debe estar ausente.
```

---

## T6 — Quitar toggle del topbar

En `_topbar()` y `_topbar_legacy` si todavía existiera (12a debió borrarlo):

1. Quitar el parámetro `toggle_callback` de la firma.
2. Quitar el bloque del `topbar-toggle-btn` dentro del `topbar-brand`.
3. Mantener el `topbar-brand` como decoración (logo de app o vacío).

Quitar también el CSS asociado en `styles/layout/topbar.css`:
`.topbar-toggle-btn`, `.topbar-toggle-btn:hover`.

**Verificación:**
```
grep "toggle_callback\|topbar-toggle-btn" src/interface/design/
# Vacío
```

---

## T7 — .andes-main fijo

En `styles/layout/content.css`:

```css
/* Antes */
.andes-main {
  margin-left: var(--sidebar-width);
  transition: margin-left ...;
}
.andes-main.sidebar-collapsed {
  margin-left: var(--sidebar-collapsed);
}

/* Después */
.andes-main {
  margin-left: var(--rail-width);
}
/* Eliminar .andes-main.sidebar-collapsed completo */
```

---

## T8 — Smoke visual

Arrancar app. Probar:

1. Click en cada icono del rail sin hijos → navega correctamente.
2. Click en icono con hijos → flyout aparece a la derecha.
3. Click en otro icono con hijos → flyout se reposiciona y muestra los nuevos.
4. Click en subitem del flyout → navega y flyout se cierra.
5. Click fuera del rail/flyout → flyout se cierra.
6. ESC → flyout se cierra.
7. Hover sobre icono sin hijos → tooltip aparece a la derecha.
8. Sección activa muestra barra accent y fondo `ink-100`.
9. Logo institucional aparece arriba (si está configurado), o monograma "ZM".
10. Roles: login como profesor, verificar que Admin no aparece. Login como
    coordinador, verificar items de admin filtrados correctamente.

Reportar en `progress/impl_12d.md` cada punto con OK / observación.

---

## T9 — Verificación final

```
python init.py           # verde
pytest tests/ --tb=short # verde
```

Reviewer:
- `_sidebar` no existe en el código.
- `toggle_callback` no existe en el código.
- El script JS de cierre no se inyecta más de una vez por carga de página.
- El flyout cierra correctamente con ESC y click fuera.
- El rail no se mueve al cambiar de página.
