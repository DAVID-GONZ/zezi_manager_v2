"""
Tests de integración — todos los repositorios SQLite.

Usa las fixtures db_seed / db_conn / seed_result definidas en conftest.py.
Cada test recibe una BD en memoria nueva con datos de seed_test aplicados.
"""
from __future__ import annotations

import pytest
from datetime import date, datetime


# ─────────────────────────────────────────────────────────────────────────────
# Importaciones de repositorios
# ─────────────────────────────────────────────────────────────────────────────
from src.infrastructure.db.repositories import (
    SqliteAcudienteRepository,
    SqliteAlertaRepository,
    SqliteAsignacionRepository,
    SqliteAsistenciaRepository,
    SqliteAuditoriaRepository,
    SqliteCierreRepository,
    SqliteConfiguracionRepository,
    SqliteConvivenciaRepository,
    SqliteEstadisticosRepository,
    SqliteEstudianteRepository,
    SqliteEvaluacionRepository,
    SqliteHabilitacionRepository,
    SqliteInfraestructuraRepository,
    SqlitePeriodoRepository,
    SqliteUsuarioRepository,
)

# ─────────────────────────────────────────────────────────────────────────────
# Importaciones de modelos
# ─────────────────────────────────────────────────────────────────────────────
from src.domain.models.acudiente import Acudiente, EstudianteAcudiente, Parentesco, TipoDocumentoAcudiente
from src.domain.models.alerta import Alerta, ConfiguracionAlerta, FiltroAlertasDTO, NivelAlerta, TipoAlerta
from src.domain.models.asignacion import Asignacion, FiltroAsignacionesDTO
from src.domain.models.asistencia import ControlDiario, EstadoAsistencia
from src.domain.models.auditoria import AccionCambio, EventoSesion, FiltroAuditoriaDTO, RegistroCambio, TipoEventoSesion
from src.domain.models.cierre import CierreAnio, CierrePeriodo, EstadoPromocion, PromocionAnual
from src.domain.models.convivencia import FiltroConvivenciaDTO, NotaComportamiento, ObservacionPeriodo, RegistroComportamiento, TipoRegistro
from src.domain.models.evaluacion import Actividad, Categoria, EstadoActividad, Nota, PuntosExtra, TipoPuntosExtra
from src.domain.models.habilitacion import EstadoHabilitacion, EstadoPlanMejoramiento, FiltroHabilitacionesDTO, Habilitacion, PlanMejoramiento, TipoHabilitacion
from src.domain.models.infraestructura import AreaConocimiento, Asignatura, Grupo, Jornada
from src.domain.models.periodo import HitoPeriodo, Periodo, TipoHito
from src.domain.models.usuario import FiltroUsuariosDTO, Rol, Usuario


# =============================================================================
# SqliteUsuarioRepository
# =============================================================================

class TestSqliteUsuarioRepository:

    def test_get_by_username(self, db_conn, seed_result):
        repo = SqliteUsuarioRepository(conn=db_conn)
        usuario = repo.get_by_username("admin_test")
        assert usuario is not None
        assert usuario.rol == Rol.ADMIN

    def test_get_by_id(self, db_conn, seed_result):
        repo = SqliteUsuarioRepository(conn=db_conn)
        uid = seed_result.usuario_ids["prof_test"]
        usuario = repo.get_by_id(uid)
        assert usuario is not None
        assert usuario.rol == Rol.PROFESOR

    def test_existe_usuario(self, db_conn, seed_result):
        repo = SqliteUsuarioRepository(conn=db_conn)
        assert repo.existe_usuario("prof_test") is True
        assert repo.existe_usuario("no_existe_xyz") is False

    def test_listar_filtrado_activos(self, db_conn, seed_result):
        repo = SqliteUsuarioRepository(conn=db_conn)
        usuarios = repo.listar_filtrado(FiltroUsuariosDTO(solo_activos=True))
        assert len(usuarios) >= 3

    def test_listar_filtrado_por_rol(self, db_conn, seed_result):
        repo = SqliteUsuarioRepository(conn=db_conn)
        profesores = repo.listar_filtrado(FiltroUsuariosDTO(rol=Rol.PROFESOR))
        assert all(u.rol == Rol.PROFESOR for u in profesores)

    def test_guardar_usuario(self, db_conn, seed_result):
        repo = SqliteUsuarioRepository(conn=db_conn)
        nuevo = Usuario(
            usuario="nuevo_test",
            nombre_completo="Nuevo Usuario",
            email="nuevo@test.co",
            rol=Rol.PROFESOR,
            activo=True,
            fecha_creacion=date.today(),
        )
        guardado = repo.guardar(nuevo)
        assert guardado.id is not None
        recuperado = repo.get_by_username("nuevo_test")
        assert recuperado is not None

    def test_actualizar_usuario(self, db_conn, seed_result):
        repo = SqliteUsuarioRepository(conn=db_conn)
        uid = seed_result.usuario_ids["prof_test"]
        usuario = repo.get_by_id(uid)
        actualizado = usuario.model_copy(update={"telefono": "3001234567"})
        repo.actualizar(actualizado)
        recuperado = repo.get_by_id(uid)
        assert recuperado.telefono == "3001234567"

    def test_desactivar_reactivar(self, db_conn, seed_result):
        repo = SqliteUsuarioRepository(conn=db_conn)
        uid = seed_result.usuario_ids["prof_test"]
        assert repo.desactivar(uid) is True
        assert repo.get_by_id(uid).activo is False
        assert repo.reactivar(uid) is True
        assert repo.get_by_id(uid).activo is True


