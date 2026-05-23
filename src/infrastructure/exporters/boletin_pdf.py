"""
boletin_pdf.py — Generador de boletines formales con ReportLab.

Produce un PDF por estudiante con:
  - Membrete institucional + espacio para logo
  - Ficha del estudiante (nombre, documento, grupo, periodo/año)
  - Tabla Área > Asignatura con nota(s) y asistencia por tipo
  - Boletín por periodo: una columna de nota + 5 columnas de asistencia
  - Boletín anual: una columna por periodo + definitiva + 5 de asistencia anual
  - Espacio para observaciones y firmas
"""
from __future__ import annotations

import io
from datetime import date as _date
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)

# ── Paleta ────────────────────────────────────────────────────────────────────

_AZUL       = colors.HexColor("#2B6CB0")
_AZUL_CLARO = colors.HexColor("#DBEAFE")
_AREA_BG    = colors.HexColor("#E2E8F0")
_AREA_FG    = colors.HexColor("#1A365D")
_GRIS_LINEA = colors.HexColor("#CBD5E0")
_GRIS_TEXTO = colors.HexColor("#374151")
_BLANCO     = colors.white

# ── Estilos ───────────────────────────────────────────────────────────────────

_ss = getSampleStyleSheet()

_sty = {
    "normal": ParagraphStyle(
        "BN", parent=_ss["Normal"],
        fontSize=8, leading=10, textColor=_GRIS_TEXTO,
    ),
    "bold": ParagraphStyle(
        "BB", parent=_ss["Normal"],
        fontSize=8, leading=10, fontName="Helvetica-Bold", textColor=_GRIS_TEXTO,
    ),
    "title": ParagraphStyle(
        "BT", parent=_ss["Normal"],
        fontSize=12, leading=14, fontName="Helvetica-Bold", textColor=_AZUL,
    ),
    "subtitle": ParagraphStyle(
        "BSub", parent=_ss["Normal"],
        fontSize=9, leading=11, fontName="Helvetica-Bold", textColor=_GRIS_TEXTO,
    ),
    "cell": ParagraphStyle(
        "BC", parent=_ss["Normal"],
        fontSize=7, leading=8.5, textColor=_GRIS_TEXTO,
    ),
    "cell_c": ParagraphStyle(
        "BCC", parent=_ss["Normal"],
        fontSize=7, leading=8.5, textColor=_GRIS_TEXTO, alignment=1,
    ),
    "cell_bold": ParagraphStyle(
        "BCB", parent=_ss["Normal"],
        fontSize=7, leading=8.5, fontName="Helvetica-Bold", textColor=_GRIS_TEXTO,
    ),
    "cell_bold_c": ParagraphStyle(
        "BCBC", parent=_ss["Normal"],
        fontSize=7, leading=8.5, fontName="Helvetica-Bold",
        textColor=_GRIS_TEXTO, alignment=1,
    ),
    "hdr": ParagraphStyle(
        "BH", parent=_ss["Normal"],
        fontSize=7, leading=8.5, fontName="Helvetica-Bold",
        textColor=_BLANCO, alignment=1,
    ),
    "hdr_l": ParagraphStyle(
        "BHL", parent=_ss["Normal"],
        fontSize=7, leading=8.5, fontName="Helvetica-Bold",
        textColor=_BLANCO,
    ),
    "area": ParagraphStyle(
        "BA", parent=_ss["Normal"],
        fontSize=7.5, leading=9, fontName="Helvetica-Bold",
        textColor=_AREA_FG,
    ),
    "promo": ParagraphStyle(
        "BP", parent=_ss["Normal"],
        fontSize=9, leading=11, fontName="Helvetica-Bold",
        textColor=_AZUL,
    ),
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _p(text, style="cell") -> Paragraph:
    val = "—" if (text is None or str(text).strip().lower() == "none") else str(text)
    return Paragraph(val, _sty[style])


def _nota(n) -> str:
    if n is None:
        return "—"
    try:
        return f"{float(n):.1f}"
    except (ValueError, TypeError):
        return str(n)


def _pct(presentes: int, fi: int, retrasos: int) -> str:
    total = presentes + fi + retrasos
    if total == 0:
        return "—"
    return f"{round(presentes / total * 100)}%"


# ── Membrete ──────────────────────────────────────────────────────────────────

def _membrete(page_w: float, titulo_doc: str, grupo: str, periodo: str) -> Table:
    """Tabla de encabezado con espacio para logo + datos institucionales."""
    logo_cell = Table(
        [[""]],
        colWidths=[2.8 * cm],
        rowHeights=[1.6 * cm],
    )
    logo_cell.setStyle(TableStyle([
        ("BOX",        (0, 0), (-1, -1), 0.5, _GRIS_LINEA),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
    ]))

    inst_lines = (
        "<b>INSTITUCIÓN EDUCATIVA ZECI</b><br/>"
        f"{titulo_doc}<br/>"
        f"Curso: {grupo} &nbsp;&nbsp; {periodo}"
    )
    info_right = f"Generado: {_date.today().strftime('%d/%m/%Y')}"

    membrete_data = [[
        logo_cell,
        Paragraph(inst_lines, ParagraphStyle(
            "MInst", parent=_ss["Normal"],
            fontSize=8.5, leading=12, textColor=_AZUL,
        )),
        Paragraph(info_right, ParagraphStyle(
            "MDate", parent=_ss["Normal"],
            fontSize=7.5, leading=10, textColor=_GRIS_TEXTO, alignment=2,
        )),
    ]]
    tbl = Table(
        membrete_data,
        colWidths=[3 * cm, page_w - 3 * cm - 3 * cm, 3 * cm],
    )
    tbl.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (1, 0), (1, 0),   8),
        ("RIGHTPADDING", (2, 0), (2, 0),   0),
        ("LINEBELOW",    (0, 0), (-1, -1), 1.2, _AZUL),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
    ]))
    return tbl


