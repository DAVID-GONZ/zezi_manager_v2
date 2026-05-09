"""
Tests unitarios — Asignacion, Habilitacion, PlanMejoramiento
=============================================================

Ejecutar:
    pytest tests/unit/domain/test_asignacion_habilitacion.py -v
"""

from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from src.domain.models.asignacion import (
    Asignacion,
    AsignacionInfo,
    FiltroAsignacionesDTO,
    NuevaAsignacionDTO,
)
from src.domain.models.habilitacion import (
    CerrarPlanMejoramientoDTO,
    EstadoHabilitacion,
    EstadoPlanMejoramiento,
    FiltroHabilitacionesDTO,
    Habilitacion,
    NuevaHabilitacionDTO,
    NuevoPlanMejoramientoDTO,
    PlanMejoramiento,
    RegistrarNotaHabilitacionDTO,
    TipoHabilitacion,
)


# =============================================================================
# ASIGNACION
# =============================================================================

class TestAsignacion:

    @pytest.fixture
    def asignacion(self) -> Asignacion:
        return Asignacion(
            id=1,
            grupo_id=1,
            asignatura_id=2,
            usuario_id=3,
            periodo_id=1,
        )

    def test_asignacion_valida(self, asignacion):
        assert asignacion.esta_activa is True
        assert asignacion.activo is True

    def test_id_cero_falla(self):
        with pytest.raises(ValidationError, match="positivo"):
            Asignacion(grupo_id=0, asignatura_id=1, usuario_id=1, periodo_id=1)

    def test_id_negativo_falla(self):
        with pytest.raises(ValidationError, match="positivo"):
            Asignacion(grupo_id=1, asignatura_id=-1, usuario_id=1, periodo_id=1)

    def test_desactivar(self, asignacion):
        inactiva = asignacion.desactivar()
        assert inactiva.activo is False
        assert inactiva.esta_activa is False
        assert asignacion.activo is True  # original intacto

    def test_desactivar_ya_inactiva_falla(self, asignacion):
        inactiva = asignacion.desactivar()
        with pytest.raises(ValueError, match="ya está inactiva"):
            inactiva.desactivar()

    def test_reactivar(self, asignacion):
        inactiva = asignacion.desactivar()
        reactivada = inactiva.reactivar()
        assert reactivada.activo is True

    def test_reactivar_ya_activa_falla(self, asignacion):
        with pytest.raises(ValueError, match="ya está activa"):
            asignacion.reactivar()

    def test_dto_to_asignacion(self):
        dto = NuevaAsignacionDTO(
            grupo_id=1, asignatura_id=2, usuario_id=3, periodo_id=1
        )
        asig = dto.to_asignacion()
        assert isinstance(asig, Asignacion)
        assert asig.activo is True
        assert asig.id is None

    def test_dto_id_invalido_falla(self):
        with pytest.raises(ValidationError, match="positivo"):
            NuevaAsignacionDTO(grupo_id=1, asignatura_id=0, usuario_id=3, periodo_id=1)


class TestAsignacionInfo:

    @pytest.fixture
    def info(self) -> AsignacionInfo:
        return AsignacionInfo(
            asignacion_id=1,
            grupo_id=1,
            grupo_codigo="601",
            asignatura_id=2,
            asignatura_nombre="Matemáticas",
            usuario_id=3,
            docente_nombre="Carlos López García",
            periodo_id=1,
            periodo_nombre="Período 1",
            periodo_numero=1,
            activo=True,
        )

    def test_display_completo(self, info):
        assert info.display_completo == (
            "601 — Matemáticas | Carlos López García (Período 1)"
        )

    def test_display_corto(self, info):
        assert info.display_corto == "601 · Matemáticas · P1"

    def test_display_docente_materia(self, info):
        assert info.display_docente_materia == "Matemáticas — 601"

    def test_campo_vacio_falla(self):
        with pytest.raises(ValidationError, match="vacío"):
            AsignacionInfo(
                asignacion_id=1,
                grupo_id=1,
                grupo_codigo="   ",   # vacío
                asignatura_id=2,
                asignatura_nombre="Matemáticas",
                usuario_id=3,
                docente_nombre="Carlos López",
                periodo_id=1,
                periodo_nombre="Período 1",
                periodo_numero=1,
                activo=True,
            )


# =============================================================================
# HABILITACIÓN
# =============================================================================

