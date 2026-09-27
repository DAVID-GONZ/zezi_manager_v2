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
import os
from contextlib import contextmanager
from typing import Any, ClassVar

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

    _cache: ClassVar[dict[str, Any]] = {}

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
    # Engine SQLAlchemy (backend_05)
    # ──────────────────────────────────────────────────────

    @classmethod
    def engine(cls):
        """Singleton del engine SQLAlchemy. Creado al primer acceso."""
        return cls._get_or_create("engine", _create_engine)

    @classmethod
    @contextmanager
    def connection(cls):
        """Context manager que cede una conexión del engine SQLAlchemy."""
        with cls.engine().connect() as conn:
            yield conn

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
        from src.infrastructure.db.repositories.sqla_configuracion_repo import (
            SqlaConfiguracionRepository,
        )
        return cls._get_or_create("configuracion_repo", SqlaConfiguracionRepository)

    @classmethod
    def infraestructura_repo(cls):
        from src.infrastructure.db.repositories.sqla_infraestructura_repo import (
            SqlaInfraestructuraRepository,
        )
        return cls._get_or_create("infraestructura_repo", SqlaInfraestructuraRepository)

    @classmethod
    def institucion_repo(cls):
        from src.infrastructure.db.repositories.sqla_institucion_repo import (
            SqlaInstitucionRepository,
        )
        return cls._get_or_create("institucion_repo", SqlaInstitucionRepository)

    @classmethod
    def usuario_repo(cls):
        from src.infrastructure.db.repositories.sqla_usuario_repo import (
            SqlaUsuarioRepository,
        )
        return cls._get_or_create("usuario_repo", SqlaUsuarioRepository)

    @classmethod
    def estudiante_repo(cls):
        from src.infrastructure.db.repositories.sqla_estudiante_repo import (
            SqlaEstudianteRepository,
        )
        return cls._get_or_create("estudiante_repo", SqlaEstudianteRepository)

    @classmethod
    def acudiente_repo(cls):
        from src.infrastructure.db.repositories.sqla_acudiente_repo import (
            SqlaAcudienteRepository,
        )
        return cls._get_or_create("acudiente_repo", SqlaAcudienteRepository)

    @classmethod
    def periodo_repo(cls):
        from src.infrastructure.db.repositories.sqla_periodo_repo import (
            SqlaPeriodoRepository,
        )
        return cls._get_or_create("periodo_repo", SqlaPeriodoRepository)

    @classmethod
    def asignacion_repo(cls):
        from src.infrastructure.db.repositories.sqla_asignacion_repo import (
            SqlaAsignacionRepository,
        )
        return cls._get_or_create("asignacion_repo", SqlaAsignacionRepository)

    @classmethod
    def evaluacion_repo(cls):
        from src.infrastructure.db.repositories.sqla_evaluacion_repo import (
            SqlaEvaluacionRepository,
        )
        return cls._get_or_create("evaluacion_repo", SqlaEvaluacionRepository)

    @classmethod
    def asistencia_repo(cls):
        from src.infrastructure.db.repositories.sqla_asistencia_repo import (
            SqlaAsistenciaRepository,
        )
        return cls._get_or_create("asistencia_repo", SqlaAsistenciaRepository)

    @classmethod
    def cierre_repo(cls):
        from src.infrastructure.db.repositories.sqla_cierre_repo import (
            SqlaCierreRepository,
        )
        return cls._get_or_create("cierre_repo", SqlaCierreRepository)

    @classmethod
    def habilitacion_repo(cls):
        from src.infrastructure.db.repositories.sqla_habilitacion_repo import (
            SqlaHabilitacionRepository,
        )
        return cls._get_or_create("habilitacion_repo", SqlaHabilitacionRepository)

    @classmethod
    def nivelacion_repo(cls):
        from src.infrastructure.db.repositories.sqla_nivelacion_repo import (
            SqlaNivelacionRepository,
        )
        return cls._get_or_create("nivelacion_repo", SqlaNivelacionRepository)

    @classmethod
    def convivencia_repo(cls):
        from src.infrastructure.db.repositories.sqla_convivencia_repo import (
            SqlaConvivenciaRepository,
        )
        return cls._get_or_create("convivencia_repo", SqlaConvivenciaRepository)

    @classmethod
    def alerta_repo(cls):
        from src.infrastructure.db.repositories.sqla_alerta_repo import (
            SqlaAlertaRepository,
        )
        return cls._get_or_create("alerta_repo", SqlaAlertaRepository)

    @classmethod
    def auditoria_repo(cls):
        from src.infrastructure.db.repositories.sqla_auditoria_repo import (
            SqlaAuditoriaRepository,
        )
        return cls._get_or_create("auditoria_repo", SqlaAuditoriaRepository)

    @classmethod
    def estadisticos_repo(cls):
        from src.infrastructure.db.repositories.sqla_estadisticos_repo import (
            SqlaEstadisticosRepository,
        )
        return cls._get_or_create("estadisticos_repo", SqlaEstadisticosRepository)

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
                auditoria_repo=cls.auditoria_repo(),
            ),
        )

    @classmethod
    def institucion_service(cls):
        from src.services.institucion_service import InstitucionService
        return cls._get_or_create(
            "institucion_service",
            lambda: InstitucionService(
                repo=cls.institucion_repo(),
                auditoria_repo=cls.auditoria_repo(),
            ),
        )

    @classmethod
    def aprovisionamiento_service(cls):
        from src.services.aprovisionamiento_institucion_service import (
            AprovisionamientoInstitucionService,
        )
        return cls._get_or_create(
            "aprovisionamiento_service",
            # Reutiliza el repo ya cableado del institucion_service (no
            # duplica wiring; el aprovisionamiento opera sobre el mismo tenant).
            lambda: AprovisionamientoInstitucionService(
                cls.institucion_service()._repo,
                cls.auditoria_repo(),
            ),
        )

    @classmethod
    def preferencias_service(cls):
        from src.infrastructure.db.repositories.sqla_preferencias_repo import (
            SqlaPreferenciasRepository,
        )
        from src.services.preferencias_institucion_service import (
            PreferenciasInstitucionService,
        )
        return cls._get_or_create(
            "preferencias_service",
            lambda: PreferenciasInstitucionService(SqlaPreferenciasRepository()),
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
                repo         = cls.asignacion_repo(),
                periodo_repo = cls.periodo_repo(),
                auditoria    = cls.auditoria_repo(),
                usuario_repo = cls.usuario_repo(),
                infra_repo   = cls.infraestructura_repo(),
                plan_svc     = cls.plan_estudios_service(),
            ),
        )

    @classmethod
    def siee_repo(cls):
        from src.infrastructure.db.repositories.sqla_siee_repo import (
            SqlaSIEERepository,
        )
        return cls._get_or_create("siee_repo", SqlaSIEERepository)

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
                siee_repo=cls.siee_repo(),
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
                auditoria_repo=cls.auditoria_repo(),
            ),
        )

    @classmethod
    def _portal_provider_factories(cls) -> dict[str, Any]:
        """Registro declarativo de pilotos del portal: módulo → fábrica.

        Sumar un módulo al portal es añadir una entrada aquí y nada más;
        `portal_provider`, `portal_providers` y el resumen global lo recogen
        solos. El orden de las claves es el orden de presentación.
        """

        def _convivencia():
            from src.services.portal.convivencia_provider import ConvivenciaProvider

            return ConvivenciaProvider(alerta_svc_provider=cls.alerta_service)

        def _evaluacion():
            from src.services.portal.evaluacion_provider import EvaluacionProvider

            return EvaluacionProvider(
                habilitacion_svc_provider=cls.habilitacion_service
            )

        return {
            "convivencia": _convivencia,
            "evaluacion": _evaluacion,
        }

    @classmethod
    def portal_provider(cls, modulo: str):
        """Retorna el PortalProvider para un módulo, o None si no hay piloto."""
        fabrica = cls._portal_provider_factories().get(modulo)
        if fabrica is None:
            return None
        return cls._get_or_create(f"portal_provider_{modulo}", fabrica)

    @classmethod
    def portal_providers(cls) -> list:
        """Todos los PortalProvider con piloto activo, en orden de registro."""
        return [
            proveedor
            for proveedor in (
                cls.portal_provider(modulo)
                for modulo in cls._portal_provider_factories()
            )
            if proveedor is not None
        ]

    @classmethod
    def portal_resumen_service(cls):
        from src.services.portal_resumen_service import PortalResumenService
        return cls._get_or_create(
            "portal_resumen_service",
            lambda: PortalResumenService(
                providers_provider=cls.portal_providers,
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
                auditoria_repo=cls.auditoria_repo(),
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
                asignacion_repo=cls.asignacion_repo(),
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
                auditoria=cls.auditoria_repo(),
            ),
        )

    @classmethod
    def nivelacion_service(cls):
        from src.services.nivelacion_service import NivelacionService
        return cls._get_or_create(
            "nivelacion_service",
            lambda: NivelacionService(
                repo=cls.nivelacion_repo(),
                cierre_repo=cls.cierre_repo(),
                config_repo=cls.configuracion_repo(),
                auditoria_repo=cls.auditoria_repo(),
            ),
        )

    @classmethod
    def plan_mejoramiento_repo(cls):
        from src.infrastructure.db.repositories.sqla_plan_mejoramiento_repo import (
            SqlaPlanMejoramientoRepository,
        )
        return cls._get_or_create("plan_mejoramiento_repo", SqlaPlanMejoramientoRepository)

    @classmethod
    def plan_mejoramiento_service(cls):
        from src.services.plan_mejoramiento_service import PlanMejoramientoService
        return cls._get_or_create(
            "plan_mejoramiento_service",
            lambda: PlanMejoramientoService(
                plan_repo=cls.plan_mejoramiento_repo(),
                eval_repo=cls.evaluacion_repo(),
                est_repo=cls.estudiante_repo(),
                auditoria_repo=cls.auditoria_repo(),
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
                # Provider lazy: enforcement de autorización (convivencia_04b).
                catalogo_academico_svc_provider=cls.catalogo_academico_service,
                # Providers lazy: concepto consolidado (convivencia_05).
                configuracion_svc_provider=cls.configuracion_service,
                periodo_svc_provider=cls.periodo_service,
                estudiante_svc_provider=cls.estudiante_service,
                # Exporter para el reporte de periodo (convivencia_06b): la
                # composición del reporte y la generación de bytes viven en
                # el servicio; la página solo pide bytes y ofrece descarga.
                exporter=cls.exporter_service(),
                # Provider lazy: autorización por objeto de observaciones
                # (convivencia_11) — verifica que el profesor sea titular de
                # la asignación antes de permitir registrar/actualizar.
                asignacion_svc_provider=cls.asignacion_service,
                # Provider lazy: política de registros en boletín (convivencia_29).
                preferencias_svc_provider=cls.preferencias_service,
                auditoria_repo=cls.auditoria_repo(),
            ),
        )

    @classmethod
    def estadisticos_service(cls):
        from src.services.estadisticos_service import EstadisticosService
        return cls._get_or_create(
            "estadisticos_service",
            lambda: EstadisticosService(
                repo            = cls.estadisticos_repo(),
                config_repo     = cls.configuracion_repo(),
                evaluacion_repo = cls.evaluacion_repo(),
                asistencia_repo = cls.asistencia_repo(),
                estudiante_repo = cls.estudiante_repo(),
                infra_repo      = cls.infraestructura_repo(),
                asignacion_repo = cls.asignacion_repo(),
                alerta_repo     = cls.alerta_repo(),
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
                estudiante_repo=cls.estudiante_repo(),
                # Provider lazy: ConvivenciaService orquesta todo (convivencia_32).
                convivencia_svc_provider=cls.convivencia_service,
            ),
        )

    @classmethod
    def infraestructura_service(cls):
        from src.services.infraestructura_service import InfraestructuraService
        return cls._get_or_create(
            "infraestructura_service",
            lambda: InfraestructuraService(
                repo=cls.infraestructura_repo(),
                auditoria_repo=cls.auditoria_repo(),
            ),
        )

    # ── Sub-servicios de infraestructura (mejora_01 — fachada por delegación) ──

    @classmethod
    def sala_service(cls):
        from src.services.sala_service import SalaService
        return cls._get_or_create(
            "sala_service",
            lambda: SalaService(repo=cls.infraestructura_repo()),
        )

    @classmethod
    def franja_service(cls):
        from src.services.franja_service import FranjaService
        return cls._get_or_create(
            "franja_service",
            lambda: FranjaService(repo=cls.infraestructura_repo()),
        )

    @classmethod
    def escenario_horario_service(cls):
        from src.services.escenario_horario_service import EscenarioHorarioService
        return cls._get_or_create(
            "escenario_horario_service",
            lambda: EscenarioHorarioService(repo=cls.infraestructura_repo()),
        )

    @classmethod
    def restriccion_generacion_service(cls):
        from src.services.restriccion_generacion_service import (
            RestriccionGeneracionService,
        )
        return cls._get_or_create(
            "restriccion_generacion_service",
            lambda: RestriccionGeneracionService(repo=cls.infraestructura_repo()),
        )

    @classmethod
    def catalogo_academico_service(cls):
        from src.services.catalogo_academico_service import CatalogoAcademicoService
        return cls._get_or_create(
            "catalogo_academico_service",
            lambda: CatalogoAcademicoService(
                repo=cls.infraestructura_repo(),
                # Provider lazy: candidatos/validación del director de grupo
                # (convivencia_02) sin acoplar el composition root.
                asignacion_svc_provider=cls.asignacion_service,
                auditoria_repo=cls.auditoria_repo(),
            ),
        )

    @classmethod
    def plan_estudios_service(cls):
        from src.services.plan_estudios_service import PlanEstudiosService
        return cls._get_or_create(
            "plan_estudios_service",
            lambda: PlanEstudiosService(
                repo=cls.infraestructura_repo(),
                # Provider lazy: evita la recursión plan↔asignacion en el arranque.
                asignacion_svc_provider=cls.asignacion_service,
                auditoria_repo=cls.auditoria_repo(),
            ),
        )

    @classmethod
    def preparacion_horario_service(cls):
        from src.services.preparacion_horario_service import PreparacionHorarioService
        return cls._get_or_create(
            "preparacion_horario_service",
            lambda: PreparacionHorarioService(
                infra_repo      = cls.infraestructura_repo(),
                asignacion_repo = cls.asignacion_repo(),
                config_repo     = cls.configuracion_repo(),
                periodo_repo    = cls.periodo_repo(),
                usuario_repo    = cls.usuario_repo(),
                plan_svc        = cls.plan_estudios_service(),
            ),
        )

    @classmethod
    def horario_service(cls):
        from src.services.horario_service import HorarioService
        return cls._get_or_create(
            "horario_service",
            lambda: HorarioService(
                infra_repo=cls.infraestructura_repo(),
                asignacion_repo=cls.asignacion_repo(),
                usuario_repo=cls.usuario_service(),
                auditoria_repo=cls.auditoria_repo(),
            ),
        )

    @classmethod
    def generador_horario_service(cls):
        from src.services.generador_horario_service import GeneradorHorarioService
        return cls._get_or_create(
            "generador_horario_service",
            lambda: GeneradorHorarioService(
                infra_repo=cls.infraestructura_repo(),
                asignacion_repo=cls.asignacion_repo(),
                usuario_repo=cls.usuario_service(),
                horario_service=cls.horario_service(),
                infraestructura_service=cls.infraestructura_service(),
                plan_svc=cls.plan_estudios_service(),
            ),
        )

    @classmethod
    def inicializar_contexto(cls, ctx):
        """Resuelve el contexto académico inicial tras el login."""
        from src.infrastructure.context.context_initializer import ContextInitializer
        return ContextInitializer.inicializar(ctx)

    @classmethod
    def security_logger(cls):
        from src.infrastructure.logging.security_logger import SecurityLogger
        return cls._get_or_create("security_logger", SecurityLogger)

    @classmethod
    def auditoria_service(cls):
        from src.services.auditoria_service import AuditoriaService
        return cls._get_or_create(
            "auditoria_service",
            lambda: AuditoriaService(
                repo=cls.auditoria_repo(),
                security_logger=cls.security_logger(),
                usuario_repo=cls.usuario_repo(),  # obs_09: resolver_actores / detalle_cambio
            ),
        )

    @classmethod
    def auditoria_export_service(cls):
        from config import settings
        from src.services.auditoria_export_service import AuditoriaExportService
        return cls._get_or_create(
            "auditoria_export_service",
            lambda: AuditoriaExportService(
                repo=cls.auditoria_repo(),
                exporter=cls.exporter_service(),
                max_filas=settings.AUDITORIA_EXPORT_MAX_FILAS,
            ),
        )

    @classmethod
    def auditoria_retencion_service(cls):
        from pathlib import Path

        from config import settings
        from src.services.auditoria_retencion_service import AuditoriaRetencionService
        archivo_dir = Path(settings.AUDITORIA_ARCHIVO_DIR)
        if not archivo_dir.is_absolute():
            from pathlib import Path as _Path
            archivo_dir = _Path(__file__).parent / settings.AUDITORIA_ARCHIVO_DIR
        return cls._get_or_create(
            "auditoria_retencion_service",
            lambda: AuditoriaRetencionService(
                repo=cls.auditoria_repo(),
                archivo_dir=archivo_dir,
            ),
        )

    @classmethod
    def busqueda_service(cls):
        from src.services.busqueda_service import BusquedaService
        return cls._get_or_create(
            "busqueda_service",
            lambda: BusquedaService(
                estudiante_svc_provider=cls.estudiante_service,
                usuario_svc_provider=cls.usuario_service,
                catalogo_svc_provider=cls.catalogo_academico_service,
                asignacion_svc_provider=cls.asignacion_service,
            ),
        )

    @classmethod
    def log_reader(cls):
        from src.infrastructure.logging.jsonl_log_reader import JsonlLogReader
        return cls._get_or_create("log_reader", JsonlLogReader)

    @classmethod
    def observabilidad_service(cls):
        from src.services.observabilidad_service import ObservabilidadService
        return cls._get_or_create(
            "observabilidad_service",
            lambda: ObservabilidadService(
                auditoria_repo=cls.auditoria_repo(),
                log_reader=cls.log_reader(),
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
            "configuracion_service", "institucion_service", "aprovisionamiento_service",
            "usuario_service",
            "estudiante_service", "periodo_service", "asignacion_service",
            "evaluacion_service", "asistencia_service", "cierre_service",
            "habilitacion_service", "nivelacion_service", "plan_mejoramiento_service", "convivencia_service", "alerta_service",
            "estadisticos_service", "informe_service", "auditoria_service",
            "auditoria_export_service", "auditoria_retencion_service",
            "infraestructura_service", "plan_estudios_service",
            "preparacion_horario_service",
            "sala_service", "franja_service", "escenario_horario_service",
            "restriccion_generacion_service", "catalogo_academico_service",
            "busqueda_service",
            "log_reader", "observabilidad_service",
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


# ---------------------------------------------------------------------------
# Factory privada del engine (backend_05)
# ---------------------------------------------------------------------------

def _create_engine():
    """Crea el engine SQLAlchemy según DB_BACKEND del entorno."""
    from sqlalchemy import create_engine, event

    from config import settings

    backend = os.getenv("DB_BACKEND", "sqlite")
    if backend == "sqlite":
        url = f"sqlite:///{settings.DATABASE_PATH}"
        engine = create_engine(url, echo=False)

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragmas(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=-64000")
            cursor.close()

        return engine

    if backend == "postgres":
        url = os.getenv("DATABASE_URL", settings.DATABASE_URL)
        if not url:
            raise ValueError(
                "DATABASE_URL debe definirse cuando DB_BACKEND=postgres"
            )
        return create_engine(url, echo=False, pool_pre_ping=True)

    raise ValueError(f"DB_BACKEND no soportado: {backend!r}")