# =============================================================================
# SqliteEstudianteRepository
# =============================================================================

class TestSqliteEstudianteRepository:

    def test_get_by_id(self, db_conn, seed_result):
        repo = SqliteEstudianteRepository(conn=db_conn)
        eid = seed_result.estudiante_ids[0]
        est = repo.get_by_id(eid)
        assert est is not None
        assert est.id == eid

    def test_get_by_documento(self, db_conn, seed_result):
        repo = SqliteEstudianteRepository(conn=db_conn)
        eid = seed_result.estudiante_ids[0]
        est = repo.get_by_id(eid)
        encontrado = repo.get_by_documento(est.numero_documento)
        assert encontrado is not None
        assert encontrado.id == eid

    def test_existe_documento(self, db_conn, seed_result):
        repo = SqliteEstudianteRepository(conn=db_conn)
        eid = seed_result.estudiante_ids[0]
        est = repo.get_by_id(eid)
        assert repo.existe_documento(est.numero_documento) is True
        assert repo.existe_documento("9999999999") is False

    def test_listar_por_grupo(self, db_conn, seed_result):
        repo = SqliteEstudianteRepository(conn=db_conn)
        gid = seed_result.grupo_ids[0]
        estudiantes = repo.listar_por_grupo(gid)
        assert len(estudiantes) == 3

    def test_contar_por_grupo(self, db_conn, seed_result):
        repo = SqliteEstudianteRepository(conn=db_conn)
        gid = seed_result.grupo_ids[0]
        assert repo.contar_por_grupo(gid) == 3

    def test_get_resumen(self, db_conn, seed_result):
        repo = SqliteEstudianteRepository(conn=db_conn)
        eid = seed_result.estudiante_ids[0]
        resumen = repo.get_resumen(eid)
        assert resumen is not None
        assert resumen.id == eid
        assert resumen.nombre_completo != ""

    def test_listar_resumenes(self, db_conn, seed_result):
        from src.domain.models.estudiante import FiltroEstudiantesDTO
        repo = SqliteEstudianteRepository(conn=db_conn)
        gid = seed_result.grupo_ids[0]
        resumenes = repo.listar_resumenes(FiltroEstudiantesDTO(grupo_id=gid))
        assert len(resumenes) == 3


# =============================================================================
# SqliteAcudienteRepository
# =============================================================================

class TestSqliteAcudienteRepository:

    def _crear_acudiente(self, db_conn, estudiante_id: int) -> Acudiente:
        repo = SqliteAcudienteRepository(conn=db_conn)
        ac = Acudiente(
            tipo_documento=TipoDocumentoAcudiente.CC,
            numero_documento="88888888",
            nombre_completo="Acudiente Prueba",
            parentesco=Parentesco.MADRE,
            celular="3009999999",
        )
        guardado = repo.guardar(ac)
        repo.vincular(EstudianteAcudiente(
            estudiante_id=estudiante_id,
            acudiente_id=guardado.id,
            es_principal=True,
        ))
        return guardado

    def test_guardar_y_get_by_id(self, db_conn, seed_result):
        repo = SqliteAcudienteRepository(conn=db_conn)
        ac = Acudiente(
            tipo_documento=TipoDocumentoAcudiente.CC,
            numero_documento="77777777",
            nombre_completo="Prueba Acudiente",
            parentesco=Parentesco.PADRE,
        )
        guardado = repo.guardar(ac)
        assert guardado.id is not None
        recuperado = repo.get_by_id(guardado.id)
        assert recuperado.nombre_completo == "Prueba Acudiente"

    def test_vincular_y_listar(self, db_conn, seed_result):
        eid = seed_result.estudiante_ids[0]
        guardado = self._crear_acudiente(db_conn, eid)
        repo = SqliteAcudienteRepository(conn=db_conn)
        lista = repo.listar_por_estudiante(eid)
        assert any(a.id == guardado.id for a in lista)

    def test_get_principal(self, db_conn, seed_result):
        eid = seed_result.estudiante_ids[0]
        guardado = self._crear_acudiente(db_conn, eid)
        repo = SqliteAcudienteRepository(conn=db_conn)
        principal = repo.get_principal(eid)
        assert principal is not None
        assert principal.id == guardado.id

    def test_establecer_principal(self, db_conn, seed_result):
        repo = SqliteAcudienteRepository(conn=db_conn)
        eid = seed_result.estudiante_ids[1]
        ac1 = repo.guardar(Acudiente(
            tipo_documento=TipoDocumentoAcudiente.CC,
            numero_documento="11111111",
            nombre_completo="Acudiente 1",
            parentesco=Parentesco.MADRE,
        ))
        ac2 = repo.guardar(Acudiente(
            tipo_documento=TipoDocumentoAcudiente.CC,
            numero_documento="22222222",
            nombre_completo="Acudiente 2",
            parentesco=Parentesco.PADRE,
        ))
        repo.vincular(EstudianteAcudiente(estudiante_id=eid, acudiente_id=ac1.id, es_principal=True))
        repo.vincular(EstudianteAcudiente(estudiante_id=eid, acudiente_id=ac2.id, es_principal=False))
        repo.establecer_principal(eid, ac2.id)
        principal = repo.get_principal(eid)
        assert principal.id == ac2.id


# =============================================================================
# SqliteAsignacionRepository
# =============================================================================

