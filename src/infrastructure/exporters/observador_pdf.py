"""
observador_pdf.py — Generador del Observador del Estudiante con ReportLab.

Diseño formal tipo hoja de observador de colegio colombiano:
  1. Membrete institucional centrado (nombre, DANE, municipio, resolución)
  2. Ficha de identificación del estudiante en tabla de 2×2 campos
  3. Tabla de observaciones académicas numeradas con columnas formales
  4. Tabla de registros de comportamiento numerados
  5. Tabla de seguimientos por registro
  6. Resumen estadístico
  7. Notas de comportamiento por periodo
  8. Firmas (director de grupo, coordinador, acudiente, estudiante)
"""

from __future__ import annotations

import io
from datetime import date as _date

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ── Paleta ───────────────────────────────────────────────────────────────────

_AZUL_OSCURO = colors.HexColor("#1A365D")
_AZUL = colors.HexColor("#2B6CB0")
_AZUL_CLARO = colors.HexColor("#DBEAFE")
_AZUL_MUY_CLARO = colors.HexColor("#EBF5FF")
_GRIS_LINEA = colors.HexColor("#CBD5E0")
_GRIS_TEXTO = colors.HexColor("#374151")
_GRIS_CLARO = colors.HexColor("#718096")
_GRIS_FONDO = colors.HexColor("#F7FAFC")
_VERDE = colors.HexColor("#276749")
_ROJO = colors.HexColor("#9B2C2C")
_AMARILLO = colors.HexColor("#975A16")
_BLANCO = colors.white

_ss = getSampleStyleSheet()


def _sty(name: str, **kw) -> ParagraphStyle:
    defaults = {
        "parent": _ss["Normal"],
        "fontSize": 7.5,
        "leading": 9.5,
        "textColor": _GRIS_TEXTO,
    }
    defaults.update(kw)
    return ParagraphStyle(name, **defaults)


_S_INST_NOMBRE = _sty("SIN", fontSize=11, leading=14, fontName="Helvetica-Bold", textColor=_AZUL_OSCURO, alignment=TA_CENTER)
_S_INST_SUB = _sty("SIS", fontSize=7.5, leading=10, textColor=_GRIS_CLARO, alignment=TA_CENTER)
_S_TITULO = _sty("STit", fontSize=12, leading=15, fontName="Helvetica-Bold", textColor=_AZUL_OSCURO, alignment=TA_CENTER, spaceBefore=2, spaceAfter=2)
_S_SECCION = _sty("SSec", fontSize=9, leading=12, fontName="Helvetica-Bold", textColor=_AZUL_OSCURO, spaceBefore=8, spaceAfter=3)
_S_HDR = _sty("SHdr", fontSize=7, leading=9, fontName="Helvetica-Bold", textColor=_BLANCO, alignment=TA_CENTER)
_S_CELL = _sty("SCel", fontSize=7, leading=9)
_S_CELL_C = _sty("SCelC", fontSize=7, leading=9, alignment=TA_CENTER)
_S_CELL_B = _sty("SCelB", fontSize=7, leading=9, fontName="Helvetica-Bold")
_S_CELL_WRAP = _sty("SCelW", fontSize=7, leading=9)
_S_LABEL = _sty("SLab", fontSize=7.5, leading=10, fontName="Helvetica-Bold", textColor=_GRIS_CLARO)
_S_VALUE = _sty("SVal", fontSize=8, leading=10)
_S_FIRMA = _sty("SFir", fontSize=7.5, leading=9, alignment=TA_CENTER, textColor=_GRIS_TEXTO)
_S_FOOTER = _sty("SFoo", fontSize=6.5, leading=8, textColor=_GRIS_CLARO, alignment=TA_RIGHT)
_S_EMPTY = _sty("SEmp", fontSize=8, leading=10, textColor=_GRIS_CLARO, alignment=TA_CENTER)
_S_NUM_BOLD = _sty("SNB", fontSize=9, leading=11, fontName="Helvetica-Bold", textColor=_AZUL, alignment=TA_CENTER)

# ── Helpers ──────────────────────────────────────────────────────────────────

_MESES_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

