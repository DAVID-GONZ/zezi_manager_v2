"""
Tests unitarios para HorarioService.

Usa FakeRepos para no tocar la BD.
Cubre las reglas R2–R10 definidas en la spec paso_14b.
"""
from __future__ import annotations

import pytest
from datetime import time

from src.domain.models.asignacion import Asignacion
from src.domain.models.infraestructura import (
    Asignatura,
    CupoDTO,
    DiaSemana,
    Horario,
)
from src.domain.ports.asignacion_repo import IAsignacionRepository
from src.domain.ports.infraestructura_repo import IInfraestructuraRepository
from src.services.horario_service import HorarioService


# ===========================================================================
# Fake repos
# ===========================================================================

class FakeInfraRepo(IInfraestructuraRepository):
    """Implementación mínima en memoria para tests."""

    def __init__(self):
        self._horarios: dict[int, Horario] = {}
        self._asignaturas: dict[int, Asignatura] = {}
        self._next_id = 1
        # control de cruces: (escenario_id, dia, h_inicio, h_fin, usuario_id?, grupo_id?, sala?) → bool
        self._cruce_result: bool = False
        self._bloques_asignacion: int = 0
        self._bloques_docente: int = 0

    # --- métodos relevantes para HorarioService ---

    def guardar_horario(self, horario: Horario) -> Horario:
        h = horario.model_copy(update={"id": self._next_id})
        self._next_id += 1
        self._horarios[h.id] = h
        return h

    def get_horario(self, horario_id: int) -> Horario | None:
        return self._horarios.get(horario_id)

    def actualizar_horario(self, horario: Horario) -> Horario:
        self._horarios[horario.id] = horario
        return horario

    def eliminar_horario(self, horario_id: int) -> bool:
        return bool(self._horarios.pop(horario_id, None))

    def get_asignatura(self, asignatura_id: int) -> Asignatura | None:
        return self._asignaturas.get(asignatura_id)

    def existe_cruce(
        self,
        escenario_id: int,
        dia_semana: str,
        hora_inicio: str,
        hora_fin: str,
        *,
        usuario_id=None,
        grupo_id=None,
        sala=None,
        excluir_horario_id=None,
    ) -> bool:
        return self._cruce_result

    def contar_bloques_asignacion(self, escenario_id: int, asignacion_id: int) -> int:
        return self._bloques_asignacion

    def contar_bloques_docente(self, escenario_id: int, usuario_id: int) -> int:
        return self._bloques_docente

    # --- métodos abstractos restantes (no usados en estos tests) ---

    def get_escenario(self, escenario_id): return None
    def listar_escenarios(self, anio_id): return []
    def get_escenario_activo(self, anio_id): return None
    def crear_escenario(self, esc): return esc
    def actualizar_escenario(self, esc): return esc
    def activar_escenario(self, escenario_id): pass
    def eliminar_escenario(self, escenario_id): return False
    def duplicar_escenario(self, escenario_id, nuevo_nombre): raise NotImplementedError
    def listar_horario_grupo_escenario(self, grupo_id, escenario_id): return []
    def listar_horario_escenario(self, escenario_id): return []
    def get_area(self, area_id): return None
    def listar_areas(self): return []
    def guardar_area(self, area): return area
    def actualizar_area(self, area): return area
    def eliminar_area(self, area_id): return False
    def actualizar_color_area(self, area_id, color): return False
    def listar_asignaturas(self, area_id=None): return []
    def guardar_asignatura(self, a): return a
    def actualizar_asignatura(self, a): return a
    def eliminar_asignatura(self, asignatura_id): return False
    def get_grupo(self, grupo_id): return None
    def get_grupo_por_codigo(self, codigo): return None
    def listar_grupos(self, grado=None): return []
    def guardar_grupo(self, g): return g
    def asignar_sala_a_grupo(self, *a): return True
    def actualizar_grupo(self, g): return g
    def eliminar_grupo(self, grupo_id): return False
    def get_info_horario(self, horario_id): return None
    def listar_horario_grupo(self, grupo_id, periodo_id): return []
    def listar_horario_docente(self, usuario_id, periodo_id): return []
    def existe_conflicto_horario(self, usuario_id, periodo_id, dia_semana, hora_inicio, hora_fin, excluir_horario_id=None): return False
    def get_estadisticas(self, periodo_id): raise NotImplementedError
    def crear_bloques_masivo(self, horarios): return len(horarios)
    def eliminar_horarios_por_asignacion(self, asignacion_id): return 0
    def get_logro(self, logro_id): return None
    def listar_logros(self, asignacion_id, periodo_id): return []
    def guardar_logro(self, logro): return logro
    def actualizar_logro(self, logro): return logro
    def eliminar_logro(self, logro_id): return False
    def crear_plantilla_franja(self, p): return p
    def get_plantilla_franja(self, plantilla_id): return None
    def listar_plantillas_franja(self): return []
    def get_plantilla_activa(self, jornada): return None
    def actualizar_plantilla_franja(self, p): return p
    def activar_plantilla_franja(self, plantilla_id): pass
    def eliminar_plantilla_franja(self, plantilla_id): return True
    def crear_franja(self, f): return f
    def listar_franjas(self, plantilla_id): return []
    def actualizar_franja(self, f): return f
    def eliminar_franja(self, franja_id): return True
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
    def listar_salas(self): return []
    def get_sala(self, sala_id): return None
    def crear_sala(self, sala): return sala
    def actualizar_sala(self, sala): return sala
    def eliminar_sala(self, sala_id): return False
    def listar_ventanas_grupo(self): return []
    def get_ventanas_por_grupo(self, grupo_id): return []
    def get_ventanas_por_grado(self, grado): return []
    def crear_ventana_grupo(self, v): return v
    def eliminar_ventana_grupo(self, ventana_id): return False
    def listar_bloques_anclados(self, escenario_id): return []
    def crear_bloque_anclado(self, b): return b
    def eliminar_bloque_anclado(self, bloque_id): return False
    def listar_franjas_reunion(self): return []
    def get_franja_reunion(self, franja_id): return None
    def crear_franja_reunion(self, f): return f
    def actualizar_franja_reunion(self, f): return f
    def eliminar_franja_reunion(self, franja_id): return False
    def get_limites_docente(self, usuario_id): return None
    def set_limites_docente(self, limites): return limites
    def listar_limites_docente(self): return []
    def listar_grados(self): return []
    def upsert_grado(self, g): return g
    def eliminar_grado(self, numero): return False
    def listar_plan_estudios(self): return []
    def get_plan_estudios_por_grado(self, grado): return []
    def set_horas_plan(self, grado, asignatura_id, horas): return None
    def eliminar_plan_estudios(self, grado, asignatura_id): return False