class TestSqliteAsignacionRepository:

    def test_get_by_id(self, db_conn, seed_result):
        repo = SqliteAsignacionRepository(conn=db_conn)
        aid = seed_result.asignacion_ids[0]
        asig = repo.get_by_id(aid)
        assert asig is not None
        assert asig.id == aid

    def test_existe(self, db_conn, seed_result):
        repo = SqliteAsignacionRepository(conn=db_conn)
        aid = seed_result.asignacion_ids[0]
        asig = repo.get_by_id(aid)
        assert repo.existe(asig.grupo_id, asig.asignatura_id, asig.usuario_id, asig.periodo_id) is True
        assert repo.existe(9999, 9999, 9999, 9999) is False

    def test_get_info(self, db_conn, seed_result):
        repo = SqliteAsignacionRepository(conn=db_conn)
        aid = seed_result.asignacion_ids[0]
        info = repo.get_info(aid)
        assert info is not None
        assert info.asignacion_id == aid
        assert info.grupo_codigo != ""
        assert info.asignatura_nombre != ""
        assert info.docente_nombre != ""

    def test_listar_por_grupo(self, db_conn, seed_result):
        repo = SqliteAsignacionRepository(conn=db_conn)
        gid = seed_result.grupo_ids[0]
        pid = seed_result.periodo_ids[0]
        infos = repo.listar_por_grupo(gid, pid)
        assert len(infos) >= 1

    def test_listar_por_docente(self, db_conn, seed_result):
        repo = SqliteAsignacionRepository(conn=db_conn)
        uid = seed_result.usuario_ids["prof_test"]
        infos = repo.listar_por_docente(uid)
        assert len(infos) >= 1

    def test_desactivar_reactivar(self, db_conn, seed_result):
        repo = SqliteAsignacionRepository(conn=db_conn)
        aid = seed_result.asignacion_ids[0]
        assert repo.desactivar(aid) is True
        assert repo.get_by_id(aid).activo is False
        assert repo.reactivar(aid) is True
        assert repo.get_by_id(aid).activo is True


# =============================================================================
# SqliteEvaluacionRepository
# =============================================================================

class TestSqliteEvaluacionRepository:

    def test_listar_categorias(self, db_conn, seed_result):
        repo = SqliteEvaluacionRepository(conn=db_conn)
        aid = seed_result.asignacion_ids[0]
        pid = seed_result.periodo_ids[0]
        cats = repo.listar_categorias(aid, pid)
        assert len(cats) >= 1

    def test_guardar_categoria(self, db_conn, seed_result):
        repo = SqliteEvaluacionRepository(conn=db_conn)
        aid = seed_result.asignacion_ids[0]
        # Usar periodo_ids[1]: el seed solo crea categorías para el primer periodo
        pid = seed_result.periodo_ids[1]
        cat = Categoria(nombre="Test Cat", peso=0.10, asignacion_id=aid, periodo_id=pid)
        guardada = repo.guardar_categoria(cat)
        assert guardada.id is not None

    def test_suma_pesos_otras(self, db_conn, seed_result):
        repo = SqliteEvaluacionRepository(conn=db_conn)
        aid = seed_result.asignacion_ids[0]
        pid = seed_result.periodo_ids[0]
        suma = repo.suma_pesos_otras(aid, pid)
        assert 0 <= suma <= 1.0

    def test_listar_actividades(self, db_conn, seed_result):
        repo = SqliteEvaluacionRepository(conn=db_conn)
        aid = seed_result.asignacion_ids[0]
        pid = seed_result.periodo_ids[0]
        acts = repo.listar_actividades(aid, pid)
        assert len(acts) >= 1

    def test_guardar_nota_y_get(self, db_conn, seed_result):
        repo = SqliteEvaluacionRepository(conn=db_conn)
        aid = seed_result.asignacion_ids[0]
        pid = seed_result.periodo_ids[0]
        eid = seed_result.estudiante_ids[0]
        acts = repo.listar_actividades(aid, pid)
        assert acts, "No hay actividades en seed"
        act_id = acts[0].id
        nota = Nota(estudiante_id=eid, actividad_id=act_id, valor=85.0)
        guardada = repo.guardar_nota(nota)
        recuperada = repo.get_nota(eid, act_id)
        assert recuperada is not None
        assert recuperada.valor == 85.0

    def test_guardar_notas_masivas(self, db_conn, seed_result):
        repo = SqliteEvaluacionRepository(conn=db_conn)
        aid = seed_result.asignacion_ids[0]
        pid = seed_result.periodo_ids[0]
        acts = repo.listar_actividades(aid, pid)
        if not acts:
            pytest.skip("Sin actividades en seed")
        act_id = acts[0].id
        notas = [
            Nota(estudiante_id=eid, actividad_id=act_id, valor=float(70 + i * 5))
            for i, eid in enumerate(seed_result.estudiante_ids)
        ]
        count = repo.guardar_notas_masivas(notas)
        assert count == len(notas)

    def test_guardar_puntos_extra(self, db_conn, seed_result):
        repo = SqliteEvaluacionRepository(conn=db_conn)
        aid = seed_result.asignacion_ids[0]
        pid = seed_result.periodo_ids[0]
        eid = seed_result.estudiante_ids[0]
        pe = PuntosExtra(
            estudiante_id=eid, asignacion_id=aid, periodo_id=pid,
            tipo=TipoPuntosExtra.PARTICIPACION, positivos=3,
        )
        guardado = repo.guardar_puntos_extra(pe)
        assert guardado.id is not None
        recuperado = repo.get_puntos_extra(eid, aid, pid, TipoPuntosExtra.PARTICIPACION)
        assert recuperado is not None
        assert recuperado.positivos == 3

    def test_listar_resultados_grupo(self, db_conn, seed_result):
        repo = SqliteEvaluacionRepository(conn=db_conn)
        gid = seed_result.grupo_ids[0]
        aid = seed_result.asignacion_ids[0]
        pid = seed_result.periodo_ids[0]
        resultados = repo.listar_resultados_grupo(gid, aid, pid)
        assert len(resultados) == 3


