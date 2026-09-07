"""
Test: datos_03_computed_fields
================================
Verifica que:
  T1 — el inventario de propiedades está catalogado y @computed_field
       preserva el acceso sin paréntesis (R8 de conventions.md §8).
  T2 — la serialización de 500 Estudiante con computed_fields no supera 3 s.
  T4 — las 7 propiedades del Grupo C (dependientes de fecha) en scope
       funcionan correctamente con fecha congelada.
  T5 — las propiedades del Grupo B (display) NO aparecen en model_dump().
  T6 — los computed_fields NO son campos de entrada.
"""

from __future__ import annotations

import time
from datetime import date, datetime
from datetime import time as time_type
from unittest.mock import patch

import pytest

# =============================================================================
# T1 — Inventario como datos (no como comentarios)
# =============================================================================

# Grupo A: reglas de negocio puras → convertidas a @computed_field
GRUPO_A: list[tuple[str, str, str]] = [
    # (módulo, clase, propiedad)
    ("acudiente", "Acudiente", "esta_activo"),
    ("acudiente", "Acudiente", "tiene_contacto"),
    ("alerta", "ConfiguracionAlerta", "umbral_entero"),
    ("alerta", "ConfiguracionAlerta", "notifica_a_alguien"),
    ("alerta", "Alerta", "esta_pendiente"),
    ("alerta", "Alerta", "es_critica"),
    ("asignacion", "Asignacion", "esta_activa"),
    ("asistencia", "ControlDiario", "es_presencia_efectiva"),
    ("asistencia", "ControlDiario", "requiere_justificacion"),
    ("asistencia", "ResumenAsistenciaDTO", "porcentaje_asistencia"),
    ("asistencia", "ResumenAsistenciaDTO", "total_faltas"),
    ("asistencia", "ResumenAsistenciaDTO", "en_riesgo_por_faltas"),
    ("asistencia", "RegistrarAsistenciaMasivaDTO", "total_estudiantes"),
    ("auditoria", "EventoSesion", "es_exitoso"),
    ("auditoria", "EventoSesion", "es_fallido"),
    ("auditoria", "EventoSesion", "es_acceso_denegado"),
    ("auditoria", "RegistroCambio", "anterior_como_dict"),
    ("auditoria", "RegistroCambio", "nuevo_como_dict"),
    ("auditoria", "RegistroCambio", "es_creacion"),
    ("auditoria", "RegistroCambio", "es_eliminacion"),
    ("cierre", "CierreAnio", "tiene_habilitacion"),
    ("cierre", "CierreAnio", "mejoro_con_habilitacion"),
    ("cierre", "PromocionAnual", "esta_pendiente"),
    ("cierre", "PromocionAnual", "esta_finalizado"),
    ("cierre", "PromocionAnual", "fue_promovido"),
    ("cierre", "PromocionAnual", "fue_reprobado"),
    ("cierre", "PromocionAnual", "es_condicional"),
    ("configuracion", "ConfiguracionAnio", "duracion_semanas"),
    ("configuracion", "ConfiguracionAnio", "tiene_informacion_institucional"),
    ("configuracion", "ConfiguracionAnio", "aprobacion_en_rango"),
    ("configuracion", "NivelDesempeno", "amplitud"),
    ("convivencia", "RegistroComportamiento", "es_negativo"),
    ("convivencia", "RegistroComportamiento", "es_positivo"),
    ("convivencia", "RegistroComportamiento", "pendiente_notificacion"),
    ("convivencia", "RegistroComportamiento", "tiene_seguimiento"),
    ("convivencia", "NotaComportamiento", "aprobado"),
    ("dtos", "ContextoAcademicoDTO", "tiene_grupo"),
    ("dtos", "ContextoAcademicoDTO", "tiene_asignacion"),
    ("dtos", "ContextoAcademicoDTO", "contexto_completo"),
    ("dtos", "DashboardMetricsDTO", "pct_en_riesgo"),
    ("dtos", "MatriculaMasivaDTO", "total_filas"),
    ("dtos", "MatriculaMasivaResultadoDTO", "tasa_exito"),
    ("dtos", "MatriculaMasivaResultadoDTO", "fue_exitosa"),
    ("estudiante", "Estudiante", "nombre_completo"),
    ("estudiante", "Estudiante", "es_activo"),
    ("estudiante", "Estudiante", "puede_recibir_calificaciones"),
    ("estudiante", "Estudiante", "requiere_atencion_diferencial"),
    ("evaluacion", "ConfiguracionSIEE", "peso_institucional"),
    ("evaluacion", "Categoria", "peso_porcentaje"),
    ("evaluacion", "Categoria", "es_docente"),
    ("evaluacion", "Actividad", "esta_publicada"),
    ("evaluacion", "Actividad", "acepta_notas"),
    ("evaluacion", "Nota", "es_aprobatoria"),
    ("evaluacion", "PuntosExtra", "balance"),
    ("evaluacion", "PuntosExtra", "tiene_impacto"),
    ("evaluacion", "RegistrarNotasMasivasDTO", "total_notas"),
    ("habilitacion", "Habilitacion", "esta_pendiente"),
    ("habilitacion", "Habilitacion", "fue_realizada"),
    ("habilitacion", "Habilitacion", "tiene_resultado_final"),
    ("habilitacion", "Habilitacion", "mejoro_nota"),
    ("habilitacion", "PlanMejoramiento", "esta_activo"),
    ("habilitacion", "PlanMejoramiento", "esta_cerrado"),
    ("habilitacion", "PlanMejoramiento", "tiene_seguimiento_programado"),
    ("infraestructura", "Horario", "duracion_minutos"),
    ("infraestructura", "Franja", "es_lectiva"),
    ("infraestructura", "HorarioInfo", "duracion_minutos"),
    ("infraestructura", "CupoDTO", "disponibles"),
    ("infraestructura", "CupoDTO", "excedido"),
    ("infraestructura", "ReporteLoteDTO", "validas"),
    ("infraestructura", "ReporteLoteDTO", "invalidas"),
    ("infraestructura", "ReporteLoteDTO", "todo_ok"),
    ("nivelacion", "NotaNivelacion", "calificada"),
    ("periodo", "Periodo", "esta_abierto"),
    ("periodo", "Periodo", "esta_vigente"),
    ("periodo", "Periodo", "duracion_dias"),
    # Nota: EstadoAsistencia.es_falta y afecta_porcentaje son StrEnum
    # y no pueden convertirse a @computed_field (solo BaseModel). Se mantienen
    # como @property regulares; no aparecen en model_dump() de ningún modelo.
]