class FakeAsignacionRepo(IAsignacionRepository):
    def __init__(self):
        self._asigs: dict[int, Asignacion] = {}

    def get_by_id(self, asignacion_id: int) -> Asignacion | None:
        return self._asigs.get(asignacion_id)

    def listar(self, filtro): return []
    def existe(self, grupo_id, asignatura_id, usuario_id, periodo_id): return False
    def get_info(self, asignacion_id): return None
    def listar_info(self, filtro): return []
    def listar_por_grupo(self, grupo_id, periodo_id, solo_activas=True): return []
    def listar_por_docente(self, usuario_id, periodo_id=None, solo_activas=True): return []
    def guardar(self, asignacion): return asignacion
    def desactivar(self, asignacion_id): return True
    def reactivar(self, asignacion_id): return True
    def reasignar_docente(self, asignacion_id, nuevo_usuario_id): return True


class FakeUsuarioRepo:
    """Stub mínimo con carga_horaria_max."""

    def __init__(self, carga_max: int | None = None):
        self._carga_max = carga_max

    def carga_horaria_max(self, usuario_id: int) -> int | None:
        return self._carga_max


# ===========================================================================
# Fixtures
# ===========================================================================

ESCENARIO_ID = 1
ASIG_ID      = 10
ASIGNATURA_ID = 5
GRUPO_ID     = 2
USUARIO_ID   = 3
PERIODO_ID   = 1


def _make_asignacion(activo: bool = True) -> Asignacion:
    return Asignacion(
        id=ASIG_ID,
        grupo_id=GRUPO_ID,
        asignatura_id=ASIGNATURA_ID,
        usuario_id=USUARIO_ID,
        periodo_id=PERIODO_ID,
        activo=activo,
    )


def _make_asignatura(horas: int = 4) -> Asignatura:
    return Asignatura(id=ASIGNATURA_ID, nombre="Matemáticas", horas_semanales=horas)