# =============================================================================
# SqliteAsistenciaRepository
# =============================================================================

class TestSqliteAsistenciaRepository:

    def _make_control(self, estudiante_id, grupo_id, asignacion_id, periodo_id, estado="P"):
        return ControlDiario(
            estudiante_id=estudiante_id,
            grupo_id=grupo_id,
            asignacion_id=asignacion_id,
            periodo_id=periodo_id,
            fecha=date(2025, 3, 10),
            estado=EstadoAsistencia(estado),
        )

    def test_registrar_y_get(self, db_conn, seed_result):
        repo = SqliteAsistenciaRepository(conn=db_conn)
        eid = seed_result.estudiante_ids[0]
        gid = seed_result.grupo_ids[0]
        aid = seed_result.asignacion_ids[0]
        pid = seed_result.periodo_ids[0]
        ctrl = self._make_control(eid, gid, aid, pid)
        guardado = repo.registrar(ctrl)
        recuperado = repo.get_por_fecha_estudiante(eid, aid, date(2025, 3, 10))
        assert recuperado is not None
        assert recuperado.estado == EstadoAsistencia.PRESENTE

    def test_registrar_masivo(self, db_conn, seed_result):
        repo = SqliteAsistenciaRepository(conn=db_conn)
        gid = seed_result.grupo_ids[0]
        aid = seed_result.asignacion_ids[0]
        pid = seed_result.periodo_ids[0]
        controles = [
            self._make_control(eid, gid, aid, pid)
            for eid in seed_result.estudiante_ids
        ]
        count = repo.registrar_masivo(controles)
        assert count == 3

    def test_resumen_por_estudiante(self, db_conn, seed_result):
        repo = SqliteAsistenciaRepository(conn=db_conn)
        eid = seed_result.estudiante_ids[0]
        gid = seed_result.grupo_ids[0]
        aid = seed_result.asignacion_ids[0]
        pid = seed_result.periodo_ids[0]
        repo.registrar(self._make_control(eid, gid, aid, pid, "FI"))
        resumen = repo.resumen_por_estudiante(eid, pid)
        assert resumen.estudiante_id == eid
        assert resumen.total_clases >= 1

    def test_contar_faltas_injustificadas(self, db_conn, seed_result):
        repo = SqliteAsistenciaRepository(conn=db_conn)
        eid = seed_result.estudiante_ids[0]
        gid = seed_result.grupo_ids[0]
        aid = seed_result.asignacion_ids[0]
        pid = seed_result.periodo_ids[0]
        repo.registrar(self._make_control(eid, gid, aid, pid, "FI"))
        count = repo.contar_faltas_injustificadas(eid, pid)
        assert count >= 1

    def test_fechas_con_registro(self, db_conn, seed_result):
        repo = SqliteAsistenciaRepository(conn=db_conn)
        eid = seed_result.estudiante_ids[0]
        gid = seed_result.grupo_ids[0]
        aid = seed_result.asignacion_ids[0]
        pid = seed_result.periodo_ids[0]
        repo.registrar(self._make_control(eid, gid, aid, pid))
        fechas = repo.fechas_con_registro(aid, pid)
        assert date(2025, 3, 10) in fechas


# =============================================================================
# SqliteCierreRepository
# =============================================================================