# Grupo B: propiedades de presentación → se mantienen como @property
# (nunca viajan en model_dump() ni en el JSON de la API)
GRUPO_B: list[tuple[str, str, str]] = [
    ("acudiente", "Acudiente", "contacto_display"),
    ("acudiente", "Acudiente", "documento_display"),
    ("asignacion", "AsignacionInfo", "display_completo"),
    ("asignacion", "AsignacionInfo", "display_corto"),
    ("asignacion", "AsignacionInfo", "display_docente_materia"),
    ("asistencia", "ResumenAsistenciaDTO", "resumen_display"),
    ("asistencia", "ControlDiario", "estado_descripcion"),
    ("auditoria", "EventoSesion", "fecha_display"),
    ("auditoria", "RegistroCambio", "timestamp_display"),
    ("cierre", "CierrePeriodo", "nota_display"),
    ("cierre", "CierreAnio", "nota_display"),
    ("configuracion", "ConfiguracionAnio", "anio_display"),
    ("configuracion", "ConfiguracionAnio", "rango_fechas_display"),
    ("estudiante", "Estudiante", "documento_display"),
    ("estudiante", "MovimientoEstudianteInfoDTO", "fecha_display"),
    ("estudiante", "MovimientoEstudianteInfoDTO", "ruta_display"),
    ("infraestructura", "Grupo", "descripcion_completa"),
    ("infraestructura", "Grupo", "descripcion_corta"),
    ("infraestructura", "Horario", "franja_display"),
    ("infraestructura", "HorarioInfo", "franja_display"),
    ("infraestructura", "HorarioInfo", "display_completo"),
    ("infraestructura", "HorarioInfo", "display_corto"),
    ("institucion", "Institucion", "nombre_display"),
    # Fuera de scope (usuario.py): nombre_display, resumen_carga, display
    # StrEnum no convertible: EstadoAsistencia.descripcion
]

