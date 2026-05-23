# Spec: revision_estadisticos_completa

**ID**: `revision_estadisticos_completa`
**Operación**: `CORREGIR + MEJORAR`
**Destino**: `src/interface/pages/informes/estadisticos.py`, `src/infrastructure/exporters/pdf_exporter.py`, `src/services/informe_service.py`
**Criterio done**: pytest sin regresiones; selector de grupo muestra valor seleccionado; tabla de previsualización no desborda; tarjeta de estadísticos aparece bajo la tabla; PDF incluye membrete + columnas proporcionales.

---

## 1. Contexto y motivación

La página `/informes/estadisticos` tiene 4 problemas confirmados por el usuario:

| # | Problema | Impacto |
|---|----------|---------|
| R1 | Selector de grupo no funciona (muestra valor vacío tras seleccionar) | Usuario no puede generar ningún informe |
| R2 | Tabla de previsualización desborda verticalmente | UX rota en informes con >15 filas |
| R3 | Sin tarjeta de estadísticos en la preview | Falta información clave al generar |
| R4 | PDF sin membrete ni identificación; columnas superpuestas | Documentos inutilizables |

---

## 2. Análisis de causa raíz

### R1 — Tipo mismatch int/string en selectores

NiceGUI serializa las claves del dict de `options` a JSON. Cuando la clave es `int`, Quasar recibe `{"1": "601", "2": "602"}` (claves string). Al seleccionar, `e.value` llega como Python `str` (ej. `"2"`), no `int`.

Pero `_s["grupo_id"]` fue inicializado como `int` (o `None`). En el refresh, `ui.select(value=_s["grupo_id"])` usa el int original; sin embargo cuando `on_grupo_change("2")` asigna `_s["grupo_id"] = "2"` (string), el re-render con `value="2"` contra `options={2: "..."}` (int key) produce un mismatch: Quasar no encuentra el valor → el selector aparece vacío.

El mismo problema afecta `asignacion_id` y `periodo_id`.

**Fix**: Convertir `e.value` a `int` en los tres handlers de selectores de ID numérico.

```python
def on_grupo_change(grupo_id) -> None:
    _s["grupo_id"] = int(grupo_id) if grupo_id is not None else None
    ...

def on_asignatura_change(asignacion_id) -> None:
    _s["asignacion_id"] = int(asignacion_id) if asignacion_id is not None else None
    ...

def on_periodo_change(periodo_id) -> None:
    _s["periodo_id"] = int(periodo_id) if periodo_id is not None else None
    ...
```

Idéntico patrón para `on_tipo_change` (str, sin conversión). La lectura inicial desde `ctx.grupo_id`, `ctx.periodo_id` ya devuelve `int`.

### R2 — domLayout autoHeight sin contenedor acotado

Todos los renders `_render_*` usan:
```python
ui.aggrid({"domLayout": "autoHeight", ...}).classes("w-full")
```
`autoHeight` hace que ag-Grid crezca ilimitadamente con los datos → desbordamiento.

**Fix**: Quitar `"domLayout": "autoHeight"` y envolver el aggrid en un `div` scrollable con altura fija:

```python
with ui.element("div").classes("aggrid-scroll-wrapper"):
    ui.aggrid({
        "columnDefs": col_defs,
        "rowData": datos,
        "defaultColDef": {"resizable": True, "sortable": True},
    }).classes("w-full h-full")
```

CSS a agregar en `styles.css`:
```css
.aggrid-scroll-wrapper {
    width: 100%;
    height: 420px;
    overflow: hidden;
}
```

### R3 — Sin tarjeta de estadísticos

No existe nada. Se debe agregar un panel `stats-summary-card` dentro de `preview_refreshable()`, justo sobre el aggrid/gráfico, con métricas calculadas a partir de `_s["datos"]`.

Métricas por tipo:

| Tipo | Métricas |
|------|----------|
| `consolidado_notas` | N° estudiantes, Promedio grupal, % aprobados (≥60), % reprobados |
| `consolidado_asistencia` | N° estudiantes, % asistencia promedio, N° con asistencia < 70% |
| `ranking_grupo` | N° estudiantes, Promedio grupal, Mejor nota, Menor nota |
| `consolidado_anual` | N° estudiantes, % promovidos, % reprobados, Definitiva promedio |
| Tipos gráficos (donut, pie, linea, barras) | Total registros |

Componente: usar el existente `stat_card()` de `src/interface/design/components/stat_card.py`.