class TestHabilitacion:

    @pytest.fixture
    def hab_periodo(self) -> Habilitacion:
        """Habilitación de periodo en estado PENDIENTE."""
        return Habilitacion(
            id=1,
            estudiante_id=10,
            asignacion_id=5,
            tipo=TipoHabilitacion.PERIODO,
            periodo_id=2,
        )

    @pytest.fixture
    def hab_anual(self) -> Habilitacion:
        """Habilitación anual en estado PENDIENTE."""
        return Habilitacion(
            estudiante_id=10,
            asignacion_id=5,
            tipo=TipoHabilitacion.ANUAL,
            nota_antes=45.0,
        )

    # -- Construcción y validación --

    def test_habilitacion_periodo_valida(self, hab_periodo):
        assert hab_periodo.esta_pendiente is True
        assert hab_periodo.fue_realizada is False

    def test_habilitacion_anual_valida(self, hab_anual):
        assert hab_anual.periodo_id is None

    def test_periodo_sin_periodo_id_falla(self):
        with pytest.raises(ValidationError, match="requiere periodo_id"):
            Habilitacion(
                estudiante_id=1,
                asignacion_id=1,
                tipo=TipoHabilitacion.PERIODO,
                periodo_id=None,
            )

    def test_anual_con_periodo_id_falla(self):
        with pytest.raises(ValidationError, match="no debe tener periodo_id"):
            Habilitacion(
                estudiante_id=1,
                asignacion_id=1,
                tipo=TipoHabilitacion.ANUAL,
                periodo_id=2,
            )

    def test_nota_en_estado_pendiente_falla(self):
        with pytest.raises(ValidationError, match="nota_habilitacion"):
            Habilitacion(
                estudiante_id=1,
                asignacion_id=1,
                tipo=TipoHabilitacion.ANUAL,
                estado=EstadoHabilitacion.PENDIENTE,
                nota_habilitacion=70.0,
            )

    def test_nota_fuera_de_rango_falla(self):
        with pytest.raises(ValidationError, match="0 y 100"):
            Habilitacion(
                estudiante_id=1,
                asignacion_id=1,
                tipo=TipoHabilitacion.ANUAL,
                nota_antes=110.0,
            )

    def test_id_negativo_falla(self):
        with pytest.raises(ValidationError, match="positivo"):
            Habilitacion(
                estudiante_id=-1,
                asignacion_id=1,
                tipo=TipoHabilitacion.ANUAL,
            )

    # -- Propiedades --

    def test_mejoro_nota_true(self, hab_anual):
        realizada = hab_anual.registrar_nota(75.0)
        assert realizada.mejoro_nota is True

    def test_mejoro_nota_false(self, hab_anual):
        realizada = hab_anual.registrar_nota(30.0)
        assert realizada.mejoro_nota is False

    def test_mejoro_nota_none_sin_datos(self, hab_periodo):
        # hab_periodo no tiene nota_antes
        realizada = hab_periodo.registrar_nota(70.0)
        assert realizada.mejoro_nota is None

    # -- Transición PENDIENTE → REALIZADA --

    def test_registrar_nota(self, hab_periodo):
        fecha = date(2025, 4, 15)
        realizada = hab_periodo.registrar_nota(nota=72.5, fecha=fecha, usuario_id=7)

        assert realizada.estado == EstadoHabilitacion.REALIZADA
        assert realizada.nota_habilitacion == 72.5
        assert realizada.fecha == fecha
        assert realizada.usuario_registro_id == 7
        assert hab_periodo.estado == EstadoHabilitacion.PENDIENTE  # intacto

    def test_registrar_nota_invalida_falla(self, hab_periodo):
        with pytest.raises(ValueError, match="0 y 100"):
            hab_periodo.registrar_nota(nota=105.0)

    def test_registrar_nota_en_estado_final_falla(self, hab_periodo):
        realizada = hab_periodo.registrar_nota(70.0)
        aprobada = realizada.aprobar()
        with pytest.raises(ValueError, match="terminal"):
            aprobada.registrar_nota(80.0)

    # -- Transición REALIZADA → APROBADA / REPROBADA --

    def test_aprobar(self, hab_periodo):
        realizada = hab_periodo.registrar_nota(70.0)
        aprobada = realizada.aprobar()
        assert aprobada.estado == EstadoHabilitacion.APROBADA
        assert aprobada.tiene_resultado_final is True

    def test_reprobar(self, hab_periodo):
        realizada = hab_periodo.registrar_nota(45.0)
        reprobada = realizada.reprobar()
        assert reprobada.estado == EstadoHabilitacion.REPROBADA
        assert reprobada.tiene_resultado_final is True

    def test_aprobar_desde_pendiente_falla(self, hab_periodo):
        with pytest.raises(ValueError, match="Transición inválida"):
            hab_periodo.aprobar()

    def test_reprobar_desde_pendiente_falla(self, hab_periodo):
        with pytest.raises(ValueError, match="Transición inválida"):
            hab_periodo.reprobar()

    def test_aprobar_dos_veces_falla(self, hab_periodo):
        aprobada = hab_periodo.registrar_nota(70.0).aprobar()
        with pytest.raises(ValueError, match="terminal"):
            aprobada.aprobar()

    # -- DTOs --

    def test_nueva_habilitacion_dto(self):
        dto = NuevaHabilitacionDTO(
            estudiante_id=1,
            asignacion_id=2,
            tipo=TipoHabilitacion.PERIODO,
            periodo_id=1,
            nota_antes=42.0,
        )
        hab = dto.to_habilitacion(usuario_id=5)
        assert isinstance(hab, Habilitacion)
        assert hab.usuario_registro_id == 5

    def test_dto_periodo_sin_periodo_id_falla(self):
        with pytest.raises(ValidationError, match="requiere periodo_id"):
            NuevaHabilitacionDTO(
                estudiante_id=1,
                asignacion_id=2,
                tipo=TipoHabilitacion.PERIODO,
            )

    def test_registrar_nota_dto(self):
        dto = RegistrarNotaHabilitacionDTO(nota=78.5, usuario_id=3)
        assert dto.nota == 78.5

    def test_registrar_nota_dto_invalida_falla(self):
        with pytest.raises(ValidationError, match="0 y 100"):
            RegistrarNotaHabilitacionDTO(nota=-5.0)