# ── Ficha del estudiante ──────────────────────────────────────────────────────

def _ficha(estudiante: dict, page_w: float) -> Table:
    """Dos columnas: datos del estudiante a la izquierda, info extra a la derecha."""
    izq = (
        f"<b>Estudiante:</b> {estudiante.get('nombre', '')}  &nbsp;&nbsp;"
        f"<b>Documento:</b> {estudiante.get('documento', '')}"
    )
    der = (
        f"<b>Grupo:</b> {estudiante.get('grupo', '')}  &nbsp;&nbsp;"
        f"<b>Año:</b> {estudiante.get('anio', estudiante.get('periodo', ''))}"
    )
    sty_ficha = ParagraphStyle(
        "Ficha", parent=_ss["Normal"],
        fontSize=8, leading=11, textColor=_GRIS_TEXTO,
    )
    tbl = Table(
        [[Paragraph(izq, sty_ficha), Paragraph(der, sty_ficha)]],
        colWidths=[page_w * 0.6, page_w * 0.4],
    )
    tbl.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND",   (0, 0), (-1, -1), _AZUL_CLARO),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("BOX",          (0, 0), (-1, -1), 0.5, _AZUL),
    ]))
    return tbl


# ── Tabla de notas por periodo ────────────────────────────────────────────────

_HDR_ASIST = ["P", "FI", "FJ", "R", "E", "%"]

