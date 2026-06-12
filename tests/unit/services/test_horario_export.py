"""Tests de plantilla_filas y filas_exportables."""
import pytest
from unittest.mock import MagicMock
from src.services.horario_service import HorarioService, COLUMNAS_HORARIO


class FakeAsigInfo:
    def __init__(self, asignacion_id, grupo_codigo, asignatura_nombre, docente_nombre,
                 grupo_id=1, asignatura_id=1, usuario_id=1):
        self.asignacion_id = asignacion_id
        self.grupo_codigo = grupo_codigo
        self.asignatura_nombre = asignatura_nombre
        self.docente_nombre = docente_nombre
        self.grupo_id = grupo_id
        self.asignatura_id = asignatura_id
        self.usuario_id = usuario_id


class FakeHorarioInfo:
    def __init__(self, id, grupo_id, asignatura_id, usuario_id, asignacion_id,
                 escenario_id, grupo_codigo, asignatura_nombre, docente_nombre,
                 dia_semana, hora_inicio, hora_fin, sala="Aula"):
        self.id = id
        self.grupo_id = grupo_id
        self.asignatura_id = asignatura_id
        self.usuario_id = usuario_id
        self.asignacion_id = asignacion_id
        self.escenario_id = escenario_id
        self.grupo_codigo = grupo_codigo
        self.asignatura_nombre = asignatura_nombre
        self.docente_nombre = docente_nombre
        self.dia_semana = dia_semana
        self.hora_inicio = hora_inicio
        self.hora_fin = hora_fin
        self.sala = sala


def _make_service(asig_infos=None, bloques=None):
    infra = MagicMock()
    infra.listar_horario_escenario.return_value = bloques or []
    asig_repo = MagicMock()
    asig_repo.listar_info.return_value = asig_infos or []
    usuario = MagicMock()
    usuario.carga_horaria_max.return_value = None
    return HorarioService(infra, asig_repo, usuario)


def test_plantilla_filas_columnas():
    """plantilla_filas retorna filas con exactamente COLUMNAS_HORARIO."""
    asigs = [FakeAsigInfo(1, "10A", "Matemáticas", "Prof. García")]
    svc = _make_service(asig_infos=asigs)
    filas = svc.plantilla_filas(periodo_id=1)
    assert len(filas) == 1
    assert set(filas[0].keys()) == set(COLUMNAS_HORARIO)


def test_plantilla_filas_tres_asignaciones():
    """Una fila por asignación activa."""
    asigs = [
        FakeAsigInfo(1, "10A", "Matemáticas", "Prof. A"),
        FakeAsigInfo(2, "10B", "Lengua", "Prof. B"),
        FakeAsigInfo(3, "11A", "Historia", "Prof. C"),
    ]
    svc = _make_service(asig_infos=asigs)
    filas = svc.plantilla_filas(periodo_id=1)
    assert len(filas) == 3


def test_plantilla_filas_dia_hora_vacios():
    """dia_semana, hora_inicio, hora_fin vacíos; sala='Aula'."""
    asigs = [FakeAsigInfo(1, "10A", "Matemáticas", "Prof. García")]
    svc = _make_service(asig_infos=asigs)
    fila = svc.plantilla_filas(periodo_id=1)[0]
    assert fila["dia_semana"] == ""
    assert fila["hora_inicio"] == ""
    assert fila["hora_fin"] == ""
    assert fila["sala"] == "Aula"


def test_plantilla_filas_sin_asignaciones():
    """Sin asignaciones activas retorna lista vacía."""
    svc = _make_service(asig_infos=[])
    assert svc.plantilla_filas(periodo_id=1) == []


def test_filas_exportables_dos_bloques():
    """filas_exportables retorna una fila por bloque con COLUMNAS_HORARIO."""
    bloques = [
        FakeHorarioInfo(1, 1, 1, 1, 10, 5, "10A", "Matemáticas", "Prof. A", "lunes", "08:00", "09:00"),
        FakeHorarioInfo(2, 2, 2, 2, 11, 5, "10B", "Lengua", "Prof. B", "martes", "10:00", "11:00"),
    ]
    svc = _make_service(bloques=bloques)
    filas = svc.filas_exportables(escenario_id=5)
    assert len(filas) == 2
    assert set(filas[0].keys()) == set(COLUMNAS_HORARIO)


def test_filas_exportables_filtro_grupo():
    """filtro grupo_id solo devuelve bloques del grupo."""
    bloques = [
        FakeHorarioInfo(1, 1, 1, 1, 10, 5, "10A", "Matemáticas", "Prof. A", "lunes", "08:00", "09:00"),
        FakeHorarioInfo(2, 2, 2, 2, 11, 5, "10B", "Lengua", "Prof. B", "martes", "10:00", "11:00"),
    ]
    svc = _make_service(bloques=bloques)
    filas = svc.filas_exportables(escenario_id=5, grupo_id=1)
    assert len(filas) == 1
    assert filas[0]["grupo"] == "10A"


def test_filas_exportables_escenario_vacio():
    """Escenario sin bloques retorna lista vacía."""
    svc = _make_service(bloques=[])
    assert svc.filas_exportables(escenario_id=99) == []
