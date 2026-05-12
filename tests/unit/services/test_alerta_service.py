"""Tests unitarios para AlertaService."""
from __future__ import annotations

from datetime import datetime

import pytest

from src.domain.models.alerta import (
    Alerta, ConfiguracionAlerta, FiltroAlertasDTO, NivelAlerta, TipoAlerta,
)
from src.domain.ports.alerta_repo import IAlertaRepository
from src.services.alerta_service import AlertaService


# ===========================================================================
# Fake
# ===========================================================================

class FakeAlertaRepo(IAlertaRepository):
    def __init__(self):
        self._alertas: dict[int, Alerta] = {}
        self._configs: dict[tuple, ConfiguracionAlerta] = {}
        self._next_id = 1
        self._next_cfg_id = 1

    def get_configuracion(self, anio_id: int, tipo: TipoAlerta) -> ConfiguracionAlerta | None:
        return self._configs.get((anio_id, tipo))

    def listar_configuraciones(self, anio_id: int, solo_activas: bool = True) -> list[ConfiguracionAlerta]:
        return [c for k, c in self._configs.items() if k[0] == anio_id]

    def guardar_configuracion(self, cfg: ConfiguracionAlerta) -> ConfiguracionAlerta:
        key = (cfg.anio_id, cfg.tipo_alerta)
        if cfg.id is None:
            cfg = cfg.model_copy(update={"id": self._next_cfg_id})
            self._next_cfg_id += 1
        self._configs[key] = cfg
        return cfg

    def desactivar_configuracion(self, anio_id: int, tipo: TipoAlerta) -> bool:
        key = (anio_id, tipo)
        if key in self._configs:
            cfg = self._configs[key]
            self._configs[key] = cfg.model_copy(update={"activa": False})
            return True
        return False

    def get_alerta(self, aid: int) -> Alerta | None:
        return self._alertas.get(aid)

    def listar_alertas(self, filtro: FiltroAlertasDTO) -> list[Alerta]:
        return list(self._alertas.values())

    def contar_pendientes(self, est_id=None, nivel=None) -> int:
        return sum(1 for a in self._alertas.values() if not a.resuelta)

    def existe_pendiente(self, est_id: int, tipo: TipoAlerta) -> bool:
        return any(
            a.estudiante_id == est_id and a.tipo_alerta == tipo and not a.resuelta
            for a in self._alertas.values()
        )

    def guardar_alerta(self, a: Alerta) -> Alerta:
        a = a.model_copy(update={"id": self._next_id})
        self._next_id += 1
        self._alertas[a.id] = a
        return a

    def guardar_alertas_masivas(self, alertas: list[Alerta]) -> int:
        for a in alertas:
            self.guardar_alerta(a)
        return len(alertas)

    def resolver_alerta(self, aid: int, uid: int, obs=None, fecha=None) -> bool:
        if aid not in self._alertas:
            return False
        a = self._alertas[aid]
        self._alertas[aid] = a.model_copy(update={
            "resuelta": True,
            "fecha_resolucion": fecha or datetime.now(),
            "usuario_resolucion_id": uid,
            "observacion_resolucion": obs,
        })
        return True

    def resolver_alertas_de_estudiante(self, est_id: int, tipo: TipoAlerta, uid: int, obs=None) -> int:
        count = 0
        for a in list(self._alertas.values()):
            if a.estudiante_id == est_id and a.tipo_alerta == tipo and not a.resuelta:
                self.resolver_alerta(a.id, uid, obs)
                count += 1
        return count


# ===========================================================================
# Helpers
# ===========================================================================

def _make_svc() -> tuple[AlertaService, FakeAlertaRepo]:
    repo = FakeAlertaRepo()
    return AlertaService(repo), repo


def _cfg(anio_id: int = 1, tipo: TipoAlerta = TipoAlerta.FALTAS_INJUSTIFICADAS) -> ConfiguracionAlerta:
    return ConfiguracionAlerta(anio_id=anio_id, tipo_alerta=tipo, umbral=3.0)


# ===========================================================================
# Tests
# ===========================================================================

class TestConfigurarAlerta:
    def test_guarda_configuracion(self):
        svc, _ = _make_svc()
        cfg = svc.configurar_alerta(_cfg())
        assert cfg.id is not None

    def test_desactiva_configuracion(self):
        svc, repo = _make_svc()
        svc.configurar_alerta(_cfg())
        resultado = svc.desactivar_configuracion(1, TipoAlerta.FALTAS_INJUSTIFICADAS)
        assert resultado is True

    def test_listar_configuraciones(self):
        svc, _ = _make_svc()
        svc.configurar_alerta(_cfg(1, TipoAlerta.FALTAS_INJUSTIFICADAS))
        svc.configurar_alerta(_cfg(1, TipoAlerta.PROMEDIO_BAJO))
        cfgs = svc.listar_configuraciones(anio_id=1)
        assert len(cfgs) == 2


class TestResolverAlerta:
    def test_resuelve_alerta_existente(self):
        svc, repo = _make_svc()
        alerta = repo.guardar_alerta(Alerta(
            estudiante_id=1,
            tipo_alerta=TipoAlerta.FALTAS_INJUSTIFICADAS,
            nivel=NivelAlerta.ADVERTENCIA,
            descripcion="Test",
        ))
        resultado = svc.resolver_alerta(alerta.id, usuario_id=99)
        assert resultado is True

    def test_lanza_si_alerta_no_existe(self):
        svc, _ = _make_svc()
        with pytest.raises(ValueError, match="999"):
            svc.resolver_alerta(999, usuario_id=1)

    def test_lanza_si_ya_resuelta(self):
        svc, repo = _make_svc()
        alerta = repo.guardar_alerta(Alerta(
            estudiante_id=1,
            tipo_alerta=TipoAlerta.FALTAS_INJUSTIFICADAS,
            nivel=NivelAlerta.ADVERTENCIA,
            descripcion="Test",
        ))
        svc.resolver_alerta(alerta.id, usuario_id=99)
        with pytest.raises(ValueError, match="ya está resuelta"):
            svc.resolver_alerta(alerta.id, usuario_id=99)


class TestContarPendientes:
    def test_cuenta_alertas_pendientes(self):
        svc, repo = _make_svc()
        repo.guardar_alerta(Alerta(
            estudiante_id=1, tipo_alerta=TipoAlerta.FALTAS_INJUSTIFICADAS,
            nivel=NivelAlerta.ADVERTENCIA, descripcion="Test1",
        ))
        repo.guardar_alerta(Alerta(
            estudiante_id=2, tipo_alerta=TipoAlerta.PROMEDIO_BAJO,
            nivel=NivelAlerta.CRITICA, descripcion="Test2",
        ))
        assert svc.contar_pendientes() == 2
