# Diseno: backend_18_css_desacoplado

## Punto de partida medido

| Componente | Estado |
|---|---|
| `styles/` | ~24 archivos CSS, ~3200 lineas |
| `styles/adapter/` | Archivos que estilan DOM de Quasar/ag-Grid |
| `styles/core/` | CSS portable semantico |
| `PORTABILITY.md` | Define la frontera Core/Adapter |
| `check_design.py` regla N | Bloquea `.q-*`, `.ag-*` fuera de adapter |
| `!important` | ~135 heredados, mayoria overrides de Quasar |

## D1 — Script de auditoria

Crear `scripts/audit_css_portability.py` que:

1. Recorra todos los `.css` en `styles/`.
2. Clasifique cada archivo como core o adapter.
3. Cuente lineas por categoria.
4. Extraiga selectores de framework (`.q-*`, `.ag-*`, `.nicegui-*`).
5. Cuente `!important` por archivo.
6. Genere el informe en markdown.

```python
FRAMEWORK_PATTERNS = [
    re.compile(r'\.q-'),      # Quasar
    re.compile(r'\.ag-'),     # ag-Grid
    re.compile(r'\.nicegui'), # NiceGUI
]
```

## D2 — HTML de verificacion

Un archivo `docs/design_system/portability_test.html` que:

```html
<!DOCTYPE html>
<html>
<head>
  <link rel="stylesheet" href="../../src/interface/design/styles/tokens.css">
  <link rel="stylesheet" href="../../src/interface/design/styles/core/badges.css">
  <link rel="stylesheet" href="../../src/interface/design/styles/core/buttons.css">
  <!-- ... demas core -->
</head>
<body>
  <div class="andes-badge andes-badge--success">Aprobado</div>
  <button class="andes-button andes-button--primary">Guardar</button>
  <!-- ... demas componentes -->
</body>
</html>
```

Se abre en el navegador directamente (file://) y debe verse correcto
sin JS, sin Quasar, sin NiceGUI.

## D3 — Estructura del informe

```markdown
# Auditoria de portabilidad CSS — Design System Aula Serena

## Resumen
- Core portable: X lineas (Y%)
- Adapter a reescribir: Z lineas (W%)
- Total: X+Z lineas

## Archivos Core (portables)
| Archivo | Lineas | Tokens usados | Estado |
|---|---|---|---|

## Archivos Adapter (requieren reescritura)
| Archivo | Lineas | Selectores de framework | !important |
|---|---|---|---|

## !important por archivo
...

## Violaciones de frontera
(encontradas por audit_css_portability.py fuera de check_design.py)

## Recomendaciones para Vue
### Copiar tal cual
### Reescribir contra DOM nativo
### Eliminar
```

## Alternativa descartada

**Ejecutar un build de purge CSS para identificar CSS muerto.**
PurgeCSS depende de Node.js y del HTML renderizado por NiceGUI.
Un script Python que analiza selectores es suficiente y no
introduce dependencias.
