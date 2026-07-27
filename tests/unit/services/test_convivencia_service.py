"""Tests unitarios para ConvivenciaService."""
from __future__ import annotations

from datetime import date

import pytest

from src.domain.models.convivencia import (
    ConceptoComportamientoDTO,
    FiltroConvivenciaDTO,
    NotaComportamiento,
    NuevaNotaComportamientoDTO,
    NuevaObservacionDTO,
    NuevoRegistroComportamientoDTO,
    ObservacionPeriodo,
    RegistroComportamiento,
    TipoRegistro,
)
from src.domain.ports.convivencia_repo import IConvivenciaRepository
from src.services.convivencia_service import ConvivenciaService

# ===========================================================================
# Fake
# ===========================================================================

class FakeConvRepo(IConvivenciaRepository):
    def __init__(self):
        self._obs: dict[int, ObservacionPeriodo] = {}
        self._regs: dict[int, RegistroComportamiento] = {}
        self._notas: dict[tuple, NotaComportamiento] = {}
        self._next_obs = 1
        self._next_reg = 1
        self._next_nota = 1

    # Observaciones
    def get_observacion(self, oid: int) -> ObservacionPeriodo | None:
        return self._obs.get(oid)

    def get_observacion_por_asignacion(self, est_id: int, asig_id: int, per_id: int) -> ObservacionPeriodo | None:
        for o in self._obs.values():
            if o.estudiante_id == est_id and o.asignacion_id == asig_id and o.periodo_id == per_id:
                return o
        return None

    def listar_observaciones_por_estudiante(self, est_id: int, per_id=None, solo_publicas=False) -> list[ObservacionPeriodo]:
        return [o for o in self._obs.values() if o.estudiante_id == est_id]

    def guardar_observacion(self, o: ObservacionPeriodo) -> ObservacionPeriodo:
        o = o.model_copy(update={"id": self._next_obs})
        self._next_obs += 1
        self._obs[o.id] = o
        return o

    def actualizar_observacion(self, o: ObservacionPeriodo) -> ObservacionPeriodo:
        self._obs[o.id] = o
        return o

    def eliminar_observacion(self, oid: int) -> bool:
        return self._obs.pop(oid, None) is not None

    # Registros
    def get_registro(self, rid: int) -> RegistroComportamiento | None:
        return self._regs.get(rid)

    def listar_registros(self, filtro: FiltroConvivenciaDTO, institucion_id=None) -> list[RegistroComportamiento]:
        return list(self._regs.values())

    def contar_registros(self, filtro: FiltroConvivenciaDTO, institucion_id=None) -> int:
        return len(self._regs)

    def guardar_registro(self, r: RegistroComportamiento) -> RegistroComportamiento:
        r = r.model_copy(update={"id": self._next_reg})
        self._next_reg += 1
        self._regs[r.id] = r
        return r

    def actualizar_registro(self, r: RegistroComportamiento) -> RegistroComportamiento:
        self._regs[r.id] = r
        return r

    def eliminar_registro(self, rid: int) -> bool:
        return self._regs.pop(rid, None) is not None

    # Notas
    def get_nota(self, est_id: int, per_id: int) -> NotaComportamiento | None:
        return self._notas.get((est_id, per_id))

    def listar_notas_por_estudiante(self, est_id: int) -> list[NotaComportamiento]:
        return []

    def listar_notas_por_grupo(self, grupo_id: int, per_id: int) -> list[NotaComportamiento]:
        return [n for (e, p), n in self._notas.items() if p == per_id and n.grupo_id == grupo_id]

    def guardar_nota(self, n: NotaComportamiento) -> NotaComportamiento:
        key = (n.estudiante_id, n.periodo_id)
        self._notas[key] = n
        return n


# ===========================================================================
# Helpers
# ===========================================================================

def _make_svc() -> tuple[ConvivenciaService, FakeConvRepo]:
    repo = FakeConvRepo()
    return ConvivenciaService(repo), repo


# ===========================================================================
# Tests
# ===========================================================================

