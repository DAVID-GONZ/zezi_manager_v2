"""
Tests unitarios — Alerta, PIAR y Convivencia
=============================================

Ejecutar:
    pytest tests/unit/domain/test_convivencia_piar_alerta.py -v
"""

from datetime import date, datetime, timedelta

import pytest
from pydantic import ValidationError

from src.domain.models.alerta import (
    Alerta,
    ConfiguracionAlerta,
    CrearAlertaDTO,
    FiltroAlertasDTO,
    NivelAlerta,
    ResolverAlertaDTO,
    TipoAlerta,
)
from src.domain.models.piar import (
    ActualizarPIARDTO,
    NuevoPIARDTO,
    PIAR,
)
from src.domain.models.convivencia import (
    FiltroConvivenciaDTO,
    NotaComportamiento,
    NuevaNotaComportamientoDTO,
    NuevaObservacionDTO,
    NuevoRegistroComportamientoDTO,
    ObservacionPeriodo,
    RegistroComportamiento,
    TipoRegistro,
)


# =============================================================================
# ALERTA
# =============================================================================

class TestConfiguracionAlerta:

    def test_configuracion_valida(self):
        cfg = ConfiguracionAlerta(
            anio_id=1,
            tipo_alerta=TipoAlerta.FALTAS_INJUSTIFICADAS,
            umbral=3.0,
        )
        assert cfg.activa is True
        assert cfg.umbral_entero == 3

    def test_umbral_cero_falla(self):
        with pytest.raises(ValidationError, match="cero"):
            ConfiguracionAlerta(
                anio_id=1,
                tipo_alerta=TipoAlerta.FALTAS_INJUSTIFICADAS,
                umbral=0,
            )

    def test_umbral_negativo_falla(self):
        with pytest.raises(ValidationError):
            ConfiguracionAlerta(
                anio_id=1,
                tipo_alerta=TipoAlerta.PROMEDIO_BAJO,
                umbral=-1.0,
            )

    def test_umbral_decimal_en_tipo_conteo_falla(self):
        with pytest.raises(ValidationError, match="entero"):
            ConfiguracionAlerta(
                anio_id=1,
                tipo_alerta=TipoAlerta.MATERIAS_EN_RIESGO,
                umbral=2.5,
            )

    def test_umbral_promedio_fuera_de_rango_falla(self):
        with pytest.raises(ValidationError, match="0 y 100"):
            ConfiguracionAlerta(
                anio_id=1,
                tipo_alerta=TipoAlerta.PROMEDIO_BAJO,
                umbral=110.0,
            )

    def test_umbral_promedio_valido(self):
        cfg = ConfiguracionAlerta(
            anio_id=1,
            tipo_alerta=TipoAlerta.PROMEDIO_BAJO,
            umbral=55.0,
        )
        assert cfg.umbral == 55.0

    def test_notifica_a_alguien_true(self):
        cfg = ConfiguracionAlerta(
            anio_id=1,
            tipo_alerta=TipoAlerta.PROMEDIO_BAJO,
            umbral=55.0,
            notificar_docente=True,
        )
        assert cfg.notifica_a_alguien is True

    def test_notifica_a_alguien_false_cuando_nadie(self):
        cfg = ConfiguracionAlerta(
            anio_id=1,
            tipo_alerta=TipoAlerta.PROMEDIO_BAJO,
            umbral=55.0,
            notificar_docente=False,
            notificar_director=False,
            notificar_acudiente=False,
        )
        assert cfg.notifica_a_alguien is False


