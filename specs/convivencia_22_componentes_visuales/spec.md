# convivencia_22_componentes_visuales — Spec

## Contexto

Las páginas de convivencia son monótonas (todo `panel-card` + listas). El hub de
Seguimiento (convivencia_25) necesita **contadores con estado de alerta** y una
**gráfica pequeña de evolución**. Se crean dos componentes reutilizables por toda
la app, respetando la regla dura del design system (tokens en `tokens.css`, clases
del `CLASS_CONTRACT`, sin hex/px hardcodeados). ECharts es la excepción documentada
(no lee variables CSS).

Lectura obligatoria antes de implementar:
`src/interface/design/components/stat_card.py` (patrón a seguir),
`src/interface/pages/academico/tablero_estadisticos.py` (helpers de color ECharts),
`src/interface/design/styles/CLASS_CONTRACT.md`, `tokens.css`, `PORTABILITY.md`.

## Requisitos (EARS)

- **R1** — `counter_card(...)` DEBE renderizar un tile compacto (título, valor,
  icono) con un estado de alerta visible (color + icono) cuando `alerta=True`.
- **R2** — `mini_chart(...)` DEBE renderizar una serie pequeña (línea) vía
  `ui.echart`, legible en claro y oscuro, usando helpers de color (no variables CSS).
- **R3** — No DEBE haber hex/px hardcodeados fuera de la excepción ECharts; las
  clases nuevas viven en `styles/components/` y pasan `check_design --all`,
  `sync_tokens --check` y `audit_design --strict`.

## Diseño

### `src/interface/design/components/counter_card.py`
```python
def counter_card(titulo: str, valor, icono: str, *,
                 variante: str = "neutral", alerta: bool = False,
                 subtitulo: str = "") -> None: ...
```
- Usa clases CSS: `.counter-card`, `.counter-card--alert` (cuando `alerta`),
  `.counter-card-value`, `.counter-card-label`, `.counter-card-icon`.
- Variantes (`neutral|primary|success|warning|danger|info`) mapean a tokens
  semánticos existentes (mismo enfoque que `stat_card`). NO redefinir colores:
  reutilizar variables de `tokens.css`.
- Icono vía `ThemeManager.icono(...)` (como el resto de componentes).

### `src/interface/design/components/mini_chart.py`
```python
def mini_chart(labels: list[str], valores: list[float | None], *,
               titulo: str = "", clase: str = "echart-sm") -> None: ...
```
- Devuelve un `ui.echart({...})` tipo `line`, con `xAxis.data=labels`,
  `series[0].data=valores`, `smooth`, tooltip.
- Colores tomados de los helpers de `tablero_estadisticos.py` (bloque `_EC_*` /
  funciones de color); si no hay uno reutilizable, definir constantes de color
  locales documentadas como excepción ECharts (igual que en tablero).
- Clase de tamaño `echart-sm`: si no existe en `styles/`, añadirla junto a
  `echart-md/echart-lg`.

### CSS
- Nuevo archivo `src/interface/design/styles/components/counter-card.css` y su
  registro en el orden de carga (buscar `CSS_LOAD_ORDER` en `theme.py`).
- `echart-sm` en el archivo de estilos donde vivan `echart-md/lg`.

### Exports
- Registrar `counter_card` y `mini_chart` en `components/__init__.py` (`__all__`).

## Tareas

- **T1** — `counter_card.py` + registro en `__init__.py`.
- **T2** — `mini_chart.py` + registro en `__init__.py`.
- **T3** — CSS: `counter-card.css` (+ orden de carga) y `echart-sm`.
- **T4** — Tests unitarios mínimos: ambos importables y renderizan sin excepción
  con datos de ejemplo (patrón de `tests/unit/interface/design/`).

## Verificación final
```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_design.py --all
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/sync_tokens.py --check
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/audit_design.py --strict
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe init.py
```
Ambos componentes importables desde `src.interface.design.components`; init.py verde.