def _make_horario(id_=1) -> Horario:
    return Horario(
        id=id_,
        grupo_id=GRUPO_ID,
        asignatura_id=ASIGNATURA_ID,
        usuario_id=USUARIO_ID,
        asignacion_id=ASIG_ID,
        escenario_id=ESCENARIO_ID,
        dia_semana=DiaSemana.LUNES,
        hora_inicio=time(7, 0),
        hora_fin=time(8, 0),
        sala="Aula",
    )


def _make_service(
    infra: FakeInfraRepo | None = None,
    asig: FakeAsignacionRepo | None = None,
    carga_max: int | None = None,
) -> tuple[HorarioService, FakeInfraRepo, FakeAsignacionRepo]:
    if infra is None:
        infra = FakeInfraRepo()
    if asig is None:
        asig = FakeAsignacionRepo()
    usuario = FakeUsuarioRepo(carga_max=carga_max)
    svc = HorarioService(
        infra_repo=infra,
        asignacion_repo=asig,
        usuario_repo=usuario,
    )
    return svc, infra, asig


# ===========================================================================
# Tests
# ===========================================================================

class TestCrearBloque:

    def test_r2_asignacion_inexistente(self):
        """R2: Si la asignación no existe → ValueError."""
        svc, _, asig = _make_service()
        # No añadimos nada al FakeAsignacionRepo → get_by_id retorna None
        with pytest.raises(ValueError, match="La asignación no existe"):
            svc.crear_bloque(ESCENARIO_ID, ASIG_ID, "Lunes", "07:00", "08:00")

    def test_r2_asignacion_inactiva(self):
        """R2: Si la asignación está inactiva → ValueError."""
        svc, infra, asig = _make_service()
        asig._asigs[ASIG_ID] = _make_asignacion(activo=False)
        infra._asignaturas[ASIGNATURA_ID] = _make_asignatura()
        with pytest.raises(ValueError, match="La asignación no existe"):
            svc.crear_bloque(ESCENARIO_ID, ASIG_ID, "Lunes", "07:00", "08:00")

    def test_r4_cruce_docente(self):
        """R4: Cruce de docente → ValueError."""
        svc, infra, asig = _make_service()
        asig._asigs[ASIG_ID] = _make_asignacion()
        infra._asignaturas[ASIGNATURA_ID] = _make_asignatura()
        infra._cruce_result = True
        with pytest.raises(ValueError, match="docente ya tiene"):
            svc.crear_bloque(ESCENARIO_ID, ASIG_ID, "Lunes", "07:00", "08:00")

    def test_r5_cruce_grupo(self):
        """R5: Cruce de grupo → ValueError."""
        svc, infra, asig = _make_service()
        asig._asigs[ASIG_ID] = _make_asignacion()
        infra._asignaturas[ASIGNATURA_ID] = _make_asignatura()

        call_count = [0]
        original_existe_cruce = infra.existe_cruce

        def existe_cruce_selectivo(*args, usuario_id=None, grupo_id=None, sala=None, excluir_horario_id=None):
            call_count[0] += 1
            # Primera llamada (docente): no hay cruce
            if call_count[0] == 1:
                return False
            # Segunda llamada (grupo): hay cruce
            return True

        infra.existe_cruce = existe_cruce_selectivo
        with pytest.raises(ValueError, match="grupo ya tiene"):
            svc.crear_bloque(ESCENARIO_ID, ASIG_ID, "Lunes", "07:00", "08:00")

    def test_r6_cruce_sala(self):
        """R6: Cruce de sala (distinta de Aula) → ValueError."""
        svc, infra, asig = _make_service()
        asig._asigs[ASIG_ID] = _make_asignacion()
        infra._asignaturas[ASIGNATURA_ID] = _make_asignatura()

        call_count = [0]

        def existe_cruce_selectivo(*args, usuario_id=None, grupo_id=None, sala=None, excluir_horario_id=None):
            call_count[0] += 1
            if call_count[0] <= 2:
                return False  # docente y grupo sin cruce
            return True  # sala con cruce

        infra.existe_cruce = existe_cruce_selectivo
        with pytest.raises(ValueError, match="sala"):
            svc.crear_bloque(ESCENARIO_ID, ASIG_ID, "Lunes", "07:00", "08:00", sala="Lab-101")

    def test_r8_tope_materia_superado(self):
        """R8: Tope de horas_semanales de la materia superado → ValueError."""
        svc, infra, asig = _make_service()
        asig._asigs[ASIG_ID] = _make_asignacion()
        infra._asignaturas[ASIGNATURA_ID] = _make_asignatura(horas=2)
        infra._cruce_result = False
        infra._bloques_asignacion = 2  # ya tiene el límite
        with pytest.raises(ValueError, match="límite"):
            svc.crear_bloque(ESCENARIO_ID, ASIG_ID, "Lunes", "07:00", "08:00")

    def test_r9_tope_docente_superado(self):
        """R9: Docente supera su carga máxima → ValueError."""
        svc, infra, asig = _make_service(carga_max=5)
        asig._asigs[ASIG_ID] = _make_asignacion()
        infra._asignaturas[ASIGNATURA_ID] = _make_asignatura(horas=10)
        infra._cruce_result = False
        infra._bloques_asignacion = 0
        infra._bloques_docente = 5  # ya en el límite
        with pytest.raises(ValueError, match="carga máxima"):
            svc.crear_bloque(ESCENARIO_ID, ASIG_ID, "Lunes", "07:00", "08:00")

    def test_r10_sin_carga_horaria_max_no_aplica_tope(self):
        """R10: Si carga_horaria_max es None, no se aplica tope de docente."""
        svc, infra, asig = _make_service(carga_max=None)
        asig._asigs[ASIG_ID] = _make_asignacion()
        infra._asignaturas[ASIGNATURA_ID] = _make_asignatura(horas=10)
        infra._cruce_result = False
        infra._bloques_asignacion = 0
        infra._bloques_docente = 999  # cualquier cantidad
        result = svc.crear_bloque(ESCENARIO_ID, ASIG_ID, "Lunes", "07:00", "08:00")
        assert isinstance(result, Horario)

    def test_creacion_valida_retorna_horario(self):
        """Creación válida retorna un objeto Horario con id asignado."""
        svc, infra, asig = _make_service(carga_max=None)
        asig._asigs[ASIG_ID] = _make_asignacion()
        infra._asignaturas[ASIGNATURA_ID] = _make_asignatura(horas=4)
        infra._cruce_result = False
        infra._bloques_asignacion = 0
        result = svc.crear_bloque(ESCENARIO_ID, ASIG_ID, "Lunes", "07:00", "08:00")
        assert isinstance(result, Horario)
        assert result.id is not None
        assert result.grupo_id == GRUPO_ID
        assert result.usuario_id == USUARIO_ID