class TestRegistrarObservacion:
    def test_crea_nueva_observacion(self):
        svc, _ = _make_svc()
        dto = NuevaObservacionDTO(
            estudiante_id=1, asignacion_id=3, periodo_id=5,
            texto="Buen desempeño", es_publica=True,
        )
        obs = svc.registrar_observacion(dto)
        assert obs.id is not None

    def test_actualiza_observacion_existente(self):
        svc, _ = _make_svc()
        dto = NuevaObservacionDTO(
            estudiante_id=1, asignacion_id=3, periodo_id=5,
            texto="Texto inicial",
        )
        svc.registrar_observacion(dto)
        dto2 = NuevaObservacionDTO(
            estudiante_id=1, asignacion_id=3, periodo_id=5,
            texto="Texto actualizado",
        )
        obs = svc.registrar_observacion(dto2)
        assert obs.texto == "Texto actualizado"


class TestRegistrarComportamiento:
    def test_registra_comportamiento_fortaleza(self):
        svc, _ = _make_svc()
        dto = NuevoRegistroComportamientoDTO(
            estudiante_id=1, grupo_id=10, periodo_id=5,
            tipo=TipoRegistro.FORTALEZA,
            descripcion="Excelente participación en clase",
            fecha=date.today(),
        )
        reg = svc.registrar_comportamiento(dto)
        assert reg.id is not None
        assert reg.tipo == TipoRegistro.FORTALEZA

    def test_notificar_acudiente_exitosamente(self):
        svc, _ = _make_svc()
        dto = NuevoRegistroComportamientoDTO(
            estudiante_id=1, grupo_id=10, periodo_id=5,
            tipo=TipoRegistro.CITACION_ACUDIENTE,
            descripcion="Citación por bajo rendimiento",
            requiere_firma=True,
            fecha=date.today(),
        )
        reg = svc.registrar_comportamiento(dto)
        notificado = svc.notificar_acudiente(reg.id)
        assert notificado.acudiente_notificado is True

    def test_lanza_si_registro_no_existe(self):
        svc, _ = _make_svc()
        with pytest.raises(ValueError, match="999"):
            svc.notificar_acudiente(999)


class TestNotaComportamiento:
    def test_registra_nota_comportamiento(self):
        svc, _ = _make_svc()
        dto = NuevaNotaComportamientoDTO(
            estudiante_id=1, grupo_id=10, periodo_id=5, valor=85.0
        )
        nota = svc.registrar_nota_comportamiento(dto)
        assert nota.valor == pytest.approx(85.0)

    def test_upsert_nota_sobreescribe(self):
        svc, _ = _make_svc()
        dto1 = NuevaNotaComportamientoDTO(
            estudiante_id=1, grupo_id=10, periodo_id=5, valor=70.0
        )
        dto2 = NuevaNotaComportamientoDTO(
            estudiante_id=1, grupo_id=10, periodo_id=5, valor=85.0
        )
        svc.registrar_nota_comportamiento(dto1)
        svc.registrar_nota_comportamiento(dto2)
        nota = svc.get_nota_comportamiento(1, 5)
        assert nota.valor == pytest.approx(85.0)


# ===========================================================================
# Enforcement de autorización (convivencia_04b — defensa en profundidad)
# ===========================================================================

class _StubCatalogoSvc:
    """Stub minimal de CatalogoAcademicoService: siempre autoriza/deniega."""
    def __init__(self, autoriza: bool):
        self._autoriza = autoriza
        self.llamadas: list[tuple] = []

    def puede_gestionar_comportamiento_en_grupo(
        self, usuario_rol, usuario_id, grupo_id
    ) -> bool:
        self.llamadas.append((usuario_rol, usuario_id, grupo_id))
        return self._autoriza


