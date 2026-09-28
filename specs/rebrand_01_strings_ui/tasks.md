# rebrand_01_strings_ui — Tareas

Scope: solo los archivos listados en `destino_v2` del paso. Cualquier otro
archivo -> PARAR y reportar al leader.

---

## T1 — APP_NAME en `config.py`

**Artefacto:** `config.py`

- Linea 72: `APP_NAME: str = "ZECI Manager"` -> `APP_NAME: str = "AVEDRA"`.
- Linea 2: docstring `config.py — Configuracion centralizada de ZECI Manager v2.0`
  -> `config.py — Configuracion centralizada de AVEDRA v2.0`.
- Linea 86: ejemplo de URL `zeci` -> `avedra`.

**Verificacion:**
```
python -c "from config import AppConfig; assert AppConfig().APP_NAME == 'AVEDRA'"
```

---

## T2 — Docstring de `main.py`

**Artefacto:** `main.py`

- Linea 2: `ZECI Manager v2.0` -> `AVEDRA v2.0`.

---

## T3 — Docstring de `login.py`

**Artefacto:** `src/interface/pages/login.py`

- Linea 2: `ZECI Manager v2.0` -> `AVEDRA v2.0`.

---

## T4 — Docstring de `theme.py`

**Artefacto:** `src/interface/design/theme.py`

- Linea 2: `ZECI Manager v2.0` -> `AVEDRA v2.0`.

---

## T5 — Pie de pagina en exportadores

**Artefactos:** `src/infrastructure/exporters/observador_pdf.py`,
`src/infrastructure/exporters/observador_excel.py`

- `observador_pdf.py:556`: `"Sistema ZECI Manager"` -> `"Sistema AVEDRA"`.
- `observador_excel.py:474`: `"Sistema ZECI Manager"` -> `"Sistema AVEDRA"`.

**Verificacion:**
```
grep -rn "ZECI" src/infrastructure/exporters/observador_*.py
```
Sin resultados.

---

## Cierre del paso

```
grep -rn "ZECI Manager" config.py main.py src/interface/pages/login.py src/interface/design/theme.py src/infrastructure/exporters/observador_*.py
python -m ruff check config.py main.py src/interface/pages/login.py src/interface/design/theme.py src/infrastructure/exporters/observador_pdf.py src/infrastructure/exporters/observador_excel.py --select F821,F811,F632,F702,B006,B008,B023,E9 --output-format concise
```
Sin resultados en grep, ruff verde.

Escribir el resumen en `progress/impl_rebrand_01_strings_ui.md` y
devolver al leader solo esa referencia.
