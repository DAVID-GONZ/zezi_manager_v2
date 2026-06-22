"""
Tests unitarios para HorarioService.analizar_lote / aplicar_lote.

Usa FakeRepos en memoria. No toca la BD.
Cubre los 6 casos especificados en paso_14f.
"""
from __future__ import annotations

import pytest
from datetime import time

from src.domain.models.asignacion import Asignacion
from src.domain.models.infraestructura import (
    Asignatura,
    DiaSemana,
    Horario,
    HorarioInfo,
)
from src.domain.ports.asignacion_repo import IAsignacionRepository
from src.domain.ports.infraestructura_repo import IInfraestructuraRepository
from src.services.horario_service import HorarioService


# ===========================================================================
# Constantes
# ===========================================================================

ESCENARIO_ID  = 1
PERIODO_ID    = 1
ASIG_ID_A     = 10   # docente 3, grupo 2, asignatura 5
ASIG_ID_B     = 11   # docente 3, grupo 2, asignatura 6  (mismo docente, otro grupo)
USUARIO_ID    = 3
GRUPO_ID_A    = 2
GRUPO_ID_B    = 4
ASIGNATURA_ID_A = 5
ASIGNATURA_ID_B = 6


# ===========================================================================
# Fake repos
# ===========================================================================

class FakeInfraRepoLote(IInfraestructuraRepository):
    """Implementación mínima en memoria para tests de carga masiva."""

    def __init__(self, bloques_existentes=None, asignaturas=None):
        self._bloques: list[HorarioInfo] = bloques_existentes or []
        self._asignaturas: dict[int, Asignatura] = asignaturas or {}
        self.guardados: list[Horario] = []

    # --- métodos relevantes para analizar_lote / aplicar_lote ---

    def listar_horario_escenario(self, escenario_id: int) -> list:
        return self._bloques

    def contar_bloques_asignacion(self, escenario_id: int, asignacion_id: int) -> int:
        return sum(1 for b in self._bloques if getattr(b, "asignacion_id", None) == asignacion_id)

    def contar_bloques_docente(self, escenario_id: int, usuario_id: int) -> int:
        return sum(1 for b in self._bloques if b.usuario_id == usuario_id)

    def crear_bloques_masivo(self, horarios: list) -> int:
        self.guardados.extend(horarios)
        return len(horarios)

    def get_asignatura(self, asignatura_id: int) -> Asignatura | None:
        return self._asignaturas.get(asignatura_id)

    # --- stubs abstractos restantes ---

    def get_escenario(self, *a): return None
    def listar_escenarios(self, *a): return []
    def get_escenario_activo(self, *a): return None
    def crear_escenario(self, esc): return esc
    def actualizar_escenario(self, esc): return esc
    def activar_escenario(self, *a): pass
    def eliminar_escenario(self, *a): return True
    def duplicar_escenario(self, *a): raise NotImplementedError
    def listar_horario_grupo_escenario(self, *a): return []
    def get_area(self, *a): return None
    def listar_areas(self): return []
    def guardar_area(self, area): return area
    def actualizar_area(self, area): return area
    def eliminar_area(self, *a): return False
    def actualizar_color_area(self, *a): return False
    def listar_asignaturas(self, area_id=None, institucion_id=None): return []
    def guardar_asignatura(self, a): return a
    def actualizar_asignatura(self, a): return a
    def eliminar_asignatura(self, *a): return False
    def get_grupo(self, *a): return None
    def get_grupo_por_codigo(self, *a): return None
    def listar_grupos(self, grado=None, institucion_id=None): return []
    def guardar_grupo(self, g): return g
    def asignar_sala_a_grupo(self, *a): return True
    def actualizar_grupo(self, g): return g
    def eliminar_grupo(self, *a): return False
    def get_horario(self, *a): return None
    def get_info_horario(self, *a): return None
    def listar_horario_grupo(self, *a): return []
    def listar_horario_docente(self, *a): return []
    def existe_conflicto_horario(self, *a, **kw): return False
    def get_estadisticas(self, *a): raise NotImplementedError
    def guardar_horario(self, h): return h
    def actualizar_horario(self, h): return h
    def eliminar_horario(self, *a): return True
    def existe_cruce(self, *a, **kw): return False
    def eliminar_horarios_por_asignacion(self, *a): return 0
    def get_logro(self, *a): return None
    def listar_logros(self, *a): return []
    def guardar_logro(self, logro): return logro
    def actualizar_logro(self, logro): return logro
    def eliminar_logro(self, *a): return False
    def crear_plantilla_franja(self, p): return p
    def get_plantilla_franja(self, *a): return None
    def listar_plantillas_franja(self, institucion_id=None): return []
    def get_plantilla_activa(self, *a): return None
    def actualizar_plantilla_franja(self, p): return p
    def activar_plantilla_franja(self, *a): pass
    def eliminar_plantilla_franja(self, *a): return True
    def crear_franja(self, f): return f
    def listar_franjas(self, *a): return []
    def actualizar_franja(self, f): return f
    def eliminar_franja(self, *a): return True
    def reemplazar_franjas(self, plantilla_id, franjas): return len(franjas)
    # paso_15b stubs
    def upsert_disponibilidad(self, d): return d
    def listar_disponibilidad_docente(self, usuario_id): return []
    def es_disponible(self, usuario_id, dia, franja_orden): return True
    def limpiar_disponibilidad_docente(self, usuario_id): return 0
    def cargar_disponibilidad_lote(self, usuario_id, slots): return 0
    def reemplazar_disponibilidad_docente(self, usuario_id, slots): return 0
    def crear_config_generacion(self, c): return c
    def get_config_generacion(self, config_id): return None
    def listar_configs_generacion(self, periodo_id=None): return []
    def actualizar_config_generacion(self, c): return c
    def eliminar_config_generacion(self, config_id): return True
    def cambiar_estado_config(self, config_id, nuevo_estado): return None
    def duplicar_config_generacion(self, config_id): return None
    # paso_17 stubs
    def listar_salas(self, institucion_id=None): return []
    def get_sala(self, *a): return None
    def crear_sala(self, sala): return sala
    def actualizar_sala(self, sala): return sala
    def eliminar_sala(self, *a): return False
    def listar_ventanas_grupo(self): return []
    def get_ventanas_por_grupo(self, *a): return []
    def get_ventanas_por_grado(self, *a): return []
    def crear_ventana_grupo(self, v): return v
    def eliminar_ventana_grupo(self, *a): return False
    def listar_bloques_anclados(self, *a): return []
    def crear_bloque_anclado(self, b): return b
    def eliminar_bloque_anclado(self, *a): return False
    def listar_franjas_reunion(self): return []
    def get_franja_reunion(self, *a): return None
    def crear_franja_reunion(self, f): return f
    def actualizar_franja_reunion(self, f): return f
    def eliminar_franja_reunion(self, *a): return False
    def get_limites_docente(self, *a): return None
    def set_limites_docente(self, limites): return limites
    def listar_limites_docente(self): return []
    def listar_grados(self): return []
    def upsert_grado(self, g): return g
    def eliminar_grado(self, numero): return False
    def listar_plan_estudios(self): return []
    def get_plan_estudios_por_grado(self, grado): return []
    def set_horas_plan(self, grado, asignatura_id, horas): return None
    def eliminar_plan_estudios(self, grado, asignatura_id): return False


