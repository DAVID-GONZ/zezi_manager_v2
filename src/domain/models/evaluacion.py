"""
Modelo de dominio: Evaluación
==============================

Contiene:
  Enums    — EstadoActividad, TipoPuntosExtra
  Entidades — Categoria, Actividad, Nota, PuntosExtra
  Lógica pura — CalculadorNotas
  DTOs     — NuevaCategoriaDTO, ActualizarCategoriaDTO,
              NuevaActividadDTO, ActualizarActividadDTO,
              RegistrarNotaDTO, RegistrarNotasMasivasDTO,
              ResultadoEstudianteDTO, FiltroNotasDTO

El corazón de este módulo es CalculadorNotas:
  calcular_definitiva()
    Promedio ponderado completo: todas las actividades, las no calificadas
    cuentan como 0. Usado para el cierre de periodo.

  calcular_promedio_ajustado(hasta_fecha)
    Solo considera actividades con fecha <= hasta_fecha Y que tienen nota.
    Muestra dónde está el estudiante HOY respecto a lo evaluado.
    Las categorías sin actividades evaluadas se excluyen y los pesos
    se renormalizan para que sumen 100%.
    Usado en el panel de seguimiento y en la planilla de notas.

  pesos_validos(categorias)
    La suma de pesos de todas las categorías de una asignación+periodo
    no puede exceder 1.0 (100%). Margen de 0.001 para flotantes.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# Enumeraciones
# =============================================================================

class EstadoActividad(str, Enum):
    BORRADOR  = "borrador"
    PUBLICADA = "publicada"
    CERRADA   = "cerrada"


class TipoPuntosExtra(str, Enum):
    COMPORTAMENTAL = "comportamental"
    PARTICIPACION  = "participacion"
    ACADEMICO      = "academico"


# =============================================================================
# Entidades
# =============================================================================

class Categoria(BaseModel):
    """
    Categoría de evaluación: agrupa actividades y define su peso
    en la nota definitiva del periodo.

    El peso está en escala 0-1 (no 0-100):
      peso=0.40 → 40% de la nota
    Esto es consistente con el schema (peso REAL NOT NULL CHECK(peso > 0 AND peso <= 1)).

    La suma de pesos de todas las categorías de una asignación+periodo
    debe ser <= 1.0. Esta invariante la verifica el trigger de BD y el
    método CalculadorNotas.pesos_validos(). El modelo valida solo el
    rango individual (> 0 y <= 1).
    """
    id:            int | None  = None
    nombre:        str
    peso:          float        # 0 < peso <= 1.0
    asignacion_id: int
    periodo_id:    int

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre de la categoría no puede estar vacío.")
        if len(v) > 100:
            raise ValueError(
                f"El nombre no puede exceder 100 caracteres (tiene {len(v)})."
            )
        return v

    @field_validator("peso")
    @classmethod
    def validar_peso(cls, v: float) -> float:
        if not (0 < v <= 1.0):
            raise ValueError(
                f"El peso debe estar entre 0 (exclusivo) y 1.0 (inclusivo) "
                f"(recibido: {v}). Use 0.40 para representar 40%."
            )
        return round(v, 4)

    @field_validator("asignacion_id", "periodo_id")
    @classmethod
    def validar_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"El ID debe ser positivo (recibido: {v}).")
        return v

    @property
    def peso_porcentaje(self) -> float:
        """Peso en porcentaje: 0.40 → 40.0"""
        return round(self.peso * 100, 2)


class Actividad(BaseModel):
    """
    Actividad evaluativa: un taller, examen, proyecto, quiz, etc.
    Pertenece a una categoría y tiene notas por estudiante.

    Estado:
      borrador  → solo el docente la ve; los estudiantes no
      publicada → visible para los estudiantes; se pueden ingresar notas
      cerrada   → no acepta más notas (el periodo fue cerrado)
    """
    id:            int | None        = None
    nombre:        str
    descripcion:   str | None        = None
    fecha:         date | None       = None
    valor_maximo:  float             = 100.0
    estado:        EstadoActividad   = EstadoActividad.BORRADOR
    categoria_id:  int

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre de la actividad no puede estar vacío.")
        if len(v) > 150:
            raise ValueError(
                f"El nombre no puede exceder 150 caracteres (tiene {len(v)})."
            )
        return v

    @field_validator("valor_maximo")
    @classmethod
    def validar_valor_maximo(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(
                f"El valor máximo debe ser positivo (recibido: {v})."
            )
        return v

    @field_validator("descripcion", mode="before")
    @classmethod
    def limpiar_descripcion(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None

    @field_validator("fecha", mode="before")
    @classmethod
    def parsear_fecha(cls, v: date | str | None) -> date | None:
        if v is None:
            return None
        if isinstance(v, str):
            return date.fromisoformat(v)
        return v

    @field_validator("categoria_id")
    @classmethod
    def validar_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"categoria_id debe ser positivo (recibido: {v}).")
        return v

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def esta_publicada(self) -> bool:
        return self.estado == EstadoActividad.PUBLICADA

    @property
    def acepta_notas(self) -> bool:
        return self.estado == EstadoActividad.PUBLICADA

    # ------------------------------------------------------------------
    # Transiciones de estado
    # ------------------------------------------------------------------

    def publicar(self) -> "Actividad":
        """Borrador → Publicada."""
        if self.estado != EstadoActividad.BORRADOR:
            raise ValueError(
                f"Solo se puede publicar una actividad en borrador. "
                f"Estado actual: '{self.estado.value}'."
            )
        return self.model_copy(update={"estado": EstadoActividad.PUBLICADA})

    def cerrar(self) -> "Actividad":
        """Publicada → Cerrada."""
        if self.estado != EstadoActividad.PUBLICADA:
            raise ValueError(
                f"Solo se puede cerrar una actividad publicada. "
                f"Estado actual: '{self.estado.value}'."
            )
        return self.model_copy(update={"estado": EstadoActividad.CERRADA})


class Nota(BaseModel):
    """
    Calificación de un estudiante en una actividad específica.

    El valor se almacena en escala 0-100, independientemente del
    valor_maximo de la actividad. El docente puede ingresar 7.5/10
    y el sistema almacena 75.0.
    """
    id:                  int | None  = None
    estudiante_id:       int
    actividad_id:        int
    valor:               float
    usuario_registro_id: int | None  = None
    fecha_registro:      datetime    = Field(default_factory=datetime.now)

    @field_validator("estudiante_id", "actividad_id")
    @classmethod
    def validar_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"El ID debe ser positivo (recibido: {v}).")
        return v

    @field_validator("valor")
    @classmethod
    def validar_valor(cls, v: float) -> float:
        if not (0 <= v <= 100):
            raise ValueError(
                f"La nota debe estar entre 0 y 100 (recibido: {v})."
            )
        return round(v, 2)

    @property
    def es_aprobatoria(self, nota_minima: float = 60.0) -> bool:
        return self.valor >= nota_minima


class PuntosExtra(BaseModel):
    """
    Puntos adicionales que afectan la nota o el comportamiento.

    tipo distingue la naturaleza del ajuste:
      comportamental → afecta la nota de convivencia
      participacion  → bonificación por participación en clase
      academico      → ajuste directo sobre la nota académica

    El impacto numérico de los puntos sobre la nota definitiva
    lo define el servicio según la configuración institucional.
    """
    id:                  int | None      = None
    estudiante_id:       int
    asignacion_id:       int
    periodo_id:          int
    tipo:                TipoPuntosExtra = TipoPuntosExtra.COMPORTAMENTAL
    positivos:           int             = Field(default=0, ge=0)
    negativos:           int             = Field(default=0, ge=0)
    observacion:         str | None      = None
    fecha_actualizacion: datetime        = Field(default_factory=datetime.now)

    @field_validator("estudiante_id", "asignacion_id", "periodo_id")
    @classmethod
    def validar_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"El ID debe ser positivo (recibido: {v}).")
        return v

    @field_validator("observacion", mode="before")
    @classmethod
    def limpiar_observacion(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None

    @property
    def balance(self) -> int:
        return self.positivos - self.negativos

    @property
    def tiene_impacto(self) -> bool:
        return self.positivos > 0 or self.negativos > 0


# =============================================================================
# Lógica de cálculo — pura, sin SQL, sin NiceGUI
# =============================================================================

class CalculadorNotas:
    """
    Lógica de cálculo de notas definitivas y promedios.
    Todas sus operaciones son métodos estáticos: no guardan estado.
    Reciben colecciones de entidades del dominio y retornan valores.

    Responsabilidad:
      - calcular_definitiva: promedio ponderado final (para cierres)
      - calcular_promedio_ajustado: promedio con actividades evaluadas
        hasta una fecha (para seguimiento en tiempo real)
      - pesos_validos / peso_total: validación de configuración

    No es responsabilidad de este calculador:
      - Consultar datos de la BD (eso es el repositorio)
      - Determinar si una nota es aprobatoria (eso usa nota_minima
        de configuracion_anio, y lo hace el servicio)
    """

    @staticmethod
    def calcular_definitiva(
        notas:       list[Nota],
        actividades: list[Actividad],
        categorias:  list[Categoria],
    ) -> float:
        """
        Calcula la nota definitiva del periodo.

        Algoritmo:
          1. Para cada categoría, calcular el promedio de todas sus
             actividades. Si una actividad no tiene nota, cuenta como 0.
          2. Ponderar cada promedio de categoría por su peso.
          3. Retornar la suma ponderada redondeada a 2 decimales.

        Args:
            notas:       todas las notas del estudiante en la asignación
            actividades: todas las actividades de las categorías
            categorias:  todas las categorías de la asignación+periodo

        Returns:
            Nota definitiva en escala 0-100.
        """
        if not categorias:
            return 0.0

        # Índices para búsqueda O(1)
        cat_map: dict[int, Categoria] = {c.id: c for c in categorias if c.id}
        act_map: dict[int, Actividad] = {a.id: a for a in actividades if a.id}
        nota_map: dict[int, float]    = {n.actividad_id: n.valor for n in notas}

        # Actividades por categoría
        acts_por_cat: dict[int, list[int]] = {}
        for act in actividades:
            if act.id and act.categoria_id in cat_map:
                acts_por_cat.setdefault(act.categoria_id, []).append(act.id)

        definitiva = 0.0
        for cat in categorias:
            if not cat.id:
                continue
            act_ids = acts_por_cat.get(cat.id, [])
            if not act_ids:
                # Categoría sin actividades: su peso cuenta como 0
                continue
            promedio_cat = sum(nota_map.get(aid, 0.0) for aid in act_ids) / len(act_ids)
            definitiva  += promedio_cat * cat.peso

        return round(definitiva, 2)

    @staticmethod
    def calcular_promedio_ajustado(
        notas:       list[Nota],
        actividades: list[Actividad],
        categorias:  list[Categoria],
        hasta_fecha: date | None = None,
    ) -> float:
        """
        Calcula el promedio ajustado a una fecha dada.

        Solo considera actividades con fecha <= hasta_fecha que tienen
        nota registrada. Las categorías sin actividades evaluadas se
        excluyen y sus pesos se renormalizan.

        Esto responde la pregunta: "Si cerráramos el periodo HOY,
        ¿cuál sería la nota del estudiante?"

        Args:
            notas:       notas registradas del estudiante
            actividades: actividades de la asignación
            categorias:  categorías de la asignación+periodo
            hasta_fecha: fecha de corte (default: hoy)

        Returns:
            Promedio ajustado en escala 0-100. 0.0 si no hay nada evaluado.
        """
        if not categorias:
            return 0.0

        corte = hasta_fecha or date.today()
        nota_map: dict[int, float] = {n.actividad_id: n.valor for n in notas}

        # Filtrar actividades con fecha <= corte que tienen nota
        acts_evaluadas: dict[int, list[float]] = {}
        for act in actividades:
            if act.id is None:
                continue
            tiene_fecha   = act.fecha is not None and act.fecha <= corte
            tiene_nota    = act.id in nota_map
            tiene_estado  = act.estado in (EstadoActividad.PUBLICADA,
                                           EstadoActividad.CERRADA)
            if (tiene_fecha or not act.fecha) and tiene_nota and tiene_estado:
                acts_evaluadas.setdefault(act.categoria_id, []).append(nota_map[act.id])

        # Categorías con al menos una actividad evaluada
        cats_con_datos = [
            c for c in categorias
            if c.id and c.id in acts_evaluadas
        ]
        if not cats_con_datos:
            return 0.0

        # Renormalizar pesos para que sumen 1.0
        peso_total = sum(c.peso for c in cats_con_datos)
        if peso_total <= 0:
            return 0.0

        promedio = 0.0
        for cat in cats_con_datos:
            valores = acts_evaluadas[cat.id]
            promedio_cat   = sum(valores) / len(valores)
            peso_ajustado  = cat.peso / peso_total
            promedio      += promedio_cat * peso_ajustado

        return round(promedio, 2)

    @staticmethod
    def pesos_validos(categorias: list[Categoria]) -> bool:
        """
        True si la suma de pesos de las categorías es <= 1.0.
        Margen de 0.001 para errores de redondeo de flotantes.
        """
        if not categorias:
            return True
        return CalculadorNotas.peso_total(categorias) <= 1.001

    @staticmethod
    def peso_total(categorias: list[Categoria]) -> float:
        """Suma de pesos de las categorías, redondeada a 4 decimales."""
        return round(sum(c.peso for c in categorias), 4)


# =============================================================================
# DTOs
# =============================================================================

class NuevaCategoriaDTO(BaseModel):
    """Datos para crear una categoría de evaluación."""
    nombre:        str
    peso:          float
    asignacion_id: int
    periodo_id:    int

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre no puede estar vacío.")
        return v

    @field_validator("peso")
    @classmethod
    def validar_peso(cls, v: float) -> float:
        if not (0 < v <= 1.0):
            raise ValueError(
                f"El peso debe estar entre 0 (exclusivo) y 1.0 (recibido: {v})."
            )
        return round(v, 4)

    def to_categoria(self) -> Categoria:
        return Categoria(**self.model_dump())


class ActualizarCategoriaDTO(BaseModel):
    """Campos actualizables de una categoría."""
    nombre: str | None  = None
    peso:   float | None = None

    @field_validator("peso")
    @classmethod
    def validar_peso(cls, v: float | None) -> float | None:
        if v is not None and not (0 < v <= 100.0):
            raise ValueError(f"El peso debe estar entre 0 y 100.0 (recibido: {v}).")
        return v

    def aplicar_a(self, categoria: Categoria) -> Categoria:
        cambios = {k: v for k, v in self.model_dump().items() if v is not None}
        return categoria.model_copy(update=cambios) if cambios else categoria


class NuevaActividadDTO(BaseModel):
    """Datos para crear una actividad evaluativa."""
    nombre:       str
    categoria_id: int
    descripcion:  str | None   = None
    fecha:        date | None  = None
    valor_maximo: float        = 100.0
    estado:       EstadoActividad = EstadoActividad.BORRADOR

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre no puede estar vacío.")
        return v

    @field_validator("valor_maximo")
    @classmethod
    def validar_valor(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(f"El valor máximo debe ser positivo (recibido: {v}).")
        return v

    def to_actividad(self) -> Actividad:
        return Actividad(**self.model_dump())


class ActualizarActividadDTO(BaseModel):
    """Campos actualizables de una actividad."""
    nombre:       str | None   = None
    descripcion:  str | None   = None
    fecha:        date | None  = None
    valor_maximo: float | None = None

    def aplicar_a(self, actividad: Actividad) -> Actividad:
        if actividad.estado == EstadoActividad.CERRADA:
            raise ValueError("No se puede modificar una actividad cerrada.")
        cambios = {k: v for k, v in self.model_dump().items() if v is not None}
        return actividad.model_copy(update=cambios) if cambios else actividad


class RegistrarNotaDTO(BaseModel):
    """Datos para registrar la nota de un único estudiante."""
    estudiante_id:       int
    actividad_id:        int
    valor:               float
    usuario_registro_id: int | None = None

    @field_validator("valor")
    @classmethod
    def validar_valor(cls, v: float) -> float:
        if not (0 <= v <= 100):
            raise ValueError(f"La nota debe estar entre 0 y 100 (recibido: {v}).")
        return round(v, 2)

    def to_nota(self) -> Nota:
        return Nota(**self.model_dump())


class RegistrarNotasMasivasDTO(BaseModel):
    """
    Registra notas para múltiples estudiantes en una misma actividad.
    Operación del ag-grid de la planilla de notas.
    """
    actividad_id:        int
    notas:               list[RegistrarNotaDTO] = Field(default_factory=list)
    usuario_registro_id: int | None             = None

    @field_validator("actividad_id")
    @classmethod
    def validar_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"actividad_id debe ser positivo (recibido: {v}).")
        return v

    @property
    def total_notas(self) -> int:
        return len(self.notas)


class ResultadoEstudianteDTO(BaseModel):
    """
    Resumen de notas de un estudiante en una asignación.
    Consumido por la planilla de notas y el informe de calificaciones.
    """
    estudiante_id:      int
    nombre_completo:    str
    notas:              dict[int, float]  = Field(default_factory=dict)
    # {actividad_id: valor}
    definitiva:         float             = 0.0
    promedio_ajustado:  float             = 0.0
    posee_piar:         bool              = False


class FiltroNotasDTO(BaseModel):
    """Parámetros para consultar notas."""
    asignacion_id:  int
    periodo_id:     int
    estudiante_id:  int | None = None
    actividad_id:   int | None = None


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Enums
    "EstadoActividad",
    "TipoPuntosExtra",
    # Entidades
    "Categoria",
    "Actividad",
    "Nota",
    "PuntosExtra",
    # Lógica pura
    "CalculadorNotas",
    # DTOs
    "NuevaCategoriaDTO",
    "ActualizarCategoriaDTO",
    "NuevaActividadDTO",
    "ActualizarActividadDTO",
    "RegistrarNotaDTO",
    "RegistrarNotasMasivasDTO",
    "ResultadoEstudianteDTO",
    "FiltroNotasDTO",
]