class TestSqliteCierreRepository:

    def test_guardar_y_get_cierre_periodo(self, db_conn, seed_result):
        repo = SqliteCierreRepository(conn=db_conn)
        eid = seed_result.estudiante_ids[0]
        aid = seed_result.asignacion_ids[0]
        pid = seed_result.periodo_ids[0]
        cierre = CierrePeriodo(
            estudiante_id=eid, asignacion_id=aid, periodo_id=pid,
            nota_definitiva=75.0, fecha_cierre=date(2025, 4, 15),
        )
        guardado = repo.guardar_cierre_periodo(cierre)
        assert guardado.id is not None
        recuperado = repo.get_cierre_periodo(eid, aid, pid)
        assert recuperado is not None
        assert recuperado.nota_definitiva == 75.0

    def test_upsert_cierre_periodo(self, db_conn, seed_result):
        repo = SqliteCierreRepository(conn=db_conn)
        eid = seed_result.estudiante_ids[0]
        aid = seed_result.asignacion_ids[0]
        pid = seed_result.periodo_ids[0]
        c1 = CierrePeriodo(estudiante_id=eid, asignacion_id=aid, periodo_id=pid,
                           nota_definitiva=70.0, fecha_cierre=date(2025, 4, 15))
        repo.guardar_cierre_periodo(c1)
        c2 = CierrePeriodo(estudiante_id=eid, asignacion_id=aid, periodo_id=pid,
                           nota_definitiva=80.0, fecha_cierre=date(2025, 4, 15))
        repo.guardar_cierre_periodo(c2)
        recuperado = repo.get_cierre_periodo(eid, aid, pid)
        assert recuperado.nota_definitiva == 80.0  # reemplazó

    def test_guardar_y_get_cierre_anio(self, db_conn, seed_result):
        repo = SqliteCierreRepository(conn=db_conn)
        eid = seed_result.estudiante_ids[0]
        aid = seed_result.asignacion_ids[0]
        anio_id = seed_result.anio_id
        cierre = CierreAnio(
            estudiante_id=eid, asignacion_id=aid, anio_id=anio_id,
            nota_promedio_periodos=72.0, nota_definitiva_anual=72.0,
            perdio=False, fecha_cierre=date(2025, 12, 1),
        )
        guardado = repo.guardar_cierre_anio(cierre)
        assert guardado.id is not None
        recuperado = repo.get_cierre_anio(eid, aid, anio_id)
        assert recuperado.nota_definitiva_anual == 72.0

    def test_guardar_y_actualizar_promocion(self, db_conn, seed_result):
        repo = SqliteCierreRepository(conn=db_conn)
        eid = seed_result.estudiante_ids[0]
        anio_id = seed_result.anio_id
        promo = PromocionAnual(estudiante_id=eid, anio_id=anio_id)
        guardada = repo.guardar_promocion(promo)
        assert guardada.id is not None
        decidida = guardada.decidir(EstadoPromocion.PROMOVIDO, usuario_id=1)
        repo.actualizar_promocion(decidida)
        recuperada = repo.get_promocion(eid, anio_id)
        assert recuperada.estado == EstadoPromocion.PROMOVIDO


# =============================================================================
# SqliteHabilitacionRepository
# =============================================================================

class TestSqliteHabilitacionRepository:

    def test_guardar_y_get_habilitacion(self, db_conn, seed_result):
        repo = SqliteHabilitacionRepository(conn=db_conn)
        eid = seed_result.estudiante_ids[0]
        aid = seed_result.asignacion_ids[0]
        pid = seed_result.periodo_ids[0]
        hab = Habilitacion(
            estudiante_id=eid, asignacion_id=aid, periodo_id=pid,
            tipo=TipoHabilitacion.PERIODO,
        )
        guardada = repo.guardar_habilitacion(hab)
        assert guardada.id is not None
        recuperada = repo.get_habilitacion(guardada.id)
        assert recuperada.estado == EstadoHabilitacion.PENDIENTE

    def test_existe_habilitacion(self, db_conn, seed_result):
        repo = SqliteHabilitacionRepository(conn=db_conn)
        eid = seed_result.estudiante_ids[1]
        aid = seed_result.asignacion_ids[0]
        pid = seed_result.periodo_ids[0]
        assert repo.existe_habilitacion(eid, aid, TipoHabilitacion.PERIODO, pid) is False
        hab = Habilitacion(estudiante_id=eid, asignacion_id=aid, periodo_id=pid,
                           tipo=TipoHabilitacion.PERIODO)
        repo.guardar_habilitacion(hab)
        assert repo.existe_habilitacion(eid, aid, TipoHabilitacion.PERIODO, pid) is True

    def test_actualizar_estado_habilitacion(self, db_conn, seed_result):
        repo = SqliteHabilitacionRepository(conn=db_conn)
        eid = seed_result.estudiante_ids[2]
        aid = seed_result.asignacion_ids[0]
        pid = seed_result.periodo_ids[0]
        hab = Habilitacion(estudiante_id=eid, asignacion_id=aid, periodo_id=pid,
                           tipo=TipoHabilitacion.PERIODO)
        guardada = repo.guardar_habilitacion(hab)
        assert repo.actualizar_estado_habilitacion(guardada.id, EstadoHabilitacion.REALIZADA)

    def test_guardar_y_actualizar_plan(self, db_conn, seed_result):
        repo = SqliteHabilitacionRepository(conn=db_conn)
        eid = seed_result.estudiante_ids[0]
        aid = seed_result.asignacion_ids[0]
        pid = seed_result.periodo_ids[0]
        plan = PlanMejoramiento(
            estudiante_id=eid, asignacion_id=aid, periodo_id=pid,
            descripcion_dificultad="Dificultad en álgebra",
            actividades_propuestas="Ejercicios adicionales",
        )
        guardado = repo.guardar_plan(plan)
        assert guardado.id is not None
        recuperado = repo.get_plan(guardado.id)
        assert recuperado.estado == EstadoPlanMejoramiento.ACTIVO


# =============================================================================
# SqliteConvivenciaRepository
# =============================================================================