class FakeAsignacionRepoLote(IAsignacionRepository):
    """Implementación mínima en memoria para tests de carga masiva."""

    def __init__(self, asignaciones=None):
        self._asigs: dict[int, Asignacion] = {a.id: a for a in (asignaciones or [])}

    def get_by_id(self, asignacion_id: int) -> Asignacion | None:
        return self._asigs.get(asignacion_id)

    def listar(self, filtro): return []
    def existe(self, *a): return False
    def get_info(self, *a): return None
    def listar_info(self, *a): return []
    def listar_por_grupo(self, *a, **kw): return []
    def listar_por_docente(self, *a, **kw): return []
    def guardar(self, a): return a
    def desactivar(self, *a): return True
    def reactivar(self, *a): return True
    def reasignar_docente(self, *a): return True


class FakeUsuarioRepoLote:
    """Stub de usuario repo con carga_horaria_max configurable."""

    def __init__(self, carga_max: int | None = None):
        self._carga_max = carga_max

    def carga_horaria_max(self, usuario_id: int) -> int | None:
        return self._carga_max


# ===========================================================================
# Helpers
# ===========================================================================

def _asig(asig_id: int, usuario_id: int, grupo_id: int, asignatura_id: int,
          activo: bool = True) -> Asignacion:
    return Asignacion(
        id=asig_id,
        grupo_id=grupo_id,
        asignatura_id=asignatura_id,
        usuario_id=usuario_id,
        periodo_id=PERIODO_ID,
        activo=activo,
    )


def _asignatura(asig_id: int, horas: int = 5) -> Asignatura:
    return Asignatura(id=asig_id, nombre=f"Materia {asig_id}", horas_semanales=horas)


def _fila(asig_id: int, dia: str = "Lunes", hi: str = "07:00",
          hf: str = "07:55", sala: str = "Aula") -> dict:
    return {
        "asignacion_id": str(asig_id),
        "dia_semana": dia,
        "hora_inicio": hi,
        "hora_fin": hf,
        "sala": sala,
    }


