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
              ResultadoEstudianteDTO

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
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from pydantic import Field, computed_field, field_validator

from src.domain.models.base import DTODominio, EntidadDominio
from src.domain.models.decimal_types import QUANT_NOTA, QUANT_PESO, NotaDecimal, PesoDecimal

# =============================================================================
# Enumeraciones
# =============================================================================


class EstadoActividad(StrEnum):
    BORRADOR = "borrador"
    PUBLICADA = "publicada"
    CERRADA = "cerrada"


class TipoPuntosExtra(StrEnum):
    COMPORTAMENTAL = "comportamental"
    PARTICIPACION = "participacion"
    ACADEMICO = "academico"


class ModoSIEE(StrEnum):
    """
    Define cómo se distribuyen las categorías de evaluación en la institución.

    LIBRE              — sin restricciones; cada docente configura todo (modo legacy).
    INSTITUCIONAL_FIJO — el admin fija todas las categorías con pesos inamovibles;
                         el docente solo crea actividades dentro de ellas.
    MIXTO_SUBCATEGORIAS— el admin define categorías macro (ej. Ser 10%, Saber 40%, Hacer 50%);
                         el docente puede crear sub-categorías dentro de las marcadas
                         con `permite_subcategorias=True`.
    MIXTO_AUTONOMIA    — el admin fija un porcentaje institucional y reserva un
                         `porcentaje_autonomia_docente`; el docente distribuye
                         libremente ese porcentaje restante con sus propias categorías.
    """

    LIBRE = "libre"
    INSTITUCIONAL_FIJO = "institucional_fijo"
    MIXTO_SUBCATEGORIAS = "mixto_subcategorias"
    MIXTO_AUTONOMIA = "mixto_autonomia"


# =============================================================================
# Entidades
# =============================================================================


class ConfiguracionSIEE(EntidadDominio):
    """
    Configuración del Sistema Institucional de Evaluación (SIEE) para un año lectivo.

    Decide el modo de distribución de categorías de evaluación:
      - LIBRE              → docentes configuran todo (comportamiento por defecto).
      - INSTITUCIONAL_FIJO → admin fija todas las categorías; docentes solo añaden actividades.
      - MIXTO_SUBCATEGORIAS→ admin fija macro-categorías; docentes sub-categorizan
                             las que tienen `permite_subcategorias=True`.
      - MIXTO_AUTONOMIA    → admin fija parte del peso; docentes gestionan `porcentaje_autonomia_docente`.

    `porcentaje_autonomia_docente` es obligatorio si modo == MIXTO_AUTONOMIA.
    """

    id: int | None = None
    anio_id: int
    modo: ModoSIEE = ModoSIEE.LIBRE
    porcentaje_autonomia_docente: PesoDecimal | None = None  # solo para MIXTO_AUTONOMIA

    @field_validator("anio_id")
    @classmethod
    def validar_anio_id(cls, v: int) -> int:
        """El año lectivo referenciado (FK) debe ser positivo."""
        if v <= 0:
            raise ValueError(f"anio_id debe ser positivo (recibido: {v}).")
        return v

    @field_validator("porcentaje_autonomia_docente")
    @classmethod
    def validar_porcentaje(cls, v: Decimal | None) -> Decimal | None:
        """Si se define, la autonomía docente debe estar en (0, 1.0] (fracción, no porcentaje)."""
        if v is not None and not (0 < v <= Decimal("1")):
            raise ValueError(
                f"porcentaje_autonomia_docente debe estar entre 0 (exclusivo) y 1.0 "
                f"(recibido: {v}). Use 0.30 para representar 30%."
            )
        return v

    @computed_field
    @property
    def peso_institucional(self) -> Decimal | None:
        """
        Peso total reservado para categorías institucionales en MIXTO_AUTONOMIA.
        Retorna None si el modo no aplica.
        """
        if self.modo != ModoSIEE.MIXTO_AUTONOMIA or self.porcentaje_autonomia_docente is None:
            return None
        return (Decimal("1") - self.porcentaje_autonomia_docente).quantize(
            QUANT_PESO, rounding=ROUND_HALF_UP
        )