_TIPO_LABEL = {
    "fortaleza": "Fortaleza",
    "dificultad": "Dificultad",
    "compromiso": "Compromiso",
    "citacion_acudiente": "Citación acudiente",
    "descargo": "Descargo",
}


def _fecha_corta(dt) -> str:
    if dt is None:
        return "—"
    try:
        return f"{dt.day:02d}/{dt.month:02d}/{dt.year}"
    except Exception:
        return str(dt)


def _fecha_hora(dt) -> str:
    if dt is None:
        return "—"
    try:
        base = f"{dt.day:02d}/{dt.month:02d}/{dt.year}"
        if hasattr(dt, "hour") and hasattr(dt, "minute"):
            return f"{base} {dt.hour:02d}:{dt.minute:02d}"
        return base
    except Exception:
        return str(dt)


def _p(text, style=_S_CELL):
    val = "—" if (text is None or str(text).strip() == "") else str(text)
    return Paragraph(val, style)


def _grid_style(n_rows: int, hdr_bg=_AZUL) -> TableStyle:
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), hdr_bg),
        ("TEXTCOLOR", (0, 0), (-1, 0), _BLANCO),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, _GRIS_LINEA),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    for i in range(1, n_rows):
        bg = _BLANCO if i % 2 == 1 else _GRIS_FONDO
        cmds.append(("BACKGROUND", (0, i), (-1, i), bg))
    return TableStyle(cmds)


# ── 1. Membrete institucional ────────────────────────────────────────────────


def _membrete(inst: dict, page_w: float) -> list:
    elements: list = []
    nombre = inst.get("nombre", "Institución Educativa")
    dane = inst.get("DANE", "")
    municipio = inst.get("municipio", "")
    resolucion = inst.get("resolucion", "")
    rector = inst.get("rector", "")
    direccion = inst.get("direccion", "")
    telefono = inst.get("telefono", "")

    elements.append(Paragraph(nombre.upper(), _S_INST_NOMBRE))

    sub_parts = []
    if resolucion:
        sub_parts.append(f"Resolución de aprobación: {resolucion}")
    if dane:
        sub_parts.append(f"DANE: {dane}")
    if municipio:
        sub_parts.append(municipio)
    if direccion:
        sub_parts.append(direccion)
    if telefono:
        sub_parts.append(f"Tel: {telefono}")
    if rector:
        sub_parts.append(f"Rector(a): {rector}")
    if sub_parts:
        elements.append(Paragraph(" — ".join(sub_parts), _S_INST_SUB))

    elements.append(Spacer(1, 4))

    line = Table([[""]], colWidths=[page_w], rowHeights=[1.5])
    line.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), _AZUL)]))
    elements.append(line)

    return elements


# ── 2. Ficha del estudiante ──────────────────────────────────────────────────


