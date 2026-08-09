"""
Catálogos estándar colombianos para aprovisionar un tenant nuevo.
====================================================================
Fuente única (single source of truth) consumida por el seed de arranque
(`src/infrastructure/db/seed.py`) y por el aprovisionamiento en runtime
(`AprovisionamientoInstitucionService`).

Módulo puro de dominio: sin dependencias de infraestructura ni interfaz.
"""
from __future__ import annotations

AREAS_ESTANDAR_CO: list[tuple[str, str]] = [
    ("Matemáticas", "MAT"),
    ("Ciencias Naturales y Educación Ambiental", "NAT"),
    ("Ciencias Sociales, Historia, Geografía y C. Económicas", "SOC"),
    ("Lenguaje", "LEN"),
    ("Educación Física, Recreación y Deportes", "EFI"),
    ("Educación Artística y Cultural", "ART"),
    ("Tecnología e Informática", "TEC"),
    ("Educación Ética y en Valores Humanos", "ETI"),
    ("Ciencias Económicas y Políticas", "CEP"),
    ("Filosofía", "FIL"),
    ("Idioma Extranjero", "IDI"),
    ("Educación Religiosa", "REL"),
]

CATEGORIAS_BASE_CO: list[tuple[str, bool]] = [
    ("Comportamiento positivo", True),
    ("Convivencia y normas", True),
    ("Académico", False),
    ("Responsabilidad y actitud", False),
]

PREF_DEFAULTS: list[tuple[str, str, str | None, str]] = [
    ("academicas",  "nota_minima_aprobacion_default", "60.0",    "float"),
    ("academicas",  "nota_minima_escala_default",     "0.0",     "float"),
    ("academicas",  "nota_maxima_escala_default",     "100.0",   "float"),
    ("academicas",  "numero_periodos_default",        "4",       "int"),
    ("convivencia", "modulo_convivencia_activo",      "true",    "bool"),
    ("convivencia", "modulo_alertas_activo",          "true",    "bool"),
    ("apariencia",  "color_primario",                 "#2E3192", "str"),
    ("apariencia",  "color_secundario",               "#8B90F0", "str"),
]

__all__ = ["AREAS_ESTANDAR_CO", "CATEGORIAS_BASE_CO", "PREF_DEFAULTS"]