class TestActualizarBloque:

    def test_r7_editar_sin_cruce_consigo_mismo(self):
        """R7: Al editar un bloque existente, no hay cruce consigo mismo → OK."""
        svc, infra, asig = _make_service(carga_max=None)
        asig._asigs[ASIG_ID] = _make_asignacion()
        infra._asignaturas[ASIGNATURA_ID] = _make_asignatura()
        # Registrar un horario en el repo
        horario = _make_horario(id_=1)
        infra._horarios[1] = horario
        # Sin cruce (el exclusion del propio id lo gestiona el repo fake)
        infra._cruce_result = False
        result = svc.actualizar_bloque(
            1, dia="Martes", hora_inicio="08:00", hora_fin="09:00", sala="Aula"
        )
        assert result.dia_semana == DiaSemana.MARTES


class TestDisponibilidad:

    def test_disponibilidad_asignacion_con_maximas(self):
        svc, infra, asig = _make_service()
        asig._asigs[ASIG_ID] = _make_asignacion()
        infra._asignaturas[ASIGNATURA_ID] = _make_asignatura(horas=4)
        infra._bloques_asignacion = 2
        cupo = svc.disponibilidad_asignacion(ESCENARIO_ID, ASIG_ID)
        assert isinstance(cupo, CupoDTO)
        assert cupo.usadas == 2
        assert cupo.maximas == 4
        assert cupo.disponibles == 2
        assert not cupo.excedido

    def test_disponibilidad_docente_sin_limite(self):
        svc, infra, asig = _make_service(carga_max=None)
        infra._bloques_docente = 10
        cupo = svc.disponibilidad_docente(ESCENARIO_ID, USUARIO_ID)
        assert cupo.maximas is None
        assert cupo.disponibles is None
        assert not cupo.excedido
