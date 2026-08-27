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

TIPOS_SITUACION_CO: list[tuple[str, int, str]] = [
    (
        "Tipo I - Conflictos manejados inadecuadamente",
        1,
        "Situaciones esporadicas que inciden negativamente en el clima escolar "
        "y que en ningun caso generan danos al cuerpo o a la salud fisica o "
        "mental de los involucrados.",
    ),
    (
        "Tipo II - Agresion escolar o acoso",
        2,
        "Situaciones de agresion escolar, acoso escolar (bullying) y "
        "ciberacoso que no revistan las caracteristicas de la comision de "
        "un delito y que cumplan con cualquiera de las siguientes "
        "caracteristicas: a) que se presenten de manera repetida o "
        "sistematica; b) que causen danos al cuerpo o a la salud (fisica "
        "o mental) sin generar incapacidad alguna.",
    ),
    (
        "Tipo III - Presuntos delitos",
        3,
        "Situaciones de agresion escolar que sean constitutivas de presuntos "
        "delitos contra la libertad, integridad y formacion sexual, u otro "
        "delito establecido en la ley penal colombiana vigente.",
    ),
]

PREF_DEFAULTS: list[tuple[str, str, str | None, str]] = [
    ("academicas", "nota_minima_aprobacion_default", "60.0", "float"),
    ("academicas", "nota_minima_escala_default", "0.0", "float"),
    ("academicas", "nota_maxima_escala_default", "100.0", "float"),
    ("academicas", "numero_periodos_default", "4", "int"),
    ("convivencia", "modulo_convivencia_activo", "true", "bool"),
    ("convivencia", "modulo_alertas_activo", "true", "bool"),
    ("apariencia", "color_primario", "#2E3192", "str"),
    ("apariencia", "color_secundario", "#8B90F0", "str"),
]

MEDIDAS_PEDAGOGICAS_CO: list[tuple[str, str, int]] = [
    ("Dialogo pedagogico", "Conversacion formativa con el estudiante", 1),
    ("Amonestacion verbal", "Llamado de atencion verbal con registro en el observador", 1),
    ("Amonestacion escrita", "Registro formal escrito en el observador del estudiante", 1),
    ("Compromiso de convivencia", "Acuerdo firmado por estudiante y acudiente", 1),
    ("Citacion a acudiente", "Convocatoria formal al representante legal", 2),
    ("Remision a orientacion escolar", "Derivacion al profesional de apoyo psicosocial", 2),
    ("Matricula condicional", "Continuidad sujeta a cumplimiento de compromisos", 3),
    ("No renovacion de matricula", "Decision del Comite de Convivencia Escolar", 3),
]

__all__ = [
    "AREAS_ESTANDAR_CO",
    "CATEGORIAS_BASE_CO",
    "MEDIDAS_PEDAGOGICAS_CO",
    "PREF_DEFAULTS",
    "TIPOS_SITUACION_CO",
]
