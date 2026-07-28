"""Tests unitarios para generar_boletin_periodo_pdf y generar_boletin_acumulado_pdf."""
from __future__ import annotations

import pytest

from src.infrastructure.exporters.boletin_pdf import (
    generar_boletin_acumulado_pdf,
    generar_boletin_periodo_pdf,
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
