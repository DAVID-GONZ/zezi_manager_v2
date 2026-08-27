"""Presenter puro de la página de observaciones (`/convivencia/observaciones`).

Sin import de NiceGUI. Guarda el view-state de la selección (periodo/grupo/
asignatura + estudiantes elegidos) y los datos cargados del grupo. `aplicar_seleccion`
copia la selección del selector inline y resetea los estudiantes elegidos; la carga
de estudiantes/asignaciones se queda en la página.

Extiende el estado con la vista del observador del estudiante (convivencia_37):
'observador_*' keys contienen las entradas cronológicas, el resumen y el
estudiante actualmente visualizado.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("OBSERVACIONES_PRESENTER")


class ObservacionesPresenter:
    """View-model de observaciones: selección periodo/grupo/asignatura + observador."""

    def __init__(self) -> None:
        self.estado: dict = {
            # ── Selección del selector inline ─────────────────────────────────
            "estudiantes": [],
            "periodos": [],
            "anio_id": None,
            "sel_estudiante_ids": [],
            "sel_periodo_id": None,
            "sel_grupo_id": None,
            "sel_grupo_nombre": "",
            "sel_asignacion_id": None,
            "sel_asignacion_nombre": "",
            "plantilla_id": None,
            "asignaciones_grupo": [],
            # ── Estado del observador (convivencia_37) ─────────────────────────
            "observador_estudiante_id": None,
            "observador_periodo_filter": None,
            "observador_entradas": [],
            "observador_resumen": {},
            "observador_cargando": False,
            "observador_error": None,
        }

    def aplicar_seleccion(self, seleccion: dict) -> None:
        """Copia periodo/grupo/asignatura del selector y limpia los estudiantes elegidos."""
        self.estado["sel_periodo_id"] = seleccion["sel_periodo_id"]
        self.estado["sel_grupo_id"] = seleccion["sel_grupo_id"]
        self.estado["sel_asignacion_id"] = seleccion["sel_asignacion_id"]
        self.estado["sel_asignacion_nombre"] = seleccion.get("sel_asignacion_nombre", "")
        self.estado["sel_estudiante_ids"] = []
        # Al cambiar de grupo, limpiar el observador
        self._reset_observador()

    def _reset_observador(self) -> None:
        """Limpia el estado del observador."""
        self.estado["observador_estudiante_id"] = None
        self.estado["observador_entradas"] = []
        self.estado["observador_resumen"] = {}
        self.estado["observador_error"] = None

    def cargar_observador(
        self,
        estudiante_id: int,
        anio_id: int,
        periodo_id: int | None = None,
        convivencia_service=None,
    ) -> None:
        """Llama al servicio y actualiza el state del observador.

        Args:
            estudiante_id: ID del estudiante a visualizar.
            anio_id: ID del año lectivo activo.
            periodo_id: filtro opcional por periodo.
            convivencia_service: instancia del ConvivenciaService.
        """
        self.estado["observador_estudiante_id"] = estudiante_id
        self.estado["observador_periodo_filter"] = periodo_id
        self.estado["observador_cargando"] = True
        self.estado["observador_error"] = None

        if convivencia_service is None:
            self.estado["observador_cargando"] = False
            self.estado["observador_error"] = "Servicio no disponible."
            return

        try:
            datos = convivencia_service.observador_estudiante(
                estudiante_id, anio_id, periodo_id
            )
            self.estado["observador_entradas"] = datos.get("entradas", [])
            self.estado["observador_resumen"] = datos.get("resumen", {})
        except Exception as exc:
            logger.warning("Error cargando observador del estudiante %s: %s", estudiante_id, exc)
            self.estado["observador_entradas"] = []
            self.estado["observador_resumen"] = {}
            self.estado["observador_error"] = str(exc)
        finally:
            self.estado["observador_cargando"] = False

    def puede_exportar(self) -> bool:
        """True si hay entradas cargadas en el observador."""
        return bool(self.estado.get("observador_entradas"))


__all__ = ["ObservacionesPresenter"]
