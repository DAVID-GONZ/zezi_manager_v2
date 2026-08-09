# Tasks: mejora_10a — Auto-hospedaje de fuentes

Prerrequisitos: ninguno. Cero cambio visual esperado.

---

## T1 — Obtener y subsetear los woff2

**Carpeta:** `src/interface/design/assets/fonts/`
- Descargar/subsetear (latin + latin-ext) a woff2:
  - Inter pesos 400, 500, 600, 700.
  - Source Serif 4 pesos 400, 600, 700.
  - Material Symbols Rounded (variable font, un archivo con axes `opsz,wght,FILL,GRAD`).
- Añadir `assets/fonts/README.md` con el comando de regeneración (`glyphhanger`/`fonttools`)
  y la licencia (OFL) de cada familia.
- *criterio*: archivos presentes; peso total documentado.

---

## T2 — Declarar `@font-face` en un CSS core

**Archivo nuevo:** `src/interface/design/styles/fonts.css` (tier CORE)
- Un `@font-face` por peso/familia, todos con `font-display: swap` y `src: url('/static/fonts/…')`.
- Material Symbols: `@font-face` de la variable font + conservar la clase
  `.material-symbols-rounded` si hoy vive en un `@import` (declararla aquí si hace falta).
- **No** tocar las variables `--font-*` de `tokens.css`.

---

## T3 — Registrar `fonts.css` primero en el orden de carga

**Archivo:** `src/interface/design/theme.py`
- Insertar `"fonts.css"` como **primer** elemento de `CSS_LOAD_ORDER` (antes de `tokens.css`).
- *criterio*: `python -c "from src.interface.design.theme import ThemeManager; print(ThemeManager.CSS_LOAD_ORDER[0])"` → `fonts.css`.

---

## T4 — Servir los estáticos

**Archivo:** `main.py` (o donde se llama `ThemeManager.aplicar()`)
- `app.add_static_files('/static/fonts', <ruta absoluta a assets/fonts>)`.
- Verificar que la ruta resuelve (arrancar la app y pedir un `.woff2` por URL).

---

## T5 — Quitar los `@import` externos

**Archivo:** `src/interface/design/styles/tokens.css`
- Eliminar las 3 líneas `@import url('https://fonts.googleapis.com/...')`.
- *criterio*: `grep -rn "fonts.googleapis" src/interface/design/styles/` → 0 resultados.

---

## T6 — Verificación final

- `python scripts/check_design.py --all` → verde (regla N incluida).
- `python init.py` → verde.
- Arrancar la app: iconos Material Symbols renderizan; sin FOIT; sin llamadas a `fonts.googleapis.com`
  en la pestaña de red.