class TestSqliteConvivenciaRepository:

    def test_guardar_y_get_observacion(self, db_conn, seed_result):
        repo = SqliteConvivenciaRepository(conn=db_conn)
        eid = seed_result.estudiante_ids[0]
        aid = seed_result.asignacion_ids[0]
        pid = seed_result.periodo_ids[0]
        obs = ObservacionPeriodo(
            estudiante_id=eid, asignacion_id=aid, periodo_id=pid,
            texto="Buen desempeño general.",
        )
        guardada = repo.guardar_observacion(obs)
        assert guardada.id is not None
        recuperada = repo.get_observacion(guardada.id)
        assert recuperada.texto == "Buen desempeño general."

    def test_guardar_y_listar_registros(self, db_conn, seed_result):
        repo = SqliteConvivenciaRepository(conn=db_conn)
        eid = seed_result.estudiante_ids[0]
        gid = seed_result.grupo_ids[0]
        pid = seed_result.periodo_ids[0]
        reg = RegistroComportamiento(
            estudiante_id=eid, grupo_id=gid, periodo_id=pid,
            tipo=TipoRegistro.FORTALEZA, descripcion="Participa activamente.",
            fecha=date(2025, 3, 5),
        )
        guardado = repo.guardar_registro(reg)
        assert guardado.id is not None
        lista = repo.listar_registros(FiltroConvivenciaDTO(estudiante_id=eid))
        assert any(r.id == guardado.id for r in lista)

    def test_guardar_nota_comportamiento(self, db_conn, seed_result):
        repo = SqliteConvivenciaRepository(conn=db_conn)
        eid = seed_result.estudiante_ids[0]
        gid = seed_result.grupo_ids[0]
        pid = seed_result.periodo_ids[0]
        nota = NotaComportamiento(
            estudiante_id=eid, grupo_id=gid, periodo_id=pid, valor=88.0
        )
        guardada = repo.guardar_nota(nota)
        recuperada = repo.get_nota(eid, pid)
        assert recuperada is not None
        assert recuperada.valor == 88.0

    def test_upsert_nota_comportamiento(self, db_conn, seed_result):
        repo = SqliteConvivenciaRepository(conn=db_conn)
        eid = seed_result.estudiante_ids[1]
        gid = seed_result.grupo_ids[0]
        pid = seed_result.periodo_ids[0]
        repo.guardar_nota(NotaComportamiento(estudiante_id=eid, grupo_id=gid, periodo_id=pid, valor=70.0))
        repo.guardar_nota(NotaComportamiento(estudiante_id=eid, grupo_id=gid, periodo_id=pid, valor=90.0))
        recuperada = repo.get_nota(eid, pid)
        assert recuperada.valor == 90.0


# =============================================================================
# SqliteAlertaRepository
# =============================================================================

class TestSqliteAlertaRepository:

    def test_guardar_config_y_get(self, db_conn, seed_result):
        repo = SqliteAlertaRepository(conn=db_conn)
        anio_id = seed_result.anio_id
        cfg = repo.get_configuracion(anio_id, TipoAlerta.FALTAS_INJUSTIFICADAS)
        # El seed ya inserta configuraciones
        assert cfg is not None

    def test_guardar_alerta_y_get(self, db_conn, seed_result):
        repo = SqliteAlertaRepository(conn=db_conn)
        eid = seed_result.estudiante_ids[0]
        alerta = Alerta(
            estudiante_id=eid,
            tipo_alerta=TipoAlerta.FALTAS_INJUSTIFICADAS,
            nivel=NivelAlerta.ADVERTENCIA,
            descripcion="3 faltas injustificadas acumuladas.",
        )
        guardada = repo.guardar_alerta(alerta)
        assert guardada.id is not None
        recuperada = repo.get_alerta(guardada.id)
        assert recuperada.resuelta is False

    def test_existe_pendiente(self, db_conn, seed_result):
        repo = SqliteAlertaRepository(conn=db_conn)
        eid = seed_result.estudiante_ids[0]
        assert repo.existe_pendiente(eid, TipoAlerta.PROMEDIO_BAJO) is False
        repo.guardar_alerta(Alerta(
            estudiante_id=eid, tipo_alerta=TipoAlerta.PROMEDIO_BAJO,
            nivel=NivelAlerta.CRITICA, descripcion="Promedio bajo.",
        ))
        assert repo.existe_pendiente(eid, TipoAlerta.PROMEDIO_BAJO) is True

    def test_resolver_alerta(self, db_conn, seed_result):
        repo = SqliteAlertaRepository(conn=db_conn)
        eid = seed_result.estudiante_ids[0]
        guardada = repo.guardar_alerta(Alerta(
            estudiante_id=eid, tipo_alerta=TipoAlerta.MATERIAS_EN_RIESGO,
            nivel=NivelAlerta.ADVERTENCIA, descripcion="Varias materias en riesgo.",
        ))
        uid = seed_result.usuario_ids["prof_test"]
        assert repo.resolver_alerta(guardada.id, uid) is True
        recuperada = repo.get_alerta(guardada.id)
        assert recuperada.resuelta is True

    def test_guardar_alertas_masivas(self, db_conn, seed_result):
        repo = SqliteAlertaRepository(conn=db_conn)
        alertas = [
            Alerta(
                estudiante_id=eid,
                tipo_alerta=TipoAlerta.HABILITACION_PENDIENTE,
                nivel=NivelAlerta.INFO,
                descripcion=f"Habilitación pendiente est {eid}.",
            )
            for eid in seed_result.estudiante_ids
        ]
        count = repo.guardar_alertas_masivas(alertas)
        assert count == 3

    def test_contar_pendientes(self, db_conn, seed_result):
        repo = SqliteAlertaRepository(conn=db_conn)
        eid = seed_result.estudiante_ids[0]
        repo.guardar_alerta(Alerta(
            estudiante_id=eid, tipo_alerta=TipoAlerta.PLAN_MEJORAMIENTO_VENCIDO,
            nivel=NivelAlerta.ADVERTENCIA, descripcion="Plan vencido.",
        ))
        count = repo.contar_pendientes(estudiante_id=eid)
        assert count >= 1


# =============================================================================
# SqliteAuditoriaRepository
# =============================================================================

