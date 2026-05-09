"""
Tests unitarios — Periodo, Infraestructura y Cierre
====================================================

Ejecutar:
    pytest tests/unit/domain/test_periodo_infra_cierre.py -v
"""

from datetime import date, datetime, time, timedelta

import pytest
from pydantic import ValidationError

from src.domain.models.periodo import (
    ActualizarPeriodoDTO,
    HitoPeriodo,
    NuevoHitoPeriodoDTO,
    NuevoPeriodoDTO,
    Periodo,
    TipoHito,
)
from src.domain.models.infraestructura import (
    AreaConocimiento,
    Asignatura,
    DiaSemana,
    Grupo,
    Horario,
    Jornada,
    Logro,
    NuevaAreaDTO,
    NuevoGrupoDTO,
    NuevoHorarioDTO,
)
from src.domain.models.cierre import (
    CierreAnio,
    CierrePeriodo,
    CrearCierreAnioDTO,
    CrearCierrePeriodoDTO,
    DecidirPromocionDTO,
    EstadoPromocion,
    PromocionAnual,
)


# =============================================================================
# PERIODO
# =============================================================================

class TestPeriodo:

    @pytest.fixture
    def periodo(self) -> Periodo:
        return Periodo(
            id=1,
            anio_id=1,
            numero=1,
            nombre="Período 1",
            fecha_inicio=date(2025, 1, 20),
            fecha_fin=date(2025, 4, 11),
            peso_porcentual=25.0,
        )

    def test_periodo_valido(self, periodo):
        assert periodo.esta_abierto is True
        assert periodo.esta_vigente is True
        assert periodo.duracion_dias == (date(2025, 4, 11) - date(2025, 1, 20)).days

    def test_numero_fuera_de_rango_falla(self):
        with pytest.raises(ValidationError, match="1 y 6"):
            Periodo(anio_id=1, numero=7, nombre="P7", peso_porcentual=10.0)

    def test_numero_cero_falla(self):
        with pytest.raises(ValidationError, match="1 y 6"):
            Periodo(anio_id=1, numero=0, nombre="P0", peso_porcentual=10.0)

    def test_nombre_vacio_falla(self):
        with pytest.raises(ValidationError, match="vacío"):
            Periodo(anio_id=1, numero=1, nombre="   ", peso_porcentual=25.0)

    def test_peso_cero_falla(self):
        with pytest.raises(ValidationError, match="0 y 100"):
            Periodo(anio_id=1, numero=1, nombre="P1", peso_porcentual=0.0)

    def test_peso_mayor_100_falla(self):
        with pytest.raises(ValidationError, match="0 y 100"):
            Periodo(anio_id=1, numero=1, nombre="P1", peso_porcentual=101.0)

    def test_fecha_inicio_posterior_a_fin_falla(self):
        with pytest.raises(ValidationError, match="posterior"):
            Periodo(
                anio_id=1, numero=1, nombre="P1",
                peso_porcentual=25.0,
                fecha_inicio=date(2025, 5, 1),
                fecha_fin=date(2025, 4, 1),
            )

    def test_cerrado_sin_fecha_cierre_real_falla(self):
        with pytest.raises(ValidationError, match="fecha_cierre_real"):
            Periodo(
                anio_id=1, numero=1, nombre="P1",
                peso_porcentual=25.0,
                cerrado=True,
                fecha_cierre_real=None,
            )

    def test_abierto_con_fecha_cierre_real_falla(self):
        with pytest.raises(ValidationError, match="fecha_cierre_real"):
            Periodo(
                anio_id=1, numero=1, nombre="P1",
                peso_porcentual=25.0,
                cerrado=False,
                fecha_cierre_real=datetime.now(),
            )

    def test_en_curso(self):
        hoy = date.today()
        periodo = Periodo(
            anio_id=1, numero=1, nombre="P1",
            peso_porcentual=25.0,
            fecha_inicio=hoy - timedelta(days=10),
            fecha_fin=hoy + timedelta(days=10),
        )
        assert periodo.en_curso is True

    def test_en_curso_false_si_terminado(self, periodo):
        assert periodo.en_curso is False   # fechas de 2025, ya pasadas

    def test_duracion_dias_none_sin_fechas(self):
        periodo = Periodo(anio_id=1, numero=1, nombre="P1", peso_porcentual=25.0)
        assert periodo.duracion_dias is None

    def test_cerrar(self, periodo):
        fecha = datetime(2025, 4, 11, 17, 0)
        cerrado = periodo.cerrar(fecha)
        assert cerrado.cerrado is True
        assert cerrado.activo is False
        assert cerrado.fecha_cierre_real == fecha
        assert periodo.cerrado is False   # original intacto

    def test_cerrar_ya_cerrado_falla(self, periodo):
        cerrado = periodo.cerrar()
        with pytest.raises(ValueError, match="ya fue cerrado"):
            cerrado.cerrar()

    def test_activar(self):
        periodo_inactivo = Periodo(
            anio_id=1, numero=2, nombre="P2",
            peso_porcentual=25.0, activo=False,
        )
        activo = periodo_inactivo.activar()
        assert activo.activo is True

    def test_activar_cerrado_falla(self, periodo):
        cerrado = periodo.cerrar()
        with pytest.raises(ValueError, match="cerrado"):
            cerrado.activar()

    def test_activar_ya_activo_falla(self, periodo):
        with pytest.raises(ValueError, match="ya está activo"):
            periodo.activar()

    def test_desactivar(self, periodo):
        inactivo = periodo.desactivar()
        assert inactivo.activo is False
        assert periodo.activo is True

    def test_desactivar_ya_inactivo_falla(self):
        periodo = Periodo(
            anio_id=1, numero=1, nombre="P1",
            peso_porcentual=25.0, activo=False,
        )
        with pytest.raises(ValueError, match="ya está inactivo"):
            periodo.desactivar()

    def test_actualizar_periodo_dto_no_modifica_cerrado(self, periodo):
        cerrado = periodo.cerrar()
        dto = ActualizarPeriodoDTO(nombre="Nuevo nombre")
        with pytest.raises(ValueError, match="cerrado"):
            dto.aplicar_a(cerrado)

    def test_nuevo_periodo_dto(self):
        dto = NuevoPeriodoDTO(
            anio_id=1, numero=1, nombre="Período 1",
            peso_porcentual=25.0,
        )
        p = dto.to_periodo()
        assert isinstance(p, Periodo)
        assert p.activo is True


