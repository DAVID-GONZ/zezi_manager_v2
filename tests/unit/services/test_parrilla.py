"""
Tests unitarios para HorarioService.datos_parrilla (paso_15e).

Verifican la estructura UI-agnóstica de la parrilla visual:
  - claves presentes (dias, franjas, celdas) siempre,
  - resolución de area_id/area_color desde la asignatura,
  - franjas desde la plantilla activa o derivadas de los bloques,
  - escenario vacío → listas vacías pero estructura presente.
Usan Fakes en memoria; no tocan la BD.
"""
from __future__ import annotations

from datetime import time

from src.domain.models.infraestructura import (
    AreaConocimiento,
    Asignatura,
    DiaSemana,
    Franja,
    HorarioInfo,
    PlantillaFranja,
)
from src.domain.ports.asignacion_repo import IAsignacionRepository
from src.domain.ports.infraestructura_repo import IInfraestructuraRepository
from src.services.horario_service import HorarioService


# ===========================================================================
# Fakes
# ===========================================================================

class FakeInfraRepo(IInfraestructuraRepository):
    def __init__(self):
        self._bloques: list[HorarioInfo] = []
        self._asignaturas: dict[int, Asignatura] = {}
        self._areas: dict[int, AreaConocimiento] = {}
        self._plantilla: PlantillaFranja | None = None
        self._franjas: list[Franja] = []

    # --- métodos usados por datos_parrilla ---
    def listar_horario_escenario(self, escenario_id): return list(self._bloques)
    def get_asignatura(self, asignatura_id): return self._asignaturas.get(asignatura_id)
    def get_area(self, area_id): return self._areas.get(area_id)
    def get_plantilla_activa(self, jornada, institucion_id=None): return self._plantilla
    def listar_franjas(self, plantilla_id): return list(self._franjas)

    # --- abstractos restantes (no usados aquí) ---
    def get_escenario(self, *a): return None
    def listar_escenarios(self, *a): return []
    def get_escenario_activo(self, *a): return None
    def crear_escenario(self, esc): return esc
    def actualizar_escenario(self, esc): return esc
    def activar_escenario(self, *a): pass
    def eliminar_escenario(self, *a): return False
    def duplicar_escenario(self, *a): raise NotImplementedError
    def listar_horario_grupo_escenario(self, *a): return []
    def listar_areas(self): return list(self._areas.values())
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
    def existe_conflicto_horario(self, *a, **k): return False
    def get_estadisticas(self, *a): raise NotImplementedError
    def guardar_horario(self, h): return h
    def actualizar_horario(self, h): return h
    def eliminar_horario(self, *a): return False
    def existe_cruce(self, *a, **k): return False
    def contar_bloques_asignacion(self, *a): return 0
    def contar_bloques_docente(self, *a): return 0
    def crear_bloques_masivo(self, horarios): return len(horarios)
    def eliminar_horarios_por_asignacion(self, *a): return 0
    def get_logro(self, *a): return None
    def listar_logros(self, *a): return []
    def guardar_logro(self, logro): return logro
    def actualizar_logro(self, logro): return logro
    def eliminar_logro(self, *a): return False
    def crear_plantilla_franja(self, p): return p
    def get_plantilla_franja(self, *a): return None
    def listar_plantillas_franja(self, institucion_id=None): return []
    def actualizar_plantilla_franja(self, p): return p
    def activar_plantilla_franja(self, *a): pass
    def eliminar_plantilla_franja(self, *a): return True
    def crear_franja(self, f): return f
    def actualizar_franja(self, f): return f
    def eliminar_franja(self, *a): return True
    def reemplazar_franjas(self, plantilla_id, franjas): return len(franjas)
    def upsert_disponibilidad(self, d): return d
    def listar_disponibilidad_docente(self, *a): return []
    def es_disponible(self, *a): return True
    def limpiar_disponibilidad_docente(self, *a): return 0
    def cargar_disponibilidad_lote(self, *a): return 0
    def reemplazar_disponibilidad_docente(self, *a): return 0
    def crear_config_generacion(self, c): return c
    def get_config_generacion(self, *a): return None
    def listar_configs_generacion(self, periodo_id=None): return []
    def actualizar_config_generacion(self, c): return c
    def eliminar_config_generacion(self, *a): return True
    def cambiar_estado_config(self, *a): return None
    def duplicar_config_generacion(self, *a): return None
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


class FakeAsignacionRepo(IAsignacionRepository):
    def get_by_id(self, *a): return None
    def listar(self, *a): return []
    def existe(self, *a): return False
    def get_info(self, *a): return None
    def listar_info(self, *a): return []
    def listar_por_grupo(self, *a, **k): return []
    def listar_por_docente(self, *a, **k): return []
    def guardar(self, a): return a
    def desactivar(self, *a): return True
    def reactivar(self, *a): return True
    def reasignar_docente(self, *a): return True