# Grupo C en scope: dependientes de date.today() → convertidas a @computed_field
GRUPO_C_SCOPE: list[tuple[str, str, str]] = [
    ("alerta", "Alerta", "dias_pendiente"),
    ("estudiante", "Estudiante", "edad"),
    ("habilitacion", "PlanMejoramiento", "seguimiento_vencido"),
    ("habilitacion", "PlanMejoramiento", "dias_activo"),
    ("periodo", "Periodo", "en_curso"),
    ("periodo", "HitoPeriodo", "esta_vencido"),
    ("periodo", "HitoPeriodo", "dias_restantes"),
]

# Grupo C fuera de scope (piar.py — NO tocar)
GRUPO_C_FUERA_SCOPE: list[tuple[str, str, str]] = [
    ("piar", "PIAR", "revision_vencida"),
    ("piar", "PIAR", "dias_para_revision"),
]


def test_inventario_no_vacio():
    """El inventario de propiedades catalogadas es coherente."""
    assert len(GRUPO_A) > 60
    assert len(GRUPO_B) >= 20
    assert len(GRUPO_C_SCOPE) == 7
    assert len(GRUPO_C_FUERA_SCOPE) == 2


def test_computed_field_acceso_sin_parentesis():
    """
    R8 de conventions.md §8: @computed_field preserva el acceso sin paréntesis
    y los derivados aparecen en model_dump().

    Si este test falla, TODO el paso depende de resolver el supuesto.
    """
    from pydantic import BaseModel, computed_field

    class ModeloPrueba(BaseModel):
        base: int

        @computed_field
        @property
        def positivo(self) -> bool:
            return self.base > 0

        @computed_field
        @property
        def doble(self) -> int:
            return self.base * 2

    m = ModeloPrueba(base=5)

    # Acceso sin paréntesis (R8)
    assert m.positivo is True
    assert m.doble == 10

    # Viaja en model_dump() (R3)
    d = m.model_dump()
    assert "positivo" in d
    assert "doble" in d
    assert d["positivo"] is True
    assert d["doble"] == 10

    # Caso base=0 → positivo=False
    m2 = ModeloPrueba(base=0)
    assert m2.positivo is False
    assert "positivo" in m2.model_dump()


# =============================================================================
# T2 — Costo de serialización (marcado slow)
# =============================================================================


@pytest.mark.slow
def test_coste_serializacion_estudiante():
    """
    500 instancias de Estudiante deben construirse y serializar
    con model_dump() en menos de 3 segundos.
    """
    from src.domain.models.estudiante import Estudiante

    inicio = time.perf_counter()

    estudiantes = [
        Estudiante(numero_documento=str(i + 1), nombre="Ana", apellido="Gil")
        for i in range(500)
    ]
    volcados = [e.model_dump() for e in estudiantes]

    elapsed = time.perf_counter() - inicio

    assert len(volcados) == 500
    # Verifica que los computed_fields aparecen en el dump
    primer = volcados[0]
    assert "nombre_completo" in primer
    assert "es_activo" in primer
    assert elapsed < 3.0, f"Serialización tardó {elapsed:.2f}s > 3.0s"


# =============================================================================
# T4 — Grupo C: propiedades dependientes de fecha (congeladas)
# =============================================================================

_FECHA_PRUEBA = date(2026, 6, 15)
_DT_PRUEBA = datetime(2026, 6, 15, 12, 0, 0)


def test_c_alerta_dias_pendiente():
    """Alerta.dias_pendiente refleja días desde la generación (fecha congelada)."""
    from src.domain.models.alerta import Alerta, TipoAlerta

    fecha_gen = datetime(2026, 6, 1, 0, 0, 0)
    alerta = Alerta(
        estudiante_id=1,
        tipo_alerta=TipoAlerta.PROMEDIO_BAJO,
        descripcion="Test alerta",
        fecha_generacion=fecha_gen,
    )

    with patch("src.domain.models.alerta.datetime") as mock_dt:
        mock_dt.now.return_value = _DT_PRUEBA
        assert alerta.dias_pendiente == 14  # 2026-06-15 - 2026-06-01

    # Alerta resuelta → None
    alerta_resuelta = Alerta(
        estudiante_id=1,
        tipo_alerta=TipoAlerta.PROMEDIO_BAJO,
        descripcion="Resuelta",
        resuelta=True,
        fecha_resolucion=_DT_PRUEBA,
    )
    assert alerta_resuelta.dias_pendiente is None

    # Verifica que el campo aparece en model_dump()
    d = alerta.model_dump()
    assert "dias_pendiente" in d


