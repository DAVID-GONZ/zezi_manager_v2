"""
src/domain/models/__init__.py
Re-exportación unificada. Permite:
    from src.domain.models import Estudiante, CalculadorNotas
"""
from .configuracion import (ConfiguracionAnio, NuevaConfiguracionAnioDTO,
    ActualizarConfiguracionAnioDTO, ActualizarInfoInstitucionalDTO,
    InformacionInstitucionalDTO)
from .infraestructura import (Jornada, DiaSemana, AreaConocimiento,
    Asignatura, Grupo, Horario, HorarioInfo, HorarioEstadisticasDTO, Logro,
    NuevaAreaDTO, NuevaAsignaturaDTO, NuevoGrupoDTO, NuevoHorarioDTO, NuevoLogroDTO)
from .usuario import (Rol, Usuario, DocenteInfoDTO, AsignacionDocenteInfoDTO,
    NuevoUsuarioDTO, ActualizarUsuarioDTO, UsuarioResumenDTO, FiltroUsuariosDTO)
from .acudiente import (TipoDocumentoAcudiente, Parentesco, Acudiente,
    EstudianteAcudiente, NuevoAcudienteDTO, ActualizarAcudienteDTO,
    VincularAcudienteDTO, AcudienteResumenDTO)
from .estudiante import (TipoDocumento, Genero, EstadoMatricula, Estudiante,
    NuevoEstudianteDTO, ActualizarEstudianteDTO, FiltroEstudiantesDTO,
    EstudianteResumenDTO)
from .periodo import (TipoHito, Periodo, HitoPeriodo, NuevoPeriodoDTO,
    ActualizarPeriodoDTO, NuevoHitoPeriodoDTO)
from .asignacion import (Asignacion, AsignacionInfo, NuevaAsignacionDTO,
    FiltroAsignacionesDTO)
from .evaluacion import (EstadoActividad, TipoPuntosExtra, Categoria,
    Actividad, Nota, PuntosExtra, CalculadorNotas, NuevaCategoriaDTO,
    ActualizarCategoriaDTO, NuevaActividadDTO, ActualizarActividadDTO,
    RegistrarNotaDTO, RegistrarNotasMasivasDTO, ResultadoEstudianteDTO,
    FiltroNotasDTO)
from .cierre import (EstadoPromocion, CierrePeriodo, CierreAnio,
    PromocionAnual, CrearCierrePeriodoDTO, CrearCierreAnioDTO,
    DecidirPromocionDTO)
from .habilitacion import (TipoHabilitacion, EstadoHabilitacion,
    EstadoPlanMejoramiento, Habilitacion, PlanMejoramiento,
    NuevaHabilitacionDTO, RegistrarNotaHabilitacionDTO, NuevoPlanMejoramientoDTO,
    CerrarPlanMejoramientoDTO, FiltroHabilitacionesDTO)
from .asistencia import (EstadoAsistencia, ControlDiario, ResumenAsistenciaDTO,
    RegistroAsistenciaItemDTO, RegistrarAsistenciaDTO,
    RegistrarAsistenciaMasivaDTO, FiltroAsistenciaDTO)
from .convivencia import (TipoRegistro, ObservacionPeriodo,
    RegistroComportamiento, NotaComportamiento, NuevaObservacionDTO,
    NuevoRegistroComportamientoDTO, NuevaNotaComportamientoDTO,
    FiltroConvivenciaDTO)
from .alerta import (TipoAlerta, NivelAlerta, ConfiguracionAlerta, Alerta,
    CrearAlertaDTO, ResolverAlertaDTO, FiltroAlertasDTO)
from .piar import (PIAR, NuevoPIARDTO, ActualizarPIARDTO)
from .auditoria import (TipoEventoSesion, AccionCambio, EventoSesion,
    RegistroCambio, CrearEventoSesionDTO, CrearRegistroCambioDTO,
    FiltroAuditoriaDTO)
from .dtos import (FormatoInforme, ContextoAcademicoDTO, InformeNotasDTO,
    InformeAsistenciaDTO, DashboardMetricsDTO, MatriculaMasivaDTO,
    MatriculaMasivaResultadoDTO, RespuestaOperacionDTO)