class TestHitoPeriodo:

    def test_hito_valido(self):
        hito = HitoPeriodo(
            periodo_id=1,
            tipo=TipoHito.ENTREGA_NOTAS,
            fecha_limite=date(2025, 4, 10),
        )
        assert hito.esta_vencido is True   # fecha en el pasado
        assert hito.dias_restantes is not None

    def test_hito_sin_fecha_no_vencido(self):
        hito = HitoPeriodo(periodo_id=1)
        assert hito.esta_vencido is False
        assert hito.dias_restantes is None

    def test_hito_futuro_no_vencido(self):
        hito = HitoPeriodo(
            periodo_id=1,
            fecha_limite=date.today() + timedelta(days=5),
        )
        assert hito.esta_vencido is False
        assert hito.dias_restantes == 5

    def test_descripcion_vacia_se_convierte_en_none(self):
        hito = HitoPeriodo(periodo_id=1, descripcion="   ")
        assert hito.descripcion is None

    def test_dto_to_hito(self):
        dto = NuevoHitoPeriodoDTO(
            periodo_id=1,
            tipo=TipoHito.INICIO_HABILITACIONES,
            fecha_limite=date(2025, 4, 15),
        )
        hito = dto.to_hito()
        assert isinstance(hito, HitoPeriodo)


# =============================================================================
# INFRAESTRUCTURA
# =============================================================================

class TestAreaConocimiento:

    def test_area_valida(self):
        area = AreaConocimiento(nombre="Matemáticas", codigo="MATE")
        assert area.codigo == "MATE"

    def test_nombre_vacio_falla(self):
        with pytest.raises(ValidationError, match="vacío"):
            AreaConocimiento(nombre="   ")

    def test_codigo_se_normaliza_a_mayusculas(self):
        area = AreaConocimiento(nombre="Matemáticas", codigo="mate")
        assert area.codigo == "MATE"

    def test_codigo_vacio_es_none(self):
        area = AreaConocimiento(nombre="Matemáticas", codigo="   ")
        assert area.codigo is None


class TestAsignatura:

    def test_asignatura_valida(self):
        asig = Asignatura(nombre="Matemáticas", horas_semanales=4)
        assert asig.horas_semanales == 4

    def test_nombre_vacio_falla(self):
        with pytest.raises(ValidationError, match="vacío"):
            Asignatura(nombre="")

    def test_horas_cero_falla(self):
        with pytest.raises(ValidationError):
            Asignatura(nombre="Matemáticas", horas_semanales=0)

    def test_area_id_negativo_falla(self):
        with pytest.raises(ValidationError, match="positivo"):
            Asignatura(nombre="Matemáticas", area_id=-1)


