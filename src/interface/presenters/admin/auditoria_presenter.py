"""Presenter puro de la página de auditoría (`/admin/auditoria`).

Sin import de NiceGUI. Concentra el view-state de los filtros y la lógica pura
que estaba dispersa en la página: parseo de fechas (con fin-de-día), coerción a
int y la construcción del `FiltroAuditoriaDTO` a partir del estado. Importar el
DTO del servicio es correcto: es backend, no UI.
"""
from __future__ import annotations

from datetime import datetime

from src.services.auditoria_service import FiltroAuditoriaDTO


class AuditoriaPresenter:
    """View-model de auditoría: filtros + helpers de parseo + construcción de DTO."""

    def __init__(self) -> None:
        self.estado: dict = {
            # filtros comunes
            "desde": None,  # "YYYY-MM-DD" o None
            "hasta": None,
            "usuario_id": None,
            "pagina": 1,
            # específicos de Cambios
            "tabla": None,
            "accion": None,
            # específicos de Sesiones
            "tipo_evento": None,
            # datos cargados
            "cambios": [],
            "sesiones": [],
            "integridad": None,
        }

    # ── Helpers puros ───────────────────────────────────────────────────────

    @staticmethod
    def a_int(valor) -> int | None:
        try:
            v = str(valor).strip()
            return int(v) if v else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def parsear_fecha(valor: str | None, fin_de_dia: bool = False) -> datetime | None:
        if not valor:
            return None
        try:
            base = datetime.strptime(valor, "%Y-%m-%d")
        except ValueError:
            return None
        return base.replace(hour=23, minute=59, second=59) if fin_de_dia else base

    # ── Transiciones de filtro ──────────────────────────────────────────────

    def set_rango(self, desde: str | None, hasta: str | None) -> None:
        self.estado["desde"] = desde
        self.estado["hasta"] = hasta

    def set_usuario(self, valor) -> None:
        self.estado["usuario_id"] = self.a_int(valor)

    def set_tabla(self, valor) -> None:
        self.estado["tabla"] = (valor or "").strip() or None

    def set_accion(self, valor) -> None:
        self.estado["accion"] = valor

    def set_tipo_evento(self, valor) -> None:
        self.estado["tipo_evento"] = valor

    def set_pagina(self, pagina: int) -> None:
        self.estado["pagina"] = pagina

    def reset_pagina(self) -> None:
        self.estado["pagina"] = 1

    def set_cambios(self, cambios) -> None:
        self.estado["cambios"] = list(cambios)

    def set_sesiones(self, sesiones) -> None:
        self.estado["sesiones"] = list(sesiones)

    # ── Construcción del DTO de consulta ────────────────────────────────────

    def construir_filtro(self, por_pagina: int) -> FiltroAuditoriaDTO:
        return FiltroAuditoriaDTO(
            usuario_id=self.estado["usuario_id"],
            tabla=self.estado["tabla"] or None,
            accion=self.estado["accion"] or None,
            tipo_evento=self.estado["tipo_evento"] or None,
            desde=self.parsear_fecha(self.estado["desde"]),
            hasta=self.parsear_fecha(self.estado["hasta"], fin_de_dia=True),
            pagina=self.estado["pagina"],
            por_pagina=por_pagina,
        )


__all__ = ["AuditoriaPresenter"]
