"""
src/domain/modulos.py
=====================
Registro unico de modulos del sistema — fuente de verdad (inicio_34).

Datos puros, sin dependencias de runtime, para que lo importen tanto
``services`` como ``interface`` sin romper las reglas de capa.

Cada modulo declara las rutas que gatea, la clave de preferencia para
desactivarlo (si aplica) y metadatos de presentacion (label, icono).
Los consumidores consultan helpers en lugar de mantener copias locales.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Modulo(StrEnum):
    ASISTENCIA = "asistencia"
    EVALUACION = "evaluacion"
    ACADEMICO = "academico"
    CONVIVENCIA = "convivencia"
    INFORMES = "informes"
    ALERTAS = "alertas"


@dataclass(frozen=True)
class DefinicionModulo:
    id: Modulo
    label: str
    descripcion: str
    icono: str
    ruta_principal: str | None  # None -> sin pagina propia, no genera tarjeta
    rutas: frozenset[str]  # rutas que el modulo gatea
    clave_preferencia: str | None  # None -> modulo nucleo, no desactivable


MODULOS: dict[Modulo, DefinicionModulo] = {
    Modulo.ASISTENCIA: DefinicionModulo(
        id=Modulo.ASISTENCIA,
        label="Asistencia",
        descripcion="Control diario de asistencia",
        icono="fact_check",
        ruta_principal="/asistencia",
        rutas=frozenset({"/asistencia"}),
        clave_preferencia=None,
    ),
    Modulo.EVALUACION: DefinicionModulo(
        id=Modulo.EVALUACION,
        label="Evaluacion",
        descripcion="Notas, habilitaciones y planes",
        icono="grading",
        ruta_principal="/evaluacion/planilla",
        rutas=frozenset(
            {
                "/evaluacion/configuracion",
                "/evaluacion/planilla",
                "/evaluacion/habilitaciones",
                "/evaluacion/planes",
                "/evaluacion/cierre-periodo",
                "/evaluacion/cierre-anio",
            }
        ),
        clave_preferencia=None,
    ),
    Modulo.ACADEMICO: DefinicionModulo(
        id=Modulo.ACADEMICO,
        label="Academico",
        descripcion="Estudiantes, grupos y horarios",
        icono="school",
        ruta_principal="/estudiantes",
        rutas=frozenset(
            {
                "/estudiantes",
                "/admin/grupos",
                "/admin/asignaturas",
                "/admin/plan-estudios",
                "/admin/asignaciones",
                "/horarios",
                "/academico/horarios",
                "/academico/generar-horario",
                "/admin/disponibilidad-docente",
                "/admin/salas",
                "/academico/tablero",
            }
        ),
        clave_preferencia=None,
    ),
    Modulo.CONVIVENCIA: DefinicionModulo(
        id=Modulo.CONVIVENCIA,
        label="Convivencia",
        descripcion="Observaciones, comportamiento y seguimiento",
        icono="psychology",
        ruta_principal="/convivencia/observaciones",
        rutas=frozenset(
            {
                "/convivencia/observaciones",
                "/convivencia/comportamiento",
                "/convivencia/notas",
                "/convivencia/reporte-periodo",
                "/convivencia/configuracion",
                "/convivencia/categorias",
                "/convivencia/plantillas",
                "/convivencia/seguimiento",
            }
        ),
        clave_preferencia="modulo_convivencia_activo",
    ),
    Modulo.INFORMES: DefinicionModulo(
        id=Modulo.INFORMES,
        label="Informes",
        descripcion="Boletines, consolidados y estadisticos",
        icono="summarize",
        ruta_principal="/informes/estadisticos",
        rutas=frozenset(
            {
                "/informes/boletin-periodo",
                "/informes/boletin-anual",
                "/informes/estadisticos",
                "/informes/consolidado-notas",
                "/informes/consolidado-asistencia",
            }
        ),
        clave_preferencia=None,
    ),
    Modulo.ALERTAS: DefinicionModulo(
        id=Modulo.ALERTAS,
        label="Alertas",
        descripcion="Notificaciones y alertas",
        icono="notifications",
        ruta_principal=None,
        rutas=frozenset(),
        clave_preferencia="modulo_alertas_activo",
    ),
}


# Indice invertido ruta -> modulo, construido una sola vez al importar.
_RUTA_A_MODULO: dict[str, Modulo] = {}
for _m, _d in MODULOS.items():
    for _r in _d.rutas:
        _RUTA_A_MODULO[_r] = _m


def modulo_de_ruta(ruta: str) -> Modulo | None:
    """Devuelve el modulo al que pertenece *ruta*, o ``None`` si es libre."""
    return _RUTA_A_MODULO.get(ruta)


def definicion(m: Modulo | str) -> DefinicionModulo | None:
    """Devuelve la definicion de un modulo por enum o por nombre string."""
    if isinstance(m, str):
        try:
            m = Modulo(m)
        except ValueError:
            return None
    return MODULOS.get(m)


def clave_de_modulo(nombre: str) -> str | None:
    """Devuelve la clave de preferencia del modulo, o ``None`` si es nucleo
    o si el modulo no existe."""
    d = definicion(nombre)
    return d.clave_preferencia if d else None


def modulos_desactivables() -> list[DefinicionModulo]:
    """Modulos con clave de preferencia (pueden desactivarse por tenant)."""
    return [d for d in MODULOS.values() if d.clave_preferencia is not None]


def modulos_con_pagina() -> list[DefinicionModulo]:
    """Modulos con ruta_principal (generan tarjeta en el hub del inicio)."""
    return [d for d in MODULOS.values() if d.ruta_principal is not None]


__all__ = [
    "MODULOS",
    "DefinicionModulo",
    "Modulo",
    "clave_de_modulo",
    "definicion",
    "modulo_de_ruta",
    "modulos_con_pagina",
    "modulos_desactivables",
]
