"""
DTOs transversales — ZECI Manager v2.0
=======================================

Este módulo contiene los DTOs que cruzan módulos y no pertenecen
a ninguna entidad específica. Los DTOs de entidades concretas viven
junto a su modelo (ej: NuevoEstudianteDTO está en estudiante.py).

Contiene:
  ContextoAcademicoDTO   — contexto activo de la sesión (reemplaza AppState)
  InformeNotasDTO        — parámetros para generar informes de notas
  InformeAsistenciaDTO   — parámetros para generar informes de asistencia
  DashboardMetricsDTO    — métricas calculadas para el panel principal
  MatriculaMasivaDTO     — entrada para carga masiva de estudiantes
  MatriculaMasivaResultadoDTO — resultado de una carga masiva
  RespuestaOperacionDTO  — envuelve resultados de operaciones con metadatos
"""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Formato de exportación
# =============================================================================

class FormatoInforme(str, Enum):
    EXCEL = "excel"
    PDF   = "pdf"


# =============================================================================
# Contexto académico — reemplaza AppState para operaciones de lectura
# =============================================================================

class ContextoAcademicoDTO(BaseModel):
    """
    Captura el contexto de trabajo activo en la sesión: usuario, periodo,
    grupo y asignación seleccionados. Es inmutable — cada cambio en la UI
    crea un nuevo DTO.

    En v1.0, este contexto vivía en AppState (estado global mutable).
    En v2.0, el IContextService construye este DTO y los servicios lo
    reciben como parámetro. Esto hace que las operaciones sean
    explícitas y testeables sin estado global.
    """
    usuario_id:    int
    anio_id:       int
    periodo_id:    int
    grupo_id:      int | None    = None
    asignacion_id: int | None    = None

    @field_validator("usuario_id", "anio_id", "periodo_id")
    @classmethod
    def validar_id_requerido(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"El ID debe ser un entero positivo (recibido: {v}).")
        return v

    @property
    def tiene_grupo(self) -> bool:
        return self.grupo_id is not None

    @property
    def tiene_asignacion(self) -> bool:
        return self.asignacion_id is not None

    @property
    def contexto_completo(self) -> bool:
        """True si tiene todos los selectores necesarios para notas y asistencia."""
        return self.tiene_grupo and self.tiene_asignacion


# =============================================================================
# Informes
# =============================================================================

class InformeNotasDTO(BaseModel):
    """
    Parámetros para generar un informe de calificaciones.
    Consumido por InformeService.generar_notas() y por los exportadores.
    """
    grupo_id:      int
    asignacion_id: int
    periodo_id:    int
    fecha_desde:   date
    fecha_hasta:   date
    formato:       FormatoInforme = FormatoInforme.EXCEL
    incluir_piar:  bool           = True   # marcar estudiantes con PIAR

    @field_validator("grupo_id", "asignacion_id", "periodo_id")
    @classmethod
    def validar_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"El ID debe ser positivo (recibido: {v}).")
        return v

    @field_validator("fecha_hasta")
    @classmethod
    def validar_rango_fechas(cls, v: date, info) -> date:
        fecha_desde = info.data.get("fecha_desde")
        if fecha_desde and v < fecha_desde:
            raise ValueError(
                f"fecha_hasta ({v}) no puede ser anterior a fecha_desde ({fecha_desde})."
            )
        return v


class InformeAsistenciaDTO(BaseModel):
    """Parámetros para generar un informe de asistencia."""
    grupo_id:      int
    asignacion_id: int
    periodo_id:    int
    fecha_desde:   date
    fecha_hasta:   date
    formato:       FormatoInforme = FormatoInforme.EXCEL

    @field_validator("grupo_id", "asignacion_id", "periodo_id")
    @classmethod
    def validar_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"El ID debe ser positivo (recibido: {v}).")
        return v

    @field_validator("fecha_hasta")
    @classmethod
    def validar_rango_fechas(cls, v: date, info) -> date:
        fecha_desde = info.data.get("fecha_desde")
        if fecha_desde and v < fecha_desde:
            raise ValueError(
                f"fecha_hasta ({v}) no puede ser anterior a fecha_desde ({fecha_desde})."
            )
        return v


