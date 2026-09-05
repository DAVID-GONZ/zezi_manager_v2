"""
Modelo de dominio: Infraestructura académica
=============================================

Entidades estructurales que soportan el funcionamiento del sistema
pero no tienen lógica de negocio compleja. Son los cimientos sobre
los que se construyen asignaciones, evaluaciones y asistencia.

Contiene:
  Enums    — Jornada, DiaSemana
  Entidades — AreaConocimiento, Asignatura, Grupo, Horario, Logro
  DTOs     — uno por entidad

Regla general: los campos de texto obligatorios se normalizan
(strip + title-case donde aplica). Los IDs de FK deben ser positivos.
"""

from __future__ import annotations

from datetime import time
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator

# =============================================================================
# Enumeraciones
# =============================================================================


class Jornada(StrEnum):
    AM = "AM"
    PM = "PM"
    UNICA = "UNICA"


class DiaSemana(StrEnum):
    LUNES = "Lunes"
    MARTES = "Martes"
    MIERCOLES = "Miércoles"
    JUEVES = "Jueves"
    VIERNES = "Viernes"
    SABADO = "Sábado"


# =============================================================================
# Entidades
# =============================================================================


class AreaConocimiento(BaseModel):
    """
    Área del currículo colombiano (Ley 115 de 1994, Art. 23).
    Ejemplos: 'Matemáticas', 'Ciencias Naturales y Educación Ambiental'.
    """

    id: int | None = None
    nombre: str
    codigo: str | None = None
    color: str | None = None  # hex "#RGB" o "#RRGGBB"; None = sin color
    institucion_id: int | None = None

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        """Normaliza el nombre del área (strip) y exige no vacío y ≤120 caracteres."""
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre del área no puede estar vacío.")
        if len(v) > 120:
            raise ValueError(f"El nombre no puede exceder 120 caracteres (tiene {len(v)}).")
        return v

    @field_validator("codigo", mode="before")
    @classmethod
    def limpiar_codigo(cls, v: str | None) -> str | None:
        """Normaliza el código a mayúsculas sin espacios; cadena vacía → None."""
        if v is None:
            return None
        v = str(v).strip().upper()
        return v if v else None

    @field_validator("color", mode="before")
    @classmethod
    def normalizar_color(cls, v: str | None) -> str | None:
        """Acepta solo hex válido (#RGB o #RRGGBB). Cualquier otro valor → None (soft)."""
        if v is None:
            return None
        v = str(v).strip()
        if not v:
            return None
        if v[0] == "#" and len(v) in (4, 7):
            return v
        return None


class Asignatura(BaseModel):
    """
    Asignatura que se dicta en la institución.
    Pertenece a un área de conocimiento.
    """

    id: int | None = None
    nombre: str
    codigo: str | None = None
    area_id: int | None = None
    horas_semanales: int = Field(default=1, ge=1)
    tipo_sala_requerido: str | None = None  # None = cualquier sala / "Aula"
    bloque_doble: bool = False  # requiere franjas consecutivas
    horas_consecutivas: int = Field(default=1, ge=1)  # bloques dobles N horas seguidas
    # Multi-tenant (paso_29): institución dueña. None = sin tenant (single-tenant
    # temprano / arranque sin sesión); el servicio y el seed la resuelven a #1.
    institucion_id: int | None = None

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        """Normaliza el nombre de la asignatura y exige no vacío y ≤100 caracteres."""
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre de la asignatura no puede estar vacío.")
        if len(v) > 100:
            raise ValueError(f"El nombre no puede exceder 100 caracteres (tiene {len(v)}).")
        return v

    @field_validator("codigo", mode="before")
    @classmethod
    def limpiar_codigo(cls, v: str | None) -> str | None:
        """Normaliza el código a mayúsculas sin espacios; cadena vacía → None."""
        if v is None:
            return None
        v = str(v).strip().upper()
        return v if v else None

    @field_validator("area_id")
    @classmethod
    def validar_area_id(cls, v: int | None) -> int | None:
        """Si se especifica área, su id debe ser positivo (FK válida)."""
        if v is not None and v <= 0:
            raise ValueError(f"area_id debe ser positivo (recibido: {v}).")
        return v