def _tabla_periodo(areas: list[dict], page_w: float) -> Table:
    """
    Tabla Area > Asignatura para boletín de periodo.
    Columnas: Área/Asignatura | Nota | P | FI | FJ | R | E | %
    """
    # Anchos: primera col 38%, nota 12%, 6 asistencia * 8.33% = 50%
    w0 = page_w * 0.38
    w_nota = page_w * 0.12
    w_asist = (page_w - w0 - w_nota) / 6
    col_w = [w0, w_nota] + [w_asist] * 6

    hdrs = ["Área / Asignatura", "Nota"] + _HDR_ASIST
    table_data: list[list] = [
        [_p(h, "hdr" if i == 0 else "hdr") for i, h in enumerate(hdrs)]
    ]
    # Override primer encabezado a izquierda
    table_data[0][0] = _p("Área / Asignatura", "hdr_l")

    ts = [
        ("BACKGROUND",    (0, 0), (-1, 0),  _AZUL),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  _BLANCO),
        ("GRID",          (0, 0), (-1, -1), 0.4, _GRIS_LINEA),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",         (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (0, -1),  6),
        ("LEFTPADDING",   (1, 0), (-1, -1), 2),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 2),
    ]

    row_idx = 1
    for area in areas:
        # Fila de área
        area_cell = [_p(f"▪ {area['area_nombre'].upper()}", "area")]
        area_row   = area_cell + [_p("", "cell")] * 7
        table_data.append(area_row)
        ts.append(("BACKGROUND", (0, row_idx), (-1, row_idx), _AREA_BG))
        ts.append(("SPAN",       (0, row_idx), (0,  row_idx)))
        row_idx += 1

        # Filas de asignaturas
        for asig in area["asignaturas"]:
            p   = asig.get("presentes", 0)
            fi  = asig.get("faltas_injustificadas", 0)
            fj  = asig.get("faltas_justificadas", 0)
            r   = asig.get("retrasos", 0)
            e   = asig.get("excusas", 0)
            row = [
                _p(f"  {asig['nombre']}", "cell"),
                _p(_nota(asig.get("nota")), "cell_c"),
                _p(str(p),  "cell_c"),
                _p(str(fi), "cell_c"),
                _p(str(fj), "cell_c"),
                _p(str(r),  "cell_c"),
                _p(str(e),  "cell_c"),
                _p(_pct(p, fi, r), "cell_c"),
            ]
            table_data.append(row)
            if row_idx % 2 == 0:
                ts.append(("BACKGROUND", (0, row_idx), (-1, row_idx),
                            colors.HexColor("#F9FAFB")))
            row_idx += 1

    tbl = Table(table_data, colWidths=col_w, repeatRows=1)
    tbl.setStyle(TableStyle(ts))
    return tbl


# ── Tabla de notas anual ──────────────────────────────────────────────────────

def _tabla_anual(
    areas: list[dict],
    periodos: list[dict],
    page_w: float,
    label_definitiva: str = "Def.",
) -> Table:
    """
    Tabla Area > Asignatura para boletín anual.
    Columnas: Área/Asignatura | P1 | P2 | ... | Pn | Def. | P | FI | FJ | R | E | %
    """
    n_per = len(periodos)
    # n_per columnas de periodo + 1 definitiva + 6 asistencia
    n_extra = n_per + 1 + 6

    # Ancho mínimo por col extra: 0.7 cm, primera col toma el resto
    w_extra = max(page_w * 0.08, 0.7 * cm)
    # Ajustar si no caben
    total_extra = w_extra * n_extra
    if total_extra > page_w * 0.70:
        w_extra = (page_w * 0.70) / n_extra
    w0 = page_w - total_extra

    col_w = [w0] + [w_extra] * n_extra

    # Encabezados
    per_hdrs = [p["nombre"] for p in periodos]
    hdrs = ["Área / Asignatura"] + per_hdrs + [label_definitiva] + _HDR_ASIST
    table_data: list[list] = [[
        (_p(h, "hdr_l") if i == 0 else _p(h, "hdr"))
        for i, h in enumerate(hdrs)
    ]]

    ts = [
        ("BACKGROUND",    (0, 0), (-1, 0),  _AZUL),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  _BLANCO),
        ("GRID",          (0, 0), (-1, -1), 0.4, _GRIS_LINEA),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",         (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (0, -1),  6),
        ("LEFTPADDING",   (1, 0), (-1, -1), 2),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 2),
    ]

    # Columna definitiva (resaltada ligeramente)
    col_def = 1 + n_per
    ts.append(("BACKGROUND", (col_def, 1), (col_def, -1),
                colors.HexColor("#EFF6FF")))

    row_idx = 1
    for area in areas:
        area_row = [_p(f"▪ {area['area_nombre'].upper()}", "area")] + [_p("")] * n_extra
        table_data.append(area_row)
        ts.append(("BACKGROUND", (0, row_idx), (-1, row_idx), _AREA_BG))
        row_idx += 1

        for asig in area["asignaturas"]:
            notas_p = asig.get("notas_periodo", {})
            p  = asig.get("presentes", 0)
            fi = asig.get("faltas_injustificadas", 0)
            fj = asig.get("faltas_justificadas", 0)
            r  = asig.get("retrasos", 0)
            e  = asig.get("excusas", 0)

            cells_periodo = [
                _p(_nota(notas_p.get(per["id"])), "cell_c")
                for per in periodos
            ]
            definitiva = asig.get("definitiva")
            row = (
                [_p(f"  {asig['nombre']}", "cell")]
                + cells_periodo
                + [_p(_nota(definitiva), "cell_bold_c")]
                + [
                    _p(str(p),  "cell_c"),
                    _p(str(fi), "cell_c"),
                    _p(str(fj), "cell_c"),
                    _p(str(r),  "cell_c"),
                    _p(str(e),  "cell_c"),
                    _p(_pct(p, fi, r), "cell_c"),
                ]
            )
            table_data.append(row)
            if row_idx % 2 == 0:
                ts.append(("BACKGROUND", (0, row_idx), (-1, row_idx),
                            colors.HexColor("#F9FAFB")))
            row_idx += 1

    tbl = Table(table_data, colWidths=col_w, repeatRows=1)
    tbl.setStyle(TableStyle(ts))
    return tbl


