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
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ── Paleta ────────────────────────────────────────────────────────────────────

_AZUL = colors.HexColor("#2B6CB0")
_AZUL_CLARO = colors.HexColor("#DBEAFE")
_AREA_BG = colors.HexColor("#E2E8F0")
_AREA_FG = colors.HexColor("#1A365D")
_GRIS_LINEA = colors.HexColor("#CBD5E0")
_GRIS_TEXTO = colors.HexColor("#374151")
_BLANCO = colors.white

# Bins del histograma de notas — sincronizar con openpyxl_exporter.py
_NOTA_BINS = [(60, "<60"), (70, "60-69"), (80, "70-79"), (90, "80-89"), (float("inf"), "90-100")]


def _clasificar_notas(notas: list[float]) -> tuple[list[str], list[int]]:
    labels = [b[1] for b in _NOTA_BINS]
    counts = [0] * len(_NOTA_BINS)
    for n in notas:
        for i, (umbral, _) in enumerate(_NOTA_BINS):
            if n < umbral:
                counts[i] += 1
                break
    return labels, counts

# ── Estilos ───────────────────────────────────────────────────────────────────

_ss = getSampleStyleSheet()

_sty = {
    "normal": ParagraphStyle(
        "BN",
        parent=_ss["Normal"],
        fontSize=8,
        leading=10,
        textColor=_GRIS_TEXTO,
    ),
    "bold": ParagraphStyle(
        "BB",
        parent=_ss["Normal"],
        fontSize=8,
        leading=10,
        fontName="Helvetica-Bold",
        textColor=_GRIS_TEXTO,
    ),
    "title": ParagraphStyle(
        "BT",
        parent=_ss["Normal"],
        fontSize=12,
        leading=14,
        fontName="Helvetica-Bold",
        textColor=_AZUL,
    ),
    "subtitle": ParagraphStyle(
        "BSub",
        parent=_ss["Normal"],
        fontSize=9,
        leading=11,
        fontName="Helvetica-Bold",
        textColor=_GRIS_TEXTO,
    ),
    "cell": ParagraphStyle(
        "BC",
        parent=_ss["Normal"],
        fontSize=7,
        leading=8.5,
        textColor=_GRIS_TEXTO,
    ),
    "cell_c": ParagraphStyle(
        "BCC",
        parent=_ss["Normal"],
        fontSize=7,
        leading=8.5,
        textColor=_GRIS_TEXTO,
        alignment=1,
    ),
    "cell_bold": ParagraphStyle(
        "BCB",
        parent=_ss["Normal"],
        fontSize=7,
        leading=8.5,
        fontName="Helvetica-Bold",
        textColor=_GRIS_TEXTO,
    ),
    "cell_bold_c": ParagraphStyle(
        "BCBC",
        parent=_ss["Normal"],
        fontSize=7,
        leading=8.5,
        fontName="Helvetica-Bold",
        textColor=_GRIS_TEXTO,
        alignment=1,
    ),
    "hdr": ParagraphStyle(
        "BH",
        parent=_ss["Normal"],
        fontSize=7,
        leading=8.5,
        fontName="Helvetica-Bold",
        textColor=_BLANCO,
        alignment=1,
    ),
    "hdr_l": ParagraphStyle(
        "BHL",
        parent=_ss["Normal"],
        fontSize=7,
        leading=8.5,
        fontName="Helvetica-Bold",
        textColor=_BLANCO,
    ),
    "area": ParagraphStyle(
        "BA",
        parent=_ss["Normal"],
        fontSize=7.5,
        leading=9,
        fontName="Helvetica-Bold",
        textColor=_AREA_FG,
    ),
    "promo": ParagraphStyle(
        "BP",
        parent=_ss["Normal"],
        fontSize=9,
        leading=11,
        fontName="Helvetica-Bold",
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


def _pct(presentes: int, fi: int, fj: int, retrasos: int, excusas: int) -> str:
    total = presentes + fi + fj + retrasos + excusas
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
    logo_cell.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, _GRIS_LINEA),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    inst_lines = (
        "<b>INSTITUCIÓN EDUCATIVA ZECI</b><br/>"
        f"{titulo_doc}<br/>"
        f"Curso: {grupo} &nbsp;&nbsp; {periodo}"
    )
    info_right = f"Generado: {_date.today().strftime('%d/%m/%Y')}"

    membrete_data = [
        [
            logo_cell,
            Paragraph(
                inst_lines,
                ParagraphStyle(
                    "MInst",
                    parent=_ss["Normal"],
                    fontSize=8.5,
                    leading=12,
                    textColor=_AZUL,
                ),
            ),
            Paragraph(
                info_right,
                ParagraphStyle(
                    "MDate",
                    parent=_ss["Normal"],
                    fontSize=7.5,
                    leading=10,
                    textColor=_GRIS_TEXTO,
                    alignment=2,
                ),
            ),
        ]
    ]
    tbl = Table(
        membrete_data,
        colWidths=[3 * cm, page_w - 3 * cm - 3 * cm, 3 * cm],
    )
    tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (1, 0), (1, 0), 8),
                ("RIGHTPADDING", (2, 0), (2, 0), 0),
                ("LINEBELOW", (0, 0), (-1, -1), 1.2, _AZUL),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
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
        "Ficha",
        parent=_ss["Normal"],
        fontSize=8,
        leading=11,
        textColor=_GRIS_TEXTO,
    )
    tbl = Table(
        [[Paragraph(izq, sty_ficha), Paragraph(der, sty_ficha)]],
        colWidths=[page_w * 0.6, page_w * 0.4],
    )
    tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (0, 0), (-1, -1), _AZUL_CLARO),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("BOX", (0, 0), (-1, -1), 0.5, _AZUL),
            ]
        )
    )
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

    hdrs = ["Área / Asignatura", "Nota", *_HDR_ASIST]
    table_data: list[list] = [[_p(h, "hdr") for h in hdrs]]
    # Override primer encabezado a izquierda
    table_data[0][0] = _p("Área / Asignatura", "hdr_l")

    ts = [
        ("BACKGROUND", (0, 0), (-1, 0), _AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), _BLANCO),
        ("GRID", (0, 0), (-1, -1), 0.4, _GRIS_LINEA),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (0, -1), 6),
        ("LEFTPADDING", (1, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]

    row_idx = 1
    for area in areas:
        # Fila de área
        area_cell = [_p(f"▪ {area['area_nombre'].upper()}", "area")]
        area_row = area_cell + [_p("", "cell")] * 7
        table_data.append(area_row)
        ts.append(("BACKGROUND", (0, row_idx), (-1, row_idx), _AREA_BG))
        ts.append(("SPAN", (0, row_idx), (0, row_idx)))
        row_idx += 1

        # Filas de asignaturas
        for asig in area["asignaturas"]:
            p = asig.get("presentes", 0)
            fi = asig.get("faltas_injustificadas", 0)
            fj = asig.get("faltas_justificadas", 0)
            r = asig.get("retrasos", 0)
            e = asig.get("excusas", 0)
            row = [
                _p(f"  {asig['nombre']}", "cell"),
                _p(_nota(asig.get("nota")), "cell_c"),
                _p(str(p), "cell_c"),
                _p(str(fi), "cell_c"),
                _p(str(fj), "cell_c"),
                _p(str(r), "cell_c"),
                _p(str(e), "cell_c"),
                _p(_pct(p, fi, fj, r, e), "cell_c"),
            ]
            table_data.append(row)
            if row_idx % 2 == 0:
                ts.append(("BACKGROUND", (0, row_idx), (-1, row_idx), colors.HexColor("#F9FAFB")))
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
    hdrs = ["Área / Asignatura", *per_hdrs, label_definitiva, *_HDR_ASIST]
    table_data: list[list] = [
        [(_p(h, "hdr_l") if i == 0 else _p(h, "hdr")) for i, h in enumerate(hdrs)]
    ]

    ts = [
        ("BACKGROUND", (0, 0), (-1, 0), _AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), _BLANCO),
        ("GRID", (0, 0), (-1, -1), 0.4, _GRIS_LINEA),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (0, -1), 6),
        ("LEFTPADDING", (1, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]

    # Columna definitiva (resaltada ligeramente)
    col_def = 1 + n_per
    ts.append(("BACKGROUND", (col_def, 1), (col_def, -1), colors.HexColor("#EFF6FF")))

    row_idx = 1
    for area in areas:
        area_row = [_p(f"▪ {area['area_nombre'].upper()}", "area")] + [_p("")] * n_extra
        table_data.append(area_row)
        ts.append(("BACKGROUND", (0, row_idx), (-1, row_idx), _AREA_BG))
        row_idx += 1

        for asig in area["asignaturas"]:
            notas_p = asig.get("notas_periodo", {})
            p = asig.get("presentes", 0)
            fi = asig.get("faltas_injustificadas", 0)
            fj = asig.get("faltas_justificadas", 0)
            r = asig.get("retrasos", 0)
            e = asig.get("excusas", 0)

            cells_periodo = [_p(_nota(notas_p.get(per["id"])), "cell_c") for per in periodos]
            definitiva = asig.get("definitiva")
            row = (
                [_p(f"  {asig['nombre']}", "cell"), *cells_periodo, _p(_nota(definitiva), "cell_bold_c"), _p(str(p), "cell_c"), _p(str(fi), "cell_c"), _p(str(fj), "cell_c"), _p(str(r), "cell_c"), _p(str(e), "cell_c"), _p(_pct(p, fi, fj, r, e), "cell_c")]
            )
            table_data.append(row)
            if row_idx % 2 == 0:
                ts.append(("BACKGROUND", (0, row_idx), (-1, row_idx), colors.HexColor("#F9FAFB")))
            row_idx += 1

    tbl = Table(table_data, colWidths=col_w, repeatRows=1)
    tbl.setStyle(TableStyle(ts))
    return tbl


# ── Sección de observaciones y firmas ─────────────────────────────────────────


def _observaciones_y_firmas(
    page_w: float,
    convivencia: dict | None = None,
    convivencia_anual: dict | None = None,
) -> list:
    """Bloque inferior: caja de observaciones + líneas de firma.

    Modos:
    - ``convivencia_anual`` (prioritario): muestra notas por periodo, definitiva,
      concepto final y observaciones agrupadas por categoría.  Usado por el boletín anual.
    - ``convivencia`` (fallback): modo por-periodo original.  Usado por boletín de periodo
      y boletín acumulado.
    - Sin datos: renderiza una caja vacía (rectángulo de 2.2 cm de alto).
    """
    story: list = []
    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width=page_w, thickness=0.5, color=_GRIS_LINEA))
    story.append(Spacer(1, 0.3 * cm))

    # Título observaciones
    story.append(_p("OBSERVACIONES Y RECOMENDACIONES:", "bold"))
    story.append(Spacer(1, 0.15 * cm))

    # Construir párrafos de convivencia
    parrafos: list = []

    def _render_eventos(registros: list[dict]) -> None:
        if not registros:
            return
        parrafos.append(Spacer(1, 0.15 * cm))
        parrafos.append(Paragraph("EVENTOS DE CONVIVENCIA:", _sty["bold"]))
        for reg in registros:
            fecha = reg.get("fecha", "")
            tipo = reg.get("tipo", "")
            desc = reg.get("descripcion", "")
            clasif = reg.get("tipo_situacion")
            medida = reg.get("medida")
            texto = f"- {fecha} · {tipo}"
            if clasif:
                texto += f" [{clasif}]"
            texto += f": {desc}"
            parrafos.append(Paragraph(texto, _sty["normal"]))
            if medida:
                parrafos.append(Paragraph(f"  Medida: {medida}", _sty["normal"]))

    if convivencia_anual is not None:
        # ── Modo anual ────────────────────────────────────────────────
        periodos_anual = convivencia_anual.get("periodos", [])
        notas_p = convivencia_anual.get("notas_por_periodo", {})
        definitiva_anual = convivencia_anual.get("definitiva")
        concepto_anual = convivencia_anual.get("concepto")
        obs_cats = convivencia_anual.get("observaciones_por_categoria", [])

        if periodos_anual or definitiva_anual is not None:
            partes: list[str] = []
            for per in periodos_anual:
                n = notas_p.get(per["id"])
                partes.append(
                    f"{per['nombre']}: {n:.1f}" if n is not None else f"{per['nombre']}: —"
                )
            def_str = f"{definitiva_anual:.1f}" if definitiva_anual is not None else "—"
            linea_notas = (
                " · ".join(partes) + f" · Definitiva: {def_str}"
                if partes
                else f"Definitiva: {def_str}"
            )
            parrafos.append(Paragraph(f"Comportamiento — {linea_notas}", _sty["bold"]))

        if concepto_anual:
            parrafos.append(Paragraph(concepto_anual, _sty["normal"]))

        for grupo in obs_cats:
            cat_nombre = grupo.get("categoria", "")
            items = grupo.get("items", [])
            if items:
                parrafos.append(Paragraph(cat_nombre, _sty["subtitle"]))
                for item in items:
                    periodo_str = item.get("periodo", "")
                    autor = item.get("autor", "")
                    texto = item.get("texto", "")
                    if autor:
                        bullet = f"• [{periodo_str}] · {autor}: {texto}"
                    else:
                        bullet = f"• [{periodo_str}]: {texto}"
                    parrafos.append(Paragraph(bullet, _sty["normal"]))

        _render_eventos(convivencia_anual.get("registros", []))

    elif convivencia:
        # ── Modo por periodo (original) ───────────────────────────────
        nota = convivencia.get("nota")
        nota_obs = convivencia.get("nota_observacion")
        observaciones = convivencia.get("observaciones", [])
        if nota is not None:
            parrafos.append(Paragraph(f"Comportamiento: {nota:.1f}", _sty["bold"]))
        if nota_obs is not None:
            parrafos.append(Paragraph(nota_obs, _sty["normal"]))
        for texto in observaciones:
            parrafos.append(Paragraph(f"• {texto}", _sty["normal"]))

        _render_eventos(convivencia.get("registros", []))

    # Caja de observaciones: con contenido o vacía
    if parrafos:
        obs_data = [[parrafos]]
        obs_tbl = Table(obs_data, colWidths=[page_w], rowHeights=None)
    else:
        obs_data = [[""] * 1]
        obs_tbl = Table(obs_data, colWidths=[page_w], rowHeights=[2.2 * cm])
    obs_tbl.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, _GRIS_LINEA),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAFA")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(obs_tbl)
    story.append(Spacer(1, 0.5 * cm))

    # Firmas: 3 columnas
    firma_sty = ParagraphStyle(
        "Firma",
        parent=_ss["Normal"],
        fontSize=7.5,
        leading=10,
        textColor=_GRIS_TEXTO,
        alignment=1,
    )
    linea = "___________________________"
    firmas_data = [
        [
            Paragraph(f"{linea}<br/>Director(a) de Grupo", firma_sty),
            Paragraph(f"{linea}<br/>Rector(a)", firma_sty),
            Paragraph(f"{linea}<br/>Acudiente / Estudiante", firma_sty),
        ]
    ]
    firmas_tbl = Table(
        firmas_data,
        colWidths=[page_w / 3] * 3,
    )
    firmas_tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
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
    est = datos.get("estudiante", {})
    areas = datos.get("areas", [])

    n_asigs = sum(len(a.get("asignaturas", [])) for a in areas)
    # Si hay muchas asignaturas, usar landscape
    page_size = landscape(A4) if n_asigs > 20 else A4

    doc = SimpleDocTemplate(
        buf,
        pagesize=page_size,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    page_w = page_size[0] - 3.6 * cm

    story: list = []
    story.append(
        _membrete(
            page_w,
            titulo_doc="BOLETÍN DE CALIFICACIONES POR PERIODO",
            grupo=est.get("grupo", ""),
            periodo=f"Periodo: {est.get('periodo', '')}",
        )
    )
    story.append(Spacer(1, 0.35 * cm))
    story.append(_ficha(est, page_w))
    story.append(Spacer(1, 0.35 * cm))

    if areas:
        story.append(_tabla_periodo(areas, page_w))
    else:
        story.append(_p("No hay datos de calificaciones para este periodo.", "normal"))

    story.extend(_observaciones_y_firmas(page_w, datos.get("convivencia")))

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
    es_ultimo = datos.get("es_ultimo_periodo", False)
    label_definitiva = "Def." if es_ultimo else "Prom."
    return _build_boletin_anual_pdf(datos, label_definitiva)


def _build_boletin_anual_pdf(datos: dict[str, Any], label_definitiva: str = "Def.") -> bytes:
    """Builder interno compartido por generar_boletin_anual_pdf y generar_boletin_acumulado_pdf."""
    buf = io.BytesIO()
    est = datos.get("estudiante", {})
    periodos = datos.get("periodos", [])
    areas = datos.get("areas", [])

    n_asigs = sum(len(a.get("asignaturas", [])) for a in areas)
    usar_land = len(periodos) > 3 or n_asigs > 18
    page_size = landscape(A4) if usar_land else A4

    doc = SimpleDocTemplate(
        buf,
        pagesize=page_size,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    page_w = page_size[0] - 3.6 * cm

    estado = est.get("estado_promocion", "")
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
        titulo_doc = "BOLETÍN ANUAL DE CALIFICACIONES"
        periodo_str = f"Año lectivo: {est.get('anio', '')}"

    story: list = []
    story.append(
        _membrete(
            page_w,
            titulo_doc=titulo_doc,
            grupo=est.get("grupo", ""),
            periodo=periodo_str,
        )
    )
    story.append(Spacer(1, 0.35 * cm))
    story.append(
        _ficha(
            {**est, "periodo": periodo_str},
            page_w,
        )
    )
    story.append(Spacer(1, 0.35 * cm))

    if areas and periodos:
        story.append(_tabla_anual(areas, periodos, page_w, label_definitiva=label_definitiva))
    else:
        story.append(_p("No hay datos registrados.", "normal"))

    if estado_txt:
        story.append(Spacer(1, 0.35 * cm))
        story.append(
            Paragraph(
                f"Estado de promoción: <b>{estado_txt}</b>",
                _sty["promo"],
            )
        )

    story.extend(
        _observaciones_y_firmas(
            page_w,
            convivencia=datos.get("convivencia"),
            convivencia_anual=datos.get("convivencia_anual"),
        )
    )
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


# ── Reporte de convivencia por grupo ─────────────────────────────────────────


def _estadisticos_grupo(filas: list[dict], page_w: float) -> list:
    """Bloque de estadísticos del grupo con tablas y gráficos: distribución
    por desempeño (pie chart), histograma de notas, totales de registros
    (bar chart). Retorna flowables para agregar al story."""
    from collections import Counter

    from reportlab.graphics.charts.barcharts import HorizontalBarChart, VerticalBarChart
    from reportlab.graphics.charts.legends import Legend
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics.shapes import Drawing, String

    _PIE_COLORS = [
        colors.HexColor("#2B6CB0"),
        colors.HexColor("#38A169"),
        colors.HexColor("#D69E2E"),
        colors.HexColor("#E53E3E"),
        colors.HexColor("#805AD5"),
        colors.HexColor("#DD6B20"),
        colors.HexColor("#319795"),
        colors.HexColor("#B83280"),
    ]

    story: list = []
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("ESTADÍSTICOS DEL GRUPO", _sty["title"]))
    story.append(Spacer(1, 0.2 * cm))

    total = len(filas)
    notas_raw = [f["nota"] for f in filas if f["nota"] is not None and f["nota"] != ""]
    notas: list[float] = []
    for n in notas_raw:
        try:
            notas.append(float(n))
        except (ValueError, TypeError):
            pass
    promedio = round(sum(notas) / len(notas), 1) if notas else "—"
    nota_max = round(max(notas), 1) if notas else "—"
    nota_min = round(min(notas), 1) if notas else "—"
    sin_nota = total - len(notas)

    niveles = Counter(f["nivel"] for f in filas if f["nivel"])
    total_fort = sum(f.get("fortalezas", 0) for f in filas)
    total_dif = sum(f.get("dificultades", 0) for f in filas)
    total_comp = sum(f.get("compromisos", 0) for f in filas)
    total_cit = sum(f.get("citaciones", 0) for f in filas)
    total_desc = sum(f.get("descargos", 0) for f in filas)
    total_obs = sum(f.get("num_obs", 0) for f in filas)

    # ── Tabla resumen general ──
    resumen_data = [
        [_p("Indicador", "hdr_l"), _p("Valor", "hdr")],
        [_p("Total estudiantes"), _p(str(total), "cell_c")],
        [_p("Con nota asignada"), _p(str(len(notas)), "cell_c")],
        [_p("Sin nota"), _p(str(sin_nota), "cell_c")],
        [_p("Promedio del grupo"), _p(str(promedio), "cell_bold_c")],
        [_p("Nota más alta"), _p(str(nota_max), "cell_c")],
        [_p("Nota más baja"), _p(str(nota_min), "cell_c")],
    ]
    w_label = page_w * 0.22
    w_val = page_w * 0.10
    tbl_resumen = Table(resumen_data, colWidths=[w_label, w_val])
    tbl_resumen.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _AZUL),
                ("TEXTCOLOR", (0, 0), (-1, 0), _BLANCO),
                ("GRID", (0, 0), (-1, -1), 0.4, _GRIS_LINEA),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_BLANCO, colors.HexColor("#F9FAFB")]),
            ]
        )
    )

    # ── Pie chart: distribución por desempeño ──
    pie_w = 5.5 * cm
    pie_h = 5.5 * cm
    d_pie = Drawing(pie_w + 4 * cm, pie_h)
    if niveles:
        pie = Pie()
        pie.x = 0.3 * cm
        pie.y = 0.3 * cm
        pie.width = 4.2 * cm
        pie.height = 4.2 * cm
        sorted_niveles = sorted(niveles.items(), key=lambda x: -x[1])
        pie.data = [c for _, c in sorted_niveles]
        pie.labels = None
        for i, (_, _cant) in enumerate(sorted_niveles):
            pie.slices[i].fillColor = _PIE_COLORS[i % len(_PIE_COLORS)]
            pie.slices[i].strokeColor = _BLANCO
            pie.slices[i].strokeWidth = 0.8
            pie.slices[i].popout = 2 if i == 0 else 0
        d_pie.add(pie)

        legend = Legend()
        legend.x = 5 * cm
        legend.y = pie_h - 1.2 * cm
        legend.dx = 8
        legend.dy = 8
        legend.deltay = 12
        legend.fontName = "Helvetica"
        legend.fontSize = 7
        legend.fillColor = None
        legend.strokeColor = None
        legend.columnMaximum = 8
        legend.colorNamePairs = [
            (_PIE_COLORS[i % len(_PIE_COLORS)], f"{nombre} ({cant})")
            for i, (nombre, cant) in enumerate(sorted_niveles)
        ]
        d_pie.add(legend)

        title_pie = String(pie_w / 2 + 1.5 * cm, pie_h - 0.15 * cm, "Distribución por desempeño")
        title_pie.fontName = "Helvetica-Bold"
        title_pie.fontSize = 7.5
        title_pie.fillColor = _GRIS_TEXTO
        title_pie.textAnchor = "middle"
        d_pie.add(title_pie)
    else:
        no_data = String(pie_w / 2, pie_h / 2, "Sin datos de desempeño")
        no_data.fontName = "Helvetica"
        no_data.fontSize = 8
        no_data.fillColor = _GRIS_TEXTO
        no_data.textAnchor = "middle"
        d_pie.add(no_data)

    # ── Histograma de notas ──
    hist_w = page_w - (w_label + w_val) - pie_w - 4 * cm - 1.5 * cm
    hist_w = max(hist_w, 5 * cm)
    hist_h = 5.5 * cm
    d_hist = Drawing(hist_w, hist_h)

    if notas:
        bin_labels, counts = _clasificar_notas(notas)

        bc = VerticalBarChart()
        bc.x = 1.2 * cm
        bc.y = 0.8 * cm
        bc.width = hist_w - 2 * cm
        bc.height = hist_h - 1.8 * cm
        bc.data = [counts]
        bc.categoryAxis.categoryNames = bin_labels
        bc.categoryAxis.labels.fontName = "Helvetica"
        bc.categoryAxis.labels.fontSize = 6
        bc.categoryAxis.labels.angle = 0
        bc.valueAxis.valueMin = 0
        bc.valueAxis.valueMax = max(counts) + 1
        bc.valueAxis.valueStep = max(1, max(counts) // 4) if max(counts) > 0 else 1
        bc.valueAxis.labels.fontName = "Helvetica"
        bc.valueAxis.labels.fontSize = 6
        bc.bars[0].fillColor = colors.HexColor("#3182CE")
        bc.bars[0].strokeColor = colors.HexColor("#2B6CB0")
        bc.bars[0].strokeWidth = 0.5
        bc.barWidth = 0.7 * cm
        bc.barLabelFormat = "%d"
        bc.barLabels.nudge = 5
        bc.barLabels.fontName = "Helvetica-Bold"
        bc.barLabels.fontSize = 6
        d_hist.add(bc)

        title_hist = String(hist_w / 2, hist_h - 0.15 * cm, "Distribución de notas")
        title_hist.fontName = "Helvetica-Bold"
        title_hist.fontSize = 7.5
        title_hist.fillColor = _GRIS_TEXTO
        title_hist.textAnchor = "middle"
        d_hist.add(title_hist)
    else:
        no_data_h = String(hist_w / 2, hist_h / 2, "Sin notas registradas")
        no_data_h.fontName = "Helvetica"
        no_data_h.fontSize = 8
        no_data_h.fillColor = _GRIS_TEXTO
        no_data_h.textAnchor = "middle"
        d_hist.add(no_data_h)

    # Fila 1: tabla resumen + pie + histograma
    row1_data = [[tbl_resumen, d_pie, d_hist]]
    row1 = Table(
        row1_data,
        colWidths=[w_label + w_val, pie_w + 4 * cm, hist_w],
    )
    row1.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(row1)
    story.append(Spacer(1, 0.3 * cm))

    # ── Bar chart horizontal: totales de registros ──
    reg_labels = ["Fortalezas", "Dificultades", "Compromisos", "Citaciones", "Descargos", "Observ."]
    reg_values = [total_fort, total_dif, total_comp, total_cit, total_desc, total_obs]
    _BAR_COLORS = [
        colors.HexColor("#38A169"),
        colors.HexColor("#E53E3E"),
        colors.HexColor("#D69E2E"),
        colors.HexColor("#805AD5"),
        colors.HexColor("#DD6B20"),
        colors.HexColor("#3182CE"),
    ]

    bar_w = page_w * 0.48
    bar_h = 4.2 * cm
    d_bar = Drawing(bar_w, bar_h)

    if any(v > 0 for v in reg_values):
        hbc = HorizontalBarChart()
        hbc.x = 2.2 * cm
        hbc.y = 0.4 * cm
        hbc.width = bar_w - 3 * cm
        hbc.height = bar_h - 1.0 * cm
        hbc.data = [[v] for v in reg_values]
        hbc.categoryAxis.categoryNames = reg_labels
        hbc.categoryAxis.labels.fontName = "Helvetica"
        hbc.categoryAxis.labels.fontSize = 6.5
        hbc.categoryAxis.labels.dx = -2
        hbc.valueAxis.valueMin = 0
        hbc.valueAxis.valueMax = max(reg_values) + max(1, max(reg_values) // 5)
        hbc.valueAxis.labels.fontName = "Helvetica"
        hbc.valueAxis.labels.fontSize = 6
        for i in range(6):
            hbc.bars[i].fillColor = _BAR_COLORS[i]
            hbc.bars[i].strokeColor = None
        hbc.barWidth = 0.35 * cm
        hbc.barLabelFormat = "%d"
        hbc.barLabels.nudge = 8
        hbc.barLabels.fontName = "Helvetica-Bold"
        hbc.barLabels.fontSize = 6.5
        d_bar.add(hbc)

        title_bar = String(bar_w / 2, bar_h - 0.15 * cm, "Registros por tipo")
        title_bar.fontName = "Helvetica-Bold"
        title_bar.fontSize = 7.5
        title_bar.fillColor = _GRIS_TEXTO
        title_bar.textAnchor = "middle"
        d_bar.add(title_bar)

    # ── Tabla distribución por desempeño (al lado del bar chart) ──
    dist_data = [[_p("Nivel de desempeño", "hdr_l"), _p("Cant.", "hdr"), _p("%", "hdr")]]
    for nivel_nombre, cant in sorted(niveles.items(), key=lambda x: -x[1]):
        pct = round(cant / total * 100) if total else 0
        dist_data.append([_p(nivel_nombre), _p(str(cant), "cell_c"), _p(f"{pct}%", "cell_c")])
    if not niveles:
        dist_data.append([_p("Sin datos"), _p("—", "cell_c"), _p("—", "cell_c")])

    w_nivel = page_w * 0.22
    w_cant = page_w * 0.08
    tbl_dist = Table(dist_data, colWidths=[w_nivel, w_cant, w_cant])
    tbl_dist.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _AZUL),
                ("TEXTCOLOR", (0, 0), (-1, 0), _BLANCO),
                ("GRID", (0, 0), (-1, -1), 0.4, _GRIS_LINEA),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_BLANCO, colors.HexColor("#F9FAFB")]),
            ]
        )
    )

    # ── Tabla totales de registros ──
    reg_tbl_data = [
        [
            _p("Fortalezas", "hdr"),
            _p("Dificultades", "hdr"),
            _p("Compromisos", "hdr"),
            _p("Citaciones", "hdr"),
            _p("Descargos", "hdr"),
            _p("Observaciones", "hdr"),
        ],
        [
            _p(str(total_fort), "cell_bold_c"),
            _p(str(total_dif), "cell_bold_c"),
            _p(str(total_comp), "cell_bold_c"),
            _p(str(total_cit), "cell_bold_c"),
            _p(str(total_desc), "cell_bold_c"),
            _p(str(total_obs), "cell_bold_c"),
        ],
    ]

    # Fila 2: bar chart + tabla distribución
    row2_data = [[d_bar, tbl_dist]]
    row2 = Table(
        row2_data,
        colWidths=[bar_w, w_nivel + w_cant * 2],
    )
    row2.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(Paragraph("Registros y distribución", _sty["subtitle"]))
    story.append(Spacer(1, 0.1 * cm))
    story.append(row2)
    story.append(Spacer(1, 0.2 * cm))

    # Fila 3: tabla totales
    story.append(Paragraph("Totales de registros del grupo", _sty["subtitle"]))
    story.append(Spacer(1, 0.1 * cm))
    w_reg = page_w / 6
    tbl_reg = Table(reg_tbl_data, colWidths=[w_reg] * 6)
    tbl_reg.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _AZUL),
                ("TEXTCOLOR", (0, 0), (-1, 0), _BLANCO),
                ("GRID", (0, 0), (-1, -1), 0.4, _GRIS_LINEA),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(tbl_reg)

    return story


