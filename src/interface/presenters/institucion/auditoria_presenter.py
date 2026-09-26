"""Presenter puro de la bitácora institucional (`/institucion/auditoria`).

Sin import de NiceGUI. Concentra el view-state de los filtros para el equipo
directivo del colegio.

Diferencias deliberadas frente a AuditoriaPresenter (admin):

  - NO hereda de AuditoriaPresenter: la herencia traería las claves
    ``institucion_id`` y ``sin_institucion`` que este paso quiere que
    NO existan en el estado.
  - El scope es INMUTABLE: lo pone el constructor desde ``ctx.institucion_id``
    y sale por una propiedad de solo lectura. Lo que no está en el estado
    no se puede cambiar desde un ``on_change``.
  - ``construir_filtro()`` incluye siempre ``institucion_id=self._institucion_id``
    para que los conteos (``contar_cambios`` / ``contar_eventos``) también
    queden dentro del tenant correcto.

obs_11 (R3, R4, R5).
"""
from __future__ import annotations

from datetime import datetime

from src.domain.models.auditoria import FiltroAuditoriaDTO
from src.domain.models.tenant import TenantScope


class AuditoriaInstitucionalPresenter:
    """
    View-model de la bitácora institucional.

    El scope no es parte del estado: lo recibe el constructor desde
    ``ctx.institucion_id`` y sale por la propiedad ``scope`` de solo
    lectura. La UI nunca puede ensancharlo.
    """

    def __init__(self, institucion_id: int) -> None:
        self._institucion_id = institucion_id
        self.estado: dict = {
            # filtros comunes
            "desde": None,        # "YYYY-MM-DD" o None
            "hasta": None,
            "usuario_id": None,
            "pagina": 1,
            # específicos de Cambios
            "tabla": None,
            "accion": None,
            "registro_id": None,  # filtro por entidad concreta
            # específicos de Sesiones
            "tipo_evento": None,
            "severidad": None,
            # datos cargados
            "cambios": [],
            "sesiones": [],
            # paginación look-ahead
            "hay_siguiente_cambios": False,
            "hay_siguiente_sesiones": False,
            # totales para «N resultados»
            "total_cambios": 0,
            "total_sesiones": 0,
            # detalle abierto y mapa de actores
            "detalle": None,
            "actores": {},
        }
        # NOTA: las claves «institucion_id» y «sin_institucion» NO existen
        # en este estado. El scope es privado e inmutable.

    # ── Scope (solo lectura) ─────────────────────────────────────────────────

    @property
    def scope(self) -> TenantScope:
        """Scope de tenant. Inmutable; proviene del constructor."""
        return self._institucion_id

    # ── Helpers puros ────────────────────────────────────────────────────────

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

    # ── Transiciones de filtro ───────────────────────────────────────────────

    def set_rango(self, desde: str | None, hasta: str | None) -> None:
        self.estado["desde"] = desde
        self.estado["hasta"] = hasta

    def set_usuario(self, valor) -> None:
        self.estado["usuario_id"] = self.a_int(valor)

    def set_registro(self, valor) -> None:
        self.estado["registro_id"] = self.a_int(valor)

    def set_tabla(self, valor) -> None:
        self.estado["tabla"] = (valor or "").strip() or None

    def set_accion(self, valor) -> None:
        self.estado["accion"] = valor

    def set_tipo_evento(self, valor) -> None:
        self.estado["tipo_evento"] = valor

    def set_severidad(self, valor) -> None:
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
        self.estado["total_cambios"] = int(total)

    def set_total_sesiones(self, total: int) -> None:
        self.estado["total_sesiones"] = int(total)

    def set_actores(self, actores: dict) -> None:
        self.estado["actores"] = dict(actores)

    def abrir_detalle(self, dto) -> None:
        self.estado["detalle"] = dto

    def cerrar_detalle(self) -> None:
        self.estado["detalle"] = None

    def nombre_actor(self, cambio) -> str:
        """
        Cascada de fallback para el nombre del actor (R9):
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

    # ── Construcción del DTO de consulta ─────────────────────────────────────

    def construir_filtro(self, por_pagina: int) -> FiltroAuditoriaDTO:
        """
        Construye el FiltroAuditoriaDTO con el scope baked-in.

        ``institucion_id`` se fuerza a ``self._institucion_id`` siempre:
        - La UI no puede cambiarlo (no existe en ``estado``).
        - Los conteos (``contar_cambios`` / ``contar_eventos``) quedan
          también dentro del tenant correcto sin necesitar scope explícito.
        ``sin_institucion`` siempre es False: la bitácora institucional
        no expone filas sin tenant (R5).
        """
        return FiltroAuditoriaDTO(
            usuario_id=self.estado["usuario_id"],
            tabla=self.estado["tabla"] or None,
            accion=self.estado["accion"] or None,
            tipo_evento=self.estado["tipo_evento"] or None,
            desde=self.parsear_fecha(self.estado["desde"]),
            hasta=self.parsear_fecha(self.estado["hasta"], fin_de_dia=True),
            institucion_id=self._institucion_id,   # scope inmutable baked-in
            sin_institucion=False,                  # nunca cruzar a filas sin tenant
            severidad=self.estado["severidad"] or None,
            registro_id=self.estado["registro_id"],
            pagina=self.estado["pagina"],
            por_pagina=por_pagina,
        )


__all__ = ["AuditoriaInstitucionalPresenter"]