def test_c_estudiante_edad():
    """Estudiante.edad devuelve años completos a la fecha congelada."""
    from src.domain.models.estudiante import Estudiante

    # fecha_nacimiento = 2010-03-01 → en 2026-06-15 tiene 16 años
    fecha_nac = date(2010, 3, 1)
    e = Estudiante(
        numero_documento="1",
        nombre="Ana",
        apellido="Gil",
        fecha_nacimiento=fecha_nac,
    )

    with patch("src.domain.models.estudiante.date") as mock_d:
        mock_d.today.return_value = _FECHA_PRUEBA
        # Necesario para que la resta de fechas funcione con el objeto real
        mock_d.side_effect = lambda *a, **k: date(*a, **k)
        resultado = e.edad

    # (2026-06-15 - 2010-03-01).days // 365
    assert resultado == 16

    # Sin fecha_nacimiento → None
    e2 = Estudiante(numero_documento="2", nombre="Bo", apellido="Gil")
    assert e2.edad is None

    # Verifica que viaja en model_dump()
    assert "edad" in e.model_dump()


def test_c_plan_mejoramiento_seguimiento_vencido():
    """PlanMejoramiento.seguimiento_vencido detecta fechas de seguimiento pasadas."""
    from src.domain.models.habilitacion import EstadoPlanMejoramiento, PlanMejoramiento

    inicio = date(2026, 5, 1)
    seguimiento = date(2026, 6, 10)  # anterior a _FECHA_PRUEBA (2026-06-15)

    plan = PlanMejoramiento(
        estudiante_id=1,
        asignacion_id=1,
        periodo_id=1,
        descripcion_dificultad="Test",
        actividades_propuestas="Test",
        fecha_inicio=inicio,
        fecha_seguimiento=seguimiento,
    )

    with patch("src.domain.models.habilitacion.date") as mock_d:
        mock_d.today.return_value = _FECHA_PRUEBA
        mock_d.side_effect = lambda *a, **k: date(*a, **k)
        assert plan.seguimiento_vencido is True

    # Plan cerrado → False (aunque la fecha haya pasado)
    plan_cerrado = PlanMejoramiento(
        estudiante_id=1,
        asignacion_id=1,
        periodo_id=1,
        descripcion_dificultad="Test",
        actividades_propuestas="Test",
        fecha_inicio=inicio,
        fecha_seguimiento=seguimiento,
        fecha_cierre=date(2026, 6, 12),
        estado=EstadoPlanMejoramiento.CUMPLIDO,
        observacion_cierre="Cumplido",
    )
    with patch("src.domain.models.habilitacion.date") as mock_d:
        mock_d.today.return_value = _FECHA_PRUEBA
        mock_d.side_effect = lambda *a, **k: date(*a, **k)
        assert plan_cerrado.seguimiento_vencido is False

    assert "seguimiento_vencido" in plan.model_dump()


def test_c_plan_mejoramiento_dias_activo():
    """PlanMejoramiento.dias_activo cuenta días desde fecha_inicio."""
    from src.domain.models.habilitacion import PlanMejoramiento

    inicio = date(2026, 5, 1)
    plan = PlanMejoramiento(
        estudiante_id=1,
        asignacion_id=1,
        periodo_id=1,
        descripcion_dificultad="Test",
        actividades_propuestas="Test",
        fecha_inicio=inicio,
    )

    with patch("src.domain.models.habilitacion.date") as mock_d:
        mock_d.today.return_value = _FECHA_PRUEBA  # 2026-06-15
        mock_d.side_effect = lambda *a, **k: date(*a, **k)
        # (2026-06-15 - 2026-05-01).days = 45
        assert plan.dias_activo == 45

    assert "dias_activo" in plan.model_dump()