# =============================================================================
# Dashboard
# =============================================================================

class DashboardMetricsDTO(BaseModel):
    """
    Métricas agregadas para el panel principal.
    El DashboardService las calcula con queries GROUP BY;
    la página las muestra directamente sin lógica adicional.
    """
    grupo_id:               int
    total_estudiantes:      int  = 0
    promedio_general:       float = 0.0
    porcentaje_asistencia:  float = 0.0
    estudiantes_en_riesgo:  int  = 0
    actividades_publicadas: int  = 0
    alertas_pendientes:     int  = 0

    @field_validator("promedio_general", "porcentaje_asistencia")
    @classmethod
    def validar_porcentaje(cls, v: float) -> float:
        if not (0 <= v <= 100):
            raise ValueError(f"El valor debe estar entre 0 y 100 (recibido: {v}).")
        return round(v, 2)

    @field_validator("total_estudiantes", "estudiantes_en_riesgo",
                     "actividades_publicadas", "alertas_pendientes")
    @classmethod
    def validar_no_negativo(cls, v: int) -> int:
        if v < 0:
            raise ValueError(f"El valor no puede ser negativo (recibido: {v}).")
        return v

    @property
    def pct_en_riesgo(self) -> float:
        """Porcentaje de estudiantes en riesgo."""
        if self.total_estudiantes == 0:
            return 0.0
        return round(self.estudiantes_en_riesgo / self.total_estudiantes * 100, 1)


# =============================================================================
# Matrícula masiva
# =============================================================================

class MatriculaMasivaDTO(BaseModel):
    """
    Entrada para carga masiva de estudiantes desde un archivo Excel/CSV.
    El servicio itera sobre `filas` y crea un Estudiante por cada una.
    """
    grupo_id:       int | None          = None
    filas:          list[dict]          = Field(default_factory=list)
    omitir_errores: bool                = True  # continuar si una fila falla

    @field_validator("filas")
    @classmethod
    def validar_filas(cls, v: list[dict]) -> list[dict]:
        if len(v) > 5000:
            raise ValueError(
                f"No se pueden cargar más de 5000 estudiantes por operación "
                f"(recibido: {len(v)})."
            )
        return v

    @property
    def total_filas(self) -> int:
        return len(self.filas)


class MatriculaMasivaResultadoDTO(BaseModel):
    """Resultado de una operación de carga masiva."""
    total_procesadas:  int         = 0
    exitosas:          int         = 0
    fallidas:          int         = 0
    errores:           list[dict]  = Field(default_factory=list)
    # Cada error: {"fila": int, "dato": str, "motivo": str}

    @property
    def tasa_exito(self) -> float:
        if self.total_procesadas == 0:
            return 0.0
        return round(self.exitosas / self.total_procesadas * 100, 1)

    @property
    def fue_exitosa(self) -> bool:
        return self.fallidas == 0

    def agregar_error(self, fila: int, dato: str, motivo: str) -> None:
        self.errores.append({"fila": fila, "dato": dato, "motivo": motivo})
        self.fallidas += 1


# =============================================================================
# Respuesta genérica de operación
# =============================================================================

class RespuestaOperacionDTO(BaseModel):
    """
    Envuelve el resultado de una operación con metadatos de éxito/error.
    Los servicios la retornan cuando la UI necesita feedback estructurado
    más allá de una excepción.
    """
    exito:    bool
    mensaje:  str
    datos:    dict | None  = None

    @classmethod
    def ok(cls, mensaje: str = "Operación exitosa", datos: dict | None = None) -> "RespuestaOperacionDTO":
        return cls(exito=True, mensaje=mensaje, datos=datos)

    @classmethod
    def error(cls, mensaje: str, datos: dict | None = None) -> "RespuestaOperacionDTO":
        return cls(exito=False, mensaje=mensaje, datos=datos)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "FormatoInforme",
    "ContextoAcademicoDTO",
    "InformeNotasDTO",
    "InformeAsistenciaDTO",
    "DashboardMetricsDTO",
    "MatriculaMasivaDTO",
    "MatriculaMasivaResultadoDTO",
    "RespuestaOperacionDTO",
]