def _ficha_estudiante(est: dict, anio: str, periodo: str | None, page_w: float) -> list:
    nombre = est.get("nombre", "—")
    documento = est.get("documento", "—")
    grupo = est.get("grupo", "—")
    grado = est.get("grado", "—")
    fecha_nac = est.get("fecha_nacimiento")
    fecha_nac_str = _fecha_corta(fecha_nac) if fecha_nac else "—"
    genero = est.get("genero") or "—"
    direccion = est.get("direccion") or "—"

    periodo_str = periodo or "Año completo"
    label_w = 2.2 * cm
    val_w = (page_w - 2 * label_w) / 2

    data = [
        [
            _p("ESTUDIANTE:", _S_LABEL), _p(nombre, _S_VALUE),
            _p("DOCUMENTO:", _S_LABEL), _p(documento, _S_VALUE),
        ],
        [
            _p("GRUPO:", _S_LABEL), _p(grupo, _S_VALUE),
            _p("GRADO:", _S_LABEL), _p(grado, _S_VALUE),
        ],
        [
            _p("FECHA NAC.:", _S_LABEL), _p(fecha_nac_str, _S_VALUE),
            _p("GÉNERO:", _S_LABEL), _p(genero, _S_VALUE),
        ],
        [
            _p("DIRECCIÓN:", _S_LABEL), _p(direccion, _S_VALUE),
            _p("AÑO LECTIVO:", _S_LABEL), _p(anio, _S_VALUE),
        ],
        [
            _p("PERIODO:", _S_LABEL), _p(periodo_str, _S_VALUE),
            _p("", _S_LABEL), _p("", _S_VALUE),
        ],
    ]
    tbl = Table(data, colWidths=[label_w, val_w, label_w, val_w])
    tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, _GRIS_LINEA),
        ("BACKGROUND", (0, 0), (0, -1), _AZUL_MUY_CLARO),
        ("BACKGROUND", (2, 0), (2, -1), _AZUL_MUY_CLARO),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))

    elements = [tbl]

    acud = est.get("acudiente") or {}
    if acud:
        elements.append(Spacer(1, 4))
        elements.append(Paragraph("Datos del acudiente principal", _S_SECCION))

        acud_data = [
            [
                _p("ACUDIENTE:", _S_LABEL), _p(acud.get("nombre", "—"), _S_VALUE),
                _p("PARENTESCO:", _S_LABEL), _p(acud.get("parentesco_display", "—"), _S_VALUE),
            ],
            [
                _p("CELULAR:", _S_LABEL), _p(acud.get("celular", "—"), _S_VALUE),
                _p("EMAIL:", _S_LABEL), _p(acud.get("email", "—"), _S_VALUE),
            ],
            [
                _p("DIRECCIÓN:", _S_LABEL), _p(acud.get("direccion", "—"), _S_VALUE),
                _p("DOCUMENTO:", _S_LABEL), _p(acud.get("documento", "—"), _S_VALUE),
            ],
        ]
        tbl_acud = Table(acud_data, colWidths=[label_w, val_w, label_w, val_w])
        tbl_acud.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, _GRIS_LINEA),
            ("BACKGROUND", (0, 0), (0, -1), _AZUL_MUY_CLARO),
            ("BACKGROUND", (2, 0), (2, -1), _AZUL_MUY_CLARO),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(tbl_acud)

    return elements


# ── 3. Tabla de observaciones ────────────────────────────────────────────────