class TestEnforcementAutorizacion:
    def _dto_registro(self) -> NuevoRegistroComportamientoDTO:
        return NuevoRegistroComportamientoDTO(
            estudiante_id=1, grupo_id=10, periodo_id=5,
            tipo=TipoRegistro.FORTALEZA,
            descripcion="Buen trabajo",
            fecha=date.today(),
        )

    def test_provider_deniega_lanza_permission_error_y_no_persiste(self):
        repo = FakeConvRepo()
        stub = _StubCatalogoSvc(autoriza=False)
        svc = ConvivenciaService(
            repo=repo,
            catalogo_academico_svc_provider=lambda: stub,
        )
        with pytest.raises(PermissionError):
            svc.registrar_comportamiento(
                self._dto_registro(),
                usuario_id=99,
                usuario_rol="profesor",
            )
        assert repo._regs == {}  # no persistió
        assert stub.llamadas == [("profesor", 99, 10)]

    def test_provider_autoriza_mutacion_ok(self):
        repo = FakeConvRepo()
        stub = _StubCatalogoSvc(autoriza=True)
        svc = ConvivenciaService(
            repo=repo,
            catalogo_academico_svc_provider=lambda: stub,
        )
        reg = svc.registrar_comportamiento(
            self._dto_registro(),
            usuario_id=99,
            usuario_rol="profesor",
        )
        assert reg.id is not None
        assert stub.llamadas == [("profesor", 99, 10)]

    def test_sin_provider_es_compat_retro(self):
        svc, repo = _make_svc()  # sin provider
        reg = svc.registrar_comportamiento(
            self._dto_registro(), usuario_id=99, usuario_rol="profesor",
        )
        assert reg.id is not None


# ===========================================================================
# Concepto consolidado (convivencia_05)
# ===========================================================================

class _FakeNivel:
    def __init__(self, id, nombre, rmin, rmax, descripcion=None):
        self.id = id
        self.nombre = nombre
        self.rango_min = rmin
        self.rango_max = rmax
        self.descripcion = descripcion


class _FakeConfigSvc:
    def __init__(self, niveles):
        self._niveles = niveles
    def listar_niveles(self, anio_id):
        return self._niveles


class _FakePeriodoSvc:
    class _P:
        anio_id = 2026
    def get_by_id(self, periodo_id):
        return self._P()


class _FakeEst:
    def __init__(self, id):
        self.id = id


class _FakeEstSvc:
    def __init__(self, ests):
        self._ests = ests
    def listar_por_grupo(self, grupo_id, solo_activos=True):
        return self._ests


_NIVELES = [
    _FakeNivel(1, "Bajo", 0, 59.99, "Bajo desempeño"),
    _FakeNivel(2, "Básico", 60, 69.99, "Básico"),
    _FakeNivel(3, "Alto", 70, 84.99, "Alto"),
    _FakeNivel(4, "Superior", 85, 100, "Superior"),
]


def _svc_completo(ests=None):
    repo = FakeConvRepo()
    svc = ConvivenciaService(
        repo=repo,
        configuracion_svc_provider=lambda: _FakeConfigSvc(_NIVELES),
        periodo_svc_provider=lambda: _FakePeriodoSvc(),
        estudiante_svc_provider=lambda: _FakeEstSvc(ests or []),
    )
    return svc, repo