class TestGrupo:

    @pytest.fixture
    def grupo(self) -> Grupo:
        return Grupo(
            id=1,
            codigo="601",
            nombre="Sexto A",
            grado=6,
            jornada=Jornada.AM,
            capacidad_maxima=35,
        )

    def test_grupo_valido(self, grupo):
        assert grupo.descripcion_completa == "601 — Sexto A (AM)"
        assert grupo.descripcion_corta == "Sexto A"

    def test_codigo_normalizado_a_mayusculas(self):
        g = Grupo(codigo="  601  ")
        assert g.codigo == "601"

    def test_codigo_vacio_falla(self):
        with pytest.raises(ValidationError, match="vacío"):
            Grupo(codigo="   ")

    def test_grado_fuera_de_rango_falla(self):
        with pytest.raises(ValidationError, match="1 y 13"):
            Grupo(codigo="601", grado=14)

    def test_descripcion_sin_nombre(self):
        g = Grupo(codigo="601", jornada=Jornada.PM)
        assert g.descripcion_completa == "601 (PM)"
        assert g.descripcion_corta == "601"

    def test_esta_lleno(self, grupo):
        assert grupo.esta_lleno(35) is True
        assert grupo.esta_lleno(34) is False
        assert grupo.esta_lleno(40) is True

    def test_esta_lleno_negativo_falla(self, grupo):
        with pytest.raises(ValueError, match="negativo"):
            grupo.esta_lleno(-1)

    def test_cupos_disponibles(self, grupo):
        assert grupo.cupos_disponibles(30) == 5
        assert grupo.cupos_disponibles(35) == 0
        assert grupo.cupos_disponibles(40) == 0   # no retorna negativo

    def test_dto_to_grupo(self):
        dto = NuevoGrupoDTO(codigo="701", grado=7)
        g = dto.to_grupo()
        assert isinstance(g, Grupo)


class TestHorario:

    @pytest.fixture
    def horario(self) -> Horario:
        return Horario(
            grupo_id=1,
            asignatura_id=2,
            usuario_id=3,
            periodo_id=1,
            dia_semana=DiaSemana.LUNES,
            hora_inicio=time(7, 0),
            hora_fin=time(7, 55),
        )

    def test_horario_valido(self, horario):
        assert horario.duracion_minutos == 55
        assert horario.franja_display == "Lunes 07:00–07:55"

    def test_hora_desde_string(self):
        h = Horario(
            grupo_id=1, asignatura_id=2, usuario_id=3, periodo_id=1,
            dia_semana=DiaSemana.MARTES,
            hora_inicio="08:00", hora_fin="08:55",
        )
        assert h.hora_inicio == time(8, 0)
        assert h.duracion_minutos == 55

    def test_hora_inicio_igual_fin_falla(self):
        with pytest.raises(ValidationError, match="anterior"):
            Horario(
                grupo_id=1, asignatura_id=2, usuario_id=3, periodo_id=1,
                dia_semana=DiaSemana.LUNES,
                hora_inicio=time(8, 0), hora_fin=time(8, 0),
            )

    def test_hora_inicio_posterior_a_fin_falla(self):
        with pytest.raises(ValidationError, match="anterior"):
            Horario(
                grupo_id=1, asignatura_id=2, usuario_id=3, periodo_id=1,
                dia_semana=DiaSemana.LUNES,
                hora_inicio=time(9, 0), hora_fin=time(8, 0),
            )

    def test_hora_string_invalida_falla(self):
        with pytest.raises(ValidationError):
            Horario(
                grupo_id=1, asignatura_id=2, usuario_id=3, periodo_id=1,
                dia_semana=DiaSemana.LUNES,
                hora_inicio="25:00", hora_fin="26:00",
            )

    def test_id_cero_falla(self):
        with pytest.raises(ValidationError, match="positivo"):
            Horario(
                grupo_id=0, asignatura_id=2, usuario_id=3, periodo_id=1,
                dia_semana=DiaSemana.LUNES,
                hora_inicio=time(7, 0), hora_fin=time(8, 0),
            )

    def test_sala_vacia_default_aula(self):
        h = Horario(
            grupo_id=1, asignatura_id=2, usuario_id=3, periodo_id=1,
            dia_semana=DiaSemana.VIERNES,
            hora_inicio=time(10, 0), hora_fin=time(11, 0),
            sala="   ",
        )
        assert h.sala == "Aula"

    def test_dto_to_horario(self):
        dto = NuevoHorarioDTO(
            grupo_id=1, asignatura_id=2, usuario_id=3, periodo_id=1,
            dia_semana=DiaSemana.MIERCOLES,
            hora_inicio="07:00", hora_fin="07:55",
        )
        h = dto.to_horario()
        assert isinstance(h, Horario)
        assert h.duracion_minutos == 55