class Categoria(EntidadDominio):
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

    Categorías institucionales (es_institucional=True):
      - Las crea el admin en la configuración SIEE del año.
      - `anio_id` está presente; `asignacion_id` y `periodo_id` son None.
      - El servicio las "proyecta" a cada asignación+periodo al primer acceso.

    Sub-categorías (categoria_padre_id IS NOT NULL):
      - Solo en modo MIXTO_SUBCATEGORIAS.
      - Son categorías de docente que viven dentro de una institucional
        con `permite_subcategorias=True`.
    """

    id: int | None = None
    nombre: str
    peso: PesoDecimal  # 0 < peso <= 1.0
    asignacion_id: int | None = None
    periodo_id: int | None = None
    anio_id: int | None = None  # solo para institucionales
    es_institucional: bool = False
    permite_subcategorias: bool = False
    categoria_padre_id: int | None = None

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        """Normaliza el nombre de la categoría; exige no vacío y ≤100 caracteres."""
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre de la categoría no puede estar vacío.")
        if len(v) > 100:
            raise ValueError(f"El nombre no puede exceder 100 caracteres (tiene {len(v)}).")
        return v

    @field_validator("peso")
    @classmethod
    def validar_peso(cls, v: Decimal) -> Decimal:
        """El peso de la categoría debe estar en (0, 1.0] (escala 0-1, no porcentaje)."""
        if not (0 < v <= Decimal("1")):
            raise ValueError(
                f"El peso debe estar entre 0 (exclusivo) y 1.0 (inclusivo) "
                f"(recibido: {v}). Use 0.40 para representar 40%."
            )
        return v

    @field_validator("asignacion_id", "periodo_id", "anio_id", "categoria_padre_id")
    @classmethod
    def validar_id_opcional(cls, v: int | None) -> int | None:
        """Cada FK opcional, si está presente, debe ser un id positivo."""
        if v is not None and v <= 0:
            raise ValueError(f"El ID debe ser positivo (recibido: {v}).")
        return v

    @computed_field
    @property
    def peso_porcentaje(self) -> Decimal:
        """Peso en porcentaje: 0.40 → 40.00"""
        return (self.peso * 100).quantize(QUANT_NOTA, rounding=ROUND_HALF_UP)

    @computed_field
    @property
    def es_docente(self) -> bool:
        """True si la categoría pertenece a un docente (no es institucional)."""
        return not self.es_institucional


class Actividad(EntidadDominio):
    """
    Actividad evaluativa: un taller, examen, proyecto, quiz, etc.
    Pertenece a una categoría y tiene notas por estudiante.

    Estado:
      borrador  → solo el docente la ve; los estudiantes no
      publicada → visible para los estudiantes; se pueden ingresar notas
      cerrada   → no acepta más notas (el periodo fue cerrado)
    """

    id: int | None = None
    nombre: str
    descripcion: str | None = None
    fecha: date | None = None
    valor_maximo: NotaDecimal = Decimal("100.00")
    estado: EstadoActividad = EstadoActividad.BORRADOR
    categoria_id: int

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        """Normaliza el nombre de la actividad; exige no vacío y ≤150 caracteres."""
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre de la actividad no puede estar vacío.")
        if len(v) > 150:
            raise ValueError(f"El nombre no puede exceder 150 caracteres (tiene {len(v)}).")
        return v

    @field_validator("valor_maximo")
    @classmethod
    def validar_valor_maximo(cls, v: float) -> float:
        """El valor máximo de la actividad debe ser positivo."""
        if v <= 0:
            raise ValueError(f"El valor máximo debe ser positivo (recibido: {v}).")
        return v

    @field_validator("descripcion", mode="before")
    @classmethod
    def limpiar_descripcion(cls, v: str | None) -> str | None:
        """Normaliza la descripción opcional (strip); cadena vacía → None."""
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None

    @field_validator("fecha", mode="before")
    @classmethod
    def parsear_fecha(cls, v: date | str | None) -> date | None:
        """Acepta un date o string ISO ('YYYY-MM-DD') y lo convierte a date."""
        if v is None:
            return None
        if isinstance(v, str):
            return date.fromisoformat(v)
        return v

    @field_validator("categoria_id")
    @classmethod
    def validar_id(cls, v: int) -> int:
        """La categoría dueña de la actividad debe referenciarse con id positivo."""
        if v <= 0:
            raise ValueError(f"categoria_id debe ser positivo (recibido: {v}).")
        return v

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @computed_field
    @property
    def esta_publicada(self) -> bool:
        """True si la actividad está en estado PUBLICADA."""
        return self.estado == EstadoActividad.PUBLICADA

    @computed_field
    @property
    def acepta_notas(self) -> bool:
        """Alias de esta_publicada. Solo las actividades PUBLICADAS aceptan notas."""
        return self.esta_publicada

    # ------------------------------------------------------------------
    # Transiciones de estado
    # ------------------------------------------------------------------

    def publicar(self) -> Actividad:
        """Borrador → Publicada."""
        if self.estado != EstadoActividad.BORRADOR:
            raise ValueError(
                f"Solo se puede publicar una actividad en borrador. "
                f"Estado actual: '{self.estado.value}'."
            )
        return self.model_copy(update={"estado": EstadoActividad.PUBLICADA})

    def cerrar(self) -> Actividad:
        """Publicada → Cerrada."""
        if self.estado != EstadoActividad.PUBLICADA:
            raise ValueError(
                f"Solo se puede cerrar una actividad publicada. "
                f"Estado actual: '{self.estado.value}'."
            )
        return self.model_copy(update={"estado": EstadoActividad.CERRADA})

    def reabrir(self) -> Actividad:
        """Cerrada → Publicada (permite volver a registrar notas)."""
        if self.estado != EstadoActividad.CERRADA:
            raise ValueError(
                f"Solo se puede reabrir una actividad cerrada. "
                f"Estado actual: '{self.estado.value}'."
            )
        return self.model_copy(update={"estado": EstadoActividad.PUBLICADA})


class Nota(EntidadDominio):
    """
    Calificación de un estudiante en una actividad específica.

    El valor se almacena en escala 0-100, independientemente del
    valor_maximo de la actividad. El docente puede ingresar 7.5/10
    y el sistema almacena 75.0.
    """

    id: int | None = None
    estudiante_id: int
    actividad_id: int
    valor: NotaDecimal
    usuario_registro_id: int | None = None
    fecha_registro: datetime = Field(default_factory=datetime.now)

    @field_validator("estudiante_id", "actividad_id")
    @classmethod
    def validar_id(cls, v: int) -> int:
        """Las FK de la nota (estudiante y actividad) deben ser positivas."""
        if v <= 0:
            raise ValueError(f"El ID debe ser positivo (recibido: {v}).")
        return v

    @field_validator("valor")
    @classmethod
    def validar_valor(cls, v: Decimal) -> Decimal:
        """La nota debe estar en el rango 0-100."""
        if not (0 <= v <= 100):
            raise ValueError(f"La nota debe estar entre 0 y 100 (recibido: {v}).")
        return v

    @computed_field
    @property
    def es_aprobatoria(self) -> bool:
        """True si el valor alcanza la nota mínima aprobatoria (60.0)."""
        return self.valor >= 60


class PuntosExtra(EntidadDominio):
    """
    Puntos adicionales que afectan la nota o el comportamiento.

    tipo distingue la naturaleza del ajuste:
      comportamental → afecta la nota de convivencia
      participacion  → bonificación por participación en clase
      academico      → ajuste directo sobre la nota académica

    El impacto numérico de los puntos sobre la nota definitiva
    lo define el servicio según la configuración institucional.
    """

    id: int | None = None
    estudiante_id: int
    asignacion_id: int
    periodo_id: int
    tipo: TipoPuntosExtra = TipoPuntosExtra.COMPORTAMENTAL
    positivos: int = Field(default=0, ge=0)
    negativos: int = Field(default=0, ge=0)
    observacion: str | None = None
    fecha_actualizacion: datetime = Field(default_factory=datetime.now)

    @field_validator("estudiante_id", "asignacion_id", "periodo_id")
    @classmethod
    def validar_id(cls, v: int) -> int:
        """Las FK (estudiante, asignación, periodo) deben ser positivas."""
        if v <= 0:
            raise ValueError(f"El ID debe ser positivo (recibido: {v}).")
        return v

    @field_validator("observacion", mode="before")
    @classmethod
    def limpiar_observacion(cls, v: str | None) -> str | None:
        """Normaliza la observación opcional (strip); cadena vacía → None."""
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None

    @computed_field
    @property
    def balance(self) -> int:
        """Diferencia neta entre puntos positivos y negativos."""
        return self.positivos - self.negativos

    @computed_field
    @property
    def tiene_impacto(self) -> bool:
        """True si hay al menos un punto positivo o negativo registrado."""
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
    def _to_nota_map(notas: list[Nota] | dict[int, Decimal]) -> dict[int, Decimal]:
        """Normaliza notas a dict {actividad_id: valor}, aceptando ambos formatos."""
        if isinstance(notas, dict):
            return {k: (v if isinstance(v, Decimal) else Decimal(str(v))) for k, v in notas.items()}
        return {n.actividad_id: n.valor for n in notas}

    @staticmethod
    def calcular_definitiva(
        notas: list[Nota] | dict[int, Decimal],
        actividades: list[Actividad],
        categorias: list[Categoria],
    ) -> Decimal:
        """
        Calcula la nota definitiva del periodo.

        Algoritmo:
          1. Para cada categoría, calcular el promedio de todas sus
             actividades. Si una actividad no tiene nota, cuenta como 0.
          2. Ponderar cada promedio de categoría por su peso.
          3. Retornar la suma ponderada cuantizada a 2 decimales (ROUND_HALF_UP).

        Args:
            notas:       todas las notas del estudiante en la asignación
            actividades: todas las actividades de las categorías
            categorias:  todas las categorías de la asignación+periodo

        Returns:
            Nota definitiva en escala 0-100 como Decimal exacto.
        """
        if not categorias:
            return Decimal("0.00")

        # Índices para búsqueda O(1)
        cat_map: dict[int, Categoria] = {c.id: c for c in categorias if c.id}
        nota_map: dict[int, Decimal] = CalculadorNotas._to_nota_map(notas)

        # Actividades por categoría
        acts_por_cat: dict[int, list[int]] = {}
        for act in actividades:
            if act.id and act.categoria_id in cat_map:
                acts_por_cat.setdefault(act.categoria_id, []).append(act.id)

        definitiva = Decimal("0")
        for cat in categorias:
            if not cat.id:
                continue
            act_ids = acts_por_cat.get(cat.id, [])
            if not act_ids:
                # Categoría sin actividades: su peso cuenta como 0
                continue
            promedio_cat = sum(
                (nota_map.get(aid, Decimal("0")) for aid in act_ids),
                Decimal("0"),
            ) / len(act_ids)
            definitiva += promedio_cat * cat.peso

        return definitiva.quantize(QUANT_NOTA, rounding=ROUND_HALF_UP)

    @staticmethod
    def calcular_definitiva_con_corte(
        notas: list[Nota] | dict[int, Decimal],
        actividades: list[Actividad],
        categorias: list[Categoria],
        nota_definitiva_plan: Decimal,
        categoria_ids_en_corte: set[int],
    ) -> Decimal:
        """
        Calcula la nota definitiva cuando hay un Plan de Mejoramiento activo.

        Algoritmo aditivo (compatible hacia atrás):
          nota_definitiva = nota_definitiva_plan
                          + Σ(cat.peso × promedio_cat)
                            para cat NOT IN categoria_ids_en_corte

        Args:
            notas:                  Notas del estudiante (puede ser lista de Nota
                                    o dict {actividad_id: valor}).
            actividades:            Todas las actividades de la asignación+periodo.
            categorias:             Todas las categorías de la asignación+periodo.
            nota_definitiva_plan:   Contribución congelada del corte (ya es
                                    escala 0-100 proporcional al peso del corte).
            categoria_ids_en_corte: IDs de las categorías ya incluidas en el corte.
                                    Estas se excluyen del cálculo posterior.

        Returns:
            Nota definitiva total en escala 0-100 como Decimal exacto.
        """
        if not isinstance(nota_definitiva_plan, Decimal):
            nota_definitiva_plan = Decimal(str(nota_definitiva_plan))
        if not categorias:
            return nota_definitiva_plan.quantize(QUANT_NOTA, rounding=ROUND_HALF_UP)

        cat_map: dict[int, Categoria] = {c.id: c for c in categorias if c.id}
        nota_map: dict[int, Decimal] = CalculadorNotas._to_nota_map(notas)

        acts_por_cat: dict[int, list[int]] = {}
        for act in actividades:
            if act.id and act.categoria_id in cat_map:
                acts_por_cat.setdefault(act.categoria_id, []).append(act.id)

        # Solo categorías que NO estuvieron en el corte
        cats_post_corte = [c for c in categorias if c.id and c.id not in categoria_ids_en_corte]

        aporte_post = Decimal("0")
        for cat in cats_post_corte:
            act_ids = acts_por_cat.get(cat.id, [])
            if not act_ids:
                continue
            promedio_cat = sum(
                (nota_map.get(aid, Decimal("0")) for aid in act_ids),
                Decimal("0"),
            ) / len(act_ids)
            aporte_post += promedio_cat * cat.peso

        return (nota_definitiva_plan + aporte_post).quantize(QUANT_NOTA, rounding=ROUND_HALF_UP)

    @staticmethod
    def calcular_promedio_ajustado(
        notas: list[Nota] | dict[int, Decimal],
        actividades: list[Actividad],
        categorias: list[Categoria],
        hasta_fecha: date | None = None,
    ) -> Decimal:
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
            Promedio ajustado en escala 0-100 como Decimal exacto. Decimal("0.00") si no hay nada evaluado.
        """
        if not categorias:
            return Decimal("0.00")

        corte = hasta_fecha or date.today()
        nota_map: dict[int, Decimal] = CalculadorNotas._to_nota_map(notas)

        # Filtrar actividades con fecha <= corte que tienen nota
        acts_evaluadas: dict[int, list[Decimal]] = {}
        for act in actividades:
            if act.id is None:
                continue
            tiene_fecha = act.fecha is not None and act.fecha <= corte
            tiene_nota = act.id in nota_map
            tiene_estado = act.estado in (EstadoActividad.PUBLICADA, EstadoActividad.CERRADA)
            if (tiene_fecha or not act.fecha) and tiene_nota and tiene_estado:
                acts_evaluadas.setdefault(act.categoria_id, []).append(nota_map[act.id])

        # Categorías con al menos una actividad evaluada
        cats_con_datos = [c for c in categorias if c.id and c.id in acts_evaluadas]
        if not cats_con_datos:
            return Decimal("0.00")

        # Renormalizar pesos para que sumen 1.0
        peso_total = sum((c.peso for c in cats_con_datos), Decimal("0"))
        if peso_total <= 0:
            return Decimal("0.00")

        promedio = Decimal("0")
        for cat in cats_con_datos:
            valores = acts_evaluadas[cat.id]
            promedio_cat = sum(valores, Decimal("0")) / len(valores)
            peso_ajustado = cat.peso / peso_total
            promedio += promedio_cat * peso_ajustado

        return promedio.quantize(QUANT_NOTA, rounding=ROUND_HALF_UP)

    @staticmethod
    def pesos_validos(categorias: list[Categoria]) -> bool:
        """
        True si la suma de pesos de las categorías es exactamente <= 1.0.
        Con Decimal no se necesita margen de tolerancia.
        """
        if not categorias:
            return True
        return CalculadorNotas.peso_total(categorias) <= Decimal("1")

    @staticmethod
    def peso_total(categorias: list[Categoria]) -> Decimal:
        """Suma exacta de pesos de las categorías (aritmética Decimal)."""
        return sum((c.peso for c in categorias), Decimal("0"))