class Grupo(BaseModel):
    """
    Grupo escolar (curso). Cada grupo tiene un grado, jornada y
    capacidad máxima de estudiantes.

    El código es el identificador legible: '601', '1101', 'A1', etc.
    """

    id: int | None = None
    codigo: str
    nombre: str | None = None
    grado: int | None = None
    jornada: Jornada = Jornada.UNICA
    capacidad_maxima: int = Field(default=40, ge=1)
    sala_id: int | None = None  # aula propia del grupo (salón base)
    # Multi-tenant (paso_29): institución dueña. None = sin tenant; el servicio
    # y el seed la resuelven a #1.
    institucion_id: int | None = None
    # Director de grupo (convivencia_01): FK opcional a usuarios(id). Autoridad
    # por objeto, no un Rol. None = grupo sin director asignado.
    director_grupo_id: int | None = None

    @field_validator("codigo", mode="before")
    @classmethod
    def validar_codigo(cls, v: str) -> str:
        """Normaliza el código del grupo a mayúsculas; exige no vacío y ≤20 caracteres."""
        v = str(v).strip().upper()
        if not v:
            raise ValueError("El código del grupo no puede estar vacío.")
        if len(v) > 20:
            raise ValueError(f"El código no puede exceder 20 caracteres (tiene {len(v)}).")
        return v

    @field_validator("nombre", mode="before")
    @classmethod
    def limpiar_nombre(cls, v: str | None) -> str | None:
        """Normaliza el nombre opcional (strip); cadena vacía → None."""
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None

    @field_validator("grado")
    @classmethod
    def validar_grado(cls, v: int | None) -> int | None:
        """Si se indica grado, debe estar en el rango 1..13 del sistema colombiano."""
        if v is not None and not (1 <= v <= 13):
            raise ValueError(f"El grado debe estar entre 1 y 13 (recibido: {v}).")
        return v

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def descripcion_completa(self) -> str:
        """
        Descripción larga para encabezados:
          Con nombre: '601 — Sexto A (AM)'
          Sin nombre: '601 (AM)'
        """
        jornada = f"({self.jornada.value})"
        if self.nombre:
            return f"{self.codigo} — {self.nombre} {jornada}"
        return f"{self.codigo} {jornada}"

    @property
    def descripcion_corta(self) -> str:
        """'601' o 'Sexto A' si hay nombre."""
        return self.nombre or self.codigo

    def esta_lleno(self, matriculados: int) -> bool:
        """True si el número de matriculados alcanza la capacidad máxima."""
        if matriculados < 0:
            raise ValueError(
                f"El número de matriculados no puede ser negativo (recibido: {matriculados})."
            )
        return matriculados >= self.capacidad_maxima

    def cupos_disponibles(self, matriculados: int) -> int:
        """Cupos libres. 0 si ya está lleno."""
        return max(0, self.capacidad_maxima - matriculados)


class Grado(BaseModel):
    """
    Grado ofrecido por la institución (1–13), con su rango de estudiantes
    (norma colombiana) y el total de horas semanales objetivo del plan.
    """

    id: int | None = None
    numero: int = Field(ge=1, le=13)
    nombre: str | None = None
    min_estudiantes: int = Field(default=0, ge=0)
    max_estudiantes: int = Field(default=40, ge=1)
    horas_semanales: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validar_rango_estudiantes(self) -> Grado:
        """El mínimo de estudiantes no puede superar el máximo del grado."""
        if self.min_estudiantes > self.max_estudiantes:
            raise ValueError(
                f"El mínimo de estudiantes ({self.min_estudiantes}) no puede "
                f"superar el máximo ({self.max_estudiantes})."
            )
        return self


class ConfiguracionGradoInstitucion(BaseModel):
    """
    Configuración por-institución de un grado (tabla puente — mejora_07-T6).
    Permite que cada institución ajuste min/max de estudiantes y horas semanales
    por grado sin modificar la tabla global `grados`.
    """

    id: int | None = None
    grado_id: int = Field(gt=0)
    institucion_id: int = Field(gt=0)
    min_estudiantes: int = Field(default=0, ge=0)
    max_estudiantes: int = Field(default=40, ge=1)
    horas_semanales: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validar_rango_estudiantes(self) -> ConfiguracionGradoInstitucion:
        """El mínimo de estudiantes no puede superar el máximo."""
        if self.min_estudiantes > self.max_estudiantes:
            raise ValueError(
                f"min_estudiantes ({self.min_estudiantes}) no puede superar "
                f"max_estudiantes ({self.max_estudiantes})."
            )
        return self


class EscenarioHorario(BaseModel):
    """
    Escenario de horario para un año lectivo.
    Solo puede haber un escenario activo por año (enforced por índice parcial).
    """

    id: int | None = None
    anio_id: int
    nombre: str
    descripcion: str | None = None
    activo: bool = False
    created_at: str | None = None

    @field_validator("anio_id")
    @classmethod
    def validar_anio_id(cls, v: int) -> int:
        """El año lectivo referenciado (FK) debe ser positivo."""
        if v <= 0:
            raise ValueError(f"anio_id debe ser positivo (recibido: {v}).")
        return v

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        """Normaliza el nombre del escenario y exige que no esté vacío."""
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre del escenario no puede estar vacío.")
        return v


class NuevoEscenarioDTO(BaseModel):
    """DTO para crear un nuevo escenario de horario."""

    anio_id: int
    nombre: str
    descripcion: str | None = None

    @field_validator("anio_id")
    @classmethod
    def validar_anio_id(cls, v: int) -> int:
        """El año lectivo referenciado (FK) debe ser positivo."""
        if v <= 0:
            raise ValueError(f"anio_id debe ser positivo (recibido: {v}).")
        return v

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        """Normaliza el nombre del escenario y exige que no esté vacío."""
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre del escenario no puede estar vacío.")
        return v

    def to_escenario(self) -> EscenarioHorario:
        """Construye un EscenarioHorario a partir de los datos del DTO."""
        return EscenarioHorario(**self.model_dump())