class TestLogro:

    def test_logro_valido(self):
        logro = Logro(
            asignacion_id=1, periodo_id=1,
            descripcion="Comprende los conceptos de función cuadrática.",
        )
        assert logro.orden == 0

    def test_descripcion_vacia_falla(self):
        with pytest.raises(ValidationError, match="vacía"):
            Logro(asignacion_id=1, periodo_id=1, descripcion="")

    def test_descripcion_muy_larga_falla(self):
        with pytest.raises(ValidationError, match="500"):
            Logro(asignacion_id=1, periodo_id=1, descripcion="x" * 501)

    def test_id_negativo_falla(self):
        with pytest.raises(ValidationError, match="positivo"):
            Logro(asignacion_id=-1, periodo_id=1, descripcion="Descripción.")


# =============================================================================
# CIERRE
# =============================================================================

class TestCierrePeriodo:

    @pytest.fixture
    def cierre(self) -> CierrePeriodo:
        return CierrePeriodo(
            estudiante_id=1,
            asignacion_id=2,
            periodo_id=1,
            nota_definitiva=75.5,
            fecha_cierre=date(2025, 4, 11),
        )

    def test_cierre_valido(self, cierre):
        assert cierre.nota_definitiva == 75.5
        assert cierre.nota_display == "75.5"

    def test_nota_fuera_de_rango_falla(self):
        with pytest.raises(ValidationError, match="0 y 100"):
            CierrePeriodo(
                estudiante_id=1, asignacion_id=1, periodo_id=1,
                nota_definitiva=101.0,
            )

    def test_nota_se_redondea(self):
        c = CierrePeriodo(
            estudiante_id=1, asignacion_id=1, periodo_id=1,
            nota_definitiva=75.555,
        )
        assert c.nota_definitiva == 75.56

    def test_fecha_futura_falla(self):
        with pytest.raises(ValidationError, match="futura"):
            CierrePeriodo(
                estudiante_id=1, asignacion_id=1, periodo_id=1,
                nota_definitiva=70.0,
                fecha_cierre=date.today() + timedelta(days=1),
            )

    def test_aprobo_true(self, cierre):
        assert cierre.aprobo(nota_minima=60.0) is True

    def test_aprobo_false(self, cierre):
        assert cierre.aprobo(nota_minima=80.0) is False

    def test_dto_to_cierre(self):
        dto = CrearCierrePeriodoDTO(
            estudiante_id=1, asignacion_id=1, periodo_id=1,
            nota_definitiva=68.5,
        )
        c = dto.to_cierre()
        assert isinstance(c, CierrePeriodo)


class TestCierreAnio:

    def test_cierre_anio_sin_habilitacion(self):
        c = CierreAnio(
            estudiante_id=1, asignacion_id=1, anio_id=1,
            nota_promedio_periodos=72.0,
            nota_definitiva_anual=72.0,
            perdio=False,
        )
        assert c.tiene_habilitacion is False
        assert c.mejoro_con_habilitacion is None

    def test_cierre_anio_con_habilitacion(self):
        c = CierreAnio(
            estudiante_id=1, asignacion_id=1, anio_id=1,
            nota_promedio_periodos=55.0,
            nota_habilitacion=62.0,
            nota_definitiva_anual=62.0,
            perdio=False,
        )
        assert c.tiene_habilitacion is True
        assert c.mejoro_con_habilitacion is True

    def test_definitiva_incoherente_con_habilitacion_falla(self):
        with pytest.raises(ValidationError, match="nota_habilitacion"):
            CierreAnio(
                estudiante_id=1, asignacion_id=1, anio_id=1,
                nota_promedio_periodos=55.0,
                nota_habilitacion=62.0,
                nota_definitiva_anual=70.0,   # debería ser 62.0
                perdio=False,
            )

    def test_definitiva_incoherente_sin_habilitacion_falla(self):
        with pytest.raises(ValidationError, match="nota_promedio_periodos"):
            CierreAnio(
                estudiante_id=1, asignacion_id=1, anio_id=1,
                nota_promedio_periodos=72.0,
                nota_definitiva_anual=75.0,   # debería ser 72.0
                perdio=False,
            )

    def test_nota_display(self):
        c = CierreAnio(
            estudiante_id=1, asignacion_id=1, anio_id=1,
            nota_promedio_periodos=71.0,
            nota_definitiva_anual=71.0,
            perdio=False,
        )
        assert c.nota_display == "71.0"

    def test_dto_to_cierre_anio(self):
        dto = CrearCierreAnioDTO(
            estudiante_id=1, asignacion_id=1, anio_id=1,
            nota_promedio_periodos=58.0,
            nota_definitiva_anual=58.0,
            perdio=True,
        )
        c = dto.to_cierre()
        assert isinstance(c, CierreAnio)
        assert c.perdio is True


