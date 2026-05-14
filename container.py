"""
container.py — Composition Root de ZECI Manager v2.0
======================================================
Punto único de instanciación de toda la infraestructura.

Patrón: Singleton lazy por nombre.
  - Cada componente se instancia una sola vez y se almacena en _cache.
  - Las páginas NiceGUI solo importan Container y llaman Container.xxx_service().
  - Los imports son LAZY (dentro de cada método) para evitar circulares
    y reducir el tiempo de arranque si un submódulo tiene errores.

Para tests: usar Container.reset() antes de cada test que necesite
instancias frescas de repositorios.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("CONTAINER")


class Container:
    """
    Composition Root — punto único de instanciación.

    Patrón: Singleton lazy por nombre.
    Cada servicio y repositorio se instancia una sola vez
    y se almacena en _cache. Las páginas NiceGUI solo importan
    Container y llaman Container.xxx_service().

    Para tests: usar Container.reset() antes de cada test
    que necesite repositorios distintos.
    """

    _cache: dict[str, Any] = {}

    # ──────────────────────────────────────────────────────
    # Reset (para tests de integración)
    # ──────────────────────────────────────────────────────

    @classmethod
    def reset(cls) -> None:
        """
        Vacía el caché. Llamar en setUp de tests de integración
        para garantizar que cada test parte con instancias frescas.
        """
        cls._cache.clear()
        logger.debug("Container reseteado")

    # ──────────────────────────────────────────────────────
    # Helper interno
    # ──────────────────────────────────────────────────────

    @classmethod
    def _get_or_create(cls, key: str, factory) -> Any:
        if key not in cls._cache:
            cls._cache[key] = factory()
            logger.debug("Instancia creada: %s", key)
        return cls._cache[key]

    # ══════════════════════════════════════════════════════
    # INFRAESTRUCTURA DE SERVICIOS
    # ══════════════════════════════════════════════════════

    @classmethod
    def auth_service(cls):
        from src.infrastructure.auth.bcrypt_auth_service import BcryptAuthService
        # Inyectar usuario_repo para que cambiar_password/resetear_password
        # puedan persistir hashes. Sin repo, solo funciona la criptografía pura.
        return cls._get_or_create(
            "auth_service",
            lambda: BcryptAuthService(repo=cls.usuario_repo()),
        )

    @classmethod
    def notification_service(cls):
        from src.infrastructure.notifications.null_notification_service import (
            NullNotificationService,
        )
        return cls._get_or_create("notification_service", NullNotificationService)

    @classmethod
    def exporter_service(cls):
        from src.infrastructure.exporters.exporter_factory import crear_exporter
        return cls._get_or_create("exporter_service", crear_exporter)

    # ══════════════════════════════════════════════════════
    # REPOSITORIOS — en orden de dependencia
    # ══════════════════════════════════════════════════════

    @classmethod
    def configuracion_repo(cls):
        from src.infrastructure.db.repositories.sqlite_configuracion_repo import (
            SqliteConfiguracionRepository,
        )
        return cls._get_or_create("configuracion_repo", SqliteConfiguracionRepository)

    @classmethod
    def infraestructura_repo(cls):
        from src.infrastructure.db.repositories.sqlite_infraestructura_repo import (
            SqliteInfraestructuraRepository,
        )
        return cls._get_or_create("infraestructura_repo", SqliteInfraestructuraRepository)

    @classmethod
    def usuario_repo(cls):
        from src.infrastructure.db.repositories.sqlite_usuario_repo import (
            SqliteUsuarioRepository,
        )
        return cls._get_or_create("usuario_repo", SqliteUsuarioRepository)

    @classmethod
    def estudiante_repo(cls):
        from src.infrastructure.db.repositories.sqlite_estudiante_repo import (
            SqliteEstudianteRepository,
        )
        return cls._get_or_create("estudiante_repo", SqliteEstudianteRepository)

    @classmethod
    def acudiente_repo(cls):
        from src.infrastructure.db.repositories.sqlite_acudiente_repo import (
            SqliteAcudienteRepository,
        )
        return cls._get_or_create("acudiente_repo", SqliteAcudienteRepository)

    @classmethod
    def periodo_repo(cls):
        from src.infrastructure.db.repositories.sqlite_periodo_repo import (
            SqlitePeriodoRepository,
        )
        return cls._get_or_create("periodo_repo", SqlitePeriodoRepository)

    @classmethod
    def asignacion_repo(cls):
        from src.infrastructure.db.repositories.sqlite_asignacion_repo import (
            SqliteAsignacionRepository,
        )
        return cls._get_or_create("asignacion_repo", SqliteAsignacionRepository)

    @classmethod
    def evaluacion_repo(cls):
        from src.infrastructure.db.repositories.sqlite_evaluacion_repo import (
            SqliteEvaluacionRepository,
        )
        return cls._get_or_create("evaluacion_repo", SqliteEvaluacionRepository)

    @classmethod
    def asistencia_repo(cls):
        from src.infrastructure.db.repositories.sqlite_asistencia_repo import (
            SqliteAsistenciaRepository,
        )
        return cls._get_or_create("asistencia_repo", SqliteAsistenciaRepository)

    @classmethod
    def cierre_repo(cls):
        from src.infrastructure.db.repositories.sqlite_cierre_repo import (
            SqliteCierreRepository,
        )
        return cls._get_or_create("cierre_repo", SqliteCierreRepository)

    @classmethod
    def habilitacion_repo(cls):
        from src.infrastructure.db.repositories.sqlite_habilitacion_repo import (
            SqliteHabilitacionRepository,
        )
        return cls._get_or_create("habilitacion_repo", SqliteHabilitacionRepository)

    @classmethod
    def convivencia_repo(cls):
        from src.infrastructure.db.repositories.sqlite_convivencia_repo import (
            SqliteConvivenciaRepository,
        )
        return cls._get_or_create("convivencia_repo", SqliteConvivenciaRepository)

    @classmethod
    def alerta_repo(cls):
        from src.infrastructure.db.repositories.sqlite_alerta_repo import (
            SqliteAlertaRepository,
        )
        return cls._get_or_create("alerta_repo", SqliteAlertaRepository)

    @classmethod
    def auditoria_repo(cls):
        from src.infrastructure.db.repositories.sqlite_auditoria_repo import (
            SqliteAuditoriaRepository,
        )
        return cls._get_or_create("auditoria_repo", SqliteAuditoriaRepository)

    @classmethod
    def estadisticos_repo(cls):
        from src.infrastructure.db.repositories.sqlite_estadisticos_repo import (
            SqliteEstadisticosRepository,
        )
        return cls._get_or_create("estadisticos_repo", SqliteEstadisticosRepository)

    # ══════════════════════════════════════════════════════
    # SERVICIOS — en orden de dependencia
    # ══════════════════════════════════════════════════════

    @classmethod
    def configuracion_service(cls):
        from src.services.configuracion_service import ConfiguracionService
        return cls._get_or_create(
            "configuracion_service",
            lambda: ConfiguracionService(
                repo=cls.configuracion_repo(),
            ),
        )

    @classmethod
    def usuario_service(cls):
        from src.services.usuario_service import UsuarioService
        return cls._get_or_create(
            "usuario_service",
            lambda: UsuarioService(
                repo=cls.usuario_repo(),
                auth_service=cls.auth_service(),
                auditoria=cls.auditoria_repo(),
            ),
        )

    @classmethod
    def estudiante_service(cls):
        from src.services.estudiante_service import EstudianteService
        return cls._get_or_create(
            "estudiante_service",
            lambda: EstudianteService(
                repo=cls.estudiante_repo(),
                acudiente_repo=cls.acudiente_repo(),
                auditoria=cls.auditoria_repo(),
            ),
        )

    @classmethod
    def periodo_service(cls):
        from src.services.periodo_service import PeriodoService
        return cls._get_or_create(
            "periodo_service",
            lambda: PeriodoService(
                repo=cls.periodo_repo(),
                config_repo=cls.configuracion_repo(),
                auditoria=cls.auditoria_repo(),
            ),
        )

    @classmethod
    def asignacion_service(cls):
        from src.services.asignacion_service import AsignacionService
        return cls._get_or_create(
            "asignacion_service",
            lambda: AsignacionService(
                repo=cls.asignacion_repo(),
                periodo_repo=cls.periodo_repo(),
                auditoria=cls.auditoria_repo(),
            ),
        )

    @classmethod
    def evaluacion_service(cls):
        from src.services.evaluacion_service import EvaluacionService
        return cls._get_or_create(
            "evaluacion_service",
            lambda: EvaluacionService(
                repo=cls.evaluacion_repo(),
                asignacion_repo=cls.asignacion_repo(),
                periodo_repo=cls.periodo_repo(),
                auditoria=cls.auditoria_repo(),
            ),
        )

    @classmethod
    def alerta_service(cls):
        from src.services.alerta_service import AlertaService
        return cls._get_or_create(
            "alerta_service",
            lambda: AlertaService(
                repo=cls.alerta_repo(),
                estadisticos_repo=cls.estadisticos_repo(),
            ),
        )

    @classmethod
    def asistencia_service(cls):
        from src.services.asistencia_service import AsistenciaService
        return cls._get_or_create(
            "asistencia_service",
            lambda: AsistenciaService(
                repo=cls.asistencia_repo(),
                alerta_repo=cls.alerta_repo(),
                config_repo=cls.configuracion_repo(),
            ),
        )

    @classmethod
    def cierre_service(cls):
        from src.services.cierre_service import CierreService
        return cls._get_or_create(
            "cierre_service",
            lambda: CierreService(
                cierre_repo=cls.cierre_repo(),
                evaluacion_repo=cls.evaluacion_repo(),
                periodo_repo=cls.periodo_repo(),
                config_repo=cls.configuracion_repo(),
                estudiante_repo=cls.estudiante_repo(),
                alerta_repo=cls.alerta_repo(),
                auditoria=cls.auditoria_repo(),
            ),
        )

    @classmethod
    def habilitacion_service(cls):
        from src.services.habilitacion_service import HabilitacionService
        return cls._get_or_create(
            "habilitacion_service",
            lambda: HabilitacionService(
                repo=cls.habilitacion_repo(),
                cierre_repo=cls.cierre_repo(),
                config_repo=cls.configuracion_repo(),
            ),
        )

    @classmethod
    def convivencia_service(cls):
        from src.services.convivencia_service import ConvivenciaService
        return cls._get_or_create(
            "convivencia_service",
            lambda: ConvivenciaService(
                repo=cls.convivencia_repo(),
                alerta_repo=cls.alerta_repo(),
            ),
        )

    @classmethod
    def estadisticos_service(cls):
        from src.services.estadisticos_service import EstadisticosService
        return cls._get_or_create(
            "estadisticos_service",
            lambda: EstadisticosService(
                repo=cls.estadisticos_repo(),
                config_repo=cls.configuracion_repo(),
            ),
        )

    @classmethod
    def informe_service(cls):
        from src.services.informe_service import InformeService
        return cls._get_or_create(
            "informe_service",
            lambda: InformeService(
                estadisticos_repo=cls.estadisticos_repo(),
                exporter=cls.exporter_service(),
            ),
        )

    # ══════════════════════════════════════════════════════
    # DIAGNÓSTICO
    # ══════════════════════════════════════════════════════

    @classmethod
    def diagnostico(cls) -> dict:
        """
        Intenta instanciar todos los servicios y reporta errores.
        Llamar desde main.py al arrancar para detectar configuraciones
        rotas antes de que un usuario encuentre el error.
        """
        resultados = {}
        metodos = [
            "auth_service", "notification_service", "exporter_service",
            "configuracion_service", "usuario_service",
            "estudiante_service", "periodo_service", "asignacion_service",
            "evaluacion_service", "asistencia_service", "cierre_service",
            "habilitacion_service", "convivencia_service", "alerta_service",
            "estadisticos_service", "informe_service",
        ]
        for nombre in metodos:
            try:
                getattr(cls, nombre)()
                resultados[nombre] = "OK"
            except Exception as e:
                resultados[nombre] = f"ERROR: {e}"
                logger.error("Container.%s falló: %s", nombre, e)

        errores = {k: v for k, v in resultados.items() if v != "OK"}
        if errores:
            logger.critical("Container con errores: %s", errores)
        else:
            logger.info(
                "Container inicializado correctamente (%d componentes)",
                len(metodos),
            )
        return resultados