class FakeUsuarioRepo:
    def carga_horaria_max(self, usuario_id): return None


def _svc(infra: FakeInfraRepo) -> HorarioService:
    return HorarioService(
        infra_repo=infra,
        asignacion_repo=FakeAsignacionRepo(),
        usuario_repo=FakeUsuarioRepo(),
    )


def _bloque(id_, *, grupo_id=1, grupo_codigo="601", asignatura_id=5,
            usuario_id=3, dia="Lunes", hi=time(7, 0), hf=time(8, 0),
            sala="Aula") -> HorarioInfo:
    return HorarioInfo(
        id=id_, grupo_id=grupo_id, grupo_codigo=grupo_codigo,
        asignatura_id=asignatura_id, asignatura_nombre="Matemáticas",
        usuario_id=usuario_id, docente_nombre="Ana Pérez",
        asignacion_id=10, periodo_id=1, periodo_nombre="P1",
        escenario_id=1, dia_semana=dia, hora_inicio=hi, hora_fin=hf, sala=sala,
    )


# ===========================================================================
# Tests
# ===========================================================================

ESC_ID = 1


def test_estructura_presente_en_escenario_vacio():
    datos = _svc(FakeInfraRepo()).datos_parrilla(ESC_ID)
    assert set(datos.keys()) == {"dias", "franjas", "celdas"}
    assert datos["dias"] == []
    assert datos["franjas"] == []
    assert datos["celdas"] == []


def test_celdas_resuelven_area_color_desde_asignatura():
    infra = FakeInfraRepo()
    infra._areas[2] = AreaConocimiento(id=2, nombre="Ciencias", color="#AABBCC")
    infra._asignaturas[5] = Asignatura(id=5, nombre="Matemáticas", area_id=2)
    infra._bloques = [_bloque(1)]

    datos = _svc(infra).datos_parrilla(ESC_ID)
    assert len(datos["celdas"]) == 1
    celda = datos["celdas"][0]
    assert celda["area_id"] == 2
    assert celda["area_color"] == "#AABBCC"
    assert celda["asignatura_nombre"] == "Matemáticas"
    assert celda["dia_semana"] == "Lunes"
    assert celda["hora_inicio"] == "07:00"


def test_area_color_none_si_area_sin_color():
    infra = FakeInfraRepo()
    infra._areas[2] = AreaConocimiento(id=2, nombre="Ciencias", color=None)
    infra._asignaturas[5] = Asignatura(id=5, nombre="Matemáticas", area_id=2)
    infra._bloques = [_bloque(1)]

    celda = _svc(infra).datos_parrilla(ESC_ID)["celdas"][0]
    assert celda["area_id"] == 2
    assert celda["area_color"] is None


def test_franjas_derivadas_de_bloques_sin_plantilla():
    infra = FakeInfraRepo()
    infra._bloques = [
        _bloque(1, hi=time(7, 0), hf=time(8, 0)),
        _bloque(2, dia="Martes", hi=time(8, 0), hf=time(9, 0)),
        _bloque(3, hi=time(7, 0), hf=time(8, 0)),  # par repetido
    ]
    datos = _svc(infra).datos_parrilla(ESC_ID)
    franjas = datos["franjas"]
    assert [f["hora_inicio"] for f in franjas] == ["07:00", "08:00"]
    assert all(f["lectiva"] for f in franjas)
    # días presentes ordenados Lunes→Sábado
    assert datos["dias"] == ["Lunes", "Martes"]


def test_franjas_desde_plantilla_activa():
    infra = FakeInfraRepo()
    infra._plantilla = PlantillaFranja(
        id=7, nombre="Jornada Única", jornada="UNICA",
        dias_activos=["Lunes", "Martes", "Miércoles"], activa=True,
    )
    infra._franjas = [
        Franja(id=1, plantilla_id=7, orden=1, hora_inicio="07:00",
               hora_fin="07:55", tipo="lectiva", etiqueta="1ª"),
        Franja(id=2, plantilla_id=7, orden=2, hora_inicio="07:55",
               hora_fin="08:25", tipo="descanso", etiqueta="Descanso"),
    ]
    infra._bloques = [_bloque(1)]

    datos = _svc(infra).datos_parrilla(ESC_ID)
    assert [f["orden"] for f in datos["franjas"]] == [1, 2]
    assert datos["franjas"][0]["lectiva"] is True
    assert datos["franjas"][1]["lectiva"] is False
    # días vienen de la plantilla, en orden canónico
    assert datos["dias"] == ["Lunes", "Martes", "Miércoles"]


def test_celdas_una_por_bloque():
    infra = FakeInfraRepo()
    infra._asignaturas[5] = Asignatura(id=5, nombre="Matemáticas", area_id=None)
    infra._bloques = [_bloque(1), _bloque(2, dia="Martes"), _bloque(3, sala="Lab")]
    datos = _svc(infra).datos_parrilla(ESC_ID)
    assert len(datos["celdas"]) == 3
    # area_id None cuando la asignatura no tiene área
    assert all(c["area_id"] is None for c in datos["celdas"])


