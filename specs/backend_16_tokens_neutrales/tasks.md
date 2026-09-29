# Tareas: backend_16_tokens_neutrales

> SCOPE — archivos que pueden editarse:
> `tokens.json` (crear), `scripts/sync_tokens.py` (reescribir),
> `scripts/css_to_tokens_json.py` (crear, temporal),
> `src/interface/design/styles/tokens.css` (regenerar),
> `tests/unit/design/test_tokens_roundtrip.py` (crear).
>
> Fuera de scope: los valores de los tokens (no se renombran ni eliminan),
> componentes CSS, paginas NiceGUI.
>
> No depende de la API REST. Puede ejecutarse en paralelo con Fase 3.

---

## T1 — Parsear tokens.css actual a JSON

Crear `scripts/css_to_tokens_json.py` que:
1. Lee `src/interface/design/styles/tokens.css`.
2. Extrae las 187 variables y sus valores.
3. Genera un `tokens.json` plano (sin clasificacion).
4. Imprime el JSON a stdout.

**Verificacion:** `python scripts/css_to_tokens_json.py | python -m json.tool`
genera JSON valido con 187 entradas.

---

## T2 — Clasificar tokens en 3 capas

Editar el `tokens.json` generado para clasificar las 187 variables en:
- `primitives` (~100 tokens: colores hex, spacing, font sizes, shadows)
- `semantic` (~60 tokens: color-primary, color-surface, etc.)
- `component` (~27 tokens: button-*, input-*, card-*, etc.)

Agregar `$type` a cada token. Agregar referencias `{...}` donde
un token semantico apunta a un primitivo.

**Verificacion:** `python -c "import json; d=json.load(open('tokens.json'));
total=sum(len(g) for l in d.values() if isinstance(l,dict) for g in l.values() if isinstance(g,dict));
print(total)"` imprime >= 187.

---

## T3 — Reescribir sync_tokens.py

Reescribir `scripts/sync_tokens.py` para que:
1. Lea `tokens.json` como fuente.
2. Resuelva referencias (`{primitives.color.ink-900}` -> `#1a1a2e`).
3. Genere `tokens.css` con el formato actual.
4. Genere `tokens.py` con el formato actual.
5. Con `--emit-ts`: genere `tokens.ts`.
6. Con `--check`: verifique que los derivados estan sincronizados.

**Verificacion:** `python scripts/sync_tokens.py --check` pasa.

---

## T4 — Regenerar tokens.css y comparar

Ejecutar `python scripts/sync_tokens.py` y comparar el CSS generado
con el original via diff. Las diferencias deben ser solo de formato
(orden, whitespace), no de contenido.

**Verificacion:** `diff` entre el CSS original y el generado.
Verificacion visual en el navegador: la app se ve igual.

---

## T5 — Test de round-trip

Crear `tests/unit/design/test_tokens_roundtrip.py`:
- Lee `tokens.json`.
- Genera CSS, PY, TS en memoria.
- Compara contra los archivos en disco.
- Falla si hay drift.

**Verificacion:** `pytest tests/unit/design/test_tokens_roundtrip.py`.

---

## T6 — Integrar en init.py

Verificar que `init.py` ya llama a `sync_tokens.py --check`.
Si no, anadirlo.

---

## T7 — Eliminar css_to_tokens_json.py

El script de migracion es de un solo uso. Eliminarlo del repo tras
verificar que `tokens.json` esta completo.

---

## T8 — Verificacion de no regresion y cierre

```
.venv/Scripts/python.exe scripts/init.py
```
TODO VERDE. `check_design.py --all` pasa. La app se ve igual.

**Artefacto:** `progress/impl_backend_16.md`.
