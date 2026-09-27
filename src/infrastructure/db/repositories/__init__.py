"""
Repositorios SQLAlchemy Core — implementaciones de los puertos de dominio.

Exporta los repositorios canónicos (sqla_*) migrados en backend_07.
Los archivos sqlite_*_repo.py son legado; solo viven para tests históricos
que aún no se han migrado (deuda técnica registrada en backend_07).
"""

from .sqla_acudiente_repo import SqlaAcudienteRepository
from .sqla_alerta_repo import SqlaAlertaRepository
from .sqla_asignacion_repo import SqlaAsignacionRepository
from .sqla_asistencia_repo import SqlaAsistenciaRepository
from .sqla_auditoria_repo import SqlaAuditoriaRepository
from .sqla_cierre_repo import SqlaCierreRepository
from .sqla_configuracion_repo import SqlaConfiguracionRepository
from .sqla_convivencia_repo import SqlaConvivenciaRepository
from .sqla_estadisticos_repo import SqlaEstadisticosRepository
from .sqla_estudiante_repo import SqlaEstudianteRepository
from .sqla_evaluacion_repo import SqlaEvaluacionRepository
from .sqla_habilitacion_repo import SqlaHabilitacionRepository
from .sqla_infraestructura_repo import SqlaInfraestructuraRepository
from .sqla_institucion_repo import SqlaInstitucionRepository
from .sqla_nivelacion_repo import SqlaNivelacionRepository
from .sqla_periodo_repo import SqlaPeriodoRepository
from .sqla_plan_mejoramiento_repo import SqlaPlanMejoramientoRepository
from .sqla_preferencias_repo import SqlaPreferenciasRepository
from .sqla_siee_repo import SqlaSIEERepository
from .sqla_usuario_repo import SqlaUsuarioRepository

__all__ = [
    "SqlaAcudienteRepository",
    "SqlaAlertaRepository",
    "SqlaAsignacionRepository",
    "SqlaAsistenciaRepository",
    "SqlaAuditoriaRepository",
    "SqlaCierreRepository",
    "SqlaConfiguracionRepository",
    "SqlaConvivenciaRepository",
    "SqlaEstadisticosRepository",
    "SqlaEstudianteRepository",
    "SqlaEvaluacionRepository",
    "SqlaHabilitacionRepository",
    "SqlaInfraestructuraRepository",
    "SqlaInstitucionRepository",
    "SqlaNivelacionRepository",
    "SqlaPeriodoRepository",
    "SqlaPlanMejoramientoRepository",
    "SqlaPreferenciasRepository",
    "SqlaSIEERepository",
    "SqlaUsuarioRepository",
]
