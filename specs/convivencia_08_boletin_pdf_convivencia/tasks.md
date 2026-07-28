# convivencia_08_boletin_pdf_convivencia — Tasks

## Objetivo
`boletin_pdf.py` usa `datos["convivencia"]` (inyectado en convivencia_07)
para rellenar la caja "OBSERVACIONES Y RECOMENDACIONES" que hoy está vacía.
Si no hay datos de convivencia (clave ausente o None), la caja queda en
blanco como antes — compatibilidad total hacia atrás.

## Scope
```
src/infrastructure/exporters/boletin_pdf.py
tests/unit/infrastructure/test_boletin_pdf.py   ← crear si no existe
```
**Nada más.**

## Diseño

### Cambio en `_observaciones_y_firmas`
La función pasa de firma `(page_w: float)` a `(page_w: float, convivencia: dict | None = None)`.

Cuando `convivencia` tiene datos, sustituir la celda vacía por contenido:

```
OBSERVACIONES Y RECOMENDACIONES:
┌───────────────────────────────────────────────────────┐
│ Comportamiento: 85.0 (Alto)                           │
│                                                       │
│ • Buen desempeño en clase.                            │
│ • Cumple con las normas de convivencia.               │
└───────────────────────────────────────────────────────┘
```

La nota de comportamiento se muestra como `"Comportamiento: {valor}"`.
Si `nota_observacion` existe, se muestra en la misma línea o siguiente.
Las observaciones públicas van como lista de viñetas (•).
Si no hay nada → caja vacía (comportamiento anterior).

### Implementación en la caja ReportLab
Reemplazar la celda vacía `[[""] * 1]` por un `Paragraph` que renderiza
el texto de convivencia con los estilos `_sty["normal"]` y `_sty["bold"]`
ya definidos en el módulo. La altura de la caja aumenta dinámicamente con
`rowHeights=None` (auto) cuando hay contenido; mantiene `2.2 * cm` cuando está vacía.

### Actualización de call sites
`_observaciones_y_firmas` se llama en 2 lugares:
- línea ~465 dentro de `generar_boletin_periodo_pdf` (usa `datos.get("convivencia")`)
- línea ~550 dentro de `generar_boletin_acumulado_pdf` (usa `datos.get("convivencia")`)

Actualizar ambas llamadas para pasar el dict.

## Tareas

### T1 — Modificar `_observaciones_y_firmas`
**Archivo**: `src/infrastructure/exporters/boletin_pdf.py`

1. Añadir parámetro `convivencia: dict | None = None`.
2. Construir el contenido de texto:
   - Si `convivencia` es None o `{"nota": None, "observaciones": []}` → lista vacía de texto (caja en blanco).
   - Si hay `nota` → línea `f"Comportamiento: {convivencia['nota']:.1f}"` con estilo `"bold"`.
   - Si hay `nota_observacion` → añadir a continuación con estilo `"normal"`.
   - Para cada texto en `convivencia["observaciones"]` → `Paragraph(f"• {texto}", _sty["normal"])`.
3. Si hay contenido: reemplazar la celda vacía por un `Table` con el `Paragraph` y `rowHeights=None` (auto).
4. Si no hay contenido: mantener la celda vacía con `rowHeights=[2.2 * cm]` (como antes).

### T2 — Actualizar call sites
**Archivo**: `src/infrastructure/exporters/boletin_pdf.py`

En `generar_boletin_periodo_pdf(datos)`:
```python
story.extend(_observaciones_y_firmas(page_w, datos.get("convivencia")))
```

En `generar_boletin_acumulado_pdf(datos)`:
```python
story.extend(_observaciones_y_firmas(page_w, datos.get("convivencia")))
```

### T3 — Tests
**Archivo**: `tests/unit/infrastructure/test_boletin_pdf.py` (crear)

Importar:
```python
from src.infrastructure.exporters.boletin_pdf import (
    generar_boletin_periodo_pdf,
    generar_boletin_acumulado_pdf,
)
```

Construir `datos_minimos` con la estructura mínima que ya esperan las funciones
(campos vacíos de `estudiante`, `areas`, `periodos`, etc.) más `convivencia`.

Tests:
- **T3a** `test_boletin_periodo_sin_convivencia`: `datos` sin clave `convivencia` → retorna bytes PDF no vacíos. La sección de observaciones tiene caja vacía (no lanza excepción).
- **T3b** `test_boletin_periodo_con_nota`: `convivencia={"nota": 78.5, "nota_observacion": None, "observaciones": []}` → bytes no vacíos.
- **T3c** `test_boletin_acumulado_con_obs`: `convivencia={"nota": 90.0, "nota_observacion": "Excelente", "observaciones": ["Puntual", "Colaborativo"]}` → bytes no vacíos.
- **T3d** `test_boletin_sin_nota_con_obs`: `convivencia={"nota": None, "nota_observacion": None, "observaciones": ["Mejorar actitud"]}` → bytes no vacíos.

Verificación:
```
.venv/Scripts/python.exe -m pytest tests/unit/infrastructure/test_boletin_pdf.py -v
```

## criterio_done
- [ ] `_observaciones_y_firmas` acepta parámetro `convivencia`.
- [ ] Caja vacía cuando no hay datos (compatibilidad hacia atrás).
- [ ] Nota y observaciones visibles cuando hay datos.
- [ ] Ambos call sites actualizados.
- [ ] 4 tests T3a..T3d verdes.
- [ ] `.venv/Scripts/python.exe init.py --quick` → ENTORNO OK.