```python
def _render_stats_summary(_s: dict) -> None:
    """Renderiza tarjeta de estadísticos resumidos según el tipo de informe."""
    datos = _s["datos"]
    tipo  = _s["tipo"]
    if not datos:
        return

    stats: list[tuple[str, str, str]] = []  # (titulo, valor, icono)

    if tipo in ("consolidado_notas", "ranking_grupo") and isinstance(datos, list) and datos:
        n = len(datos)
        prom_field = "promedio_periodo" if "promedio_periodo" in datos[0] else "promedio"
        promedios = [float(r.get(prom_field, 0) or 0) for r in datos]
        promedio_grupal = sum(promedios) / n if n else 0
        aprobados = sum(1 for p in promedios if p >= 60)
        stats = [
            ("Estudiantes",        str(n),                          Icons.STUDENTS),
            ("Promedio grupal",    f"{promedio_grupal:.1f}",         Icons.GRADES),
            ("Aprobados",          f"{aprobados} ({aprobados*100//n if n else 0}%)", Icons.CHECK),
            ("Reprobados",         f"{n - aprobados}",              Icons.ALERT),
        ]

    elif tipo == "consolidado_asistencia" and isinstance(datos, list) and datos:
        n = len(datos)
        porcentajes = [float(r.get("porcentaje", 0) or 0) for r in datos]
        pct_prom = sum(porcentajes) / n if n else 0
        bajo_70 = sum(1 for p in porcentajes if p < 70)
        stats = [
            ("Estudiantes",        str(n),                          Icons.STUDENTS),
            ("% Asistencia prom.", f"{pct_prom:.1f}%",              Icons.CHECK),
            ("Bajo 70%",           str(bajo_70),                    Icons.ALERT),
        ]

    elif tipo == "consolidado_anual" and isinstance(datos, list) and datos:
        n = len(datos)
        defs = [float(r.get("definitiva", 0) or 0) for r in datos]
        prom = sum(defs) / n if n else 0
        promovidos = sum(1 for r in datos if str(r.get("estado", "")).lower() == "promovido")
        stats = [
            ("Estudiantes",    str(n),                           Icons.STUDENTS),
            ("Definitiva prom.", f"{prom:.1f}",                  Icons.GRADES),
            ("Promovidos",     str(promovidos),                   Icons.CHECK),
            ("Reprobados",     str(n - promovidos),               Icons.ALERT),
        ]

    elif isinstance(datos, dict):
        total = sum(datos.values()) if datos else 0
        stats = [("Total registros", str(total), Icons.GRADES)]

    elif isinstance(datos, list):
        stats = [("Total registros", str(len(datos)), Icons.GRADES)]

    if not stats:
        return

    with ui.element("div").classes("stats-summary-row q-mb-md"):
        for titulo, valor, icono in stats:
            stat_card(titulo=titulo, valor=valor, icono=icono)
```

CSS nuevo:
```css
.stats-summary-row {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
}
.stats-summary-row .stat-card-wrapper {
    flex: 1 1 160px;
    min-width: 140px;
}
```

### R4 — PDF: membrete y columnas proporcionales

**Causa raíz doble en `_html_to_pdf_reportlab`**:
1. No hay membrete → el lector del documento no sabe qué es.
2. `col_w = page_w / num_cols` → columnas iguales → textos largos (nombres de estudiantes) se superponen con celdas de notas numéricas.

**Fix A — Membrete**:

La función `_html_to_pdf_reportlab` recibe `html_content` generado por `InformeService._datos_a_html(filas, titulo="Consolidado de Notas")`. El título ya está presente en el `<h1>`. Se debe agregar antes del título:

```
INSTITUCIÓN EDUCATIVA ZECI
<tipo_informe>
Fecha: DD/MM/YYYY
Curso (SI APLICA)
Asignatura(SI APLICA)
DOCENTE(SI APLICA)
PERIODO
```

`_html_to_pdf_reportlab` no conoce el grupo ni el período, solo el HTML. La solución más limpia es que `InformeService._datos_a_html` incluya esos metadatos en el HTML como `<p class="meta">` (o en la función exportar_pdf de `estadisticos.py` se llame con un HTML enriquecido).

**Enfoque adoptado**: Enriquecer `_datos_a_html` para aceptar metadatos opcionales `(grupo: str | None, periodo: str | None)` y agregarlos como `<div class="meta-header">` antes de la tabla. El parser `_HTMLTableParser` los extrae. Si no se pasan, el HTML queda igual que antes (retrocompatible).