def test_celdas_incluyen_area_nombre():
    infra = FakeInfraRepo()
    infra._areas[2] = AreaConocimiento(id=2, nombre="Ciencias", color="#AABBCC")
    infra._asignaturas[5] = Asignatura(id=5, nombre="Matemáticas", area_id=2)
    infra._bloques = [_bloque(1)]
    celda = _svc(infra).datos_parrilla(ESC_ID)["celdas"][0]
    assert celda["area_nombre"] == "Ciencias"


# ===========================================================================
# metricas_parrilla (paso_15f)
# ===========================================================================

def test_metricas_claves_y_escenario_vacio():
    m = _svc(FakeInfraRepo()).metricas_parrilla(ESC_ID)
    assert set(m.keys()) == {
        "total_bloques", "n_grupos", "n_docentes",
        "n_salas", "huecos_grupo", "ocupacion_pct",
    }
    assert m == {
        "total_bloques": 0, "n_grupos": 0, "n_docentes": 0,
        "n_salas": 0, "huecos_grupo": 0, "ocupacion_pct": 0,
    }


def test_metricas_valores_coherentes():
    infra = FakeInfraRepo()
    infra._asignaturas[5] = Asignatura(id=5, nombre="Matemáticas", area_id=None)
    infra._bloques = [
        _bloque(1, grupo_id=1, usuario_id=3, hi=time(7, 0), hf=time(8, 0)),
        _bloque(2, grupo_id=1, usuario_id=4, dia="Martes",
                hi=time(8, 0), hf=time(9, 0)),
        _bloque(3, grupo_id=2, usuario_id=3, sala="Lab",
                hi=time(7, 0), hf=time(8, 0)),
    ]
    m = _svc(infra).metricas_parrilla(ESC_ID)
    datos = _svc(infra).datos_parrilla(ESC_ID)
    assert m["total_bloques"] == len(datos["celdas"]) == 3
    assert m["n_grupos"] == 2
    assert m["n_docentes"] == 2
    assert m["n_salas"] == 2          # "Aula" y "Lab"
    assert m["huecos_grupo"] >= 0
    assert 0 <= m["ocupacion_pct"] <= 100


def test_metricas_huecos_grupo_intra_dia():
    """Grupo con franjas 1 y 3 ocupadas (la 2 vacía) = 1 hueco."""
    infra = FakeInfraRepo()
    infra._plantilla = PlantillaFranja(
        id=7, nombre="U", jornada="UNICA",
        dias_activos=["Lunes"], activa=True,
    )
    infra._franjas = [
        Franja(id=1, plantilla_id=7, orden=1, hora_inicio="07:00",
               hora_fin="08:00", tipo="lectiva"),
        Franja(id=2, plantilla_id=7, orden=2, hora_inicio="08:00",
               hora_fin="09:00", tipo="lectiva"),
        Franja(id=3, plantilla_id=7, orden=3, hora_inicio="09:00",
               hora_fin="10:00", tipo="lectiva"),
    ]
    infra._bloques = [
        _bloque(1, grupo_id=1, hi=time(7, 0), hf=time(8, 0)),
        _bloque(2, grupo_id=1, hi=time(9, 0), hf=time(10, 0)),
    ]
    m = _svc(infra).metricas_parrilla(ESC_ID)
    assert m["huecos_grupo"] == 1
    # capacidad = 1 grupo × 3 franjas × 1 día = 3; 2 colocados => 67%
    assert m["ocupacion_pct"] == 67


# ===========================================================================
# areas_parrilla (paso_15f)
# ===========================================================================

def test_areas_parrilla_vacio():
    assert _svc(FakeInfraRepo()).areas_parrilla(ESC_ID) == []


def test_areas_parrilla_dedup_y_orden():
    infra = FakeInfraRepo()
    infra._areas[2] = AreaConocimiento(id=2, nombre="Matemáticas", color="#AABBCC")
    infra._areas[3] = AreaConocimiento(id=3, nombre="Artes", color=None)
    infra._asignaturas[5] = Asignatura(id=5, nombre="Mate", area_id=2)
    infra._asignaturas[6] = Asignatura(id=6, nombre="Arte", area_id=3)
    infra._bloques = [
        _bloque(1, asignatura_id=5),
        _bloque(2, asignatura_id=5, dia="Martes"),   # duplica área 2
        _bloque(3, asignatura_id=6),
    ]
    areas = _svc(infra).areas_parrilla(ESC_ID)
    assert [a["area_nombre"] for a in areas] == ["Artes", "Matemáticas"]
    assert {a["area_id"] for a in areas} == {2, 3}
    artes = next(a for a in areas if a["area_id"] == 3)
    assert artes["color"] is None
    mate = next(a for a in areas if a["area_id"] == 2)
    assert mate["color"] == "#AABBCC"
