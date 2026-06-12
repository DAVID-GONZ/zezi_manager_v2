"""
src/infrastructure/context/context_initializer.py
==================================================
Resuelve el contexto académico inicial para un usuario autenticado.

Se invoca UNA VEZ, inmediatamente después del login exitoso,
antes de redirigir al dashboard.

Responsabilidades:
  1. Encontrar el año académico activo en la BD.
  2. Encontrar el periodo activo de ese año.
  3. Para profesores: encontrar su primer grupo y asignatura
     del periodo activo (ordenado alfabéticamente para reproducibilidad).
  4. Para directores/coordinadores: año, periodo y primer grupo
     activo de la institución (sin asignatura).
  5. Para admin: solo el año activo (sin periodo ni grupo).
  6. Escribir todo en SessionContext (IDs y nombres legibles).

Lo que NO hace:
  - No toca app.storage.user directamente (eso es SessionContext.guardar())
  - No lanza excepciones al llamador (captura todo internamente)
  - No decide si el usuario puede acceder (eso es AuthService)
  - No envía notificaciones ni registra auditoría
  - No importa nicegui, src.interface.pages ni src.interface.design

Uso en login.py:
    from src.interface.context.session_context import SessionContext
    from src.infrastructure.context.context_initializer import ContextInitializer

    ctx = SessionContext(usuario_id=user.id, ...)
    ctx = ContextInitializer.inicializar(ctx)
    ctx.guardar()
    ui.navigate.to("/inicio")
"""
from __future__ import annotations

import logging

# `SessionContext` se usa solo en anotaciones de tipo de cadena porque
# el módulo de infraestructura no debe importar la capa de interfaz.

logger = logging.getLogger("CONTEXT_INIT")