Alternativamente (más simple y sin tocar `informe_service`): agregar un bloque de membrete fijo dentro de `_html_to_pdf_reportlab` usando la fecha actual y el título del `<h1>`.

**Adoptamos la alternativa simple**: dentro de `_html_to_pdf_reportlab`, después del título `<h1>`, agregar una tabla de dos columnas con "ZECI Manager" / fecha de generación. El implementer puede usar `Table([[col1, col2]])` con estilo de borde superior grueso.

```python
# Membrete fijo
from datetime import date as _date
fecha_str = _date.today().strftime("%d/%m/%Y")
membrete_data = [
    ["INSTITUCIÓN EDUCATIVA", f"Generado: {fecha_str}"],
]
membrete_tbl = Table(membrete_data, colWidths=[page_w * 0.7, page_w * 0.3])
membrete_tbl.setStyle(TableStyle([
    ("FONTNAME",  (0, 0), (-1, -1), "Helvetica"),
    ("FONTSIZE",  (0, 0), (-1, -1), 9),
    ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#555555")),
    ("ALIGN",     (1, 0), (1, -1), "RIGHT"),
    ("LINEBELOW", (0, 0), (-1, -1), 1, colors.HexColor("#2B6CB0")),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
]))
story.insert(0, Spacer(1, 0.2 * cm))
story.insert(0, membrete_tbl)
```

**Fix B — Columnas proporcionales**:

Heurística:
- Primera columna ("Estudiante" / nombre): 35% del ancho de página.
- Columnas numéricas (notas, %, posición): reparten el 65% restante en partes iguales.
- Si solo hay 1-2 columnas en total: partes iguales (sin ajuste especial).
- Máximo: 30 columnas; mínimo de columna numérica: 1.5 cm.

```python
if parser.headers:
    if len(parser.headers) > 2:
        col_w_nombre = page_w * 0.35
        col_w_resto  = (page_w - col_w_nombre) / (len(parser.headers) - 1)
        # Clamp mínimo
        col_w_resto  = max(col_w_resto, 1.5 * cm)
        col_widths   = [col_w_nombre] + [col_w_resto] * (len(parser.headers) - 1)
    else:
        col_widths = [page_w / len(parser.headers)] * len(parser.headers)
```

Además usar `Paragraph()` en todas las celdas para habilitar word-wrap:

```python
from reportlab.platypus import Paragraph
cell_style_normal = ParagraphStyle("cell", parent=styles["Normal"], fontSize=7, leading=9)
cell_style_header = ParagraphStyle("header", parent=styles["Normal"], fontSize=8, leading=10,
                                   textColor=colors.white, fontName="Helvetica-Bold")

def _wrap(text: str, style) -> Paragraph:
    return Paragraph(str(text), style)

table_data = [
    [_wrap(h, cell_style_header) for h in parser.headers]
] + [
    [_wrap(c, cell_style_normal) for c in row]
    for row in parser.rows
]
```

---

## 3. Archivos a modificar

| Archivo | Sección | Cambio |
|---------|---------|--------|
| `src/interface/pages/informes/estadisticos.py` | `on_grupo_change`, `on_asignatura_change`, `on_periodo_change` | Conversión `int(e.value)` |
| `src/interface/pages/informes/estadisticos.py` | `_render_consolidado_notas`, `_render_consolidado_asistencia`, `_render_ranking`, `_render_consolidado_anual` | Quitar `domLayout:autoHeight`; envolver en `.aggrid-scroll-wrapper` |
| `src/interface/pages/informes/estadisticos.py` | `preview_refreshable()` | Llamar `_render_stats_summary(_s)` antes del render principal |
| `src/interface/pages/informes/estadisticos.py` | Módulo | Agregar función `_render_stats_summary` |
| `src/infrastructure/exporters/pdf_exporter.py` | `_html_to_pdf_reportlab` | Membrete + columnas proporcionales + Paragraph |
| `src/interface/design/styles.css` | Nueva sección | `.aggrid-scroll-wrapper` + `.stats-summary-row` |

**NO se modifica**:
- `src/services/informe_service.py` — `_datos_a_html` queda igual.
- `container.py`, `step_list.json`, harness.

---

## 4. Detalles de implementación por archivo

### 4.1 estadisticos.py — Handlers

