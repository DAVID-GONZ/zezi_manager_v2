"""Tests unitarios para ConvivenciaService."""
from __future__ import annotations

from datetime import date

import pytest

from src.domain.models.convivencia import (
    FiltroConvivenciaDTO, NotaComportamiento,
    NuevaNotaComportamientoDTO, NuevaObservacionDTO,
    NuevoRegistroComportamientoDTO, ObservacionPeriodo,
    RegistroComportamiento, TipoRegistro,
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

    def listar_registros(self, filtro: FiltroConvivenciaDTO) -> list[RegistroComportamiento]:
        return list(self._regs.values())

    def contar_registros(self, filtro: FiltroConvivenciaDTO) -> int:
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
        return []

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