class Horario(BaseModel):
    """
    Franja horaria de una asignatura para un grupo en un escenario.

    hora_inicio y hora_fin aceptan objetos time o strings "HH:MM".
    Invariante: hora_inicio < hora_fin.
    periodo_id es nullable (resolución vía escenario activo).
    """

    id: int | None = None
    grupo_id: int
    asignatura_id: int
    usuario_id: int
    asignacion_id: int | None = None
    periodo_id: int | None = None
    escenario_id: int
    dia_semana: DiaSemana
    hora_inicio: time
    hora_fin: time
    sala: str = "Aula"

    @field_validator("grupo_id", "asignatura_id", "usuario_id")
    @classmethod
    def validar_id_positivo(cls, v: int) -> int:
        """Las FK del bloque (grupo, asignatura, docente) deben ser positivas."""
        if v <= 0:
            raise ValueError(f"El ID debe ser un entero positivo (recibido: {v}).")
        return v

    @field_validator("escenario_id")
    @classmethod
    def validar_escenario_id(cls, v: int) -> int:
        """El escenario dueño del bloque debe referenciarse con un id positivo."""
        if v <= 0:
            raise ValueError(f"escenario_id debe ser un entero positivo (recibido: {v}).")
        return v

    @field_validator("hora_inicio", "hora_fin", mode="before")
    @classmethod
    def parsear_hora(cls, v: time | str) -> time:
        """Acepta un time o un string 'HH:MM' y lo convierte a datetime.time."""
        if isinstance(v, time):
            return v
        if isinstance(v, str):
            partes = v.strip().split(":")
            if len(partes) < 2:
                raise ValueError(f"Formato de hora inválido: '{v}'. Use HH:MM.")
            try:
                return time(int(partes[0]), int(partes[1]))
            except ValueError as e:
                raise ValueError(f"Hora fuera de rango: '{v}'.") from e
        raise ValueError(f"Tipo de hora no soportado: {type(v)}.")

    @field_validator("sala", mode="before")
    @classmethod
    def validar_sala(cls, v: str) -> str:
        """Normaliza la sala; si queda vacía usa 'Aula' por defecto."""
        v = str(v).strip()
        return v if v else "Aula"

    @model_validator(mode="after")
    def validar_orden_horas(self) -> Self:
        """Invariante temporal: la hora de inicio debe ser anterior a la de fin."""
        if self.hora_inicio >= self.hora_fin:
            raise ValueError(
                f"hora_inicio ({self.hora_inicio}) debe ser anterior a hora_fin ({self.hora_fin})."
            )
        return self

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def duracion_minutos(self) -> int:
        """Duración de la clase en minutos."""
        inicio = self.hora_inicio.hour * 60 + self.hora_inicio.minute
        fin = self.hora_fin.hour * 60 + self.hora_fin.minute
        return fin - inicio

    @property
    def franja_display(self) -> str:
        """
        Representación para mostrar en grillas de horario:
        'Lunes 07:00–07:55'
        """
        return (
            f"{self.dia_semana.value} "
            f"{self.hora_inicio.strftime('%H:%M')}–"
            f"{self.hora_fin.strftime('%H:%M')}"
        )


class Logro(BaseModel):
    """
    Logro o competencia evaluado en una asignación durante un periodo.

    El logro es el enunciado del aprendizaje esperado que aparece
    en el boletín junto a la nota. Ejemplo:
    'Comprende y aplica los conceptos de función cuadrática.'
    """

    id: int | None = None
    asignacion_id: int
    periodo_id: int
    descripcion: str
    orden: int = Field(default=0, ge=0)

    @field_validator("asignacion_id", "periodo_id")
    @classmethod
    def validar_id_positivo(cls, v: int) -> int:
        """Las FK del logro (asignación y periodo) deben ser positivas."""
        if v <= 0:
            raise ValueError(f"El ID debe ser positivo (recibido: {v}).")
        return v

    @field_validator("descripcion", mode="before")
    @classmethod
    def validar_descripcion(cls, v: str) -> str:
        """Normaliza el enunciado del logro; exige no vacío y ≤500 caracteres."""
        v = str(v).strip()
        if not v:
            raise ValueError("La descripción del logro no puede estar vacía.")
        if len(v) > 500:
            raise ValueError(f"La descripción no puede exceder 500 caracteres (tiene {len(v)}).")
        return v


# =============================================================================
# Rejilla de franjas horarias (paso_15a)
# =============================================================================

# Días válidos para la rejilla. Derivado del enum DiaSemana (misma fuente de
# verdad) pero expuesto como list[str] porque dias_activos se persiste como CSV.
DIAS_VALIDOS: list[str] = [d.value for d in DiaSemana]

TIPOS_FRANJA: set[str] = {"lectiva", "descanso", "almuerzo"}
JORNADAS_VALIDAS: set[str] = {"AM", "PM", "UNICA"}