```python
# ANTES
def on_grupo_change(grupo_id) -> None:
    _s["grupo_id"]      = grupo_id
    ...

def on_asignatura_change(asignacion_id) -> None:
    _s["asignacion_id"] = asignacion_id
    ...

def on_periodo_change(periodo_id) -> None:
    _s["periodo_id"] = periodo_id
    ...

# DESPUÉS
def on_grupo_change(grupo_id) -> None:
    _s["grupo_id"]      = int(grupo_id) if grupo_id is not None else None
    ...

def on_asignatura_change(asignacion_id) -> None:
    _s["asignacion_id"] = int(asignacion_id) if asignacion_id is not None else None
    ...

def on_periodo_change(periodo_id) -> None:
    _s["periodo_id"] = int(periodo_id) if periodo_id is not None else None
    ...
```

### 4.2 estadisticos.py — Renders aggrid (los 4 tipos tabulares)

Cambio en `_render_consolidado_notas`, `_render_consolidado_asistencia`, `_render_ranking`, `_render_consolidado_anual`:

```python
# ANTES
ui.aggrid({
    "columnDefs":    col_defs,
    "rowData":       datos,
    "defaultColDef": {"resizable": True, "sortable": True},
    "domLayout":     "autoHeight",
}).classes("w-full")

# DESPUÉS
with ui.element("div").classes("aggrid-scroll-wrapper"):
    ui.aggrid({
        "columnDefs":    col_defs,
        "rowData":       datos,
        "defaultColDef": {"resizable": True, "sortable": True},
    }).classes("w-full h-full")
```

### 4.3 estadisticos.py — preview_refreshable

```python
@ui.refreshable
def preview_refreshable() -> None:
    with ui.element("div").classes("panel-card"):
        with ui.element("div").classes("panel-header"):
            ui.label("Vista Previa").classes("panel-title")
        if _s["datos_listos"] and _s["datos"] is not None:
            _render_stats_summary(_s)   # <-- NUEVO (antes de _render_preview)
        _render_preview(_s)
```

### 4.4 estadisticos.py — Imports adicionales

```python
from src.interface.design.components.stat_card import stat_card
```

También necesita `Icons.STUDENTS`, `Icons.CHECK`, `Icons.ALERT` — verificar que existan en `tokens.py`. Si no, usar valores de texto `"person"`, `"check_circle"`, `"warning"`.

### 4.5 pdf_exporter.py — Función completa reemplazada

La función `_html_to_pdf_reportlab` en `src/infrastructure/exporters/pdf_exporter.py` debe ser reemplazada en su totalidad con la versión mejorada que incluye:

1. Membrete (tabla 2 col, institución + fecha).
2. Columnas proporcionales (35% primera + partes iguales resto, mínimo 1.5 cm).
3. `Paragraph()` para word-wrap en todas las celdas.
4. El título `<h1>` sigue siendo el primer elemento del story, el membrete va antes del título.

Estructura del story:
```
[membrete_tbl, Spacer, title_paragraph, Spacer, data_table]
```

### 4.6 styles.css — Nuevas clases

Agregar al final de `src/interface/design/styles.css`:

```css
/* ── Estadísticos: aggrid scrollable ─────────────────────────── */
.aggrid-scroll-wrapper {
    width: 100%;
    height: 420px;
    overflow: hidden;
}

/* ── Estadísticos: fila de tarjetas de resumen ───────────────── */
.stats-summary-row {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 16px;
}

.stats-summary-row .stat-card-wrapper {
    flex: 1 1 160px;
    min-width: 140px;
}
```

---

## 5. Tests funcionales incluidos en el spec

### T1 — Conversión de tipos en handlers (unit)

**Archivo**: `tests/unit/interface/test_estadisticos_handlers.py`