def test_c_periodo_en_curso():
    """Periodo.en_curso es True cuando la fecha actual está dentro del rango."""
    from src.domain.models.periodo import Periodo

    inicio = date(2026, 3, 1)
    fin = date(2026, 11, 30)
    periodo = Periodo(
        anio_id=1,
        numero=1,
        nombre="P1",
        fecha_inicio=inicio,
        fecha_fin=fin,
    )

    with patch("src.domain.models.periodo.date") as mock_d:
        mock_d.today.return_value = _FECHA_PRUEBA  # dentro del rango
        mock_d.side_effect = lambda *a, **k: date(*a, **k)
        assert periodo.en_curso is True

    with patch("src.domain.models.periodo.date") as mock_d:
        mock_d.today.return_value = date(2025, 12, 1)  # antes del inicio
        mock_d.side_effect = lambda *a, **k: date(*a, **k)
        assert periodo.en_curso is False

    assert "en_curso" in periodo.model_dump()


def test_c_hito_esta_vencido():
    """HitoPeriodo.esta_vencido es True si la fecha límite ya pasó."""
    from src.domain.models.periodo import HitoPeriodo, TipoHito

    hito = HitoPeriodo(
        periodo_id=1,
        tipo=TipoHito.ENTREGA_NOTAS,
        descripcion="Entrega",
        fecha_limite=date(2026, 6, 10),  # anterior a _FECHA_PRUEBA
    )

    with patch("src.domain.models.periodo.date") as mock_d:
        mock_d.today.return_value = _FECHA_PRUEBA
        mock_d.side_effect = lambda *a, **k: date(*a, **k)
        assert hito.esta_vencido is True

    hito_futuro = HitoPeriodo(
        periodo_id=1,
        tipo=TipoHito.ENTREGA_NOTAS,
        descripcion="Futura",
        fecha_limite=date(2026, 7, 1),
    )
    with patch("src.domain.models.periodo.date") as mock_d:
        mock_d.today.return_value = _FECHA_PRUEBA
        mock_d.side_effect = lambda *a, **k: date(*a, **k)
        assert hito_futuro.esta_vencido is False

    # Sin fecha_limite → False
    hito_sin_fecha = HitoPeriodo(periodo_id=1, descripcion="Sin fecha")
    assert hito_sin_fecha.esta_vencido is False

    assert "esta_vencido" in hito.model_dump()


def test_c_hito_dias_restantes():
    """HitoPeriodo.dias_restantes calcula días que faltan (negativo si venció)."""
    from src.domain.models.periodo import HitoPeriodo, TipoHito

    hito = HitoPeriodo(
        periodo_id=1,
        tipo=TipoHito.ENTREGA_BOLETINES,
        descripcion="Boletines",
        fecha_limite=date(2026, 6, 20),
    )

    with patch("src.domain.models.periodo.date") as mock_d:
        mock_d.today.return_value = _FECHA_PRUEBA  # 2026-06-15
        mock_d.side_effect = lambda *a, **k: date(*a, **k)
        # (2026-06-20 - 2026-06-15).days = 5
        assert hito.dias_restantes == 5

    hito_vencido = HitoPeriodo(
        periodo_id=1,
        descripcion="Vencido",
        fecha_limite=date(2026, 6, 10),
    )
    with patch("src.domain.models.periodo.date") as mock_d:
        mock_d.today.return_value = _FECHA_PRUEBA
        mock_d.side_effect = lambda *a, **k: date(*a, **k)
        # (2026-06-10 - 2026-06-15).days = -5
        assert hito_vencido.dias_restantes == -5

    # Sin fecha_limite → None
    hito_sin_fecha = HitoPeriodo(periodo_id=1, descripcion="Sin fecha")
    assert hito_sin_fecha.dias_restantes is None

    assert "dias_restantes" in hito.model_dump()


# =============================================================================
# T5 — Grupo B: propiedades de presentación NO viajan en model_dump()
# =============================================================================


@pytest.mark.presentacion
def test_grupo_b_no_viaja_acudiente():
    """Acudiente: contacto_display y documento_display son @property, no @computed_field."""
    from src.domain.models.acudiente import Acudiente, Parentesco, TipoDocumentoAcudiente

    a = Acudiente(
        tipo_documento=TipoDocumentoAcudiente.CC,
        numero_documento="12345678",
        nombre_completo="Test User",
        parentesco=Parentesco.PADRE,
        celular="3001234567",
    )
    d = a.model_dump()
    assert "contacto_display" not in d
    assert "documento_display" not in d
    # Pero sí son accesibles como atributo
    assert a.contacto_display  # no vacío
    assert a.documento_display  # no vacío


