# Design: mejora_10a — Auto-hospedaje de fuentes y carga no bloqueante

> **Origen:** evaluación de modernidad del design system (2026-08-09).
> **Tipo:** mejora de rendimiento/robustez de la capa visual. No cambia el diseño.
> **Prerrequisitos:** ninguno (trabaja sobre el design system actual).

---

## Problema

`styles/tokens.css` carga las 3 familias tipográficas con `@import` a Google Fonts:

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:...&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:...');  /* SIN display=swap */
```

Tres defectos:
1. **Render-blocking:** `@import` dentro de CSS **serializa** la descarga (el navegador
   descubre las fuentes tarde) — peor que `<link>`.
2. **Material Symbols sin `display=swap`** → FOIT: los iconos quedan **invisibles**
   hasta que baja la fuente.
3. **Dependencia externa de Google:** rompe en offline y en los builds **Tauri/Capacitor**
   (Etapa B), y añade una llamada a terceros (privacidad).

## Objetivo

Servir las 3 fuentes **desde la propia app** (woff2 subseteado), con `font-display: swap`,
sin ninguna llamada externa. Cero cambio visual.

---

## 1. Ubicación de los assets

Carpeta nueva `src/interface/design/assets/fonts/` con los `.woff2`:
- `inter-{400,500,600,700}.woff2` (subset latin + latin-ext).
- `source-serif-4-{400,600,700}.woff2` (los pesos realmente usados; ver `--font-display`).
- `material-symbols-rounded.woff2` (axes `opsz,wght,FILL,GRAD` — variable font; un solo archivo).

> Subset con `glyphhanger`/`fonttools` (latin+latin-ext) para minimizar peso. Documentar
> el comando usado en un `README.md` de la carpeta para regenerarlos.

## 2. Declaración `@font-face`

Archivo core nuevo `styles/fonts.css` (tier CORE, portable), cargado **primero** en
`ThemeManager.CSS_LOAD_ORDER` (antes de `tokens.css`, que ya no importa nada externo):

```css
@font-face {
  font-family: 'Inter'; font-style: normal; font-weight: 400;
  font-display: swap;                      /* clave: swap en TODAS, incl. Material Symbols */
  src: url('/static/fonts/inter-400.woff2') format('woff2');
}
/* … 500/600/700, Source Serif 4, y Material Symbols Rounded (variable) … */
```

Las variables `--font-family`, `--font-display`, `--font-mono` de `tokens.css` **no cambian**
(siguen apuntando a los mismos nombres de familia).

## 3. Servir los assets estáticamente

NiceGUI expone estáticos con `app.add_static_files(url_path, local_dir)`. En `main.py`
(donde se llama `ThemeManager.aplicar()`), registrar:

```python
app.add_static_files('/static/fonts', str(Path(__file__).parent /
    'src/interface/design/assets/fonts'))
```

Las URLs de `@font-face` (`/static/fonts/...`) resuelven contra esa ruta. En el fork Vue
las mismas woff2 se copian a `public/fonts/` (transfiere).

## 4. Quitar los `@import` externos

Eliminar las 3 líneas `@import url('https://fonts.googleapis.com/...')` de `tokens.css`.
`tokens.css` queda 100% sin red externa.

---

## Verificación

- `grep -rn "fonts.googleapis" src/interface/design/styles/` → **0 resultados**.
- La app arranca; los iconos Material Symbols renderizan (no cuadros □) y no hay FOIT.
- `python scripts/check_design.py --all` y `python init.py` en verde.
- (Opcional) Lighthouse: desaparecen los avisos de render-blocking de fuentes.
