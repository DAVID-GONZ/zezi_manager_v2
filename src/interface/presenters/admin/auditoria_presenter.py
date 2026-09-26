"""Presenter puro de la página de auditoría (`/admin/auditoria`).

Sin import de NiceGUI. Concentra el view-state de los filtros y la lógica pura
que estaba dispersa en la página: parseo de fechas (con fin-de-día), coerción a
int y la construcción del `FiltroAuditoriaDTO` a partir del estado. Importar el
DTO del servicio es correcto: es backend, no UI.

obs_09: añade state para registro_id, sin_institucion, detalle y actores (T10).
El presenter NO calcula diff ni etiquetas (R13).
"""
from __future__ import annotations

from datetime import datetime

from src.services.auditoria_service import FiltroAuditoriaDTO

# Centinela que la UI usa como clave en el selector de institución para la
# opción «Sin institución» (R12). El presenter lo detecta en set_institucion.
_SIN_INSTITUCION_SENTINEL = "__sin_institucion__"


class AuditoriaPresenter:
    """View-model de auditoría: filtros + helpers de parseo + construcción de DTO."""

    def __init__(self) -> None:
        self.estado: dict = {
            # filtros comunes
            "desde": None,  # "YYYY-MM-DD" o None
            "hasta": None,
            "usuario_id": None,
            "institucion_id": None,
            "pagina": 1,
            # específicos de Cambios
            "tabla": None,
            "accion": None,
            # específicos de Sesiones
            "tipo_evento": None,
            "severidad": None,                # obs_07 T11: filtro por severidad
            # datos cargados
            "cambios": [],
            "sesiones": [],
            "integridad": None,
            # paginación look-ahead
            "hay_siguiente_cambios": False,
            "hay_siguiente_sesiones": False,
            # obs_08 T10: totales para mostrar «N resultados» junto a la paginación
            "total_cambios": 0,
            "total_sesiones": 0,
            # obs_09 T10: nuevos
            "registro_id": None,              # filtro por entidad concreta (R11)
            "sin_institucion": False,         # opción «Sin institución» (R12)
            "detalle": None,                  # DetalleCambioDTO | None — cambio abierto
            "actores": {},                    # usuario_id → nombre, de la página actual
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

    def set_institucion(self, valor) -> None:
        """Acepta el centinela «sin institución», un entero o None (R12)."""
        if valor == _SIN_INSTITUCION_SENTINEL:
            self.estado["institucion_id"] = None
            self.estado["sin_institucion"] = True
        else:
            self.estado["sin_institucion"] = False
            self.estado["institucion_id"] = self.a_int(valor)

    def set_registro(self, valor) -> None:
        """obs_09 T10: filtro por registro_id (R11)."""
        self.estado["registro_id"] = self.a_int(valor)

    def set_tabla(self, valor) -> None:
        self.estado["tabla"] = (valor or "").strip() or None

    def set_accion(self, valor) -> None:
        self.estado["accion"] = valor

    def set_tipo_evento(self, valor) -> None:
        self.estado["tipo_evento"] = valor

    def set_severidad(self, valor) -> None:
        """obs_07 T11: filtro por severidad (valor: string o None)."""
        self.estado["severidad"] = valor or None

    def set_pagina(self, pagina: int) -> None:
        self.estado["pagina"] = pagina

    def reset_pagina(self) -> None:
        self.estado["pagina"] = 1

    def set_cambios(self, cambios) -> None:
        self.estado["cambios"] = list(cambios)

    def set_sesiones(self, sesiones) -> None:
        self.estado["sesiones"] = list(sesiones)

    def set_total_cambios(self, total: int) -> None:
        """obs_08 T10: total de cambios para el filtro activo (R11)."""
        self.estado["total_cambios"] = int(total)

    def set_total_sesiones(self, total: int) -> None:
        """obs_08 T10: total de sesiones para el filtro activo (R11)."""
        self.estado["total_sesiones"] = int(total)

    def set_actores(self, actores: dict) -> None:
        """obs_09 T10: almacena el mapa usuario_id → nombre de la página actual."""
        self.estado["actores"] = dict(actores)

    def abrir_detalle(self, dto) -> None:
        """obs_09 T10: almacena el DetalleCambioDTO del cambio abierto."""
        self.estado["detalle"] = dto

    def cerrar_detalle(self) -> None:
        """obs_09 T10: limpia el detalle abierto."""
        self.estado["detalle"] = None

    def nombre_actor(self, cambio) -> str:
        """
        obs_09 T10: cascada de fallback para el nombre del actor (R9).

        1. Nombre completo del mapa actores (resuelto por AuditoriaService).
        2. Username almacenado en la fila (snapshot de obs_06).
        3. «Usuario #N» si solo hay usuario_id.
        4. «—» si no hay ninguna referencia.
        """
        usuario_id = getattr(cambio, "usuario_id", None)
        if usuario_id is not None:
            nombre = self.estado["actores"].get(usuario_id)
            if nombre:
                return nombre
        snapshot = getattr(cambio, "usuario", None)
        if snapshot:
            return snapshot
        if usuario_id is not None:
            return f"Usuario #{usuario_id}"
        return "—"

    # ── Construcción del DTO de consulta ────────────────────────────────────

    def construir_filtro(self, por_pagina: int) -> FiltroAuditoriaDTO:
        return FiltroAuditoriaDTO(
            usuario_id=self.estado["usuario_id"],
            tabla=self.estado["tabla"] or None,
            accion=self.estado["accion"] or None,
            tipo_evento=self.estado["tipo_evento"] or None,
            desde=self.parsear_fecha(self.estado["desde"]),
            hasta=self.parsear_fecha(self.estado["hasta"], fin_de_dia=True),
            institucion_id=self.estado["institucion_id"],
            severidad=self.estado["severidad"] or None,   # obs_07 T11
            registro_id=self.estado["registro_id"],        # obs_09 T10
            sin_institucion=self.estado["sin_institucion"],  # obs_09 T10
            pagina=self.estado["pagina"],
            por_pagina=por_pagina,
        )


__all__ = ["_SIN_INSTITUCION_SENTINEL", "AuditoriaPresenter"]