def _tabla_observaciones(entradas: list, page_w: float) -> list:
    obs = [e for e in entradas if e.get("tipo") == "observacion"]
    if not obs:
        return [Paragraph("No se registran observaciones académicas en el periodo consultado.", _S_EMPTY)]

    col_widths = [
        0.8 * cm,           # N°
        2.0 * cm,           # Fecha/Hora
        1.8 * cm,           # Periodo
        2.2 * cm,           # Asignatura
        1.8 * cm,           # Categoría
        page_w - 12.1 * cm, # Descripción (flex)
        1.5 * cm,           # Visibilidad
        2.0 * cm,           # Docente
    ]

    header = [
        _p("N°", _S_HDR), _p("Fecha y hora", _S_HDR), _p("Periodo", _S_HDR),
        _p("Asignatura", _S_HDR), _p("Categoría", _S_HDR), _p("Descripción", _S_HDR),
        _p("Tipo", _S_HDR), _p("Registrado por", _S_HDR),
    ]
    rows = [header]

    for i, o in enumerate(obs, 1):
        subtipo = o.get("subtipo", "")
        visib = "Pública" if subtipo == "publica" else "Privada"
        rows.append([
            _p(str(i), _S_CELL_C),
            _p(_fecha_hora(o.get("fecha")), _S_CELL_C),
            _p(o.get("periodo", "—"), _S_CELL_C),
            _p(o.get("asignatura", "—"), _S_CELL),
            _p(o.get("categoria", "—"), _S_CELL),
            _p(o.get("descripcion", ""), _S_CELL_WRAP),
            _p(visib, _S_CELL_C),
            _p(o.get("responsable", "—"), _S_CELL),
        ])

    tbl = Table(rows, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(_grid_style(len(rows)))
    return [tbl]


# ── 4. Tabla de registros de comportamiento ──────────────────────────────────


def _tabla_registros(entradas: list, page_w: float) -> list:
    regs = [e for e in entradas if e.get("tipo") == "registro"]
    if not regs:
        return [Paragraph("No se registran anotaciones de comportamiento en el periodo consultado.", _S_EMPTY)]

    col_widths = [
        0.8 * cm,           # N°
        1.8 * cm,           # Fecha
        1.8 * cm,           # Periodo
        1.8 * cm,           # Tipo
        1.6 * cm,           # Situación
        page_w - 12.3 * cm, # Descripción (flex)
        1.8 * cm,           # Medida
        0.9 * cm,           # Seg.
        1.8 * cm,           # Registrado por
    ]

    header = [
        _p("N°", _S_HDR), _p("Fecha", _S_HDR), _p("Periodo", _S_HDR),
        _p("Tipo", _S_HDR), _p("Situación", _S_HDR), _p("Descripción", _S_HDR),
        _p("Medida", _S_HDR), _p("Seg.", _S_HDR), _p("Registrado por", _S_HDR),
    ]
    rows = [header]

    for i, r in enumerate(regs, 1):
        subtipo = r.get("subtipo", "")
        n_seg = len(r.get("seguimiento_entries", []))
        rows.append([
            _p(str(i), _S_CELL_C),
            _p(_fecha_corta(r.get("fecha")), _S_CELL_C),
            _p(r.get("periodo", "—"), _S_CELL_C),
            _p(_TIPO_LABEL.get(subtipo, subtipo), _S_CELL),
            _p(r.get("tipo_situacion", "—"), _S_CELL),
            _p(r.get("descripcion", ""), _S_CELL_WRAP),
            _p(r.get("medida") or "—", _S_CELL),
            _p(str(n_seg) if n_seg else "—", _S_CELL_C),
            _p(r.get("responsable", "—"), _S_CELL),
        ])

    tbl = Table(rows, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(_grid_style(len(rows)))
    return [tbl]


# ── 5. Detalle de seguimientos ───────────────────────────────────────────────


def _tabla_seguimientos(entradas: list, page_w: float) -> list:
    regs_con_seg = [
        (i, e)
        for i, e in enumerate(
            (e for e in entradas if e.get("tipo") == "registro"), 1
        )
        if e.get("seguimiento_entries")
    ]
    if not regs_con_seg:
        return []

    col_widths = [
        1.2 * cm,           # Reg. N°
        2.0 * cm,           # Fecha
        page_w - 5.2 * cm,  # Anotación (flex)
        2.0 * cm,           # Responsable
    ]

    header = [
        _p("Reg. N°", _S_HDR), _p("Fecha", _S_HDR),
        _p("Anotación de seguimiento", _S_HDR), _p("Responsable", _S_HDR),
    ]
    rows = [header]
    for reg_num, entry in regs_con_seg:
        for seg in entry.get("seguimiento_entries", []):
            rows.append([
                _p(str(reg_num), _S_CELL_C),
                _p(_fecha_hora(seg.get("fecha")), _S_CELL_C),
                _p(seg.get("texto", ""), _S_CELL_WRAP),
                _p(seg.get("responsable", "—"), _S_CELL),
            ])

    tbl = Table(rows, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(_grid_style(len(rows), hdr_bg=colors.HexColor("#4A5568")))
    return [
        Paragraph("Detalle de seguimientos", _S_SECCION),
        tbl,
    ]


# ── 6. Resumen estadístico ──────────────────────────────────────────────────


def _tabla_resumen(resumen: dict, page_w: float) -> Table:
    items = [
        ("Observaciones", resumen.get("num_observaciones", 0), _AZUL),
        ("Fortalezas", resumen.get("fortalezas", 0), _VERDE),
        ("Dificultades", resumen.get("dificultades", 0), _ROJO),
        ("Compromisos", resumen.get("compromisos", 0), _AMARILLO),
        ("Citaciones", resumen.get("citaciones", 0), colors.HexColor("#C05621")),
        ("Descargos", resumen.get("descargos", 0), colors.HexColor("#6B46C1")),
    ]
    col_w = page_w / len(items)

    header_row = [_p(label, _S_HDR) for label, _, _ in items]
    value_row = [_p(str(val), _S_NUM_BOLD) for _, val, _ in items]

    tbl = Table([header_row, value_row], colWidths=[col_w] * len(items))
    cmds = [
        ("GRID", (0, 0), (-1, -1), 0.4, _GRIS_LINEA),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("BACKGROUND", (0, 1), (-1, 1), _BLANCO),
    ]
    for i, (_, _, color) in enumerate(items):
        cmds.append(("BACKGROUND", (i, 0), (i, 0), color))
    tbl.setStyle(TableStyle(cmds))
    return tbl


# ── 7. Notas de comportamiento por periodo ───────────────────────────────────


def _tabla_notas_periodo(resumen: dict, page_w: float) -> list:
    notas = resumen.get("notas_por_periodo", {})
    if not notas:
        return []

    col_w = page_w / len(notas)
    header = [_p(per, _S_HDR) for per in notas]
    valores = [
        _p(f"{v:.1f}" if v is not None else "—", _S_NUM_BOLD)
        for v in notas.values()
    ]

    tbl = Table([header, valores], colWidths=[col_w] * len(notas))
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _AZUL_OSCURO),
        ("GRID", (0, 0), (-1, -1), 0.4, _GRIS_LINEA),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("BACKGROUND", (0, 1), (-1, 1), _BLANCO),
    ]))
    return [
        Paragraph("Valoración de comportamiento por periodo", _S_SECCION),
        tbl,
    ]