# =============================================================================
# Lógica de desempeño — umbrales del sistema educativo colombiano
# =============================================================================

#: Umbrales de clasificación según el Decreto 1290 (MEN, Colombia).
#: Escala numérica 1.0–5.0; cada institución puede ajustar estos valores
#: mediante su PEI, pero estos son los umbrales típicos del sector público.
_UMBRALES_DESEMPENO: list[tuple[float, str]] = [
    (3.0, "Bajo"),
    (3.8, "Básico"),
    (4.6, "Alto"),
    (float("inf"), "Superior"),
]


def nivel_desempeno(nota: float) -> str:
    """
    Clasifica una nota numérica en un nivel de desempeño académico.

    Escala colombiana 1.0–5.0 según el Decreto 1290 del MEN:
      - [1.0, 3.0) → "Bajo"
      - [3.0, 3.8) → "Básico"
      - [3.8, 4.6) → "Alto"
      - [4.6, 5.0] → "Superior"

    Args:
        nota: Nota numérica en escala 1.0–5.0.

    Returns:
        Cadena con el nivel de desempeño correspondiente.

    Note:
        Los umbrales están definidos en ``_UMBRALES_DESEMPENO`` para
        facilitar su ajuste institucional sin dispersión de literales.
    """
    for limite, nivel in _UMBRALES_DESEMPENO:
        if nota < limite:
            return nivel
    return "Superior"  # fallback explícito para nota == 5.0


