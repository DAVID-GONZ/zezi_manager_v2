"""Tests unitarios para generar_boletin_periodo_pdf, generar_boletin_acumulado_pdf y generar_reporte_convivencia_grupo_pdf."""
from __future__ import annotations

from src.infrastructure.exporters.boletin_pdf import (
    generar_boletin_acumulado_pdf,
    generar_boletin_periodo_pdf,
    generar_reporte_convivencia_grupo_pdf,
)

# ---------------------------------------------------------------------------
# Datos mínimos reutilizables
# ---------------------------------------------------------------------------

_ESTUDIANTE_BASE = {
    "nombre": "Juan Estudiante",
    "documento": "12345678",
    "grupo": "10A",
    "periodo": "Periodo 1",
    "anio": "2025",
    "estado_promocion": "promovido",
}

_AREA_BASE = {
    "area_nombre": "Matemáticas",
    "asignaturas": [
        {
            "nombre": "Álgebra",
            "nota": 4.5,
            "presentes": 20,
            "faltas_injustificadas": 1,
            "faltas_justificadas": 0,
            "retrasos": 0,
            "excusas": 0,
        }
    ],
}

_PERIODOS_BASE = [
    {"id": 1, "nombre": "P1"},
    {"id": 2, "nombre": "P2"},
]

_AREA_ANUAL_BASE = {
    "area_nombre": "Matemáticas",
    "asignaturas": [
        {
            "nombre": "Álgebra",
            "notas_periodo": {1: 4.5, 2: 4.0},
            "definitiva": 4.3,
            "presentes": 40,
            "faltas_injustificadas": 2,
            "faltas_justificadas": 0,
            "retrasos": 1,
            "excusas": 0,
        }
    ],
}


def _datos_periodo(**kwargs) -> dict:
    base = {
        "estudiante": _ESTUDIANTE_BASE,
        "areas": [_AREA_BASE],
    }
    base.update(kwargs)
    return base


def _datos_acumulado(**kwargs) -> dict:
    base = {
        "estudiante": _ESTUDIANTE_BASE,
        "periodos": _PERIODOS_BASE,
        "areas": [_AREA_ANUAL_BASE],
        "es_ultimo_periodo": False,
    }
    base.update(kwargs)
    return base


# ---------------------------------------------------------------------------
# T3a — periodo sin clave convivencia
# ---------------------------------------------------------------------------

def test_boletin_periodo_sin_convivencia():
    """Sin clave convivencia → la caja queda vacía; no lanza excepción."""
    datos = _datos_periodo()
    assert "convivencia" not in datos

    resultado = generar_boletin_periodo_pdf(datos)

    assert isinstance(resultado, bytes)
    assert len(resultado) > 0


# ---------------------------------------------------------------------------
# T3b — periodo con nota de convivencia
# ---------------------------------------------------------------------------

def test_boletin_periodo_con_nota():
    """convivencia con nota numérica → PDF generado sin excepción."""
    datos = _datos_periodo(
        convivencia={"nota": 78.5, "nota_observacion": None, "observaciones": []}
    )

    resultado = generar_boletin_periodo_pdf(datos)

    assert isinstance(resultado, bytes)
    assert len(resultado) > 0


# ---------------------------------------------------------------------------
# T3c — acumulado con nota, nota_observacion y lista de observaciones
# ---------------------------------------------------------------------------

def test_boletin_acumulado_con_obs():
    """convivencia completa en boletín acumulado → PDF generado sin excepción."""
    datos = _datos_acumulado(
        convivencia={
            "nota": 90.0,
            "nota_observacion": "Excelente",
            "observaciones": ["Puntual", "Colaborativo"],
        }
    )

    resultado = generar_boletin_acumulado_pdf(datos)

    assert isinstance(resultado, bytes)
    assert len(resultado) > 0


# ---------------------------------------------------------------------------
# T3d — sin nota pero con observaciones
# ---------------------------------------------------------------------------

def test_boletin_sin_nota_con_obs():
    """convivencia con nota=None pero con observación textual → PDF generado sin excepción."""
    datos = _datos_periodo(
        convivencia={
            "nota": None,
            "nota_observacion": None,
            "observaciones": ["Mejorar actitud"],
        }
    )

    resultado = generar_boletin_periodo_pdf(datos)

    assert isinstance(resultado, bytes)
    assert len(resultado) > 0


# ---------------------------------------------------------------------------
# Reporte de convivencia por grupo (generar_reporte_convivencia_grupo_pdf)
# ---------------------------------------------------------------------------

_FILA_GRUPO_BASE = {
    "estudiante": "López García, María",
    "nota": 85.0,
    "nivel": "Superior",
    "fortalezas": 2,
    "dificultades": 1,
    "compromisos": 0,
    "citaciones": 0,
    "descargos": 0,
    "concepto": "Buen comportamiento.",
    "observaciones": "1. Participación activa",
    "num_obs": 1,
}


def test_reporte_grupo_pdf_basico():
    """Genera PDF con filas de grupo y verifica encabezado válido."""
    resultado = generar_reporte_convivencia_grupo_pdf(
        filas=[_FILA_GRUPO_BASE],
        titulo="Reporte de convivencia",
        grupo="5A",
        periodo="Periodo 1",
    )
    assert isinstance(resultado, bytes)
    assert resultado[:5] == b"%PDF-"
    assert len(resultado) > 100


def test_reporte_grupo_pdf_sin_filas():
    """Genera PDF vacío sin excepción cuando no hay estudiantes."""
    resultado = generar_reporte_convivencia_grupo_pdf(
        filas=[], titulo="Reporte vacío", grupo="5A", periodo="P1",
    )
    assert isinstance(resultado, bytes)
    assert resultado[:5] == b"%PDF-"


def test_reporte_grupo_pdf_con_desglose():
    """Genera PDF incluyendo columnas de desglose por tipo de situación."""
    fila = {**_FILA_GRUPO_BASE, "Tipo I": 2, "Tipo II": 0}
    resultado = generar_reporte_convivencia_grupo_pdf(
        filas=[fila],
        titulo="Reporte con desglose",
        grupo="8B",
        periodo="Periodo 2",
        desglose_cols=["Tipo I", "Tipo II"],
    )
    assert isinstance(resultado, bytes)
    assert resultado[:5] == b"%PDF-"


def test_reporte_grupo_pdf_nota_none():
    """Estudiante sin nota no causa excepción y se refleja en estadísticos."""
    fila = {**_FILA_GRUPO_BASE, "nota": None, "nivel": ""}
    resultado = generar_reporte_convivencia_grupo_pdf(
        filas=[fila], titulo="Reporte", grupo="3C", periodo="P1",
    )
    assert isinstance(resultado, bytes)
    assert resultado[:5] == b"%PDF-"


def test_reporte_grupo_pdf_multiples_estudiantes():
    """PDF con múltiples estudiantes y estadísticos calculados."""
    filas = [
        {**_FILA_GRUPO_BASE, "estudiante": "Est 1", "nota": 90.0, "nivel": "Superior"},
        {**_FILA_GRUPO_BASE, "estudiante": "Est 2", "nota": 70.0, "nivel": "Básico"},
        {**_FILA_GRUPO_BASE, "estudiante": "Est 3", "nota": 60.0, "nivel": "Bajo"},
        {**_FILA_GRUPO_BASE, "estudiante": "Est 4", "nota": None, "nivel": ""},
    ]
    resultado = generar_reporte_convivencia_grupo_pdf(
        filas=filas, titulo="Reporte múltiple", grupo="10A", periodo="P2",
    )
    assert isinstance(resultado, bytes)
    assert resultado[:5] == b"%PDF-"