class TestConceptoComportamiento:
    def test_sin_nota_devuelve_dto_vacio(self):
        svc, _ = _svc_completo()
        dto = svc.get_concepto_periodo(estudiante_id=1, periodo_id=5)
        assert isinstance(dto, ConceptoComportamientoDTO)
        assert dto.valor is None
        assert dto.aprobado is False
        assert dto.nivel_nombre is None
        assert dto.concepto is None

    def test_con_desempeno_id_explicito(self):
        svc, repo = _svc_completo()
        repo._notas[(1, 5)] = NotaComportamiento(
            estudiante_id=1, grupo_id=10, periodo_id=5,
            valor=65.0, desempeno_id=4, observacion="Excelente actitud",
        )
        dto = svc.get_concepto_periodo(1, 5)
        # desempeno_id=4 (Superior) prevalece sobre el rango que daría "Básico"
        assert dto.nivel_nombre == "Superior"
        assert dto.valor == 65.0
        assert dto.concepto == "Excelente actitud"
        assert dto.aprobado is True

    def test_sin_desempeno_id_resuelve_por_rango(self):
        svc, repo = _svc_completo()
        repo._notas[(1, 5)] = NotaComportamiento(
            estudiante_id=1, grupo_id=10, periodo_id=5, valor=72.5,
        )
        dto = svc.get_concepto_periodo(1, 5)
        assert dto.nivel_nombre == "Alto"
        assert dto.aprobado is True

    def test_nota_menor_a_minima_no_aprobado(self):
        svc, repo = _svc_completo()
        repo._notas[(1, 5)] = NotaComportamiento(
            estudiante_id=1, grupo_id=10, periodo_id=5, valor=55.0,
        )
        dto = svc.get_concepto_periodo(1, 5, nota_minima=60.0)
        assert dto.aprobado is False
        assert dto.nivel_nombre == "Bajo"

    def test_listar_conceptos_grupo_incluye_estudiantes_sin_nota(self):
        ests = [_FakeEst(1), _FakeEst(2), _FakeEst(3)]
        svc, repo = _svc_completo(ests=ests)
        # Solo el estudiante 2 tiene nota.
        repo._notas[(2, 5)] = NotaComportamiento(
            estudiante_id=2, grupo_id=10, periodo_id=5, valor=90.0,
        )
        conceptos = svc.listar_conceptos_grupo(grupo_id=10, periodo_id=5)
        assert len(conceptos) == 3
        by_est = {c.estudiante_id: c for c in conceptos}
        assert by_est[1].valor is None and by_est[1].aprobado is False
        assert by_est[2].valor == 90.0 and by_est[2].nivel_nombre == "Superior"
        assert by_est[3].valor is None

    # -----------------------------------------------------------------
    # convivencia_06 — Reporte por grupo/periodo
    # -----------------------------------------------------------------

    def test_reporte_periodo_grupo_combina_notas_y_observaciones(self):
        ests = [_FakeEst(1), _FakeEst(2), _FakeEst(3)]
        # Añadimos nombre/apellido dinámicamente sin acoplar el modelo real.
        for e, nom, ape in [(ests[0], "Ana", "Ruiz"), (ests[1], "Bob", "Diaz"), (ests[2], "Cyd", "Paz")]:
            e.nombre = nom
            e.apellido = ape
        svc, repo = _svc_completo(ests=ests)
        # Estudiante 1 → nota + 2 observaciones.
        repo._notas[(1, 5)] = NotaComportamiento(
            estudiante_id=1, grupo_id=10, periodo_id=5,
            valor=90.0, observacion="Excelente disciplina",
        )
        repo.guardar_observacion(ObservacionPeriodo(
            estudiante_id=1, asignacion_id=99, periodo_id=5,
            texto="Muy participativo",
        ))
        repo.guardar_observacion(ObservacionPeriodo(
            estudiante_id=1, asignacion_id=100, periodo_id=5,
            texto="Colabora con compañeros",
        ))
        # Estudiante 2 → sin nota, con 1 observación.
        repo.guardar_observacion(ObservacionPeriodo(
            estudiante_id=2, asignacion_id=99, periodo_id=5,
            texto="Debe entregar tareas a tiempo",
        ))
        # Estudiante 3 → sin nota, sin observaciones.

        filas = svc.reporte_periodo_grupo(grupo_id=10, periodo_id=5)
        assert len(filas) == 3
        by_id = {f.estudiante_id: f for f in filas}

        # Estudiante 1: nota + concepto + 2 observaciones
        assert by_id[1].valor == 90.0
        assert by_id[1].nivel_nombre == "Superior"
        assert by_id[1].concepto == "Excelente disciplina"
        assert set(by_id[1].observaciones) == {
            "Muy participativo", "Colabora con compañeros",
        }
        assert by_id[1].nombre == "Ruiz Ana"

        # Estudiante 2: sin nota, 1 observación
        assert by_id[2].valor is None
        assert by_id[2].nivel_nombre is None
        assert by_id[2].concepto is None
        assert by_id[2].observaciones == ["Debe entregar tareas a tiempo"]

        # Estudiante 3: sin nota, sin observaciones
        assert by_id[3].valor is None
        assert by_id[3].observaciones == []

    def test_reporte_periodo_grupo_sin_provider_lanza(self):
        repo = FakeConvRepo()
        svc = ConvivenciaService(repo=repo)
        with pytest.raises(RuntimeError):
            svc.reporte_periodo_grupo(grupo_id=10, periodo_id=5)

    def test_get_concepto_sin_providers_lanza(self):
        repo = FakeConvRepo()
        repo._notas[(1, 5)] = NotaComportamiento(
            estudiante_id=1, grupo_id=10, periodo_id=5, valor=70.0,
        )
        svc = ConvivenciaService(repo=repo)
        with pytest.raises(RuntimeError):
            svc.get_concepto_periodo(1, 5)


