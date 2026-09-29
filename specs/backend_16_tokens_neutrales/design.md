# Diseno: backend_16_tokens_neutrales

## Punto de partida medido

| Componente | Estado |
|---|---|
| `tokens.css` | 187 variables CSS, fuente actual del design system |
| `tokens.py` | Generado por `sync_tokens.py` desde CSS (flujo CSS->Python) |
| `sync_tokens.py` | Lee CSS, genera Python. Flag `--emit-ts` ya emite TS |
| `tokens.json` | No existe |
| `tokens.ts` | No existe (se genera con `--emit-ts` pero no esta en el repo) |
| `check_design.py` | Verifica tokens en CSS/Python, no sabe de JSON |

## D1 — Estructura de tokens.json

Formato W3C Design Tokens (simplificado):

```json
{
  "$schema": "https://design-tokens.org/schema.json",
  "primitives": {
    "color": {
      "ink-900": { "$value": "#1a1a2e", "$type": "color" },
      "ink-700": { "$value": "#2d2d44", "$type": "color" },
      ...
    },
    "spacing": {
      "xs": { "$value": "0.25rem", "$type": "dimension" },
      ...
    },
    "font": {
      "family-body": { "$value": "Inter, system-ui, sans-serif", "$type": "fontFamily" },
      ...
    }
  },
  "semantic": {
    "color-primary": { "$value": "{primitives.color.primary-500}", "$type": "color" },
    "color-surface": { "$value": "{primitives.color.surface-100}", "$type": "color" },
    ...
  },
  "component": {
    "button-bg": { "$value": "{semantic.color-primary}", "$type": "color" },
    "input-border": { "$value": "{primitives.color.ink-200}", "$type": "color" },
    ...
  }
}
```

La estructura de 3 capas refleja el CSS actual pero organizada:
- Las 187 variables actuales se clasifican en las 3 capas.
- Las referencias (`{...}`) se resuelven al generar CSS/TS/Python.

## D2 — Flujo invertido de sync_tokens.py

**Antes (actual):**
```
tokens.css  --[sync_tokens.py]--> tokens.py
                                  tokens.ts (con --emit-ts)
```

**Despues:**
```
tokens.json --[sync_tokens.py]--> tokens.css
                                  tokens.py
                                  tokens.ts
```

El script cambia de "parser de CSS" a "resolutor de JSON + emitter".

## D3 — Generacion de tokens.css desde JSON

```python
def generar_css(tokens: dict) -> str:
    lines = [":root {"]
    for layer in ("primitives", "semantic", "component"):
        for group in tokens.get(layer, {}).values():
            for name, token in group.items():
                value = resolver_referencia(token["$value"], tokens)
                lines.append(f"  --{name}: {value};")
    lines.append("}")
    return "\n".join(lines)
```

El dark mode se define como un grupo `"dark"` en el JSON con la misma
estructura y se genera como bloque `[data-theme="dark"]`.

## D4 — Generacion de tokens.ts

```typescript
// Auto-generated from tokens.json — do not edit
export const Colors = {
  INK_900: "#1a1a2e",
  ...
} as const;

export const Spacing = {
  XS: "0.25rem",
  ...
} as const;
```

## D5 — Migracion inicial: CSS -> JSON (una sola vez)

Un script auxiliar `scripts/css_to_tokens_json.py` parsea el CSS
actual y genera el `tokens.json` inicial. Despues se descarta.
La clasificacion en primitivo/semantico/componente se hace manualmente
sobre el resultado.

## Alternativa descartada

**Style Dictionary (Amazon).** Herramienta madura pero introduce una
dependencia Node.js en un toolchain 100% Python. Para 187 tokens,
un script propio de ~150 lineas es suficiente y mantenible.