def generar_reporte_convivencia_grupo_pdf(
    filas: list[dict],
    titulo: str = "Reporte de convivencia",
    grupo: str = "",
    periodo: str = "",
    desglose_cols: list[str] | None = None,
) -> bytes:
    """Genera el PDF del reporte de convivencia por grupo con ReportLab.

    Args:
        filas: list[dict] con claves: estudiante, nota, nivel, fortalezas,
            dificultades, compromisos, citaciones, descargos, concepto,
            observaciones (str), num_obs (int), y las claves de desglose.
        titulo: título del documento.
        grupo: nombre del grupo.
        periodo: nombre del periodo.
        desglose_cols: nombres de columnas de desglose por tipo de situación.
    """
    buf = io.BytesIO()
    page_size = landscape(A4)
    doc = SimpleDocTemplate(
        buf,
        pagesize=page_size,
        leftMargin=1.2 * cm,
        rightMargin=1.2 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
    )
    page_w = page_size[0] - 2.4 * cm

    story: list = []

    # ── Membrete ──
    story.append(
        _membrete(page_w, titulo_doc=titulo, grupo=grupo, periodo=periodo)
    )
    story.append(Spacer(1, 0.3 * cm))

    if not filas:
        story.append(_p("No hay datos de estudiantes para este grupo y periodo.", "normal"))
        doc.build(story)
        return buf.getvalue()

    # ── Tabla principal ──
    desglose_cols = desglose_cols or []
    base_cols: list[tuple[str, str]] = [
        ("estudiante", "Estudiante"),
        ("nota", "Nota"),
        ("nivel", "Desempeño"),
        ("fortalezas", "Fort."),
        ("dificultades", "Dif."),
        ("compromisos", "Comp."),
        ("citaciones", "Cit."),
        ("descargos", "Desc."),
    ]
    extra_cols = [(c, c) for c in desglose_cols]
    text_cols: list[tuple[str, str]] = [
        ("concepto", "Concepto de comportamiento"),
        ("observaciones", "Observaciones"),
    ]
    all_cols = base_cols + extra_cols + text_cols

    # Anchos: estudiante flexible, numéricos fijos, texto flexible
    n_num = 5 + len(desglose_cols)
    w_num = 1.0 * cm
    w_desemp = 1.8 * cm
    w_nota = 1.0 * cm
    w_fixed = w_nota + w_desemp + n_num * w_num
    w_text = page_w - w_fixed
    w_est = w_text * 0.25
    w_concepto = w_text * 0.35
    w_obs = w_text * 0.40

    col_widths = [w_est, w_nota, w_desemp]
    col_widths += [w_num] * 5
    col_widths += [w_num] * len(desglose_cols)
    col_widths += [w_concepto, w_obs]

    # Reescalar si excede
    total_w = sum(col_widths)
    if total_w > page_w:
        factor = page_w / total_w
        col_widths = [w * factor for w in col_widths]

    # Encabezados
    hdrs = [(_p(h, "hdr_l") if i == 0 else _p(h, "hdr")) for i, (_, h) in enumerate(all_cols)]
    table_data: list[list] = [hdrs]

    ts = [
        ("BACKGROUND", (0, 0), (-1, 0), _AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), _BLANCO),
        ("GRID", (0, 0), (-1, -1), 0.4, _GRIS_LINEA),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (0, -1), 4),
        ("LEFTPADDING", (1, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]
    # Concepto y Observaciones: alinear izquierda
    col_concepto_idx = len(base_cols) + len(desglose_cols)
    col_obs_idx = col_concepto_idx + 1
    ts.append(("ALIGN", (col_concepto_idx, 1), (col_concepto_idx, -1), "LEFT"))
    ts.append(("ALIGN", (col_obs_idx, 1), (col_obs_idx, -1), "LEFT"))

    for row_idx, fila in enumerate(filas, start=1):
        cells: list = []
        for key, _ in all_cols:
            val = fila.get(key, "")
            if key == "nota":
                cells.append(_p(_nota(val), "cell_c"))
            elif key in ("estudiante", "concepto", "observaciones"):
                cells.append(_p(str(val).replace("\n", "<br/>") if val else "", "cell"))
            elif key == "nivel":
                cells.append(_p(str(val) if val else "", "cell_c"))
            else:
                cells.append(_p(str(val) if val else "0", "cell_c"))
        table_data.append(cells)
        if row_idx % 2 == 0:
            ts.append(("BACKGROUND", (0, row_idx), (-1, row_idx), colors.HexColor("#F9FAFB")))

    tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle(ts))
    story.append(tbl)

    # ── Estadísticos ──
    filas_stats = []
    for fila in filas:
        filas_stats.append({
            "nota": fila.get("nota"),
            "nivel": fila.get("nivel", ""),
            "fortalezas": fila.get("fortalezas", 0),
            "dificultades": fila.get("dificultades", 0),
            "compromisos": fila.get("compromisos", 0),
            "citaciones": fila.get("citaciones", 0),
            "descargos": fila.get("descargos", 0),
            "num_obs": fila.get("num_obs", 0),
        })
    story.extend(_estadisticos_grupo(filas_stats, page_w))

    # ── Firmas ──
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width=page_w, thickness=0.5, color=_GRIS_LINEA))
    story.append(Spacer(1, 0.5 * cm))
    firma_sty = ParagraphStyle(
        "FirmaGrupo",
        parent=_ss["Normal"],
        fontSize=7.5,
        leading=10,
        textColor=_GRIS_TEXTO,
        alignment=1,
    )
    linea = "___________________________"
    firmas_data = [
        [
            Paragraph(f"{linea}<br/>Director(a) de Grupo", firma_sty),
            Paragraph(f"{linea}<br/>Coordinador(a)", firma_sty),
            Paragraph(f"{linea}<br/>Rector(a)", firma_sty),
        ]
    ]
    firmas_tbl = Table(firmas_data, colWidths=[page_w / 3] * 3)
    firmas_tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    story.append(firmas_tbl)

    doc.build(story)
    return buf.getvalue()


__all__ = [
    "generar_boletin_acumulado_pdf",
    "generar_boletin_anual_pdf",
    "generar_boletin_periodo_pdf",
    "generar_reporte_convivencia_grupo_pdf",
]
