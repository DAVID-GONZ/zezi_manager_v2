# Diseno: backend_17_contratos_componentes

## Punto de partida medido

| Componente | Estado |
|---|---|
| `CLASS_CONTRACT.md` | Existe, lista clases CSS y sus reglas |
| `PORTABILITY.md` | Existe, define la frontera Core/Adapter |
| `tokens.css` | 187 tokens, fuente del design system |
| Componentes CSS en `styles/` | ~24 archivos, organizados por dominio |
| Documentacion de componentes | No existe como spec formal |

## D1 — Estructura del documento

```markdown
# Catalogo de Componentes — Design System Aula Serena

## Como usar este catalogo
...

## Badge
### Proposito
Etiqueta visual para estado, categoria o conteo.
### Variantes
- success, warning, danger, info, neutral
### Estados
- default, disabled
### Clases CSS
- `.andes-badge`, `.andes-badge--success`, ...
### Tokens consumidos
- `--color-success`, `--color-warning`, `--border-radius-sm`, ...
### A11y
- role="status" cuando es dinamico
### Ejemplo
Un badge verde con texto "Aprobado" y esquinas redondeadas.

## Button
...
```

## D2 — Fuentes para documentar

El implementer debe leer:
1. `CLASS_CONTRACT.md` — clases y reglas de cada componente.
2. `styles/components/*.css` — implementacion real de cada componente.
3. `tokens.css` — tokens que cada componente consume.
4. `PORTABILITY.md` — que es core (portable) y que es adapter.
5. `src/interface/design/components/*.py` — uso actual en NiceGUI (para
   entender props y estados, no para copiar el render).
6. `form_fields.py` — la puerta unica de inputs.

## D3 — Generacion semi-automatica

Un script auxiliar puede extraer automaticamente:
- Clases de cada archivo CSS (`grep` de selectores).
- Tokens consumidos (`grep` de `var(--`).
- Variantes (sufijos BEM: `--success`, `--danger`, etc.).

La clasificacion por proposito, los estados y la a11y se
documentan manualmente.

## Alternativa descartada

**Generar documentacion desde el codigo con pydoc/typedoc.**
Los componentes de NiceGUI son Python y las clases CSS estan
en archivos separados. No hay un formato unico del que extraer todo.
La documentacion manual es el unico camino que cubre las 7 dimensiones.