class Franja(BaseModel):
    """
    Una franja horaria dentro de una plantilla (rejilla fija).

    Las horas se modelan como strings "HH:MM" y se comparan
    lexicográficamente, coherente con el resto del modelo de horarios.
    """

    id: int | None = None
    plantilla_id: int
    orden: int = Field(ge=1)
    hora_inicio: str
    hora_fin: str
    tipo: str = "lectiva"
    etiqueta: str | None = None

    @field_validator("plantilla_id")
    @classmethod
    def validar_plantilla_id(cls, v: int) -> int:
        """La plantilla dueña de la franja debe referenciarse con id positivo."""
        if v <= 0:
            raise ValueError(f"plantilla_id debe ser positivo (recibido: {v}).")
        return v

    @field_validator("hora_inicio", "hora_fin", mode="before")
    @classmethod
    def normalizar_hora(cls, v: str) -> str:
        """Normaliza 'H:MM' -> 'HH:MM' (pad con 0); rechaza lo que no parsee
        como HH:MM. T15 (horario_01): antes solo hacía strip y comparaba las
        horas lexicográficamente sin normalizar ('7:00' >= '07:00' es True),
        lo que rompía la invariante hora_inicio < hora_fin con horas sin
        padding."""
        v = str(v).strip()
        if not v:
            raise ValueError("La hora no puede estar vacía.")
        partes = v.split(":")
        if len(partes) != 2:
            raise ValueError(f"Hora inválida: '{v}'. Use el formato HH:MM.")
        try:
            hora, minuto = int(partes[0]), int(partes[1])
        except ValueError as exc:
            raise ValueError(f"Hora inválida: '{v}'. Use el formato HH:MM.") from exc
        if not (0 <= hora <= 23 and 0 <= minuto <= 59):
            raise ValueError(f"Hora fuera de rango: '{v}'.")
        return f"{hora:02d}:{minuto:02d}"

    @field_validator("tipo", mode="before")
    @classmethod
    def validar_tipo(cls, v: str) -> str:
        """El tipo de franja debe ser uno de TIPOS_FRANJA (lectiva/descanso/almuerzo)."""
        v = str(v).strip().lower()
        if v not in TIPOS_FRANJA:
            raise ValueError(f"tipo inválido: '{v}'. Use uno de {sorted(TIPOS_FRANJA)}.")
        return v

    @field_validator("etiqueta", mode="before")
    @classmethod
    def limpiar_etiqueta(cls, v: str | None) -> str | None:
        """Normaliza la etiqueta opcional (strip); cadena vacía → None."""
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None

    @model_validator(mode="after")
    def validar_orden_horas(self) -> Self:
        """Invariante temporal: la hora de inicio debe ser anterior a la de fin."""
        if self.hora_inicio >= self.hora_fin:
            raise ValueError(
                f"hora_inicio ({self.hora_inicio}) debe ser anterior a hora_fin ({self.hora_fin})."
            )
        return self

    @property
    def es_lectiva(self) -> bool:
        """True si la franja es de tipo lectiva (dictada, no descanso ni almuerzo)."""
        return self.tipo == "lectiva"


class PlantillaFranja(BaseModel):
    """
    Plantilla (rejilla) de franjas para una jornada. A lo sumo una activa
    por jornada (índice único parcial en BD).
    """

    id: int | None = None
    nombre: str
    jornada: str = "UNICA"
    dias_activos: list[str]
    activa: bool = False
    created_at: str | None = None
    institucion_id: int | None = None  # paso_32: lo resuelve el servicio si falta

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        """Normaliza el nombre de la plantilla y exige que no esté vacío."""
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre de la plantilla no puede estar vacío.")
        return v

    @field_validator("jornada", mode="before")
    @classmethod
    def validar_jornada(cls, v: str) -> str:
        """La jornada debe ser una de JORNADAS_VALIDAS (AM/PM/UNICA)."""
        v = str(v).strip().upper()
        if v not in JORNADAS_VALIDAS:
            raise ValueError(f"jornada inválida: '{v}'. Use uno de {sorted(JORNADAS_VALIDAS)}.")
        return v

    @field_validator("dias_activos", mode="before")
    @classmethod
    def validar_dias(cls, v: list[str]) -> list[str]:
        """Acepta lista o CSV de días, normaliza y exige que todos estén en DIAS_VALIDOS y no vacío."""
        if isinstance(v, str):
            v = [d.strip() for d in v.split(",") if d.strip()]
        if not isinstance(v, (list, tuple)):
            raise ValueError("dias_activos debe ser una lista de días.")
        dias = [str(d).strip() for d in v if str(d).strip()]
        if not dias:
            raise ValueError("dias_activos no puede estar vacío.")
        invalidos = [d for d in dias if d not in DIAS_VALIDOS]
        if invalidos:
            raise ValueError(
                f"Días inválidos en dias_activos: {invalidos}. Válidos: {DIAS_VALIDOS}."
            )
        return dias


class NuevaPlantillaFranjaDTO(BaseModel):
    nombre: str
    jornada: str = "UNICA"
    dias_activos: list[str]

    def to_plantilla(self) -> PlantillaFranja:
        """Construye una PlantillaFranja a partir de los datos del DTO."""
        return PlantillaFranja(**self.model_dump())


class NuevaFranjaDTO(BaseModel):
    plantilla_id: int
    orden: int
    hora_inicio: str
    hora_fin: str
    tipo: str = "lectiva"
    etiqueta: str | None = None

    def to_franja(self) -> Franja:
        """Construye una Franja a partir de los datos del DTO."""
        return Franja(**self.model_dump())


# =============================================================================
# Generador de horarios (paso_15b)
# =============================================================================


class PesosGeneracion(BaseModel):
    huecos: float = Field(default=1.0, ge=0.0, le=2.0)
    distribucion: float = Field(default=1.0, ge=0.0, le=2.0)
    compactacion: float = Field(default=0.5, ge=0.0, le=2.0)
    balance_diario: float = Field(default=0.0, ge=0.0, le=2.0)
    franja_preferida: float = Field(default=0.0, ge=0.0, le=2.0)
    dia_libre: float = Field(default=0.0, ge=0.0, le=2.0)
    hueco_comun: float = Field(default=0.0, ge=0.0, le=2.0)