class TestAlerta:

    @pytest.fixture
    def alerta_pendiente(self) -> Alerta:
        return Alerta(
            id=1,
            estudiante_id=10,
            tipo_alerta=TipoAlerta.PROMEDIO_BAJO,
            nivel=NivelAlerta.ADVERTENCIA,
            descripcion="Promedio por debajo de 55 en Matemáticas.",
        )

    def test_alerta_pendiente_por_defecto(self, alerta_pendiente):
        assert alerta_pendiente.esta_pendiente is True
        assert alerta_pendiente.resuelta is False

    def test_descripcion_vacia_falla(self):
        with pytest.raises(ValidationError, match="vacía"):
            Alerta(
                estudiante_id=1,
                tipo_alerta=TipoAlerta.PROMEDIO_BAJO,
                descripcion="   ",
            )

    def test_descripcion_muy_larga_falla(self):
        with pytest.raises(ValidationError):
            Alerta(
                estudiante_id=1,
                tipo_alerta=TipoAlerta.PROMEDIO_BAJO,
                descripcion="x" * 501,
            )

    def test_resuelta_sin_fecha_falla(self):
        with pytest.raises(ValidationError, match="fecha_resolucion"):
            Alerta(
                estudiante_id=1,
                tipo_alerta=TipoAlerta.PROMEDIO_BAJO,
                descripcion="Alerta de prueba.",
                resuelta=True,
                fecha_resolucion=None,
            )

    def test_pendiente_con_fecha_resolucion_falla(self):
        with pytest.raises(ValidationError, match="datos de resolución"):
            Alerta(
                estudiante_id=1,
                tipo_alerta=TipoAlerta.PROMEDIO_BAJO,
                descripcion="Alerta de prueba.",
                resuelta=False,
                fecha_resolucion=datetime.now(),
            )

    def test_resolver_alerta_pendiente(self, alerta_pendiente):
        fecha = datetime(2025, 4, 10, 9, 0)
        resuelta = alerta_pendiente.resolver(usuario_id=5, observacion="Se habló con el estudiante.", fecha=fecha)

        assert resuelta.resuelta is True
        assert resuelta.usuario_resolucion_id == 5
        assert resuelta.fecha_resolucion == fecha
        assert resuelta.observacion_resolucion == "Se habló con el estudiante."
        # El original no se modifica
        assert alerta_pendiente.resuelta is False

    def test_resolver_alerta_ya_resuelta_falla(self, alerta_pendiente):
        resuelta = alerta_pendiente.resolver(usuario_id=5, fecha=datetime.now())
        with pytest.raises(ValueError, match="ya fue resuelta"):
            resuelta.resolver(usuario_id=5, fecha=datetime.now())

    def test_dias_pendiente_es_none_si_resuelta(self, alerta_pendiente):
        resuelta = alerta_pendiente.resolver(usuario_id=5, fecha=datetime.now())
        assert resuelta.dias_pendiente is None

    def test_es_critica(self):
        alerta = Alerta(
            estudiante_id=1,
            tipo_alerta=TipoAlerta.MATERIAS_EN_RIESGO,
            nivel=NivelAlerta.CRITICA,
            descripcion="Tres materias perdidas.",
        )
        assert alerta.es_critica is True

    def test_crear_alerta_dto(self):
        dto = CrearAlertaDTO(
            estudiante_id=10,
            tipo_alerta=TipoAlerta.FALTAS_INJUSTIFICADAS,
            descripcion="5 faltas injustificadas en el periodo.",
        )
        alerta = dto.to_alerta()
        assert isinstance(alerta, Alerta)
        assert alerta.esta_pendiente is True


# =============================================================================
# PIAR
# =============================================================================