def _make_service(
    bloques_existentes=None,
    asignaciones=None,
    asignaturas=None,
    carga_max: int | None = None,
) -> HorarioService:
    infra = FakeInfraRepoLote(
        bloques_existentes=bloques_existentes,
        asignaturas={a.id: a for a in (asignaturas or [])},
    )
    asig_repo = FakeAsignacionRepoLote(asignaciones=asignaciones)
    usuario_repo = FakeUsuarioRepoLote(carga_max=carga_max)
    return HorarioService(infra, asig_repo, usuario_repo)


# Pequeño helper para construir un HorarioInfo mínimo que sirva como bloque existente
def _bloque_existente(
    usuario_id: int,
    grupo_id: int,
    dia: str,
    hora_inicio: str,
    hora_fin: str,
    sala: str = "Aula",
    asignacion_id: int | None = None,
) -> HorarioInfo:
    return HorarioInfo(
        id=1,
        grupo_id=grupo_id,
        grupo_codigo="G01",
        asignatura_id=1,
        asignatura_nombre="Test",
        usuario_id=usuario_id,
        docente_nombre="Docente Test",
        asignacion_id=asignacion_id,
        periodo_id=None,
        periodo_nombre="",
        escenario_id=ESCENARIO_ID,
        dia_semana=DiaSemana(dia),
        hora_inicio=time(*map(int, hora_inicio.split(":"))),
        hora_fin=time(*map(int, hora_fin.split(":"))),
        sala=sala,
    )


# ===========================================================================
# Tests
# ===========================================================================

class TestAnalizarLote:

    def test_fila_sin_asignacion_valida(self):
        """Fila con asignacion_id=999 (no existe) → ok=False."""
        svc = _make_service()
        filas = [_fila(asig_id=999)]

        reporte = svc.analizar_lote(ESCENARIO_ID, PERIODO_ID, filas)

        assert len(reporte.filas) == 1
        assert reporte.filas[0].ok is False
        assert reporte.invalidas == 1
        assert reporte.validas == 0

    def test_cruce_interno_lote(self):
        """Dos filas, mismo docente, mismo día y hora solapada → segunda fila ok=False."""
        asignacion_a = _asig(ASIG_ID_A, USUARIO_ID, GRUPO_ID_A, ASIGNATURA_ID_A)
        asignacion_b = _asig(ASIG_ID_B, USUARIO_ID, GRUPO_ID_B, ASIGNATURA_ID_B)
        asignatura_a = _asignatura(ASIGNATURA_ID_A, horas=5)
        asignatura_b = _asignatura(ASIGNATURA_ID_B, horas=5)
        svc = _make_service(
            asignaciones=[asignacion_a, asignacion_b],
            asignaturas=[asignatura_a, asignatura_b],
        )
        filas = [
            _fila(ASIG_ID_A, "Lunes", "07:00", "07:55"),
            _fila(ASIG_ID_B, "Lunes", "07:00", "07:55"),  # mismo docente, solapado
        ]

        reporte = svc.analizar_lote(ESCENARIO_ID, PERIODO_ID, filas)

        assert reporte.filas[0].ok is True
        assert reporte.filas[1].ok is False
        assert "docente" in (reporte.filas[1].motivo or "").lower()

    def test_tope_docente_acumulado(self):
        """Docente con carga_horaria_max=2, ya tiene 2 bloques existentes → fila nueva ok=False."""
        asignacion = _asig(ASIG_ID_A, USUARIO_ID, GRUPO_ID_A, ASIGNATURA_ID_A)
        asignatura = _asignatura(ASIGNATURA_ID_A, horas=10)  # tope materia holgado
        # Simular 2 bloques existentes del mismo docente
        bloques = [
            _bloque_existente(USUARIO_ID, GRUPO_ID_A, "Lunes", "07:00", "07:55"),
            _bloque_existente(USUARIO_ID, GRUPO_ID_A, "Martes", "07:00", "07:55"),
        ]
        svc = _make_service(
            bloques_existentes=bloques,
            asignaciones=[asignacion],
            asignaturas=[asignatura],
            carga_max=2,
        )
        filas = [_fila(ASIG_ID_A, "Miércoles", "07:00", "07:55")]

        reporte = svc.analizar_lote(ESCENARIO_ID, PERIODO_ID, filas)

        assert reporte.filas[0].ok is False
        assert "docente" in (reporte.filas[0].motivo or "").lower()