# =============================================================================
# DTOs
# =============================================================================


class NuevaConfiguracionSIEEDTO(DTODominio):
    """Datos para crear o reemplazar la configuración SIEE de un año."""

    anio_id: int
    modo: ModoSIEE = ModoSIEE.LIBRE
    porcentaje_autonomia_docente: PesoDecimal | None = None

    @field_validator("anio_id")
    @classmethod
    def validar_anio_id(cls, v: int) -> int:
        """El año lectivo referenciado (FK) debe ser positivo."""
        if v <= 0:
            raise ValueError(f"anio_id debe ser positivo (recibido: {v}).")
        return v

    @field_validator("porcentaje_autonomia_docente")
    @classmethod
    def validar_porcentaje(cls, v: Decimal | None) -> Decimal | None:
        """Si se define, la autonomía docente debe estar en (0, 1.0]."""
        if v is not None and not (0 < v <= Decimal("1")):
            raise ValueError(
                f"porcentaje_autonomia_docente debe estar entre 0 y 1.0 (recibido: {v})."
            )
        return v

    def to_configuracion_siee(self) -> ConfiguracionSIEE:
        """Construye una ConfiguracionSIEE a partir de los datos del DTO."""
        return ConfiguracionSIEE(**self.model_dump())


class NuevaCategoriaInstitucionalDTO(DTODominio):
    """
    Datos para crear una categoría institucional en la configuración SIEE.

    Las categorías institucionales se definen a nivel de año (no de asignación+periodo).
    El servicio las proyecta automáticamente a cada asignación+periodo cuando
    el docente accede por primera vez a su planilla.
    """

    nombre: str
    peso: PesoDecimal
    anio_id: int
    permite_subcategorias: bool = False

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        """Normaliza el nombre; exige no vacío y ≤100 caracteres."""
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre no puede estar vacío.")
        if len(v) > 100:
            raise ValueError(f"El nombre no puede exceder 100 caracteres (tiene {len(v)}).")
        return v

    @field_validator("peso")
    @classmethod
    def validar_peso(cls, v: Decimal) -> Decimal:
        """El peso institucional debe estar en (0, 1.0]."""
        if not (0 < v <= Decimal("1")):
            raise ValueError(f"El peso debe estar entre 0 (exclusivo) y 1.0 (recibido: {v}).")
        return v

    @field_validator("anio_id")
    @classmethod
    def validar_anio_id(cls, v: int) -> int:
        """El año lectivo referenciado (FK) debe ser positivo."""
        if v <= 0:
            raise ValueError(f"anio_id debe ser positivo (recibido: {v}).")
        return v

    def to_categoria(self) -> Categoria:
        """Construye la Categoria institucional (es_institucional=True) del DTO."""
        return Categoria(
            nombre=self.nombre,
            peso=self.peso,
            anio_id=self.anio_id,
            es_institucional=True,
            permite_subcategorias=self.permite_subcategorias,
        )