class TestPIAR:

    @pytest.fixture
    def piar_base(self) -> PIAR:
        return PIAR(
            estudiante_id=1,
            anio_id=1,
            descripcion_necesidad="Dislexia leve. Requiere tiempo adicional en evaluaciones.",
            fecha_elaboracion=date(2025, 2, 1),
        )

    def test_piar_valido(self, piar_base):
        assert piar_base.tiene_revision_programada is False
        assert piar_base.revision_vencida is False
        assert piar_base.dias_para_revision is None

    def test_descripcion_vacia_falla(self):
        with pytest.raises(ValidationError, match="vacía"):
            PIAR(
                estudiante_id=1,
                anio_id=1,
                descripcion_necesidad="   ",
            )

    def test_fecha_elaboracion_futura_falla(self):
        manana = date.today() + timedelta(days=1)
        with pytest.raises(ValidationError, match="futura"):
            PIAR(
                estudiante_id=1,
                anio_id=1,
                descripcion_necesidad="Descripción válida.",
                fecha_elaboracion=manana,
            )

    def test_fecha_revision_anterior_a_elaboracion_falla(self):
        with pytest.raises(ValidationError, match="anterior"):
            PIAR(
                estudiante_id=1,
                anio_id=1,
                descripcion_necesidad="Descripción válida.",
                fecha_elaboracion=date(2025, 3, 1),
                fecha_revision=date(2025, 2, 1),
            )

    def test_fecha_revision_igual_a_elaboracion_es_valida(self):
        piar = PIAR(
            estudiante_id=1,
            anio_id=1,
            descripcion_necesidad="Descripción válida.",
            fecha_elaboracion=date(2025, 2, 1),
            fecha_revision=date(2025, 2, 1),
        )
        assert piar.tiene_revision_programada is True

    def test_revision_vencida_cuando_fecha_pasada(self):
        piar = PIAR(
            estudiante_id=1,
            anio_id=1,
            descripcion_necesidad="Descripción.",
            fecha_elaboracion=date(2024, 1, 1),
            fecha_revision=date(2024, 6, 1),  # pasada
        )
        assert piar.revision_vencida is True

    def test_dias_para_revision_positivo(self):
        futura = date.today() + timedelta(days=10)
        piar = PIAR(
            estudiante_id=1,
            anio_id=1,
            descripcion_necesidad="Desc.",
            fecha_elaboracion=date(2025, 1, 1),
            fecha_revision=futura,
        )
        assert piar.dias_para_revision == 10

    def test_programar_revision(self, piar_base):
        nueva_fecha = date(2025, 6, 1)
        actualizado = piar_base.programar_revision(nueva_fecha)
        assert actualizado.fecha_revision == nueva_fecha
        assert piar_base.fecha_revision is None  # original intacto

    def test_programar_revision_anterior_falla(self, piar_base):
        with pytest.raises(ValueError, match="anterior"):
            piar_base.programar_revision(date(2025, 1, 1))

    def test_actualizar_ajustes(self, piar_base):
        actualizado = piar_base.actualizar_ajustes(
            ajustes_evaluativos="Tiempo extra de 30 minutos.",
            ajustes_pedagogicos="Uso de materiales concretos.",
        )
        assert actualizado.ajustes_evaluativos == "Tiempo extra de 30 minutos."
        assert actualizado.ajustes_pedagogicos == "Uso de materiales concretos."
        assert piar_base.ajustes_evaluativos is None  # original intacto

    def test_actualizar_ajustes_vacio_establece_none(self, piar_base):
        actualizado = piar_base.actualizar_ajustes(ajustes_evaluativos="   ")
        assert actualizado.ajustes_evaluativos is None

    def test_nuevo_piar_dto_to_piar(self):
        dto = NuevoPIARDTO(
            estudiante_id=1,
            anio_id=1,
            descripcion_necesidad="TDAH con predominio inatento.",
        )
        piar = dto.to_piar(usuario_id=5)
        assert isinstance(piar, PIAR)
        assert piar.usuario_elaboracion_id == 5

    def test_actualizar_piar_dto_aplica_cambios(self, piar_base):
        dto = ActualizarPIARDTO(
            ajustes_evaluativos="Evaluación oral permitida.",
        )
        actualizado = dto.aplicar_a(piar_base)
        assert actualizado.ajustes_evaluativos == "Evaluación oral permitida."

    def test_actualizar_piar_dto_vacio_no_cambia(self, piar_base):
        dto = ActualizarPIARDTO()
        sin_cambios = dto.aplicar_a(piar_base)
        assert sin_cambios == piar_base

    def test_descripcion_vacia_en_dto_actualizacion_falla(self):
        with pytest.raises(ValidationError):
            ActualizarPIARDTO(descripcion_necesidad="")


# =============================================================================
# CONVIVENCIA
# =============================================================================