class ContextInitializer:
    """
    Resuelve y escribe el contexto académico inicial de un usuario.
    Todos los métodos son @staticmethod — sin estado, sin instanciación.

    Jerarquía de resolución:
      Todos los roles → _resolver_anio
      Todos los roles → _resolver_periodo
      profesor / coordinador → _resolver_grupo_y_asignatura
      director              → _resolver_grupo_director
      admin                 → (solo año, sin grupo ni asignatura)
    """

    @staticmethod
    def inicializar(ctx: "SessionContext") -> "SessionContext":
        """
        Punto de entrada principal.

        Intenta resolver el contexto completo para el rol del usuario.
        Si cualquier paso falla, continúa con lo que pudo resolver.
        Nunca lanza excepciones — retorna siempre un ctx parcialmente
        o totalmente completado.

        Args:
            ctx: SessionContext con usuario_id, usuario_nombre y
                 usuario_rol ya seteados.

        Returns:
            El mismo ctx mutado con año, periodo, grupo y asignatura
            según el rol. NO llama ctx.guardar() — eso es
            responsabilidad del llamador (login.py).
        """
        logger.info(
            "Inicializando contexto para '%s' (rol=%s)",
            ctx.usuario_nombre,
            ctx.usuario_rol,
        )

        # Paso 1 — Año académico activo (todos los roles)
        anio_ok = ContextInitializer._resolver_anio(ctx)
        if not anio_ok:
            logger.warning(
                "Sin año académico activo. Contexto parcial para '%s'.",
                ctx.usuario_nombre,
            )
            return ctx  # sin año no hay nada más que resolver

        # Paso 2 — Periodo activo (todos los roles)
        periodo_ok = ContextInitializer._resolver_periodo(ctx)

        # Paso 3 — Grupo y asignatura según rol
        if periodo_ok:
            rol = ctx.usuario_rol
            if rol in ("profesor", "coordinador"):
                ContextInitializer._resolver_grupo_y_asignatura(ctx)
            elif rol == "director":
                # El director necesita un grupo para ver estadísticas,
                # pero no tiene asignatura propia.
                ContextInitializer._resolver_grupo_director(ctx)
            # admin: solo necesita año; no se fuerza grupo ni asignatura.

        logger.info(
            "Contexto resuelto — año=%r, periodo=%r, grupo=%r, asig=%r",
            ctx.anio_nombre,
            ctx.periodo_nombre,
            ctx.grupo_nombre,
            ctx.asignacion_nombre,
        )
        return ctx

    # ── Resolución por paso ───────────────────────────────────────────────────

    @staticmethod
    def _resolver_anio(ctx: "SessionContext") -> bool:
        """
        Encuentra el año académico activo y lo escribe en ctx.
        Retorna True si lo encontró.
        """
        try:
            from container import Container
            config = Container.configuracion_service().get_activa()
            if not config or not config.id:
                return False

            ctx.anio_id     = config.id
            ctx.anio_nombre = str(config.anio)
            return True

        except Exception as exc:
            logger.error("Error resolviendo año activo: %s", exc)
            return False

    @staticmethod
    def _resolver_periodo(ctx: "SessionContext") -> bool:
        """
        Encuentra el periodo activo del año y lo escribe en ctx.
        Si `get_activo()` no encuentra un periodo marcado como activo,
        usa el primero no cerrado de la lista.
        Retorna True si encontró un periodo válido.
        """
        if not ctx.anio_id:
            return False

        try:
            from container import Container
            svc = Container.periodo_service()

            # Intento principal: periodo marcado como activo
            periodo = None
            try:
                periodo = svc.get_activo(ctx.anio_id)
            except Exception:
                pass  # puede lanzar si no hay periodo activo

            # Fallback: primer periodo no cerrado del año
            if not periodo or not periodo.id:
                periodos = svc.listar_por_anio(ctx.anio_id)
                periodo = next(
                    (p for p in periodos if not getattr(p, "cerrado", False)),
                    periodos[0] if periodos else None,
                )

            if not periodo or not periodo.id:
                return False

            ctx.periodo_id     = periodo.id
            ctx.periodo_nombre = periodo.nombre
            return True

        except Exception as exc:
            logger.error("Error resolviendo periodo activo: %s", exc)
            return False

    @staticmethod
    def _resolver_grupo_y_asignatura(ctx: "SessionContext") -> bool:
        """
        Para PROFESORES y COORDINADORES:
        Encuentra el primer grupo/asignatura del docente en el periodo activo.

        Criterio de selección:
          Se ordena por (grupo_codigo, asignatura_nombre) para garantizar
          reproducibilidad entre sesiones y entre reinicios del servidor.

        Retorna True si resolvió al menos el grupo.
        """
        if not ctx.periodo_id:
            return False

        try:
            from container import Container

            # listar_por_docente retorna list[AsignacionInfo]
            # Campos disponibles: asignacion_id, grupo_id, grupo_codigo,
            #                     asignatura_nombre, activo, ...
            # Usamos asignacion_service (no el repo directo) para que
            # cualquier lógica de permisos o cache futura sea respetada.
            asignaciones = Container.asignacion_service().listar_por_docente(
                ctx.usuario_id,
                ctx.periodo_id,
            )

            if not asignaciones:
                logger.info(
                    "Docente id=%s sin asignaciones activas en periodo id=%s.",
                    ctx.usuario_id,
                    ctx.periodo_id,
                )
                return False

            # Ordenar alfabéticamente para consistencia entre sesiones
            asignaciones.sort(
                key=lambda a: (
                    a.grupo_codigo or "",
                    a.asignatura_nombre or "",
                )
            )

            primera = asignaciones[0]
            ctx.grupo_id          = primera.grupo_id
            ctx.grupo_nombre      = primera.grupo_codigo
            ctx.asignacion_id     = primera.asignacion_id
            ctx.asignacion_nombre = primera.asignatura_nombre
            return True

        except Exception as exc:
            logger.error("Error resolviendo grupo/asignatura del docente: %s", exc)
            return False

    @staticmethod
    def _resolver_grupo_director(ctx: "SessionContext") -> bool:
        """
        Para DIRECTORES:
        Encuentra el primer grupo activo de la institución, ordenado por
        código, para que el director vea estadísticas de un grupo al entrar.
        No asigna asignacion_id (el director ve todos los docentes).
        Retorna True si encontró al menos un grupo.
        """
        try:
            from container import Container

            # listar_grupos retorna list[Grupo]; Grupo.codigo es str (requerido)
            grupos = Container.infraestructura_repo().listar_grupos()
            if not grupos:
                return False

            grupos.sort(key=lambda g: g.codigo or "")
            primero = grupos[0]

            ctx.grupo_id     = primero.id
            ctx.grupo_nombre = primero.codigo
            # Sin asignacion_id ni asignacion_nombre para directores
            return True

        except Exception as exc:
            logger.error("Error resolviendo grupo para director: %s", exc)
            return False

    # ── Verificación de validez ───────────────────────────────────────────────

    @staticmethod
    def contexto_es_valido(ctx: "SessionContext") -> bool:
        """
        Verifica que el contexto guardado sigue siendo válido en la BD.
        Útil para detectar cambios académicos (cierre de periodo, reasignación)
        mientras el usuario tenía sesión abierta.

        Retorna True si el año sigue activo, el periodo existe y
        la asignación (si existe) sigue activa.
        """
        try:
            from container import Container

            # Sin IDs mínimos → inválido por definición
            if not ctx.anio_id or not ctx.periodo_id:
                return False

            # Verificar que el año sigue activo
            config = Container.configuracion_service().get_by_id(ctx.anio_id)
            if not config or not getattr(config, "activo", True) is True:
                return False

            # Verificar que el periodo sigue existiendo.
            # periodo_service.get_by_id lanza ValueError si no existe;
            # lo capturamos igual que cualquier otro error.
            try:
                periodo = Container.periodo_service().get_by_id(ctx.periodo_id)
            except ValueError:
                return False
            if not periodo:
                return False

            # Verificar asignación si existe en el contexto.
            # asignacion_service.get_by_id lanza ValueError si no existe.
            if ctx.asignacion_id:
                try:
                    asig = Container.asignacion_service().get_by_id(ctx.asignacion_id)
                except ValueError:
                    return False
                if not asig or not asig.activo:
                    logger.info(
                        "Asignación id=%s ya no está activa. Contexto inválido.",
                        ctx.asignacion_id,
                    )
                    return False

            return True

        except Exception as exc:
            logger.error("Error verificando validez del contexto: %s", exc)
            return False

    @staticmethod
    def refrescar_si_invalido(ctx: "SessionContext") -> "SessionContext":
        """
        Si el contexto guardado no es válido, lo limpia y re-inicializa.
        Útil al inicio de cada página protegida para detectar cambios
        académicos ocurridos mientras el usuario tenía sesión abierta.

        Persiste el contexto actualizado via ctx.guardar() solo si
        tuvo que re-inicializar.

        Uso en páginas autenticadas:
            ctx = SessionContext.desde_storage()
            ctx = ContextInitializer.refrescar_si_invalido(ctx)
        """
        if not ContextInitializer.contexto_es_valido(ctx):
            logger.info(
                "Contexto inválido para '%s'. Re-inicializando.",
                ctx.usuario_nombre,
            )
            # Limpiar IDs y nombres para forzar re-resolución limpia
            ctx.anio_id           = None
            ctx.periodo_id        = None
            ctx.grupo_id          = None
            ctx.asignacion_id     = None
            ctx.anio_nombre       = ""
            ctx.periodo_nombre    = ""
            ctx.grupo_nombre      = ""
            ctx.asignacion_nombre = ""

            ctx = ContextInitializer.inicializar(ctx)
            ctx.guardar()  # persistir el contexto re-calculado

        return ctx


__all__ = ["ContextInitializer"]