class TestSqliteAuditoriaRepository:

    def test_registrar_evento(self, db_conn, seed_result):
        repo = SqliteAuditoriaRepository(conn=db_conn)
        uid = seed_result.usuario_ids["admin_test"]
        evento = EventoSesion(
            usuario="admin_test",
            usuario_id=uid,
            tipo_evento=TipoEventoSesion.LOGIN_EXITOSO,
            ip_address="127.0.0.1",
        )
        guardado = repo.registrar_evento(evento)
        assert guardado.id is not None

    def test_listar_eventos(self, db_conn, seed_result):
        repo = SqliteAuditoriaRepository(conn=db_conn)
        uid = seed_result.usuario_ids["admin_test"]
        repo.registrar_evento(EventoSesion(
            usuario="admin_test", usuario_id=uid,
            tipo_evento=TipoEventoSesion.LOGIN_EXITOSO,
        ))
        eventos = repo.listar_eventos(FiltroAuditoriaDTO(usuario_id=uid))
        assert len(eventos) >= 1

    def test_get_ultimo_login(self, db_conn, seed_result):
        repo = SqliteAuditoriaRepository(conn=db_conn)
        uid = seed_result.usuario_ids["prof_test"]
        repo.registrar_evento(EventoSesion(
            usuario="prof_test", usuario_id=uid,
            tipo_evento=TipoEventoSesion.LOGIN_EXITOSO,
        ))
        ultimo = repo.get_ultimo_login(uid)
        assert ultimo is not None

    def test_contar_fallos_recientes(self, db_conn, seed_result):
        repo = SqliteAuditoriaRepository(conn=db_conn)
        uid = seed_result.usuario_ids["prof_test"]
        repo.registrar_evento(EventoSesion(
            usuario="prof_test", usuario_id=uid,
            tipo_evento=TipoEventoSesion.LOGIN_FALLIDO,
        ))
        count = repo.contar_fallos_recientes("prof_test", ventana_minutos=60)
        assert count >= 1

    def test_registrar_cambio(self, db_conn, seed_result):
        repo = SqliteAuditoriaRepository(conn=db_conn)
        cambio = RegistroCambio(
            usuario_id=seed_result.usuario_ids["admin_test"],
            accion=AccionCambio.CREATE,
            tabla="estudiantes",
            registro_id=1,
            valor_nuevo='{"nombre": "Test"}',
        )
        guardado = repo.registrar_cambio(cambio)
        assert guardado.id is not None

    def test_registrar_cambios_masivos(self, db_conn, seed_result):
        repo = SqliteAuditoriaRepository(conn=db_conn)
        uid = seed_result.usuario_ids["admin_test"]
        cambios = [
            RegistroCambio(usuario_id=uid, accion=AccionCambio.UPDATE,
                           tabla="notas", registro_id=i, valor_nuevo=f'{{"valor": {i}}}')
            for i in range(1, 4)
        ]
        count = repo.registrar_cambios_masivos(cambios)
        assert count == 3


# =============================================================================
# SqliteInfraestructuraRepository
# =============================================================================

class TestSqliteInfraestructuraRepository:

    def test_listar_areas(self, db_conn, seed_result):
        repo = SqliteInfraestructuraRepository(conn=db_conn)
        areas = repo.listar_areas()
        assert len(areas) >= 1

    def test_guardar_area(self, db_conn, seed_result):
        repo = SqliteInfraestructuraRepository(conn=db_conn)
        area = AreaConocimiento(nombre="Nuevas Tecnologías", codigo="NT")
        guardada = repo.guardar_area(area)
        assert guardada.id is not None
        recuperada = repo.get_area(guardada.id)
        assert recuperada.nombre == "Nuevas Tecnologías"

    def test_listar_asignaturas(self, db_conn, seed_result):
        repo = SqliteInfraestructuraRepository(conn=db_conn)
        asigs = repo.listar_asignaturas()
        assert len(asigs) >= 1

    def test_get_grupo(self, db_conn, seed_result):
        repo = SqliteInfraestructuraRepository(conn=db_conn)
        gid = seed_result.grupo_ids[0]
        grupo = repo.get_grupo(gid)
        assert grupo is not None
        assert grupo.id == gid

    def test_guardar_grupo(self, db_conn, seed_result):
        repo = SqliteInfraestructuraRepository(conn=db_conn)
        grupo = Grupo(codigo="902", nombre="Noveno B", grado=9, jornada=Jornada.UNICA)
        guardado = repo.guardar_grupo(grupo)
        assert guardado.id is not None


# =============================================================================
# SqlitePeriodoRepository
# =============================================================================

class TestSqlitePeriodoRepository:

    def test_get_by_id(self, db_conn, seed_result):
        repo = SqlitePeriodoRepository(conn=db_conn)
        pid = seed_result.periodo_ids[0]
        periodo = repo.get_by_id(pid)
        assert periodo is not None
        assert periodo.id == pid

    def test_get_activo(self, db_conn, seed_result):
        repo = SqlitePeriodoRepository(conn=db_conn)
        periodo = repo.get_activo(seed_result.anio_id)
        # Debe haber al menos uno activo creado por el seed
        assert periodo is not None

    def test_listar_por_anio(self, db_conn, seed_result):
        repo = SqlitePeriodoRepository(conn=db_conn)
        periodos = repo.listar_por_anio(seed_result.anio_id)
        assert len(periodos) >= 1

    def test_suma_pesos_otros(self, db_conn, seed_result):
        repo = SqlitePeriodoRepository(conn=db_conn)
        suma = repo.suma_pesos_otros(seed_result.anio_id)
        assert suma >= 0

    def test_guardar_hito(self, db_conn, seed_result):
        repo = SqlitePeriodoRepository(conn=db_conn)
        pid = seed_result.periodo_ids[0]
        hito = HitoPeriodo(
            periodo_id=pid,
            tipo=TipoHito.ENTREGA_BOLETINES,
            descripcion="Entrega de boletín P1",
            fecha_limite=date(2025, 4, 20),
        )
        guardado = repo.guardar_hito(hito)
        assert guardado.id is not None
        recuperado = repo.get_hito(guardado.id)
        assert recuperado.tipo == TipoHito.ENTREGA_BOLETINES