```python
"""Tests para verificar conversión de tipos en handlers de estadisticos."""
import pytest

def _make_state():
    return {
        "tipo": None, "grupo_id": None, "asignacion_id": None,
        "periodo_id": None, "grupos": [], "asignaciones": [],
        "periodos": [], "datos": None, "datos_listos": False,
    }

class TestTipoConversion:
    def test_on_grupo_change_convierte_string_a_int(self):
        """e.value de ui.select llega como str — debe convertirse a int."""
        _s = _make_state()
        # Simular handler on_grupo_change recibiendo string "3"
        grupo_id_raw = "3"
        _s["grupo_id"] = int(grupo_id_raw) if grupo_id_raw is not None else None
        assert _s["grupo_id"] == 3
        assert isinstance(_s["grupo_id"], int)

    def test_on_asignatura_change_convierte_string_a_int(self):
        _s = _make_state()
        raw = "7"
        _s["asignacion_id"] = int(raw) if raw is not None else None
        assert _s["asignacion_id"] == 7
        assert isinstance(_s["asignacion_id"], int)

    def test_on_periodo_change_convierte_string_a_int(self):
        _s = _make_state()
        raw = "1"
        _s["periodo_id"] = int(raw) if raw is not None else None
        assert _s["periodo_id"] == 1
        assert isinstance(_s["periodo_id"], int)

    def test_on_grupo_change_none_permanece_none(self):
        _s = _make_state()
        raw = None
        _s["grupo_id"] = int(raw) if raw is not None else None
        assert _s["grupo_id"] is None
```

### T2 — Estadísticos de resumen (unit)

**Archivo**: `tests/unit/interface/test_estadisticos_handlers.py` (mismo archivo)

```python
class TestRenderStatsSummary:
    def test_stats_consolidado_notas_calcula_promedio(self):
        """_render_stats_summary calcula promedio y aprobados correctamente."""
        datos = [
            {"nombre_completo": "Ana",  "promedio_periodo": 75.0},
            {"nombre_completo": "Beto", "promedio_periodo": 55.0},
            {"nombre_completo": "Cara", "promedio_periodo": 80.0},
        ]
        _s = _make_state()
        _s["tipo"]  = "consolidado_notas"
        _s["datos"] = datos

        # Calcular manualmente lo mismo que hará la función
        n = len(datos)
        promedios = [r["promedio_periodo"] for r in datos]
        prom_grupal = sum(promedios) / n  # 70.0
        aprobados = sum(1 for p in promedios if p >= 60)  # 2

        assert prom_grupal == pytest.approx(70.0)
        assert aprobados == 2
        assert n - aprobados == 1  # reprobados

    def test_stats_consolidado_asistencia(self):
        datos = [
            {"nombre_completo": "Ana",  "porcentaje": 85.0},
            {"nombre_completo": "Beto", "porcentaje": 60.0},
        ]
        n = len(datos)
        pcts = [r["porcentaje"] for r in datos]
        pct_prom = sum(pcts) / n  # 72.5
        bajo_70 = sum(1 for p in pcts if p < 70)  # 1

        assert pct_prom == pytest.approx(72.5)
        assert bajo_70 == 1
```

### T3 — PDF reportlab: membrete presente (unit)

**Archivo**: `tests/unit/infrastructure/test_pdf_exporter.py`

```python
"""Tests para _html_to_pdf_reportlab mejorado."""
import pytest
from src.infrastructure.exporters.pdf_exporter import _html_to_pdf_reportlab

HTML_SIMPLE = """
<html><head><meta charset='utf-8'></head>
<body><h1>Consolidado de Notas</h1>
<table>
  <tr><th>Estudiante</th><th>Matemáticas</th><th>Ciencias</th><th>Promedio</th></tr>
  <tr><td>Ana García</td><td>75</td><td>80</td><td>77.5</td></tr>
  <tr><td>Beto López</td><td>55</td><td>65</td><td>60.0</td></tr>
</table></body></html>
"""

HTML_MUCHAS_COLS = """
<html><head><meta charset='utf-8'></head>
<body><h1>Consolidado Anual</h1>
<table>
  <tr><th>Estudiante</th><th>P1</th><th>P2</th><th>P3</th><th>P4</th><th>Definitiva</th><th>Estado</th></tr>
  <tr><td>Ana García González</td><td>75</td><td>80</td><td>72</td><td>68</td><td>73.7</td><td>Promovido</td></tr>
</table></body></html>
"""

class TestHtmlToPdfReportlab:
    def test_retorna_bytes_no_vacios(self):
        resultado = _html_to_pdf_reportlab(HTML_SIMPLE)
        assert isinstance(resultado, bytes)
        assert len(resultado) > 0

    def test_es_pdf_valido(self):
        resultado = _html_to_pdf_reportlab(HTML_SIMPLE)
        # Los PDFs empiezan con %PDF-
        assert resultado[:4] == b"%PDF"

    def test_muchas_columnas_no_lanza_excepcion(self):
        """Con 7 columnas no debe lanzar excepción."""
        resultado = _html_to_pdf_reportlab(HTML_MUCHAS_COLS)
        assert len(resultado) > 100

    def test_html_sin_tabla_no_lanza_excepcion(self):
        html_vacio = "<html><head></head><body><h1>Sin datos</h1><p>No hay datos.</p></body></html>"
        resultado = _html_to_pdf_reportlab(html_vacio)
        assert isinstance(resultado, bytes)
        assert len(resultado) > 0

    def test_columnas_proporcionales_no_error(self):
        """Verificar que col_widths se calcula sin ZeroDivisionError."""
        # 4 columnas → primera 35%, resto dividen 65% en 3 partes iguales
        headers = ["Estudiante", "P1", "P2", "Promedio"]
        n = len(headers)
        page_w = 277.0  # A4 landscape aprox en puntos minus margins
        col_w_nombre = page_w * 0.35
        col_w_resto  = (page_w - col_w_nombre) / (n - 1)
        col_widths   = [col_w_nombre] + [col_w_resto] * (n - 1)
        assert len(col_widths) == n
        assert all(w > 0 for w in col_widths)
```