class NuevaCategoriaDTO(DTODominio):
    """Datos para crear una categoría de evaluación de docente."""

    nombre: str
    peso: PesoDecimal
    asignacion_id: int
    periodo_id: int
    categoria_padre_id: int | None = None  # solo en modo MIXTO_SUBCATEGORIAS

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        """Normaliza el nombre y exige que no esté vacío."""
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre no puede estar vacío.")
        return v

    @field_validator("peso")
    @classmethod
    def validar_peso(cls, v: Decimal) -> Decimal:
        """El peso de la categoría debe estar en (0, 1.0]."""
        if not (0 < v <= Decimal("1")):
            raise ValueError(f"El peso debe estar entre 0 (exclusivo) y 1.0 (recibido: {v}).")
        return v

    def to_categoria(self) -> Categoria:
        """Construye una Categoria de docente a partir de los datos del DTO."""
        return Categoria(**self.model_dump())


class ActualizarCategoriaDTO(DTODominio):
    """Campos actualizables de una categoría."""

    nombre: str | None = None
    peso: PesoDecimal | None = None

    @field_validator("peso")
    @classmethod
    def validar_peso(cls, v: Decimal | None) -> Decimal | None:
        """Si se actualiza el peso, debe permanecer en (0, 1.0]."""
        if v is not None and not (0 < v <= Decimal("1")):
            raise ValueError(f"El peso debe estar entre 0 y 1.0 (recibido: {v}).")
        return v

    def aplicar_a(self, categoria: Categoria) -> Categoria:
        """Devuelve una copia de la categoría con solo los campos no nulos del DTO aplicados."""
        cambios = {k: v for k, v in self.model_dump().items() if v is not None}
        return categoria.model_copy(update=cambios) if cambios else categoria