# =============================================================================
# SqliteConfiguracionRepository
# =============================================================================

class TestSqliteConfiguracionRepository:

    def test_get_anio_activo(self, db_conn, seed_result):
        repo = SqliteConfiguracionRepository(conn=db_conn)
        anio = repo.get_activa()
        assert anio is not None

    def test_get_anio_by_id(self, db_conn, seed_result):
        repo = SqliteConfiguracionRepository(conn=db_conn)
        anio = repo.get_by_id(seed_result.anio_id)
        assert anio is not None
        assert anio.id == seed_result.anio_id

    def test_listar_niveles(self, db_conn, seed_result):
        repo = SqliteConfiguracionRepository(conn=db_conn)
        niveles = repo.listar_niveles(seed_result.anio_id)
        assert len(niveles) == 4  # seed_test crea 4 niveles

    def test_get_criterios_promocion(self, db_conn, seed_result):
        repo = SqliteConfiguracionRepository(conn=db_conn)
        criterios = repo.get_criterios(seed_result.anio_id)
        assert criterios is not None


# =============================================================================
# SqliteEstadisticosRepository
# =============================================================================

class TestSqliteEstadisticosRepository:

    def test_calcular_metricas_dashboard(self, db_conn, seed_result):
        repo = SqliteEstadisticosRepository(conn=db_conn)
        gid = seed_result.grupo_ids[0]
        pid = seed_result.periodo_ids[0]
        metrics = repo.calcular_metricas_dashboard(gid, pid)
        assert metrics.grupo_id == gid
        assert metrics.total_estudiantes == 3

    def test_promedio_general_grupo(self, db_conn, seed_result):
        repo = SqliteEstadisticosRepository(conn=db_conn)
        gid = seed_result.grupo_ids[0]
        pid = seed_result.periodo_ids[0]
        promedio = repo.promedio_general_grupo(gid, pid)
        assert 0.0 <= promedio <= 100.0

    def test_porcentaje_asistencia_global(self, db_conn, seed_result):
        repo = SqliteEstadisticosRepository(conn=db_conn)
        gid = seed_result.grupo_ids[0]
        pid = seed_result.periodo_ids[0]
        pct = repo.porcentaje_asistencia_global(gid, pid)
        assert 0.0 <= pct <= 100.0

    def test_ranking_grupo(self, db_conn, seed_result):
        repo = SqliteEstadisticosRepository(conn=db_conn)
        gid = seed_result.grupo_ids[0]
        pid = seed_result.periodo_ids[0]
        ranking = repo.ranking_grupo(gid, pid)
        assert len(ranking) == 3
        assert all("posicion" in r and "nombre_completo" in r for r in ranking)

    def test_distribucion_estados_asistencia(self, db_conn, seed_result):
        repo = SqliteEstadisticosRepository(conn=db_conn)
        gid = seed_result.grupo_ids[0]
        aid = seed_result.asignacion_ids[0]
        pid = seed_result.periodo_ids[0]
        dist = repo.distribucion_estados_asistencia(gid, aid, pid)
        assert set(dist.keys()) == {"P", "FJ", "FI", "R", "E"}

    def test_consolidado_notas_grupo(self, db_conn, seed_result):
        repo = SqliteEstadisticosRepository(conn=db_conn)
        gid = seed_result.grupo_ids[0]
        pid = seed_result.periodo_ids[0]
        consolidado = repo.consolidado_notas_grupo(gid, pid)
        assert len(consolidado) == 3
        assert all("nombre_completo" in r for r in consolidado)

    def test_consolidado_asistencia_grupo(self, db_conn, seed_result):
        repo = SqliteEstadisticosRepository(conn=db_conn)
        gid = seed_result.grupo_ids[0]
        pid = seed_result.periodo_ids[0]
        consolidado = repo.consolidado_asistencia_grupo(gid, pid)
        # Puede ser 0 si no hay asistencias registradas en el seed_test
        assert isinstance(consolidado, list)

    def test_contar_alertas_pendientes(self, db_conn, seed_result):
        repo = SqliteEstadisticosRepository(conn=db_conn)
        gid = seed_result.grupo_ids[0]
        count = repo.contar_alertas_pendientes(gid)
        assert count >= 0


if __name__ == "__main__":
    import sys
    
    print("\n" + "="*80)
    print(" INICIANDO PRUEBAS DE INTEGRACION: REPOSITORIOS SQLITE ".center(80))
    print("="*80 + "\n")
    
    # Ejecuta pytest sobre este mismo archivo para mostrar los resultados 
    # de consola de forma detallada y amigable.
    sys.exit(pytest.main(["-v", "-s", "--tb=short", __file__]))