class TestAplicarLote:

    def test_todo_o_nada_no_persiste_con_errores(self):
        """Lote con 1 válida y 1 error, solo_validas=False → creados=0."""
        asignacion = _asig(ASIG_ID_A, USUARIO_ID, GRUPO_ID_A, ASIGNATURA_ID_A)
        asignatura = _asignatura(ASIGNATURA_ID_A, horas=5)
        svc = _make_service(
            asignaciones=[asignacion],
            asignaturas=[asignatura],
        )
        filas = [
            _fila(ASIG_ID_A, "Lunes", "07:00", "07:55"),  # válida
            _fila(asig_id=999, dia="Martes"),               # inválida (asig no existe)
        ]

        resultado = svc.aplicar_lote(ESCENARIO_ID, PERIODO_ID, filas, solo_validas=False)

        assert resultado.creados == 0
        assert resultado.omitidos == len(filas)

    def test_solo_validas_persiste_subconjunto(self):
        """Mismo lote, solo_validas=True → creados=1."""
        asignacion = _asig(ASIG_ID_A, USUARIO_ID, GRUPO_ID_A, ASIGNATURA_ID_A)
        asignatura = _asignatura(ASIGNATURA_ID_A, horas=5)
        svc = _make_service(
            asignaciones=[asignacion],
            asignaturas=[asignatura],
        )
        filas = [
            _fila(ASIG_ID_A, "Lunes", "07:00", "07:55"),  # válida
            _fila(asig_id=999, dia="Martes"),               # inválida
        ]

        resultado = svc.aplicar_lote(ESCENARIO_ID, PERIODO_ID, filas, solo_validas=True)

        assert resultado.creados == 1

    def test_conteos_correctos(self):
        """creados + omitidos == len(filas) siempre."""
        asignacion = _asig(ASIG_ID_A, USUARIO_ID, GRUPO_ID_A, ASIGNATURA_ID_A)
        asignatura = _asignatura(ASIGNATURA_ID_A, horas=5)
        svc = _make_service(
            asignaciones=[asignacion],
            asignaturas=[asignatura],
        )
        filas = [
            _fila(ASIG_ID_A, "Lunes", "07:00", "07:55"),
            _fila(ASIG_ID_A, "Martes", "07:00", "07:55"),
            _fila(asig_id=999),
        ]

        resultado = svc.aplicar_lote(ESCENARIO_ID, PERIODO_ID, filas, solo_validas=True)

        assert resultado.creados + resultado.omitidos == len(filas)


def test_ida_vuelta_exportar_y_reanalizar():
    """filas_exportables → analizar_lote sobre escenario vacío → todo ok."""
    from src.services.horario_service import COLUMNAS_HORARIO, _dia_str, _hora_str
    asig = _asig(asig_id=1, usuario_id=5, grupo_id=10, asignatura_id=20)

    class FakeInfraConBloque:
        def listar_horario_escenario(self, escenario_id):
            class B:
                id = 1; grupo_id = 10; asignatura_id = 20; usuario_id = 5
                asignacion_id = 1; escenario_id = 99; grupo_codigo = "10A"
                asignatura_nombre = "Matemáticas"; docente_nombre = "Prof. A"
                dia_semana = "lunes"; hora_inicio = "08:00"; hora_fin = "09:00"; sala = "Aula"
            return [B()] if escenario_id == 99 else []

        def existe_cruce(self, *a, **kw): return False
        def contar_bloques_asignacion(self, *a, **kw): return 0
        def contar_bloques_docente(self, *a, **kw): return 0
        def get_asignatura(self, asignatura_id):
            class Sub:
                horas_semanales = 5
            return Sub()
        def crear_bloques_masivo(self, horarios): return len(horarios)
        def get_horario(self, id): return None
        def guardar_horario(self, h): return h
        def actualizar_horario(self, h): return h
        def eliminar_horario(self, id): return True

    class FakeAsigRepoIda:
        def listar_info(self, filtro): return []
        def get_by_id(self, id):
            return asig if id == 1 else None

    infra_bloque = FakeInfraConBloque()
    asig_repo = FakeAsigRepoIda()
    usuario_repo = FakeUsuarioRepoLote()
    svc = HorarioService(infra_bloque, asig_repo, usuario_repo)

    # Exportar filas del escenario 99
    filas_exp = svc.filas_exportables(escenario_id=99)
    assert len(filas_exp) == 1

    # Analizar sobre escenario vacío (escenario_id=100)
    class FakeInfraVacio(FakeInfraConBloque):
        def listar_horario_escenario(self, escenario_id): return []

    svc2 = HorarioService(FakeInfraVacio(), asig_repo, usuario_repo)
    reporte = svc2.analizar_lote(escenario_id=100, periodo_id=1, filas=filas_exp)
    assert reporte.todo_ok, [f.motivo for f in reporte.filas if not f.ok]
