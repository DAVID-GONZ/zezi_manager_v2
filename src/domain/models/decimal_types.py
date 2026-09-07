"""
Tipos anotados y funciones de cuantización decimal exacta.

Fuente única de verdad para NotaDecimal y PesoDecimal (R7).
Todos los modelos que representan calificaciones y pesos importan desde aquí.

Decisiones de diseño (datos_04_decimal_notas):
  - ROUND_HALF_UP (no ROUND_HALF_EVEN): 2.995 → 3.00 de forma predecible.
  - Dos precisiones: notas a 2 decimales, pesos a 4 decimales.
  - BeforeValidator garantiza la cuantización antes de la validación de rango.
"""

from __future__ import annotations

import sys

# Consola UTF-8 (windows cp1252)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from pydantic import BeforeValidator

# ── Cuantizadores ────────────────────────────────────────────────────────────

QUANT_NOTA: Decimal = Decimal("0.01")   # 2 decimales
QUANT_PESO: Decimal = Decimal("0.0001")  # 4 decimales


def cuantizar_nota(v: str | int | float | Decimal) -> Decimal:
    """
    Normaliza cualquier entrada numérica a Decimal con 2 decimales ROUND_HALF_UP.

    Acepta str, int, float y Decimal (R5, R6).
    La conversión desde float usa str() para evitar ruido binario (R19).
    """
    if isinstance(v, Decimal):
        d = v
    elif isinstance(v, float):
        d = Decimal(str(v))
    else:
        d = Decimal(str(v))
    return d.quantize(QUANT_NOTA, rounding=ROUND_HALF_UP)


def cuantizar_peso(v: str | int | float | Decimal) -> Decimal:
    """
    Normaliza cualquier entrada numérica a Decimal con 4 decimales ROUND_HALF_UP.

    Acepta str, int, float y Decimal (R5, R6).
    La conversión desde float usa str() para evitar ruido binario (R19).
    """
    if isinstance(v, Decimal):
        d = v
    elif isinstance(v, float):
        d = Decimal(str(v))
    else:
        d = Decimal(str(v))
    return d.quantize(QUANT_PESO, rounding=ROUND_HALF_UP)


# ── Tipos anotados ────────────────────────────────────────────────────────────

#: Calificación, umbral o límite de escala: 2 decimales, ROUND_HALF_UP.
NotaDecimal = Annotated[Decimal, BeforeValidator(cuantizar_nota)]

#: Peso de ponderación (fracción 0-1): 4 decimales, ROUND_HALF_UP.
PesoDecimal = Annotated[Decimal, BeforeValidator(cuantizar_peso)]


__all__ = [
    "QUANT_NOTA",
    "QUANT_PESO",
    "NotaDecimal",
    "PesoDecimal",
    "cuantizar_nota",
    "cuantizar_peso",
]