# ── Sección de observaciones y firmas ─────────────────────────────────────────

def _observaciones_y_firmas(page_w: float) -> list:
    """Bloque inferior: caja de observaciones + líneas de firma."""
    story: list = []
    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width=page_w, thickness=0.5, color=_GRIS_LINEA))
    story.append(Spacer(1, 0.3 * cm))

    # Título observaciones
    story.append(_p("OBSERVACIONES Y RECOMENDACIONES:", "bold"))
    story.append(Spacer(1, 0.15 * cm))

    # Caja vacía para escribir
    obs_data = [[""] * 1]
    obs_tbl = Table(obs_data, colWidths=[page_w], rowHeights=[2.2 * cm])
    obs_tbl.setStyle(TableStyle([
        ("BOX",        (0, 0), (-1, -1), 0.5, _GRIS_LINEA),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAFA")),
    ]))
    story.append(obs_tbl)
    story.append(Spacer(1, 0.5 * cm))

    # Firmas: 3 columnas
    firma_sty = ParagraphStyle(
        "Firma", parent=_ss["Normal"],
        fontSize=7.5, leading=10, textColor=_GRIS_TEXTO, alignment=1,
    )
    linea = "___________________________"
    firmas_data = [[
        Paragraph(f"{linea}<br/>Director(a) de Grupo", firma_sty),
        Paragraph(f"{linea}<br/>Rector(a)", firma_sty),
        Paragraph(f"{linea}<br/>Acudiente / Estudiante", firma_sty),
    ]]
    firmas_tbl = Table(
        firmas_data,
        colWidths=[page_w / 3] * 3,
    )
    firmas_tbl.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",   (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(firmas_tbl)
    return story


# ── Funciones públicas ────────────────────────────────────────────────────────

def generar_boletin_periodo_pdf(datos: dict[str, Any]) -> bytes:
    """
    Genera el boletín de periodo formal como PDF.

    Args:
        datos: estructura retornada por
               ``IEstadisticosRepository.boletin_datos_periodo()``.
    """
    buf = io.BytesIO()
    est    = datos.get("estudiante", {})
    areas  = datos.get("areas", [])

    n_asigs = sum(len(a.get("asignaturas", [])) for a in areas)
    # Si hay muchas asignaturas, usar landscape
    page_size = landscape(A4) if n_asigs > 20 else A4

    doc = SimpleDocTemplate(
        buf,
        pagesize=page_size,
        leftMargin=1.8 * cm, rightMargin=1.8 * cm,
        topMargin=1.5 * cm,  bottomMargin=1.5 * cm,
    )
    page_w = page_size[0] - 3.6 * cm

    story: list = []
    story.append(_membrete(
        page_w,
        titulo_doc="BOLETÍN DE CALIFICACIONES POR PERIODO",
        grupo=est.get("grupo", ""),
        periodo=f"Periodo: {est.get('periodo', '')}",
    ))
    story.append(Spacer(1, 0.35 * cm))
    story.append(_ficha(est, page_w))
    story.append(Spacer(1, 0.35 * cm))

    if areas:
        story.append(_tabla_periodo(areas, page_w))
    else:
        story.append(_p("No hay datos de calificaciones para este periodo.", "normal"))

    story.extend(_observaciones_y_firmas(page_w))

    doc.build(story)
    return buf.getvalue()