class TestObservacionPeriodo:

    @pytest.fixture
    def obs(self) -> ObservacionPeriodo:
        return ObservacionPeriodo(
            estudiante_id=1,
            asignacion_id=2,
            periodo_id=1,
            texto="Excelente participación durante el periodo.",
        )

    def test_observacion_valida(self, obs):
        assert obs.es_publica is True

    def test_texto_vacio_falla(self):
        with pytest.raises(ValidationError, match="vacía"):
            ObservacionPeriodo(
                estudiante_id=1,
                asignacion_id=2,
                periodo_id=1,
                texto="   ",
            )

    def test_texto_muy_largo_falla(self):
        with pytest.raises(ValidationError, match="2000"):
            ObservacionPeriodo(
                estudiante_id=1,
                asignacion_id=2,
                periodo_id=1,
                texto="x" * 2001,
            )

    def test_hacer_privada(self, obs):
        privada = obs.hacer_privada()
        assert privada.es_publica is False
        assert obs.es_publica is True  # original intacto

    def test_hacer_publica(self):
        obs_privada = ObservacionPeriodo(
            estudiante_id=1, asignacion_id=2, periodo_id=1,
            texto="Nota interna.", es_publica=False,
        )
        publica = obs_privada.hacer_publica()
        assert publica.es_publica is True

    def test_dto_to_observacion(self):
        dto = NuevaObservacionDTO(
            estudiante_id=1, asignacion_id=2, periodo_id=1,
            texto="Muestra liderazgo positivo.",
        )
        obs = dto.to_observacion(usuario_id=7)
        assert isinstance(obs, ObservacionPeriodo)
        assert obs.usuario_id == 7


class TestRegistroComportamiento:

    @pytest.fixture
    def registro_dificultad(self) -> RegistroComportamiento:
        return RegistroComportamiento(
            estudiante_id=1,
            grupo_id=1,
            periodo_id=1,
            tipo=TipoRegistro.DIFICULTAD,
            descripcion="No trajo materiales tres veces consecutivas.",
            requiere_firma=True,
        )

    @pytest.fixture
    def registro_fortaleza(self) -> RegistroComportamiento:
        return RegistroComportamiento(
            estudiante_id=1,
            grupo_id=1,
            periodo_id=1,
            tipo=TipoRegistro.FORTALEZA,
            descripcion="Ayudó a un compañero durante la clase.",
        )

    def test_registro_valido(self, registro_dificultad):
        assert registro_dificultad.es_negativo is True
        assert registro_dificultad.es_positivo is False
        assert registro_dificultad.pendiente_notificacion is True

    def test_fortaleza_es_positiva(self, registro_fortaleza):
        assert registro_fortaleza.es_positivo is True
        assert registro_fortaleza.es_negativo is False

    def test_descripcion_vacia_falla(self):
        with pytest.raises(ValidationError, match="vacía"):
            RegistroComportamiento(
                estudiante_id=1, grupo_id=1, periodo_id=1,
                tipo=TipoRegistro.DIFICULTAD,
                descripcion="",
            )

    def test_fecha_futura_falla(self):
        with pytest.raises(ValidationError, match="futura"):
            RegistroComportamiento(
                estudiante_id=1, grupo_id=1, periodo_id=1,
                tipo=TipoRegistro.DIFICULTAD,
                descripcion="Descripción válida.",
                fecha=date.today() + timedelta(days=1),
            )

    def test_descargo_con_requiere_firma_falla(self):
        with pytest.raises(ValidationError, match="DESCARGO"):
            RegistroComportamiento(
                estudiante_id=1, grupo_id=1, periodo_id=1,
                tipo=TipoRegistro.DESCARGO,
                descripcion="El estudiante declara que...",
                requiere_firma=True,
            )

    def test_registrar_notificacion(self, registro_dificultad):
        notificado = registro_dificultad.registrar_notificacion()
        assert notificado.acudiente_notificado is True
        assert notificado.pendiente_notificacion is False
        assert registro_dificultad.acudiente_notificado is False  # intacto

    def test_registrar_notificacion_sin_requiere_firma_falla(self, registro_fortaleza):
        with pytest.raises(ValueError, match="no requiere notificación"):
            registro_fortaleza.registrar_notificacion()

    def test_registrar_notificacion_ya_notificado_falla(self, registro_dificultad):
        notificado = registro_dificultad.registrar_notificacion()
        with pytest.raises(ValueError, match="ya fue notificado"):
            notificado.registrar_notificacion()

    def test_agregar_seguimiento(self, registro_dificultad):
        con_seguimiento = registro_dificultad.agregar_seguimiento(
            "Se habló con el acudiente. Firma recibida el 15/03."
        )
        assert con_seguimiento.tiene_seguimiento is True
        assert registro_dificultad.seguimiento is None  # intacto

    def test_agregar_seguimiento_vacio_falla(self, registro_dificultad):
        with pytest.raises(ValueError, match="vacío"):
            registro_dificultad.agregar_seguimiento("   ")

    def test_dto_to_registro(self):
        dto = NuevoRegistroComportamientoDTO(
            estudiante_id=1, grupo_id=1, periodo_id=1,
            tipo=TipoRegistro.COMPROMISO,
            descripcion="El estudiante se compromete a entregar tareas puntualmente.",
        )
        registro = dto.to_registro(usuario_id=3)
        assert isinstance(registro, RegistroComportamiento)
        assert registro.usuario_registro_id == 3

    def test_citacion_acudiente_es_negativo(self):
        registro = RegistroComportamiento(
            estudiante_id=1, grupo_id=1, periodo_id=1,
            tipo=TipoRegistro.CITACION_ACUDIENTE,
            descripcion="Se requiere presencia del acudiente.",
        )
        assert registro.es_negativo is True