class NuevaActividadDTO(DTODominio):
    """Datos para crear una actividad evaluativa."""

    nombre: str
    categoria_id: int
    descripcion: str | None = None
    fecha: date | None = None
    valor_maximo: NotaDecimal = Decimal("100.00")
    estado: EstadoActividad = EstadoActividad.BORRADOR

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        """Normaliza el nombre y exige que no esté vacío."""
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre no puede estar vacío.")
        return v

    @field_validator("valor_maximo")
    @classmethod
    def validar_valor(cls, v: Decimal) -> Decimal:
        """El valor máximo de la actividad debe ser positivo."""
        if v <= 0:
            raise ValueError(f"El valor máximo debe ser positivo (recibido: {v}).")
        return v

    def to_actividad(self) -> Actividad:
        """Construye una Actividad a partir de los datos del DTO."""
        return Actividad(**self.model_dump())


class ActualizarActividadDTO(DTODominio):
    """Campos actualizables de una actividad."""

    nombre: str | None = None
    descripcion: str | None = None
    fecha: date | None = None
    valor_maximo: NotaDecimal | None = None

    def aplicar_a(self, actividad: Actividad) -> Actividad:
        """Aplica los campos no nulos a la actividad; rechaza si está CERRADA."""
        if actividad.estado == EstadoActividad.CERRADA:
            raise ValueError("No se puede modificar una actividad cerrada.")
        cambios = {k: v for k, v in self.model_dump().items() if v is not None}
        return actividad.model_copy(update=cambios) if cambios else actividad