PESOS_DEFAULT = PesosGeneracion()


ESTADOS_CONFIG: set[str] = {"borrador", "generado", "aplicado"}

TRANSICIONES_CONFIG: dict[str, set[str]] = {
    "borrador": {"generado"},
    "generado": {"aplicado", "borrador"},
    "aplicado": set(),  # terminal
}


class DisponibilidadDocente(BaseModel):
    id: int | None = None
    usuario_id: int = Field(gt=0)
    dia_semana: str
    franja_orden: int = Field(ge=1)
    disponible: bool = True

    @field_validator("dia_semana", mode="before")
    @classmethod
    def validar_dia(cls, v: str) -> str:
        """El día de la disponibilidad debe pertenecer a DIAS_VALIDOS."""
        v = str(v).strip()
        if v not in DIAS_VALIDOS:
            raise ValueError(f"dia_semana inválido: '{v}'. Válidos: {DIAS_VALIDOS}.")
        return v


class ConfigGeneracion(BaseModel):
    id: int | None = None
    nombre: str
    periodo_id: int = Field(gt=0)
    anio_id: int = Field(gt=0)
    plantilla_id: int = Field(gt=0)
    estado: str = "borrador"
    grupos: list[int] = Field(default_factory=list)
    pesos: PesosGeneracion = Field(default_factory=PesosGeneracion)
    escenario_destino_id: int | None = None
    restricciones: dict = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        """Normaliza el nombre de la configuración y exige que no esté vacío."""
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre no puede estar vacío.")
        return v

    @field_validator("estado", mode="before")
    @classmethod
    def validar_estado(cls, v: str) -> str:
        """El estado debe ser uno de ESTADOS_CONFIG (borrador/generado/aplicado)."""
        if v not in ESTADOS_CONFIG:
            raise ValueError(f"estado inválido: {v!r}")
        return v

    def puede_transicionar_a(self, nuevo: str) -> bool:
        """True si el estado destino es alcanzable desde el actual según TRANSICIONES_CONFIG."""
        return nuevo in TRANSICIONES_CONFIG.get(self.estado, set())


class NuevaDisponibilidadDTO(BaseModel):
    usuario_id: int
    dia_semana: str
    franja_orden: int
    disponible: bool = True

    def to_modelo(self) -> DisponibilidadDocente:
        """Construye una DisponibilidadDocente a partir de los datos del DTO."""
        return DisponibilidadDocente(**self.model_dump())


class NuevaConfigGeneracionDTO(BaseModel):
    nombre: str
    periodo_id: int
    anio_id: int
    plantilla_id: int
    grupos: list[int] = Field(default_factory=list)
    pesos: PesosGeneracion = Field(default_factory=PesosGeneracion)
    restricciones: dict = Field(default_factory=dict)

    def to_config(self) -> ConfigGeneracion:
        """Construye una ConfigGeneracion a partir de los datos del DTO."""
        return ConfigGeneracion(**self.model_dump())


# =============================================================================
# Generador de horarios (paso_15c)
# =============================================================================


class BloqueGeneradoDTO(BaseModel):
    """Un bloque colocado por el generador en una franja lectiva concreta."""

    asignacion_id: int
    grupo_id: int
    usuario_id: int
    dia_semana: str
    franja_orden: int
    hora_inicio: str
    hora_fin: str
    sala: str = "Aula"
    sala_id: int | None = None  # None = sala "Aula" legacy


class MetricasCalidadDTO(BaseModel):
    """Métricas de calidad blanda de una solución del generador (paso_15d)."""

    huecos_grupo: int = 0  # ventanas vacías intra-día de los grupos
    huecos_docente: int = 0  # ventanas vacías intra-día de los docentes
    solapes_distribucion: int = 0  # exceso de bloques de una misma asignación el mismo día
    dias_docente: int = 0  # suma de días distintos trabajados por todos los docentes
    costo_inicial: float = 0.0
    costo_final: float = 0.0
    pasos_mejora: int = 0


class ResultadoGeneracionDTO(BaseModel):
    """Resultado de una corrida del generador de horarios v1."""

    escenario_id: int | None = None
    total_requeridos: int = 0  # suma de horas_semanales de las asignaciones
    colocados: int = 0
    no_colocados: int = 0
    bloques: list[BloqueGeneradoDTO] = []
    incidencias: list[str] = []  # motivos de lo no colocado
    valido: bool = False  # analizar_lote.todo_ok del lote final
    metricas: MetricasCalidadDTO | None = None
    causas: dict[str, int] = Field(default_factory=dict)  # {"sin_sala": 3, "tope_docente": 1}
    relajadas: list[str] = Field(default_factory=list)  # restricciones relajadas por infactibilidad
    total_slots: int = 0
    grupos_procesados: int = 0
    demanda_por_grupo: dict[str, int] = Field(default_factory=dict)
    metodo_usado: str = ""
    presupuesto_agotado: bool = False


# =============================================================================
# Restricciones configurables (paso_17)
# =============================================================================


