"""Presenter puro de la página de estadísticos (informes).

Sin ningún import de NiceGUI. Contiene el estado del formulario, las transiciones
de los selectores (con su cascada de reseteos) y el **mapeo a presentación** de
las métricas de resumen. Los NÚMEROS de ese resumen (con los umbrales de negocio)
los calcula el backend en `estadisticos_service.resumen_consolidado`; el presenter
solo los formatea a tarjetas. La página `estadisticos.py` queda como adaptador:
crea el presenter, comparte su `estado` con los refreshables, llama a las
transiciones en los handlers y luego dispara los `.refresh()`. La carga de datos
(Container/repos) sigue en la página.

Las métricas de resumen se devuelven como `MetricaResumen` con `icono` y
`variante` en forma de *claves semánticas* (strings neutrales); la página las
mapea a los tokens de diseño reales. Así el presenter no depende ni de NiceGUI
ni del design system.
"""
from __future__ import annotations

from dataclasses import dataclass


def estado_inicial() -> dict:
    """Estado inicial del formulario (espejo del que usaba la página)."""
    return {
        "tipo": None,  # str | None — uno de los IDs de tipo de informe
        "grupo_id": None,
        "asignacion_id": None,
        "periodo_id": None,
        "grupos": [],
        "asignaciones": [],
        "periodos": [],
        "todas_asignaciones_docente": [],  # solo usado cuando rol == "profesor"
        "datos": None,  # list | dict | None
        "datos_listos": False,
    }


def _a_int(valor) -> int | None:
    """Coerciona el valor de un selector (str de Quasar) a int, preservando None."""
    return int(valor) if valor is not None else None


@dataclass(frozen=True)
class MetricaResumen:
    """Una tarjeta de resumen: título + valor ya formateado + claves de estilo."""

    titulo: str
    valor: str
    icono: str = ""     # clave semántica: students | grades | check | warning
    variante: str = ""  # primary | info | success | danger


class EstadisticosPresenter:
    """Estado + lógica de decisión de la página de estadísticos (sin UI)."""

    def __init__(self, tipos_map: dict[str, dict] | None = None) -> None:
        # `tipos_map`: {id_tipo: {"filtros": [...], ...}} — catálogo de tipos de
        # informe; el presenter solo lee la lista de filtros requeridos.
        self._tipos = tipos_map or {}
        self.estado: dict = estado_inicial()

    # ── Transiciones (mutan el estado; sin tocar la UI) ─────────────────────

    def _limpiar_datos(self) -> None:
        self.estado["datos"] = None
        self.estado["datos_listos"] = False

    def set_tipo(self, tipo: str | None) -> None:
        """Cambiar el tipo de informe resetea asignatura y periodo."""
        self.estado["tipo"] = tipo
        self.estado["asignacion_id"] = None
        self.estado["periodo_id"] = None
        self._limpiar_datos()

    def set_grupo(self, grupo_id) -> None:
        """Cambiar el grupo resetea la asignatura (depende del grupo)."""
        self.estado["grupo_id"] = _a_int(grupo_id)
        self.estado["asignacion_id"] = None
        self._limpiar_datos()

    def set_asignacion(self, asignacion_id) -> None:
        self.estado["asignacion_id"] = _a_int(asignacion_id)
        self._limpiar_datos()

    def set_periodo(self, periodo_id) -> None:
        self.estado["periodo_id"] = _a_int(periodo_id)
        self._limpiar_datos()

    # ── Consultas puras ─────────────────────────────────────────────────────

    def tipo_activo(self) -> dict | None:
        return self._tipos.get(self.estado["tipo"])

    def filtros_completos(self) -> bool:
        """True si están elegidos todos los filtros que el tipo activo requiere."""
        tipo = self.tipo_activo()
        if not tipo:
            return False
        filtros = tipo["filtros"]
        if "grupo" in filtros and not self.estado["grupo_id"]:
            return False
        if "asignatura" in filtros and not self.estado["asignacion_id"]:
            return False
        return not ("periodo" in filtros and not self.estado["periodo_id"])

    # ── Resumen (cálculo puro de las tarjetas) ──────────────────────────────

    @staticmethod
    def resumen(tipo: str | None, datos) -> list[MetricaResumen]:
        """Tarjetas de resumen para (tipo, datos). Lista vacía si no hay datos.

        Los NÚMEROS los calcula el backend (`resumen_consolidado`, que aplica los
        umbrales de negocio); aquí solo se **mapea a presentación**: títulos,
        formato y claves de icono/variante.
        """
        from src.services.estadisticos_service import resumen_consolidado

        r = resumen_consolidado(tipo, datos)
        if r is None:
            return []

        if r.clase in ("notas", "ranking"):
            aprob_pct = r.aprobados * 100 // r.n if r.n else 0
            metricas = [
                MetricaResumen("Estudiantes", str(r.n), "students", "primary"),
                MetricaResumen("Promedio grupal", f"{r.promedio_grupal:.1f}", "grades", "info"),
                MetricaResumen("Aprobados", f"{r.aprobados} ({aprob_pct}%)", "check", "success"),
                MetricaResumen("Reprobados", str(r.reprobados), "warning", "danger"),
            ]
            if r.clase == "ranking":
                metricas.append(MetricaResumen("Mejor nota", f"{r.mejor:.1f}", "grades", "success"))
                metricas.append(MetricaResumen("Menor nota", f"{r.menor:.1f}", "warning", "danger"))
            return metricas

        if r.clase == "asistencia":
            return [
                MetricaResumen("Estudiantes", str(r.n), "students", "primary"),
                MetricaResumen(
                    "% Asistencia prom.", f"{r.pct_asistencia_prom:.1f}%", "check", "success"
                ),
                MetricaResumen("Bajo 70%", str(r.bajo_umbral_asistencia), "warning", "danger"),
            ]

        if r.clase == "anual":
            return [
                MetricaResumen("Estudiantes", str(r.n), "students", "primary"),
                MetricaResumen("Definitiva prom.", f"{r.definitiva_prom:.1f}", "grades", "info"),
                MetricaResumen("Promovidos", str(r.promovidos), "check", "success"),
                MetricaResumen("Reprobados", str(r.reprobados), "warning", "danger"),
            ]

        return [MetricaResumen("Total registros", str(r.total_registros), "grades", "primary")]


__all__ = ["EstadisticosPresenter", "MetricaResumen", "estado_inicial"]