class RegistrarNotaDTO(DTODominio):
    """Datos para registrar la nota de un único estudiante."""

    estudiante_id: int
    actividad_id: int
    valor: NotaDecimal
    usuario_registro_id: int | None = None

    @field_validator("valor")
    @classmethod
    def validar_valor(cls, v: Decimal) -> Decimal:
        """La nota debe estar en el rango 0-100."""
        if not (0 <= v <= 100):
            raise ValueError(f"La nota debe estar entre 0 y 100 (recibido: {v}).")
        return v

    def to_nota(self, usuario_registro_id: int | None = None) -> Nota:
        """Construye una Nota del DTO, fijando el usuario que la registra si se indica."""
        data = self.model_dump()
        if usuario_registro_id is not None:
            data["usuario_registro_id"] = usuario_registro_id
        return Nota(**data)


class RegistrarNotasMasivasDTO(DTODominio):
    """
    Registra notas para múltiples estudiantes en una misma actividad.
    Operación del ag-grid de la planilla de notas.
    """

    actividad_id: int
    notas: list[RegistrarNotaDTO] = Field(default_factory=list)
    usuario_registro_id: int | None = None

    @field_validator("actividad_id")
    @classmethod
    def validar_id(cls, v: int) -> int:
        """La actividad destino del registro masivo debe tener id positivo."""
        if v <= 0:
            raise ValueError(f"actividad_id debe ser positivo (recibido: {v}).")
        return v

    @computed_field
    @property
    def total_notas(self) -> int:
        """Cantidad de notas incluidas en el registro masivo."""
        return len(self.notas)

    def to_notas(self, usuario_registro_id: int | None = None) -> list[Nota]:
        """Convierte la lista de RegistrarNotaDTO a entidades Nota listas para persistir."""
        uid = usuario_registro_id or self.usuario_registro_id
        return [dto.to_nota(usuario_registro_id=uid) for dto in self.notas]


class ResultadoEstudianteDTO(DTODominio):
    """
    Resumen de notas de un estudiante en una asignación.
    Consumido por la planilla de notas y el informe de calificaciones.
    """

    estudiante_id: int
    nombre_completo: str
    notas: dict[int, Decimal] = Field(default_factory=dict)
    # {actividad_id: valor}
    definitiva: NotaDecimal = Decimal("0.00")
    promedio_ajustado: NotaDecimal = Decimal("0.00")
    posee_piar: bool = False


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "Actividad",
    "ActualizarActividadDTO",
    "ActualizarCategoriaDTO",
    # Lógica pura
    "CalculadorNotas",
    "Categoria",
    # Entidades
    "ConfiguracionSIEE",
    # Enums
    "EstadoActividad",
    "ModoSIEE",
    "Nota",
    "NuevaActividadDTO",
    "NuevaCategoriaDTO",
    "NuevaCategoriaInstitucionalDTO",
    # DTOs
    "NuevaConfiguracionSIEEDTO",
    "PuntosExtra",
    "RegistrarNotaDTO",
    "RegistrarNotasMasivasDTO",
    "ResultadoEstudianteDTO",
    "TipoPuntosExtra",
]