class VentanaGrupo(BaseModel):
    """Restringe a qué franjas puede asignarse un grupo/grado."""

    id: int | None = None
    grupo_id: int | None = None  # None = aplica por grado
    grado: int | None = None  # None = aplica a grupo_id específico
    franjas_permitidas: list[int]  # lista de franja_orden permitidos

    @model_validator(mode="after")
    def validar_exclusividad(self) -> VentanaGrupo:
        """La ventana aplica a grupo_id XOR grado: exige exactamente uno de los dos."""
        if self.grupo_id is None and self.grado is None:
            raise ValueError("VentanaGrupo requiere grupo_id o grado.")
        if self.grupo_id is not None and self.grado is not None:
            raise ValueError("VentanaGrupo no puede tener grupo_id y grado simultáneamente.")
        return self


class BloqueAnclado(BaseModel):
    """Un bloque pre-colocado que el motor debe respetar."""

    id: int | None = None
    escenario_id: int
    asignacion_id: int
    dia_semana: str
    franja_orden: int = Field(ge=1)
    sala_id: int | None = None

    @field_validator("dia_semana", mode="before")
    @classmethod
    def validar_dia(cls, v: str) -> str:
        """El día del bloque anclado debe pertenecer a DIAS_VALIDOS."""
        v = str(v).strip()
        if v not in DIAS_VALIDOS:
            raise ValueError(f"dia_semana inválido: '{v}'.")
        return v


class FranjaReunion(BaseModel):
    """Franja reservada para reunión de un conjunto de docentes."""

    id: int | None = None
    nombre: str
    docentes: list[int]  # lista de usuario_id
    dia_semana: str
    franja_orden: int = Field(ge=1)
    modo: str = "preferente"  # "estricta" | "preferente"
    institucion_id: int | None = None

    @field_validator("dia_semana", mode="before")
    @classmethod
    def validar_dia(cls, v: str) -> str:
        """El día de la franja de reunión debe pertenecer a DIAS_VALIDOS."""
        v = str(v).strip()
        if v not in DIAS_VALIDOS:
            raise ValueError(f"dia_semana inválido: '{v}'.")
        return v

    @field_validator("modo", mode="before")
    @classmethod
    def validar_modo(cls, v: str) -> str:
        """El modo de la reunión debe ser 'estricta' o 'preferente'."""
        v = str(v).strip().lower()
        if v not in {"estricta", "preferente"}:
            raise ValueError(f"modo inválido: '{v}'. Use 'estricta' o 'preferente'.")
        return v

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        """Normaliza el nombre de la franja de reunión y exige que no esté vacío."""
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre de la franja de reunión no puede estar vacío.")
        return v


class LimitesDocente(BaseModel):
    """Límites de carga diaria por docente (amplía carga_horaria_max en usuario)."""

    id: int | None = None
    usuario_id: int = Field(gt=0)
    min_horas_dia: int = Field(default=0, ge=0)
    max_horas_dia: int = Field(default=8, ge=1)

    @model_validator(mode="after")
    def validar_rango(self) -> LimitesDocente:
        """El mínimo de horas diarias no puede superar el máximo del docente."""
        if self.min_horas_dia > self.max_horas_dia:
            raise ValueError(
                f"min_horas_dia ({self.min_horas_dia}) no puede ser mayor "
                f"que max_horas_dia ({self.max_horas_dia})."
            )
        return self


# =============================================================================
# Plan de estudios (paso_19)
# =============================================================================


class PlanEstudios(BaseModel):
    """Horas semanales de una asignatura para un grado específico."""

    id: int | None = None
    grado: int = Field(ge=1, le=13)
    asignatura_id: int = Field(gt=0)
    horas_semanales: int = Field(ge=1, le=40)
    institucion_id: int | None = None


# =============================================================================
# DTOs
# =============================================================================


class NuevaAreaDTO(BaseModel):
    nombre: str
    codigo: str | None = None

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        """Normaliza el nombre y exige que no esté vacío."""
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre no puede estar vacío.")
        return v

    def to_area(self) -> AreaConocimiento:
        """Construye un AreaConocimiento a partir de los datos del DTO."""
        return AreaConocimiento(**self.model_dump())


class NuevaAsignaturaDTO(BaseModel):
    nombre: str
    codigo: str | None = None
    area_id: int | None = None
    horas_semanales: int = 1
    tipo_sala_requerido: str | None = None
    bloque_doble: bool = False
    horas_consecutivas: int = Field(default=1, ge=1)
    institucion_id: int | None = None  # paso_29: lo resuelve el servicio si falta

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        """Normaliza el nombre y exige que no esté vacío."""
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre no puede estar vacío.")
        return v

    def to_asignatura(self) -> Asignatura:
        """Construye una Asignatura a partir de los datos del DTO."""
        return Asignatura(**self.model_dump())


class NuevoGrupoDTO(BaseModel):
    codigo: str
    nombre: str | None = None
    grado: int | None = None
    jornada: Jornada = Jornada.UNICA
    capacidad_maxima: int = 40
    institucion_id: int | None = None  # paso_29: lo resuelve el servicio si falta

    @field_validator("codigo", mode="before")
    @classmethod
    def validar_codigo(cls, v: str) -> str:
        """Normaliza el código a mayúsculas y exige que no esté vacío."""
        v = str(v).strip().upper()
        if not v:
            raise ValueError("El código no puede estar vacío.")
        return v

    def to_grupo(self) -> Grupo:
        """Construye un Grupo a partir de los datos del DTO."""
        return Grupo(**self.model_dump())