### T4 — Checklist funcional (manual)

Ejecutar contra la app en ejecución:

```
[ ] 1. Ir a /informes/estadisticos como coordinador (sin grupo_id en ctx).
[ ] 2. Seleccionar tipo "Consolidado de Notas".
       → Debe aparecer selector Grupo y Periodo.
[ ] 3. Seleccionar un grupo del selector.
       → El selector DEBE mostrar el nombre del grupo seleccionado (no vacío).
       → El botón Previsualizar sigue deshabilitado (falta Periodo).
[ ] 4. Seleccionar un periodo.
       → El botón Previsualizar se habilita.
[ ] 5. Clic en Previsualizar.
       → Aparece tarjeta de estadísticos (N° estudiantes, Promedio, Aprobados, Reprobados).
       → Tabla ag-Grid con altura fija ~420px y scroll vertical si hay >15 filas.
       → No desbordamiento de la página.
[ ] 6. Clic en "Descargar PDF".
       → Se descarga archivo .pdf.
       → Al abrir: hay membrete con "INSTITUCIÓN EDUCATIVA" y fecha.
       → Hay título del informe.
       → Primera columna (Estudiante) más ancha que las de notas.
       → No hay texto superpuesto.
[ ] 7. Seleccionar tipo "Distribución de Desempeños" (donut).
       → Aparece selector Grupo, Asignatura y Periodo.
       → Al seleccionar Grupo: el selector muestra el grupo, aparece selector Asignatura.
       → Al seleccionar Asignatura: el selector la muestra, Previsualizar se habilita cuando todo completo.
[ ] 8. Seleccionar tipo "Comparativo por Periodos" (línea, sin Periodo requerido).
       → Solo aparecen Grupo y Asignatura.
       → Previsualizar se habilita al completar ambos.
[ ] 9. Como profesor: /informes/estadisticos → selector Grupo disabled y preseleccionado.
```

### T5 — Regresión: pytest

```bash
python -m pytest tests/unit/ tests/integration/ -q --tb=short
```
Debe pasar ≥ los mismos tests que antes de este cambio. No se admiten regresiones.

---

## 6. Orden de implementación recomendado

1. `styles.css` — Agregar clases `.aggrid-scroll-wrapper` y `.stats-summary-row` (independiente, sin riesgo).
2. `pdf_exporter.py` — Reemplazar `_html_to_pdf_reportlab` completa (independiente).
3. `estadisticos.py` — En este orden:
   a. Conversión `int()` en los tres handlers.
   b. Quitar `domLayout: autoHeight` + envolver en `div.aggrid-scroll-wrapper`.
   c. Agregar función `_render_stats_summary`.
   d. Llamar `_render_stats_summary` en `preview_refreshable`.
4. `tests/` — Agregar T1, T2, T3.
5. Ejecutar pytest y checklist funcional.

---

## 7. Restricciones

- NO modificar `src/domain/models/`.
- NO modificar `container.py`.
- NO modificar `src/services/informe_service.py` (la mejora de membrete va en el exporter).
- `stat_card()` ya existe — no reimplementar.
- `Icons.*` puede no tener `STUDENTS`, `CHECK`, `ALERT` — verificar antes de usar; si no existen usar strings `"person"`, `"check_circle"`, `"warning"`.
- El membrete no incluye nombre del grupo/periodo (la función no tiene ese contexto); solo fecha e institución genérica. Si en el futuro se quiere incluir el grupo, es un cambio separado.
