# paso_13e — Legacy Buttons & Badges Cleanup: spec

**Fecha:** 2026-06-08
**Status sugerido:** spec_ready

## Problema

Hallazgos de la auditoría de paso_13a que el validador `init.py` no detecta:

### H1 — Botones inline con `.props("flat round dense...")` (4 ocurrencias)
```
estudiantes.py:317  ui.button(_fila_editar).props("flat round dense size=sm color=primary")
estudiantes.py:319  ui.button(_fila_retirar).props("flat round dense size=sm color=negative")
estudiantes.py:321  ui.button(_fila_piar).props("flat round dense size=sm color=secondary")
habilitaciones.py:243  ui.button("Cancelar").props("flat")
```

### H5 — Badges con `.props("color=...")` Quasar (3 ocurrencias)
```
estudiantes.py:303          ui.badge(...).props(f"color={_color} rounded")
configuracion_sie.py:726    ui.badge(...).props(f"color={color_badge}")
configuracion_sie.py:771    ui.badge("sub-cats").props("color=teal outline")
```

### H6 — `style=` inline (10 ocurrencias en 6 archivos)
- `login.py:2`, `estudiantes.py:1`, `planes_mejoramiento.py:2`,
  `comportamiento.py:2`, `notas_convivencia.py:1`, `observaciones.py:2`.
- Algunas son estáticas (violación) y otras dinámicas (aceptable). Requiere
  revisión caso por caso.

## Objetivo

Limpieza técnica final del design system: cero usos de API Quasar cruda en pages,
cero estilos inline estáticos, todos los botones a través de `btn_*`.

## Tareas

### T1 — Migrar botones inline (estudiantes.py:317-321)

Antes:
```python
with ui.button(on_click=_fila_editar).props("flat round dense size=sm color=primary").classes("btn-icon").tooltip("Editar estudiante"):
    ThemeManager.icono(Icons.EDIT, size=16)
```

Después:
```python
btn_icon(Icons.EDIT, on_click=_fila_editar, tooltip="Editar estudiante", variante="primary")
btn_icon(Icons.DELETE, on_click=_fila_retirar, tooltip="Retirar matrícula", variante="danger")
btn_icon(Icons.PIAR, on_click=_fila_piar, tooltip="Ver / registrar PIAR", variante="secondary")
```

Verificar primero la firma de `btn_icon` — si no acepta `variante`, extenderla.

### T2 — Migrar botón Cancelar (habilitaciones.py:243)

Si el dialog se migra a `confirm_dialog` en paso_13c, este botón desaparece
automáticamente. Si paso_13c aún no se ejecuta, usar `btn_secondary("Cancelar", on_click=dlg.close)`.

### T3 — Migrar badges con `.props("color=...")`

#### estudiantes.py:303
```python
# Antes
ui.badge(fila["estado_str"]).props(f"color={_color} rounded")
# Después
status_badge(fila["estado_str"], variante=_mapear_color_a_variante(_color))
# o si _color ya es semántico:
status_badge(fila["estado_str"], variante=fila["estado_variante"])
```

#### configuracion_sie.py:726, 771
Idem — mapear `color_badge` a variantes del design system (`success/warning/error/info/neutral`).

### T4 — Auditar `style=` inline caso por caso

Por cada archivo, revisar las ocurrencias:
- **Si el valor es estático** (`style="color: red"`) → mover a clase CSS.
- **Si el valor es dinámico** (`style=f"background: {color_dominio}"`) → mantener (excepción documentada).

Para los dinámicos, considerar exponer la clase CSS con variantes en lugar de inyectar
el valor (`status_badge` ya lo hace bien).

## Criterio done

- `grep -E "ui\.button.*\.props\(" src/interface/pages/` → 0 ocurrencias.
- `grep -E "ui\.badge.*\.props\(.*color=" src/interface/pages/` → 0 ocurrencias.
- `style=` inline estáticos: 0. Dinámicos: documentados en el spec con justificación.
- 740 tests verdes; init.py verde.

## Notas

- Si los pasos 13b, 13c, 13d se ejecutan antes, algunas de estas violaciones
  desaparecen como efecto colateral (botón Cancelar de habilitaciones lo hace
  paso_13c). Ejecutar 13e al final del bloque 13b-13e para evitar trabajo duplicado.
