"""Tests unitarios de NivelacionService."""
import pytest
from unittest.mock import MagicMock
from datetime import date

from src.services.nivelacion_service import NivelacionService, CalificarNotaNivelacionDTO
from src.domain.models.nivelacion import (
    ActividadNivelacion,
    CierreNivelacion,
    NotaNivelacion,
    NuevaActividadNivelacionDTO,
)
from src.domain.models.cierre import CierrePeriodo


def _act(id_, peso, asig=1, per=1):
    return ActividadNivelacion(id=id_, asignacion_id=asig, periodo_id=per,
                               nombre=f"Act {id_}", peso=peso)

def _nota(act_id, est_id, valor, asig=1, per=1):
    return NotaNivelacion(id=1, actividad_nivelacion_id=act_id,
                          estudiante_id=est_id, asignacion_id=asig,
                          periodo_id=per, valor=valor)

def _cierre_p(est_id, asig_id, per_id, nota):
    return CierrePeriodo(estudiante_id=est_id, asignacion_id=asig_id,
                         periodo_id=per_id, nota_definitiva=nota,
                         fecha_cierre=date.today())


def _make_svc(repo=None, cierre_repo=None, config_repo=None):
    return NivelacionService(
        repo=repo or MagicMock(),
        cierre_repo=cierre_repo or MagicMock(),
        config_repo=config_repo,
    )


class TestListarBajoDesempeno:
    def test_llama_repo_con_ids_y_nota_maxima(self):
        cierre_repo = MagicMock()
        cierre_repo.listar_cierres_periodo_por_asignaciones.return_value = []
        svc = _make_svc(cierre_repo=cierre_repo)
        svc.listar_bajo_desempeno([1, 2], 5, nota_maxima=59.99)
        cierre_repo.listar_cierres_periodo_por_asignaciones.assert_called_once_with(
            asignacion_ids=[1, 2], periodo_id=5, nota_maxima=59.99
        )

    def test_lista_vacia_si_no_hay_asignaciones(self):
        svc = _make_svc()
        result = svc.listar_bajo_desempeno([], 1)
        assert result == []


class TestAgregarActividad:
    def test_crea_actividad_y_notas_vacias(self):
        repo = MagicMock()
        repo.suma_pesos_actividades.return_value = 0.0
        act_creada = _act(99, 0.5)
        repo.guardar_actividad.return_value = act_creada
        repo.guardar_nota.return_value = MagicMock()

        svc = _make_svc(repo=repo)
        dto = NuevaActividadNivelacionDTO(asignacion_id=1, periodo_id=1, nombre="T1", peso=0.5)
        result = svc.agregar_actividad(dto, [10, 11])

        assert result == act_creada
        # 2 notas vacías (una por estudiante)
        assert repo.guardar_nota.call_count == 2

    def test_lanza_si_suma_pesos_supera_100(self):
        repo = MagicMock()
        repo.suma_pesos_actividades.return_value = 0.7

        svc = _make_svc(repo=repo)
        dto = NuevaActividadNivelacionDTO(asignacion_id=1, periodo_id=1, nombre="T1", peso=0.4)
        with pytest.raises(ValueError, match="supera"):
            svc.agregar_actividad(dto, [10])


class TestCalificarNota:
    def test_actualiza_nota_existente(self):
        repo = MagicMock()
        nota_existente = _nota(1, 10, None)
        repo.get_nota.return_value = nota_existente
        repo.get_cierre.return_value = None
        repo.actualizar_nota.return_value = nota_existente.model_copy(update={"valor": 75.0})

        svc = _make_svc(repo=repo)
        dto = CalificarNotaNivelacionDTO(valor=75.0)
        result = svc.calificar_nota(1, 10, dto)

        repo.actualizar_nota.assert_called_once()

    def test_lanza_si_nivelacion_cerrada(self):
        repo = MagicMock()
        repo.get_nota.return_value = _nota(1, 10, None)
        repo.get_cierre.return_value = CierreNivelacion(
            asignacion_id=1, periodo_id=1, fecha_cierre=date.today()
        )
        svc = _make_svc(repo=repo)
        with pytest.raises(ValueError, match="cerrada"):
            svc.calificar_nota(1, 10, CalificarNotaNivelacionDTO(valor=70))

    def test_lanza_si_nota_no_existe(self):
        repo = MagicMock()
        repo.get_nota.return_value = None
        svc = _make_svc(repo=repo)
        with pytest.raises(ValueError, match="No existe"):
            svc.calificar_nota(1, 10, CalificarNotaNivelacionDTO(valor=70))


class TestCerrarNivelacion:
    def _setup_repo_ok(self):
        repo = MagicMock()
        repo.get_cierre.return_value = None
        repo.listar_actividades.return_value = [_act(1, 0.4), _act(2, 0.6)]
        repo.listar_notas_por_asignacion.return_value = [
            _nota(1, 10, 70.0), _nota(2, 10, 80.0),
        ]
        cierre_guardado = CierreNivelacion(
            id=1, asignacion_id=1, periodo_id=1, fecha_cierre=date.today()
        )
        repo.guardar_cierre.return_value = cierre_guardado
        return repo

    def test_cierra_correctamente(self):
        repo = self._setup_repo_ok()
        svc = _make_svc(repo=repo)
        result = svc.cerrar_nivelacion(1, 1, usuario_id=5)
        assert result.asignacion_id == 1
        repo.guardar_cierre.assert_called_once()

    def test_lanza_si_ya_cerrada(self):
        repo = MagicMock()
        repo.get_cierre.return_value = CierreNivelacion(
            asignacion_id=1, periodo_id=1, fecha_cierre=date.today()
        )
        svc = _make_svc(repo=repo)
        with pytest.raises(ValueError, match="ya fue cerrada"):
            svc.cerrar_nivelacion(1, 1)

    def test_lanza_sin_actividades(self):
        repo = MagicMock()
        repo.get_cierre.return_value = None
        repo.listar_actividades.return_value = []
        svc = _make_svc(repo=repo)
        with pytest.raises(ValueError, match="No hay actividades"):
            svc.cerrar_nivelacion(1, 1)

    def test_lanza_si_pesos_no_suman_100(self):
        repo = MagicMock()
        repo.get_cierre.return_value = None
        repo.listar_actividades.return_value = [_act(1, 0.3), _act(2, 0.3)]
        svc = _make_svc(repo=repo)
        with pytest.raises(ValueError, match="pesos"):
            svc.cerrar_nivelacion(1, 1)

    def test_lanza_si_hay_notas_pendientes(self):
        repo = MagicMock()
        repo.get_cierre.return_value = None
        repo.listar_actividades.return_value = [_act(1, 0.5), _act(2, 0.5)]
        repo.listar_notas_por_asignacion.return_value = [
            _nota(1, 10, 70.0),
            _nota(2, 10, None),   # pendiente
        ]
        svc = _make_svc(repo=repo)
        with pytest.raises(ValueError, match="sin calificar"):
            svc.cerrar_nivelacion(1, 1)