@pytest.mark.presentacion
def test_grupo_b_no_viaja_asignacion_info():
    """AsignacionInfo: display_* son @property, no @computed_field."""
    from src.domain.models.asignacion import AsignacionInfo

    info = AsignacionInfo(
        asignacion_id=1,
        grupo_id=1,
        grupo_codigo="601",
        asignatura_id=1,
        asignatura_nombre="Matemáticas",
        usuario_id=1,
        docente_nombre="Carlos López",
        periodo_id=1,
        periodo_nombre="Período 1",
        periodo_numero=1,
        activo=True,
    )
    d = info.model_dump()
    for prop in ("display_completo", "display_corto", "display_docente_materia"):
        assert prop not in d, f"{prop} no debe estar en model_dump()"
        assert getattr(info, prop), f"{prop} debe ser accesible como atributo"


@pytest.mark.presentacion
def test_grupo_b_no_viaja_asistencia():
    """ResumenAsistenciaDTO.resumen_display y ControlDiario.estado_descripcion."""
    from src.domain.models.asistencia import ControlDiario, ResumenAsistenciaDTO

    res = ResumenAsistenciaDTO(estudiante_id=1, total_clases=10, presentes=8, faltas_injustificadas=2)
    d_res = res.model_dump()
    assert "resumen_display" not in d_res
    assert res.resumen_display

    ctrl = ControlDiario(estudiante_id=1, grupo_id=1, asignacion_id=1, periodo_id=1)
    d_ctrl = ctrl.model_dump()
    assert "estado_descripcion" not in d_ctrl
    assert ctrl.estado_descripcion


@pytest.mark.presentacion
def test_grupo_b_no_viaja_auditoria():
    """EventoSesion.fecha_display y RegistroCambio.timestamp_display."""
    from src.domain.models.auditoria import (
        AccionCambio,
        EventoSesion,
        RegistroCambio,
        TipoEventoSesion,
    )

    ev = EventoSesion(usuario="admin", tipo_evento=TipoEventoSesion.LOGIN_EXITOSO)
    assert "fecha_display" not in ev.model_dump()
    assert ev.fecha_display

    rc = RegistroCambio(accion=AccionCambio.CREATE, tabla="test")
    assert "timestamp_display" not in rc.model_dump()
    assert rc.timestamp_display


@pytest.mark.presentacion
def test_grupo_b_no_viaja_cierre():
    """CierrePeriodo.nota_display y CierreAnio.nota_display."""
    from src.domain.models.cierre import CierreAnio, CierrePeriodo

    cp = CierrePeriodo(
        estudiante_id=1, asignacion_id=1, periodo_id=1, nota_definitiva=75.0
    )
    assert "nota_display" not in cp.model_dump()
    assert cp.nota_display == "75.0"

    ca = CierreAnio(
        estudiante_id=1,
        asignacion_id=1,
        anio_id=1,
        nota_promedio_periodos=75.0,
        nota_definitiva_anual=75.0,
        perdio=False,
    )
    assert "nota_display" not in ca.model_dump()
    assert ca.nota_display == "75.0"


@pytest.mark.presentacion
def test_grupo_b_no_viaja_configuracion():
    """ConfiguracionAnio.anio_display y rango_fechas_display."""
    from src.domain.models.configuracion import ConfiguracionAnio

    cfg = ConfiguracionAnio(anio=2026)
    d = cfg.model_dump()
    assert "anio_display" not in d
    assert "rango_fechas_display" not in d
    assert cfg.anio_display
    assert cfg.rango_fechas_display


@pytest.mark.presentacion
def test_grupo_b_no_viaja_estudiante():
    """Estudiante.documento_display y MovimientoEstudianteInfoDTO displays."""
    from src.domain.models.estudiante import Estudiante, MovimientoEstudianteInfoDTO

    e = Estudiante(numero_documento="1", nombre="Ana", apellido="Gil")
    d = e.model_dump()
    assert "documento_display" not in d
    assert e.documento_display

    mov = MovimientoEstudianteInfoDTO(estudiante_id=1)
    d_mov = mov.model_dump()
    assert "fecha_display" not in d_mov
    assert "ruta_display" not in d_mov
    assert mov.fecha_display
    assert mov.ruta_display