class TestNotaComportamiento:

    def test_nota_valida(self):
        nota = NotaComportamiento(
            estudiante_id=1, grupo_id=1, periodo_id=1,
            valor=85.5,
        )
        assert nota.valor == 85.5

    def test_valor_fuera_de_rango_falla(self):
        with pytest.raises(ValidationError, match="0 y 100"):
            NotaComportamiento(
                estudiante_id=1, grupo_id=1, periodo_id=1,
                valor=101.0,
            )

    def test_valor_negativo_falla(self):
        with pytest.raises(ValidationError):
            NotaComportamiento(
                estudiante_id=1, grupo_id=1, periodo_id=1,
                valor=-1.0,
            )

    def test_valor_se_redondea_a_dos_decimales(self):
        nota = NotaComportamiento(
            estudiante_id=1, grupo_id=1, periodo_id=1,
            valor=85.555,
        )
        assert nota.valor == 85.56

    def test_aprobado_con_nota_por_encima_del_minimo(self):
        nota = NotaComportamiento(
            estudiante_id=1, grupo_id=1, periodo_id=1, valor=65.0
        )
        assert nota.aprobado is True

    def test_reprobado_con_nota_por_debajo_del_minimo(self):
        nota = NotaComportamiento(
            estudiante_id=1, grupo_id=1, periodo_id=1, valor=55.0
        )
        assert nota.aprobado is False

    def test_observacion_solo_espacios_es_none(self):
        nota = NotaComportamiento(
            estudiante_id=1, grupo_id=1, periodo_id=1,
            valor=70.0,
            observacion="   ",
        )
        assert nota.observacion is None

    def test_dto_to_nota(self):
        dto = NuevaNotaComportamientoDTO(
            estudiante_id=1, grupo_id=1, periodo_id=1, valor=78.5,
        )
        nota = dto.to_nota(usuario_id=4)
        assert isinstance(nota, NotaComportamiento)
        assert nota.usuario_id == 4


class TestFiltros:

    def test_filtro_alertas_defecto(self):
        f = FiltroAlertasDTO()
        assert f.solo_pendientes is True
        assert f.pagina == 1

    def test_filtro_convivencia_defecto(self):
        f = FiltroConvivenciaDTO()
        assert f.solo_negativos is False
        assert f.por_pagina == 50