# =============================================================================
# Sala (paso_17)
# =============================================================================


class Sala(BaseModel):
    """Sala o espacio físico donde se dictan clases."""

    id: int | None = None
    nombre: str
    tipo: str = "aula"  # "aula" | "laboratorio" | "computo" | "ed_fisica" | "otro"
    capacidad: int = Field(default=30, ge=1)
    institucion_id: int | None = None  # paso_32: lo resuelve el servicio si falta

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        """Normaliza el nombre de la sala y exige que no esté vacío."""
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre de la sala no puede estar vacío.")
        return v

    @field_validator("tipo", mode="before")
    @classmethod
    def validar_tipo(cls, v: str) -> str:
        """El tipo de sala debe ser uno de aula/laboratorio/computo/ed_fisica/otro."""
        v = str(v).strip().lower()
        tipos = {"aula", "laboratorio", "computo", "ed_fisica", "otro"}
        if v not in tipos:
            raise ValueError(f"tipo inválido: '{v}'. Use uno de {sorted(tipos)}.")
        return v


class NuevaSalaDTO(BaseModel):
    nombre: str
    tipo: str = "aula"
    capacidad: int = 30

    def to_sala(self) -> Sala:
        """Construye una Sala a partir de los datos del DTO."""
        return Sala(**self.model_dump())


class NuevoHorarioDTO(BaseModel):
    grupo_id: int
    asignatura_id: int
    usuario_id: int
    escenario_id: int
    periodo_id: int | None = None
    dia_semana: DiaSemana
    hora_inicio: time
    hora_fin: time
    asignacion_id: int | None = None
    sala: str = "Aula"

    @field_validator("hora_inicio", "hora_fin", mode="before")
    @classmethod
    def parsear_hora(cls, v: time | str) -> time:
        """Acepta un time o string 'HH:MM' y lo convierte a datetime.time."""
        if isinstance(v, time):
            return v
        partes = str(v).strip().split(":")
        return time(int(partes[0]), int(partes[1]))

    @model_validator(mode="after")
    def validar_horas(self) -> Self:
        """Invariante temporal: la hora de inicio debe ser anterior a la de fin."""
        if self.hora_inicio >= self.hora_fin:
            raise ValueError("hora_inicio debe ser anterior a hora_fin.")
        return self

    def to_horario(self) -> Horario:
        """Construye un Horario a partir de los datos del DTO."""
        return Horario(**self.model_dump())


class NuevoLogroDTO(BaseModel):
    asignacion_id: int
    periodo_id: int
    descripcion: str
    orden: int = 0

    @field_validator("descripcion", mode="before")
    @classmethod
    def validar_descripcion(cls, v: str) -> str:
        """Normaliza la descripción y exige que no esté vacía."""
        v = str(v).strip()
        if not v:
            raise ValueError("La descripción no puede estar vacía.")
        return v

    def to_logro(self) -> Logro:
        """Construye un Logro a partir de los datos del DTO."""
        return Logro(**self.model_dump())


# =============================================================================
# Modelos de lectura (read models desde JOINs)
# =============================================================================


class HorarioInfo(BaseModel):
    """
    Vista enriquecida de un bloque horario con nombres resueltos por JOIN.

    Equivalente a AsignacionInfo para el módulo de horarios. No se persiste:
    lo construye el repositorio desde una consulta con JOINs sobre grupos,
    asignaturas, usuarios y periodos.

    El grid de la página de horarios consume este modelo directamente.
    Los nombres de campo son los que el repositorio mapea desde las columnas
    del JOIN; la página v2.0 los usa sin transformación adicional.
    """

    id: int
    grupo_id: int
    grupo_codigo: str  # grupos.codigo
    asignatura_id: int
    asignatura_nombre: str  # asignaturas.nombre
    usuario_id: int
    docente_nombre: str  # usuarios.nombre_completo
    asignacion_id: int | None
    periodo_id: int | None
    periodo_nombre: str  # periodos.nombre (puede ser '' si no hay periodo)
    escenario_id: int
    dia_semana: DiaSemana
    hora_inicio: time
    hora_fin: time
    sala: str = "Aula"

    @field_validator("grupo_codigo", "asignatura_nombre", "docente_nombre", mode="before")
    @classmethod
    def no_vacio(cls, v: str) -> str:
        """Normaliza los nombres resueltos por JOIN; ninguno puede quedar vacío."""
        v = str(v).strip()
        if not v:
            raise ValueError("El campo no puede estar vacío.")
        return v

    @field_validator("periodo_nombre", mode="before")
    @classmethod
    def limpiar_periodo_nombre(cls, v: str | None) -> str:
        """Normaliza el nombre de periodo; None se representa como cadena vacía."""
        if v is None:
            return ""
        return str(v).strip()

    @field_validator("hora_inicio", "hora_fin", mode="before")
    @classmethod
    def parsear_hora(cls, v: time | str) -> time:
        """Acepta un time o string 'HH:MM' y lo convierte a datetime.time."""
        if isinstance(v, time):
            return v
        partes = str(v).strip().split(":")
        if len(partes) < 2:
            raise ValueError(f"Formato de hora inválido: '{v}'. Use HH:MM.")
        try:
            return time(int(partes[0]), int(partes[1]))
        except ValueError as e:
            raise ValueError(f"Hora fuera de rango: '{v}'.") from e

    # ------------------------------------------------------------------
    # Propiedades de display
    # ------------------------------------------------------------------

    @property
    def franja_display(self) -> str:
        """'Lunes 07:00–07:55'"""
        return (
            f"{self.dia_semana.value} "
            f"{self.hora_inicio.strftime('%H:%M')}–"
            f"{self.hora_fin.strftime('%H:%M')}"
        )

    @property
    def duracion_minutos(self) -> int:
        """Duración del bloque en minutos."""
        inicio = self.hora_inicio.hour * 60 + self.hora_inicio.minute
        fin = self.hora_fin.hour * 60 + self.hora_fin.minute
        return fin - inicio

    @property
    def display_completo(self) -> str:
        """
        Descripción completa para encabezados de horario:
        '601 | Matemáticas | Carlos López | Lunes 07:00–07:55'
        """
        return (
            f"{self.grupo_codigo} | {self.asignatura_nombre} | "
            f"{self.docente_nombre} | {self.franja_display}"
        )

    @property
    def display_corto(self) -> str:
        """Para chips o tooltips: 'Lunes 07:00–07:55 — Matemáticas'"""
        return f"{self.franja_display} — {self.asignatura_nombre}"


