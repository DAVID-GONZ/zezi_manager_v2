# paso_13c — Dialog Consolidation: spec

**Fecha:** 2026-06-08
**Status sugerido:** spec_ready
**Prerequisito:** paso_10j (confirm_dialog existe) + paso_10k (form_dialog existe)

## Problema

8 ocurrencias de `ui.dialog()` inline en 5 archivos de `src/interface/pages/`:

| Archivo | Línea | Naturaleza | Componente destino |
|---|---|---|---|
| `cierre_periodo.py` | 174 | Confirmación de cierre | `confirm_dialog` |
| `cierre_periodo.py` | 203 | Confirmación cierre asignación | `confirm_dialog` |
| `cierre_periodo.py` | 254 | Confirmación post-cierre | `confirm_dialog` |
| `cierre_anio.py` | 83 | Confirmación cierre año | `confirm_dialog` |
| `habilitaciones.py` | 236 | Confirmación de eliminación | `confirm_dialog` |
| `horarios.py` | 260 | Form crear/editar bloque | `form_dialog` |
| `estudiantes.py` | 399 | Form CSV masivo | `form_dialog` |
| `estudiantes.py` | 542 | Form PIAR | `form_dialog` |

Consecuencia: UX inconsistente en operaciones críticas (cierres destructivos). Los
dialogs inline usan `ui.card().classes("w-full max-w-md")` con estilos divergentes.

## Objetivo

Migrar las 8 ocurrencias a `confirm_dialog()` o `form_dialog()` según naturaleza,
preservando el comportamiento exacto (handlers, validaciones, mensajes).

## API de los componentes

### `confirm_dialog`

```python
from src.interface.design.components import confirm_dialog

confirm_dialog(
    titulo="Cerrar periodo",
    mensaje="¿Estás seguro? Esta operación es irreversible.",
    on_confirm=lambda: _ejecutar_cierre(),
    variante="danger",  # o "warning" / "primary"
    label_confirmar="Cerrar periodo",
    label_cancelar="Cancelar",
)
```

### `form_dialog`

```python
from src.interface.design.components import form_dialog

form_dialog(
    titulo="Editar bloque de horario",
    campos=[
        {"key": "dia", "label": "Día", "tipo": "select", "opciones": [...]},
        {"key": "hora_inicio", "label": "Hora inicio", "tipo": "time"},
        ...
    ],
    valores_iniciales={"dia": "Lunes", ...},
    on_submit=lambda data: _guardar_bloque(data),
    label_submit="Guardar",
)
```

## Tareas

| # | Archivo | Cambio |
|---|---|---|
| T1 | `cierre_periodo.py` × 3 | Reemplazar 3 dialogs con `confirm_dialog(variante="danger")`. Preservar texto de mensajes y handlers `on_confirm`. |
| T2 | `cierre_anio.py` × 1 | Idem T1 |
| T3 | `habilitaciones.py` × 1 | `confirm_dialog(variante="danger")` para eliminación |
| T4 | `horarios.py` × 1 | `form_dialog` con campos día/hora_inicio/hora_fin/asignatura |
| T5 | `estudiantes.py` × 2 | (a) `form_dialog` con upload csv (b) `form_dialog` con campos PIAR |
| T6 | Tests + init.py verde | — |

## Criterio done

- `grep -E "ui\.dialog\(\)" src/interface/pages/` → 0 ocurrencias.
- `grep -E "confirm_dialog\(" src/interface/pages/` → ≥ 8 (existentes + 5 nuevos).
- `grep -E "form_dialog\(" src/interface/pages/` → ≥ 12 (existentes + 3 nuevos).
- Operaciones de cierre siguen funcionando: cierre_periodo, cierre_anio.
- Form de horarios crea/edita bloques correctamente.
- CSV masivo de estudiantes sube y reporta éxitos/errores.
- Form PIAR guarda con los mismos campos previos.
- 740 tests verdes; init.py verde.

## Notas

- `form_dialog` puede no soportar `upload` (CSV de estudiantes) — verificar primero en
  `src/interface/design/components/form_dialog.py`. Si no soporta, opciones:
  (a) extender `form_dialog` para incluir tipo `"upload"`, o
  (b) dejar el dialog de CSV masivo inline y documentar excepción.
- El form PIAR puede tener campos `textarea` largos — verificar que `base_form` los
  renderiza correctamente.