# ── 8. Firmas ────────────────────────────────────────────────────────────────


def _tabla_firmas(page_w: float) -> Table:
    roles = ["Director(a) de grupo", "Coordinador(a)", "Acudiente", "Estudiante"]
    col_w = page_w / len(roles)

    line = "_" * 26
    data = [
        [_p("", _S_FIRMA)] * len(roles),  # espacio
        [_p(line, _S_FIRMA) for _ in roles],
        [_p(r, _S_FIRMA) for r in roles],
    ]
    tbl = Table(data, colWidths=[col_w] * len(roles))
    tbl.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 0), 18),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 2),
        ("TOPPADDING", (0, 2), (-1, 2), 1),
    ]))
    return tbl


# ── Función principal ────────────────────────────────────────────────────────


def generar_observador_pdf(datos: dict) -> bytes:
    """Genera el PDF del observador del estudiante y retorna los bytes."""
    buffer = io.BytesIO()
    page_w, page_h = A4
    margin = 1.5 * cm

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=1.2 * cm,
    )

    content_w = page_w - 2 * margin
    est = datos.get("estudiante", {})
    inst = datos.get("institucion", {})
    anio = str(datos.get("anio", ""))
    periodo = datos.get("periodo")
    entradas = datos.get("entradas", [])
    resumen = datos.get("resumen", {})

    story: list = []

    # 1. Membrete institucional
    story.extend(_membrete(inst, content_w))
    story.append(Spacer(1, 6))

    # 2. Título
    story.append(Paragraph("OBSERVADOR DEL ESTUDIANTE", _S_TITULO))
    story.append(Spacer(1, 4))

    # 3. Ficha de identificación + datos del acudiente
    story.extend(_ficha_estudiante(est, anio, periodo, content_w))
    story.append(Spacer(1, 4))

    # 4. Observaciones académicas
    story.append(Paragraph("I. Observaciones académicas", _S_SECCION))
    story.extend(_tabla_observaciones(entradas, content_w))

    # 5. Registros de comportamiento
    story.append(Paragraph("II. Registros de comportamiento", _S_SECCION))
    story.extend(_tabla_registros(entradas, content_w))

    # 6. Seguimientos
    seg_elements = _tabla_seguimientos(entradas, content_w)
    if seg_elements:
        story.extend(seg_elements)

    # 7. Resumen
    story.append(Paragraph("Resumen consolidado", _S_SECCION))
    story.append(_tabla_resumen(resumen, content_w))

    # 8. Notas de comportamiento por periodo
    story.extend(_tabla_notas_periodo(resumen, content_w))

    # 9. Firmas
    story.append(_tabla_firmas(content_w))

    # 10. Pie con fecha de generación
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f"Documento generado el {_date.today().strftime('%d/%m/%Y')} — Sistema ZECI Manager",
        _S_FOOTER,
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


__all__ = ["generar_observador_pdf"]