class HorarioEstadisticasDTO(BaseModel):
    """
    Métricas del horario maestro para el panel de estadísticas.

    El servicio calcula estos valores a partir de queries de agregación;
    la página los muestra directamente sin lógica adicional.
    """

    total_bloques: int = 0  # filas totales en horarios
    grupos_cubiertos: int = 0  # grupos con al menos un bloque
    materias_cargadas: int = 0  # asignaturas distintas con horario
    docentes_con_horario: int = 0  # docentes con al menos un bloque


class CupoDTO(BaseModel):
    usadas: int
    maximas: int | None = None

    @property
    def disponibles(self) -> int | None:
        """Cupos libres (máximas − usadas); None si no hay tope definido."""
        if self.maximas is None:
            return None
        return max(0, self.maximas - self.usadas)

    @property
    def excedido(self) -> bool:
        """True si las usadas superan el máximo; False si no hay tope."""
        if self.maximas is None:
            return False
        return self.usadas > self.maximas


# =============================================================================
# DTO plan de estudios (paso_19)
# =============================================================================


class NuevoPlanEstudiosDTO(BaseModel):
    grado: int = Field(ge=1, le=13)
    asignatura_id: int = Field(gt=0)
    horas_semanales: int = Field(ge=1, le=40)


# =============================================================================
# DTOs de carga masiva
# =============================================================================


class FilaReporteDTO(BaseModel):
    indice: int
    ok: bool
    motivo: str | None = None
    resumen: str = ""


class ReporteLoteDTO(BaseModel):
    filas: list[FilaReporteDTO] = []
    # Cruces de sala detectados con salas_bloquean=False (paso_17 T1): no
    # invalidan la fila, pero se listan para que la UI los muestre.
    avisos: list[str] = []

    @property
    def validas(self) -> int:
        """Número de filas del lote marcadas como válidas (ok=True)."""
        return sum(1 for f in self.filas if f.ok)

    @property
    def invalidas(self) -> int:
        """Número de filas del lote marcadas como inválidas (ok=False)."""
        return sum(1 for f in self.filas if not f.ok)

    @property
    def todo_ok(self) -> bool:
        """True solo si hay filas y todas son válidas."""
        return bool(self.filas) and all(f.ok for f in self.filas)


class ResultadoLoteDTO(BaseModel):
    creados: int = 0
    omitidos: int = 0
    reporte: ReporteLoteDTO


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "DIAS_VALIDOS",
    "ESTADOS_CONFIG",
    "PESOS_DEFAULT",
    "TRANSICIONES_CONFIG",
    "AreaConocimiento",
    "Asignatura",
    "BloqueAnclado",
    # paso_15c
    "BloqueGeneradoDTO",
    "ConfigGeneracion",
    # mejora_07-T6
    "ConfiguracionGradoInstitucion",
    "CupoDTO",
    "DiaSemana",
    "DisponibilidadDocente",
    "EscenarioHorario",
    "FilaReporteDTO",
    "Franja",
    "FranjaReunion",
    "Grado",
    "Grupo",
    "Horario",
    "HorarioEstadisticasDTO",
    "HorarioInfo",
    "Jornada",
    "LimitesDocente",
    "Logro",
    # paso_15d
    "MetricasCalidadDTO",
    "NuevaAreaDTO",
    "NuevaAsignaturaDTO",
    "NuevaConfigGeneracionDTO",
    "NuevaDisponibilidadDTO",
    "NuevaFranjaDTO",
    "NuevaPlantillaFranjaDTO",
    "NuevaSalaDTO",
    "NuevoEscenarioDTO",
    "NuevoGrupoDTO",
    "NuevoHorarioDTO",
    "NuevoLogroDTO",
    "NuevoPlanEstudiosDTO",
    # paso_15b
    "PesosGeneracion",
    # paso_19
    "PlanEstudios",
    "PlantillaFranja",
    "ReporteLoteDTO",
    "ResultadoGeneracionDTO",
    "ResultadoLoteDTO",
    # paso_17
    "Sala",
    "VentanaGrupo",
]