def generar_boletin_acumulado_pdf(datos: dict[str, Any]) -> bytes:
    """
    Genera el boletín acumulado de un periodo como PDF.

    Muestra todos los periodos del año hasta el actual.
    La columna resumen se llama "Prom." para periodos intermedios
    y "Def." para el último periodo del año.

    Args:
        datos: estructura retornada por
               ``IEstadisticosRepository.boletin_datos_acumulado()``.
    """
    es_ultimo        = datos.get("es_ultimo_periodo", False)
    label_definitiva = "Def." if es_ultimo else "Prom."
    return _build_boletin_anual_pdf(datos, label_definitiva)


def _build_boletin_anual_pdf(datos: dict[str, Any], label_definitiva: str = "Def.") -> bytes:
    """Builder interno compartido por generar_boletin_anual_pdf y generar_boletin_acumulado_pdf."""
    buf      = io.BytesIO()
    est      = datos.get("estudiante", {})
    periodos = datos.get("periodos", [])
    areas    = datos.get("areas", [])

    n_asigs   = sum(len(a.get("asignaturas", [])) for a in areas)
    usar_land = len(periodos) > 3 or n_asigs > 18
    page_size = landscape(A4) if usar_land else A4

    doc = SimpleDocTemplate(
        buf,
        pagesize=page_size,
        leftMargin=1.8 * cm, rightMargin=1.8 * cm,
        topMargin=1.5 * cm,  bottomMargin=1.5 * cm,
    )
    page_w = page_size[0] - 3.6 * cm

    estado     = est.get("estado_promocion", "")
    _PROMO_MAP = {
        "promovido": "PROMOVIDO(A)",
        "reprobado": "NO PROMOVIDO(A)",
        "pendiente": "EN PROCESO",
    }
    estado_txt = _PROMO_MAP.get(estado.lower(), estado.upper()) if estado else ""

    # Título: para boletín acumulado usamos el nombre del periodo actual
    periodo_label = est.get("periodo", "")
    if periodo_label:
        titulo_doc = "BOLETÍN ACUMULADO DE CALIFICACIONES"
        periodo_str = f"Hasta: {periodo_label}"
    else:
        titulo_doc  = "BOLETÍN ANUAL DE CALIFICACIONES"
        periodo_str = f"Año lectivo: {est.get('anio', '')}"

    story: list = []
    story.append(_membrete(
        page_w,
        titulo_doc=titulo_doc,
        grupo=est.get("grupo", ""),
        periodo=periodo_str,
    ))
    story.append(Spacer(1, 0.35 * cm))
    story.append(_ficha(
        {**est, "periodo": periodo_str},
        page_w,
    ))
    story.append(Spacer(1, 0.35 * cm))

    if areas and periodos:
        story.append(_tabla_anual(areas, periodos, page_w, label_definitiva=label_definitiva))
    else:
        story.append(_p("No hay datos registrados.", "normal"))

    if estado_txt:
        story.append(Spacer(1, 0.35 * cm))
        story.append(Paragraph(
            f"Estado de promoción: <b>{estado_txt}</b>",
            _sty["promo"],
        ))

    story.extend(_observaciones_y_firmas(page_w))
    doc.build(story)
    return buf.getvalue()


def generar_boletin_anual_pdf(datos: dict[str, Any]) -> bytes:
    """
    Genera el boletín anual formal como PDF.

    Args:
        datos: estructura retornada por
               ``IEstadisticosRepository.boletin_datos_anual()``.
    """
    return _build_boletin_anual_pdf(datos, label_definitiva="Def.")


__all__ = [
    "generar_boletin_periodo_pdf",
    "generar_boletin_acumulado_pdf",
    "generar_boletin_anual_pdf",
]