class TestPromocionAnual:

    @pytest.fixture
    def promocion(self) -> PromocionAnual:
        return PromocionAnual(estudiante_id=10, anio_id=1)

    def test_promocion_pendiente_por_defecto(self, promocion):
        assert promocion.esta_pendiente is True
        assert promocion.esta_finalizado is False

    def test_pendiente_con_fecha_decision_falla(self):
        with pytest.raises(ValidationError, match="fecha_decision"):
            PromocionAnual(
                estudiante_id=1, anio_id=1,
                estado=EstadoPromocion.PENDIENTE,
                fecha_decision=date.today(),
            )

    def test_finalizado_sin_fecha_decision_falla(self):
        with pytest.raises(ValidationError, match="fecha_decision"):
            PromocionAnual(
                estudiante_id=1, anio_id=1,
                estado=EstadoPromocion.PROMOVIDO,
                fecha_decision=None,
            )

    def test_fecha_futura_falla(self):
        with pytest.raises(ValidationError, match="futura"):
            PromocionAnual(
                estudiante_id=1, anio_id=1,
                estado=EstadoPromocion.PROMOVIDO,
                fecha_decision=date.today() + timedelta(days=1),
            )

    def test_decidir_promovido(self, promocion):
        fecha = date(2025, 12, 10)
        promovido = promocion.decidir(
            EstadoPromocion.PROMOVIDO,
            usuario_id=5,
            fecha=fecha,
        )
        assert promovido.fue_promovido is True
        assert promovido.fue_reprobado is False
        assert promovido.fecha_decision == fecha
        assert promocion.esta_pendiente is True   # original intacto

    def test_decidir_reprobado(self, promocion):
        reprobado = promocion.decidir(
            EstadoPromocion.REPROBADO,
            asignaturas_perdidas=4,
            observacion="Perdió 4 asignaturas.",
            fecha=date(2025, 12, 10),
        )
        assert reprobado.fue_reprobado is True
        assert reprobado.asignaturas_perdidas == 4

    def test_decidir_condicional(self, promocion):
        condicional = promocion.decidir(
            EstadoPromocion.CONDICIONAL,
            asignaturas_perdidas=2,
            observacion="Aprueba con 2 materias pendientes.",
            fecha=date(2025, 12, 10),
        )
        assert condicional.es_condicional is True
        assert condicional.fue_promovido is True   # condicional también es promovido

    def test_decidir_pendiente_falla(self, promocion):
        with pytest.raises(ValueError, match="PENDIENTE"):
            promocion.decidir(EstadoPromocion.PENDIENTE)

    def test_decidir_dos_veces_falla(self, promocion):
        promovido = promocion.decidir(
            EstadoPromocion.PROMOVIDO,
            fecha=date(2025, 12, 10),
        )
        with pytest.raises(ValueError, match="ya fue decidida"):
            promovido.decidir(EstadoPromocion.REPROBADO, fecha=date(2025, 12, 11))

    def test_asignaturas_perdidas_negativas_falla(self, promocion):
        with pytest.raises(ValueError, match="negativo"):
            promocion.decidir(
                EstadoPromocion.REPROBADO,
                asignaturas_perdidas=-1,
                fecha=date(2025, 12, 10),
            )

    def test_decidir_promocion_dto_pendiente_falla(self):
        with pytest.raises(ValidationError, match="PENDIENTE"):
            DecidirPromocionDTO(estado=EstadoPromocion.PENDIENTE)

    def test_decidir_promocion_dto_valido(self):
        dto = DecidirPromocionDTO(
            estado=EstadoPromocion.PROMOVIDO,
            observacion="Sin materias perdidas.",
        )
        assert dto.estado == EstadoPromocion.PROMOVIDO