# =============================================================================
# PLAN DE MEJORAMIENTO
# =============================================================================

class TestPlanMejoramiento:

    @pytest.fixture
    def plan(self) -> PlanMejoramiento:
        return PlanMejoramiento(
            id=1,
            estudiante_id=10,
            asignacion_id=5,
            periodo_id=1,
            descripcion_dificultad="Dificultad en comprensión de álgebra.",
            actividades_propuestas="Ejercicios de factorización y taller grupal.",
            fecha_inicio=date(2025, 3, 1),
        )

    # -- Construcción y validación --

    def test_plan_valido(self, plan):
        assert plan.esta_activo is True
        assert plan.esta_cerrado is False

    def test_descripcion_vacia_falla(self):
        with pytest.raises(ValidationError, match="vacío"):
            PlanMejoramiento(
                estudiante_id=1,
                asignacion_id=1,
                periodo_id=1,
                descripcion_dificultad="",
                actividades_propuestas="Algo.",
            )

    def test_actividades_vacias_falla(self):
        with pytest.raises(ValidationError, match="vacío"):
            PlanMejoramiento(
                estudiante_id=1,
                asignacion_id=1,
                periodo_id=1,
                descripcion_dificultad="Dificultad.",
                actividades_propuestas="   ",
            )

    def test_fecha_seguimiento_anterior_falla(self, plan):
        with pytest.raises(ValidationError, match="anterior al inicio"):
            PlanMejoramiento(
                estudiante_id=1,
                asignacion_id=1,
                periodo_id=1,
                descripcion_dificultad="Desc.",
                actividades_propuestas="Act.",
                fecha_inicio=date(2025, 3, 1),
                fecha_seguimiento=date(2025, 2, 1),
            )

    def test_estado_cerrado_sin_observacion_falla(self):
        with pytest.raises(ValidationError, match="observacion_cierre"):
            PlanMejoramiento(
                estudiante_id=1,
                asignacion_id=1,
                periodo_id=1,
                descripcion_dificultad="Desc.",
                actividades_propuestas="Act.",
                estado=EstadoPlanMejoramiento.CUMPLIDO,
                observacion_cierre=None,
            )

    def test_plan_activo_con_fecha_cierre_falla(self):
        # fecha_inicio explícita en el pasado, fecha_cierre posterior,
        # para que el validator de fechas no interfiera y se evalúe la regla ACTIVO
        with pytest.raises(ValidationError, match="ACTIVO"):
            PlanMejoramiento(
                estudiante_id=1,
                asignacion_id=1,
                periodo_id=1,
                descripcion_dificultad="Desc.",
                actividades_propuestas="Act.",
                fecha_inicio=date(2025, 1, 1),
                estado=EstadoPlanMejoramiento.ACTIVO,
                fecha_cierre=date(2025, 4, 1),
            )

    # -- Propiedades --

    def test_seguimiento_vencido_true(self, plan):
        plan_con_seguimiento = plan.model_copy(
            update={"fecha_seguimiento": date(2024, 1, 1)}
        )
        assert plan_con_seguimiento.seguimiento_vencido is True

    def test_seguimiento_vencido_false_si_futuro(self, plan):
        futuro = date.today() + timedelta(days=10)
        plan_con_seguimiento = plan.model_copy(
            update={"fecha_seguimiento": futuro}
        )
        assert plan_con_seguimiento.seguimiento_vencido is False

    def test_seguimiento_vencido_false_si_cerrado(self):
        plan_cerrado = PlanMejoramiento(
            estudiante_id=1,
            asignacion_id=1,
            periodo_id=1,
            descripcion_dificultad="Desc.",
            actividades_propuestas="Act.",
            fecha_inicio=date(2025, 1, 1),
            fecha_cierre=date(2025, 3, 1),
            fecha_seguimiento=date(2025, 1, 15),   # después del inicio, ya vencida
            estado=EstadoPlanMejoramiento.CUMPLIDO,
            observacion_cierre="Se cumplieron las actividades.",
        )
        assert plan_cerrado.seguimiento_vencido is False

    def test_dias_activo(self, plan):
        # fecha_inicio=2025-03-01, sin cierre → cuenta hasta hoy
        dias = plan.dias_activo
        esperado = (date.today() - date(2025, 3, 1)).days
        assert dias == esperado

    # -- Métodos de dominio --

    def test_programar_seguimiento(self, plan):
        fecha = date(2025, 4, 1)
        con_seguimiento = plan.programar_seguimiento(fecha)
        assert con_seguimiento.fecha_seguimiento == fecha
        assert plan.fecha_seguimiento is None  # intacto

    def test_programar_seguimiento_anterior_falla(self, plan):
        with pytest.raises(ValueError, match="anterior"):
            plan.programar_seguimiento(date(2025, 2, 1))

    def test_programar_seguimiento_en_plan_cerrado_falla(self, plan):
        cerrado = plan.cerrar(
            EstadoPlanMejoramiento.CUMPLIDO,
            "Completado satisfactoriamente.",
        )
        with pytest.raises(ValueError, match="cerrado"):
            cerrado.programar_seguimiento(date(2025, 5, 1))

    def test_cerrar_como_cumplido(self, plan):
        cerrado = plan.cerrar(
            EstadoPlanMejoramiento.CUMPLIDO,
            "El estudiante completó todas las actividades.",
            fecha=date(2025, 4, 30),
        )
        assert cerrado.estado == EstadoPlanMejoramiento.CUMPLIDO
        assert cerrado.esta_cerrado is True
        assert cerrado.fecha_cierre == date(2025, 4, 30)
        assert plan.estado == EstadoPlanMejoramiento.ACTIVO  # intacto

    def test_cerrar_como_incumplido(self, plan):
        cerrado = plan.cerrar(
            EstadoPlanMejoramiento.INCUMPLIDO,
            "No se presentó a las sesiones de refuerzo.",
        )
        assert cerrado.estado == EstadoPlanMejoramiento.INCUMPLIDO

    def test_cerrar_con_observacion_vacia_falla(self, plan):
        with pytest.raises(ValueError, match="obligatoria"):
            plan.cerrar(EstadoPlanMejoramiento.CUMPLIDO, "   ")

    def test_cerrar_con_estado_activo_falla(self, plan):
        with pytest.raises(ValueError, match="ACTIVO"):
            plan.cerrar(EstadoPlanMejoramiento.ACTIVO, "Razón.")

    def test_cerrar_plan_ya_cerrado_falla(self, plan):
        cerrado = plan.cerrar(EstadoPlanMejoramiento.CUMPLIDO, "Listo.")
        with pytest.raises(ValueError, match="ya fue cerrado"):
            cerrado.cerrar(EstadoPlanMejoramiento.INCUMPLIDO, "Otra razón.")

    def test_cerrar_con_fecha_anterior_al_inicio_falla(self, plan):
        with pytest.raises(ValueError, match="anterior al inicio"):
            plan.cerrar(
                EstadoPlanMejoramiento.CUMPLIDO,
                "Observación.",
                fecha=date(2025, 2, 1),
            )

    # -- DTOs --

    def test_nuevo_plan_dto(self):
        dto = NuevoPlanMejoramientoDTO(
            estudiante_id=1,
            asignacion_id=2,
            periodo_id=1,
            descripcion_dificultad="Dificultad con fracciones.",
            actividades_propuestas="Taller de fracciones equivalentes.",
        )
        plan = dto.to_plan(usuario_id=4)
        assert isinstance(plan, PlanMejoramiento)
        assert plan.usuario_id == 4

    def test_cerrar_plan_dto_estado_activo_falla(self):
        with pytest.raises(ValidationError, match="ACTIVO"):
            CerrarPlanMejoramientoDTO(
                estado=EstadoPlanMejoramiento.ACTIVO,
                observacion="Razón.",
            )

    def test_cerrar_plan_dto_observacion_vacia_falla(self):
        with pytest.raises(ValidationError, match="vacía"):
            CerrarPlanMejoramientoDTO(
                estado=EstadoPlanMejoramiento.CUMPLIDO,
                observacion="   ",
            )

    def test_filtro_habilitaciones_defecto(self):
        f = FiltroHabilitacionesDTO()
        assert f.pagina == 1
        assert f.por_pagina == 50