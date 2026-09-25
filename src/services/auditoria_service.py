"""
AuditoriaService
================
Punto de acceso de la UI a los datos de auditoría.

Responsabilidades:
  - Listar cambios del audit_log con filtros opcionales (paginado).
  - Listar eventos de sesión con filtros opcionales (paginado).
  - Calcular el diff campo a campo de un RegistroCambio (obs_09).
  - Resolver identidades de actores en una sola consulta (obs_09, R8).
  - Componer la vista de detalle de un cambio (obs_09, R6).

La auditoría es de solo lectura desde la perspectiva de los servicios
de aplicación. Las escrituras las realizan otros servicios vía
IAuditoriaRepository.registrar_cambio / registrar_evento.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from src.domain.models.auditoria import (
    AccionCambio,
    CampoDiffDTO,
    DetalleCambioDTO,
    EventoSesion,
    FiltroAuditoriaDTO,
    RegistroCambio,
    ResumenUsoDTO,
    SeveridadEvento,
    TipoCambioCampo,
    TipoEventoSesion,
)
from src.domain.models.tenant import TenantScope
from src.domain.ports.auditoria_repo import IAuditoriaRepository

if TYPE_CHECKING:
    from src.domain.ports.security_logger import ISecurityLogger
    from src.domain.ports.usuario_repo import IUsuarioRepository


# Campos cuyos valores no se exponen en el diff (defensa en profundidad, R3).
# El modelo ya excluye password_temporal via `exclude=True`, pero el diff lee
# JSON histórico que pudo escribirse antes de esa garantía.
_CAMPOS_SENSIBLES: frozenset[str] = frozenset({
    "password",
    "password_hash",
    "password_temporal",
    "token",
    "secreto",
})


def _texto(val: object) -> str | None:
    """Convierte un valor del dict JSON a string legible, o None si es None."""
    if val is None:
        return None
    return str(val)


class AuditoriaService:
    """
    Servicio de lectura de auditoría.

    Expone los datos de auditoría a la capa de interfaz sin
    exponer el repositorio directamente.
    """

    def __init__(
        self,
        repo: IAuditoriaRepository,
        security_logger: ISecurityLogger | None = None,
        usuario_repo: IUsuarioRepository | None = None,
    ) -> None:
        """Inyecta el repositorio de auditoría, el logger de seguridad y el repo de usuarios."""
        self._repo = repo
        self._security_logger = security_logger
        self._usuario_repo = usuario_repo

    def registrar_evento(self, evento: EventoSesion) -> EventoSesion:
        """Registra un evento de sesión (delegado al repositorio)."""
        if evento.institucion_id is None:
            try:
                from src.services.contexto_tenant import institucion_actual

                evento = evento.model_copy(update={"institucion_id": institucion_actual()})
            except Exception:
                pass
        resultado = self._repo.registrar_evento(evento)

        # Emitir al security logger sin romper la auditoría ante fallos de logging
        if self._security_logger is not None:
            try:
                self._emit_security_log(evento)
            except Exception:
                pass

        # alerta_ip: registrar fallo por IP cuando el evento es LOGIN_FALLIDO
        if evento.tipo_evento == TipoEventoSesion.LOGIN_FALLIDO and evento.ip_address is not None:
            try:
                from src.domain.policies import alerta_ip
                alerta_ip.registrar_fallo_ip(evento.ip_address)
            except Exception:
                pass

        return resultado

    def _emit_security_log(self, evento: EventoSesion) -> None:
        """Despacha el evento al security logger según su tipo."""
        sl = self._security_logger
        if sl is None:
            return

        usuario = evento.usuario
        ip = evento.ip_address or ""
        detalles = evento.detalles or ""
        institucion_id = evento.institucion_id or 0
        tipo = evento.tipo_evento

        if tipo == TipoEventoSesion.LOGIN_EXITOSO:
            sl.login_exitoso(usuario, ip, rol=detalles, institucion_id=institucion_id)
        elif tipo == TipoEventoSesion.LOGIN_FALLIDO:
            sl.login_fallido(usuario, ip, motivo=detalles)
        elif tipo == TipoEventoSesion.LOGOUT:
            sl.logout(usuario, ip)
        elif tipo == TipoEventoSesion.ACCESO_DENEGADO:
            sl.acceso_denegado(usuario, ip, recurso=detalles)
        elif tipo in (TipoEventoSesion.VER_COMO_INICIO, TipoEventoSesion.VER_COMO_FIN):
            sl.ver_como(admin=usuario, objetivo=detalles, accion=tipo.value)
        elif tipo in (
            TipoEventoSesion.CREAR_USUARIO,
            TipoEventoSesion.EDITAR_USUARIO,
            TipoEventoSesion.CAMBIAR_ROL,
            TipoEventoSesion.DESACTIVAR_USUARIO,
            TipoEventoSesion.ACTIVAR_USUARIO,
            TipoEventoSesion.RESETEAR_PASSWORD,
        ):
            sl.gestion_usuario(actor=usuario, objetivo=detalles, operacion=tipo.value)

    def listar_cambios(
        self,
        filtro: FiltroAuditoriaDTO,
    ) -> list[RegistroCambio]:
        """
        Retorna registros del audit_log ordenados por timestamp descendente.

        Args:
            filtro: Criterios de búsqueda y paginación.

        Returns:
            Lista de RegistroCambio (puede ser vacía).
        """
        return self._repo.listar_cambios(filtro)

    def listar_eventos_sesion(
        self,
        filtro: FiltroAuditoriaDTO,
    ) -> list[EventoSesion]:
        """
        Retorna eventos de sesión (login, logout, fallos) paginados.

        Args:
            filtro: Criterios de búsqueda y paginación.

        Returns:
            Lista de EventoSesion (puede ser vacía).
        """
        return self._repo.listar_eventos(filtro)

    def verificar_integridad(self, completa: bool = False) -> dict:
        """
        Verifica el encadenamiento por hash de las dos tablas de auditoría
        (seguridad_03, M3) y compone un resultado de SOLO LECTURA.

        Con `completa=False` (por defecto) reanuda desde el último punto de
        control guardado (verificación incremental). Con `completa=True`
        verifica desde el origen (R8).

        Devuelve un dict de primitivos (no un DTO de dominio):

            {
              "eventos_ok":       bool,
              "cambios_ok":       bool,
              "evento_roto_id":   int | None,
              "cambio_roto_id":   int | None,
              "alcance":          "incremental" | "completa",    # NUEVO (R9)
              "desde_id_eventos": int | None,                    # NUEVO (R9)
              "desde_id_cambios": int | None,                    # NUEVO (R9)
              "verificado_en":    str | None,                    # NUEVO (R9) ISO-8601
            }

        Un repo sin soporte de cadena devuelve None en ambos, reportado como
        «íntegro» (no hay evidencia de manipulación detectable).
        """
        desde_id_eventos: int | None = None
        desde_id_cambios: int | None = None

        if not completa:
            # Leer los checkpoints para informarlos en el resultado (R9)
            try:
                desde_id_eventos, _ = self._repo._leer_checkpoint("auditoria")
            except AttributeError:
                desde_id_eventos = None
            try:
                desde_id_cambios, _ = self._repo._leer_checkpoint("audit_log")
            except AttributeError:
                desde_id_cambios = None

        evento_roto_id = self._repo.verificar_cadena_eventos(completa=completa)
        cambio_roto_id = self._repo.verificar_cadena_cambios(completa=completa)
        return {
            "eventos_ok": evento_roto_id is None,
            "cambios_ok": cambio_roto_id is None,
            "evento_roto_id": evento_roto_id,
            "cambio_roto_id": cambio_roto_id,
            "alcance": "completa" if completa else "incremental",
            "desde_id_eventos": desde_id_eventos,
            "desde_id_cambios": desde_id_cambios,
            "verificado_en": datetime.now().isoformat(),
        }

    def contar_cambios(self, filtro: FiltroAuditoriaDTO) -> int:
        """Delega en el repositorio sin exponer _repo."""
        return self._repo.contar_cambios(filtro)

    def contar_eventos(self, filtro: FiltroAuditoriaDTO) -> int:
        """Delega en el repositorio sin exponer _repo."""
        return self._repo.contar_eventos(filtro)

    def resumen_uso(self, dias: int = 7, scope: TenantScope = "*") -> ResumenUsoDTO:
        """
        Agregación de SOLO LECTURA del uso de la plataforma para el dashboard
        de admin.

        Calcula los KPIs mediante agregados SQL vía `resumen_eventos`, sin
        techo de filas ni recorrido en Python (R4, R5).

        `scope` restringe los KPIs a una institución; `"*"` (default) es
        cross-tenant (para el rol admin).

        No muta nada. Robusto ante repos vacíos o sin soporte de agregados
        (fall-through a ceros si `resumen_eventos` devuelve `{}`).
        """
        dias = max(1, dias)
        ahora = datetime.now()
        agg = self._repo.resumen_eventos(
            ahora - timedelta(days=dias),
            institucion_id=scope,
        )
        por_tipo = agg.get("por_tipo", {})
        return ResumenUsoDTO(
            logins_hoy=agg.get("logins_hoy", 0),
            logins_periodo=por_tipo.get("LOGIN_EXITOSO", 0),
            accesos_denegados=agg.get("denegados_criticos", 0),
            usuarios_activos=agg.get("usuarios_distintos", 0),
            sesiones_periodo=por_tipo.get("LOGIN_EXITOSO", 0),
            dias=dias,
        )


    # -----------------------------------------------------------------------
    # Diff campo a campo (obs_09, T4)
    # -----------------------------------------------------------------------

    def diff_cambio(
        self,
        cambio: RegistroCambio,
        *,
        incluir_sin_cambio: bool = False,
    ) -> list[CampoDiffDTO]:
        """
        Compara ``valor_anterior`` y ``valor_nuevo`` campo a campo.

        CREATE → todo ANADIDO. DELETE → todo ELIMINADO. UPDATE → por campo.
        Los campos sensibles se marcan ``oculto=True`` y viajan sin valores (R3).
        JSON malformado → lista vacía sin excepción.

        Args:
            cambio: Registro del audit_log a analizar.
            incluir_sin_cambio: Si True, incluye los campos sin variación
                                con ``tipo=SIN_CAMBIO``.

        Returns:
            Lista ordenada de ``CampoDiffDTO``, vacía si el JSON no es parseable.
        """
        try:
            anterior = cambio.anterior_como_dict or {}
            nuevo = cambio.nuevo_como_dict or {}
        except Exception:
            return []

        campos: list[CampoDiffDTO] = []
        for nombre in sorted(set(anterior) | set(nuevo)):
            va = anterior.get(nombre)
            vn = nuevo.get(nombre)

            if va == vn:
                tipo = TipoCambioCampo.SIN_CAMBIO
                if not incluir_sin_cambio:
                    continue
            elif nombre not in anterior:
                tipo = TipoCambioCampo.ANADIDO
            elif nombre not in nuevo:
                tipo = TipoCambioCampo.ELIMINADO
            else:
                tipo = TipoCambioCampo.MODIFICADO

            sensible = nombre.lower() in _CAMPOS_SENSIBLES
            campos.append(CampoDiffDTO(
                nombre=nombre,
                valor_anterior=None if sensible else _texto(va),
                valor_nuevo=None if sensible else _texto(vn),
                tipo=tipo,
                oculto=sensible,
            ))
        return campos

    # -----------------------------------------------------------------------
    # Detalle de cambio (obs_09, T6)
    # -----------------------------------------------------------------------

    def detalle_cambio(self, cambio_id: int) -> DetalleCambioDTO | None:
        """
        Construye la vista completa de un cambio: cabecera + diff.

        Devuelve ``None`` si el cambio no existe.

        El nombre del actor se resuelve en orden: nombre completo (del repo de
        usuarios si disponible) → username almacenado en la fila → «Usuario #N»
        → «—».
        """
        from src.domain.tablas_auditables import etiqueta_de_tabla

        cambio = self._repo.get_cambio(cambio_id)
        if cambio is None:
            return None

        # Resolver nombre del actor
        actor_nombre = "—"
        if cambio.usuario_id is not None and self._usuario_repo is not None:
            try:
                usuario = self._usuario_repo.get_by_id(cambio.usuario_id)
                if usuario is not None:
                    actor_nombre = usuario.nombre_completo
                elif cambio.usuario:
                    actor_nombre = cambio.usuario
                else:
                    actor_nombre = f"Usuario #{cambio.usuario_id}"
            except Exception:
                actor_nombre = cambio.usuario or f"Usuario #{cambio.usuario_id}"
        elif cambio.usuario:
            actor_nombre = cambio.usuario
        elif cambio.usuario_id is not None:
            actor_nombre = f"Usuario #{cambio.usuario_id}"

        return DetalleCambioDTO(
            cambio=cambio,
            actor_nombre=actor_nombre,
            etiqueta_tabla=etiqueta_de_tabla(cambio.tabla),
            campos=self.diff_cambio(cambio),
        )

    # -----------------------------------------------------------------------
    # Resolución de actores en una sola consulta (obs_09, T7, R8)
    # -----------------------------------------------------------------------

    def resolver_actores(self, cambios: list[RegistroCambio]) -> dict[int, str]:
        """
        Devuelve un mapa ``usuario_id → nombre_completo`` para la lista de cambios.

        Una sola consulta al repositorio de usuarios (R8). Si el repositorio no
        está disponible (inyección opcional), devuelve un dict vacío — la interfaz
        aplicará la cascada de fallback (R9).

        Args:
            cambios: Página de cambios visible en pantalla.

        Returns:
            Dict ``{usuario_id: nombre_completo}``.
        """
        if self._usuario_repo is None:
            return {}
        ids = {c.usuario_id for c in cambios if c.usuario_id is not None}
        if not ids:
            return {}
        try:
            usuarios = self._usuario_repo.get_varios(ids)
            return {u.id: u.nombre_completo for u in usuarios if u.id is not None}
        except Exception:
            return {}


__all__ = [
    "AccionCambio",
    "AuditoriaService",
    "CampoDiffDTO",
    "DetalleCambioDTO",
    "EventoSesion",
    "FiltroAuditoriaDTO",
    "RegistroCambio",
    "ResumenUsoDTO",
    "SeveridadEvento",
    "TipoCambioCampo",
    "TipoEventoSesion",
]