@pytest.mark.presentacion
def test_grupo_b_no_viaja_infraestructura():
    """Grupo.descripcion_*, Horario.franja_display, HorarioInfo displays."""
    from src.domain.models.infraestructura import (
        DiaSemana,
        Grupo,
        Horario,
        HorarioInfo,
    )

    g = Grupo(codigo="601")
    d_g = g.model_dump()
    assert "descripcion_completa" not in d_g
    assert "descripcion_corta" not in d_g
    assert g.descripcion_completa
    assert g.descripcion_corta

    h = Horario(
        grupo_id=1,
        asignatura_id=1,
        usuario_id=1,
        escenario_id=1,
        dia_semana=DiaSemana.LUNES,
        hora_inicio=time_type(7, 0),
        hora_fin=time_type(8, 0),
    )
    assert "franja_display" not in h.model_dump()
    assert h.franja_display

    hi = HorarioInfo(
        id=1,
        grupo_id=1,
        grupo_codigo="601",
        asignatura_id=1,
        asignatura_nombre="Mate",
        usuario_id=1,
        docente_nombre="Doc",
        asignacion_id=1,
        periodo_id=1,
        periodo_nombre="P1",
        escenario_id=1,
        dia_semana=DiaSemana.LUNES,
        hora_inicio=time_type(7, 0),
        hora_fin=time_type(8, 0),
    )
    d_hi = hi.model_dump()
    for prop in ("franja_display", "display_completo", "display_corto"):
        assert prop not in d_hi, f"{prop} no debe estar en model_dump()"
        assert getattr(hi, prop), f"{prop} debe ser accesible"


@pytest.mark.presentacion
def test_grupo_b_no_viaja_institucion():
    """Institucion.nombre_display."""
    from src.domain.models.institucion import Institucion

    inst = Institucion(nombre="IESB")
    assert "nombre_display" not in inst.model_dump()
    assert inst.nombre_display


# =============================================================================
# T6 — Los computed_fields NO son campos de entrada
# =============================================================================


@pytest.mark.entrada
def test_computed_field_no_es_entrada_dto():
    """
    En DTODominio (extra='forbid'), pasar un computed_field como kwarg
    al constructor lanza ValidationError — el campo de salida no es de entrada.
    """
    import pydantic

    from src.domain.models.dtos import ContextoAcademicoDTO

    # tiene_grupo es @computed_field de ContextoAcademicoDTO
    with pytest.raises(pydantic.ValidationError):
        ContextoAcademicoDTO(
            usuario_id=1,
            anio_id=1,
            periodo_id=1,
            tiene_grupo=True,  # computed_field — no debe ser aceptado como entrada
        )


@pytest.mark.entrada
def test_computed_field_se_calcula_correctamente():
    """
    En EntidadDominio, el computed_field se calcula desde los datos base,
    independientemente de si se intenta pasar como entrada.
    """
    from src.domain.models.asignacion import Asignacion

    a = Asignacion(grupo_id=1, asignatura_id=1, usuario_id=1, periodo_id=1, activo=True)
    assert a.esta_activa is True

    d = a.model_dump()
    assert "esta_activa" in d
    assert d["esta_activa"] is True

    a_inactiva = Asignacion(
        grupo_id=1, asignatura_id=1, usuario_id=1, periodo_id=1, activo=False
    )
    assert a_inactiva.esta_activa is False


@pytest.mark.entrada
def test_computed_field_no_acepta_setter():
    """Los computed_fields son de solo lectura — asignar lanza AttributeError."""
    from src.domain.models.estudiante import Estudiante

    e = Estudiante(numero_documento="1", nombre="Ana", apellido="Gil")
    assert e.es_activo is True

    with pytest.raises((AttributeError, pydantic.ValidationError if False else AttributeError)):
        e.es_activo = False  # type: ignore[misc]


# Importación necesaria para el último test
import pydantic  # noqa: E402
