"""
Tests unitarios para PreparacionHorarioService (horario_01_validacion_generacion).

Fakes en memoria, sin BD.

T3: puerta `aulas_base_unicas` (P8) — detecta grupos que comparten la misma
aula base (`sala_id`).
T8/T9/T10/T11: `validar_config()` sobre la ConfigGeneracion real (con filtro
de grupos), `horas_plan_asignaciones` y `horas_grupo_vs_slots` reescritas
sobre asignaciones reales (no el plan declarado), `capacidad_docente` sube a
"dura", y las puertas nuevas `asignaciones_activas`, `capacidad_docente_slots`,
`disponibilidad_coherente`, `grupos_con_grado`.
"""
from __future__ import annotations

from src.domain.models.asignacion import Asignacion
from src.domain.models.infraestructura import (
    Asignatura,
    ConfigGeneracion,
    DisponibilidadDocente,
    Franja,
    Grupo,
    PlantillaFranja,
)
from src.domain.models.usuario import Usuario
from src.services.preparacion_horario_service import PreparacionHorarioService

# ===========================================================================
# Fakes mínimos (duck-typed; solo lo que PreparacionHorarioService invoca)
# ===========================================================================


class _FakeInfraRepo:
    def __init__(
        self,
        grupos=None,
        asignaturas=None,
        salas=None,
        franjas=None,
        plantillas=None,
        config_generacion=None,
        disponibilidad=None,
    ):
        self._grupos = grupos or []
        self._asignaturas = asignaturas or []
        self._salas = salas or []
        self._franjas = franjas or []
        self._plantillas = plantillas or []
        self._config_generacion = config_generacion
        self._disponibilidad = disponibilidad or []

    def listar_grupos(self, institucion_id=None):
        return list(self._grupos)

    def listar_asignaturas(self, institucion_id=None):
        return list(self._asignaturas)

    def listar_salas(self, institucion_id=None):
        return list(self._salas)

    def listar_franjas(self, plantilla_id):
        return list(self._franjas)

    def listar_plantillas_franja(self, institucion_id=None):
        return list(self._plantillas)

    def get_config_generacion(self, config_id):
        return self._config_generacion

    def listar_disponibilidad_docente(self, usuario_id):
        return [d for d in self._disponibilidad if d.usuario_id == usuario_id]


class _FakeAsignacionRepo:
    def __init__(self, asignaciones=None):
        self._asigs = asignaciones or []

    def listar(self, filtro):
        return list(self._asigs)


class _FakeConfigRepo:
    def __init__(self, config=None):
        self._config = config

    def get_by_id(self, anio_id):
        return self._config


class _FakePeriodoRepo:
    def __init__(self, periodo=None):
        self._periodo = periodo

    def get_by_id(self, periodo_id):
        return self._periodo


class _FakeUsuarioRepo:
    def __init__(self, usuarios=None):
        self._usuarios = {u.id: u for u in (usuarios or [])}

    def get_by_id(self, usuario_id):
        return self._usuarios.get(usuario_id)


class _FakePlanService:
    """Plan vacío por defecto: `horas_de` siempre cae al fallback global de
    la asignatura (igual que el motor real cuando el grado no tiene plan)."""

    def listar(self):
        return []

    def horas_por_grado(self, grado):
        return 0

    def horas_de(self, grado, asignatura_id):
        return 0


def _svc(
    grupos=None,
    asignaturas=None,
    salas=None,
    franjas=None,
    plantillas=None,
    asignaciones=None,
    usuarios=None,
    config_generacion=None,
    disponibilidad=None,
):
    infra = _FakeInfraRepo(
        grupos=grupos,
        asignaturas=asignaturas,
        salas=salas,
        franjas=franjas,
        plantillas=plantillas,
        config_generacion=config_generacion,
        disponibilidad=disponibilidad,
    )
    return PreparacionHorarioService(
        infra_repo=infra,
        asignacion_repo=_FakeAsignacionRepo(asignaciones),
        config_repo=_FakeConfigRepo(),
        periodo_repo=_FakePeriodoRepo(),
        usuario_repo=_FakeUsuarioRepo(usuarios),
        plan_svc=_FakePlanService(),
    )


# ===========================================================================
# Puerta aulas_base_unicas (T3)
# ===========================================================================


def test_aulas_base_unicas_ok_sin_duplicados():
    """Cada grupo con aula base tiene una sala distinta → puerta en ok."""
    grupos = [
        Grupo(id=1, codigo="601", sala_id=10),
        Grupo(id=2, codigo="602", sala_id=11),
        Grupo(id=3, codigo="701", sala_id=None),  # sin aula base: se ignora
    ]
    svc = _svc(grupos)

    puerta = svc._p8_aulas_base_unicas(grupos)

    assert puerta.id == "aulas_base_unicas"
    assert puerta.severidad == "advertencia"
    assert puerta.ok is True


def test_aulas_base_unicas_detecta_duplicado():
    """Dos grupos con el mismo sala_id → puerta en advertencia, no en ok."""
    grupos = [
        Grupo(id=1, codigo="601", sala_id=10),
        Grupo(id=2, codigo="602", sala_id=10),  # comparte aula con 601
        Grupo(id=3, codigo="701", sala_id=11),
    ]
    svc = _svc(grupos)

    puerta = svc._p8_aulas_base_unicas(grupos)

    assert puerta.ok is False
    assert puerta.severidad == "advertencia"  # nunca bloquea la generación
    assert puerta.fix_ruta == "/admin/salas"
    assert "601" in puerta.detalle
    assert "602" in puerta.detalle


def test_aulas_base_unicas_lista_hasta_3_ejemplos_y_resto():
    """Con más de 3 aulas duplicadas, se muestran 3 ejemplos + 'y N más'."""
    grupos = []
    for i in range(4):
        sid = 100 + i
        grupos.append(Grupo(id=i * 2 + 1, codigo=f"G{i}A", sala_id=sid))
        grupos.append(Grupo(id=i * 2 + 2, codigo=f"G{i}B", sala_id=sid))
    svc = _svc(grupos)

    puerta = svc._p8_aulas_base_unicas(grupos)

    assert puerta.ok is False
    assert "y 1 más" in puerta.detalle


def test_aulas_base_unicas_ignora_grupos_sin_aula():
    """Varios grupos con sala_id=None no cuentan como duplicado entre sí."""
    grupos = [
        Grupo(id=1, codigo="601", sala_id=None),
        Grupo(id=2, codigo="602", sala_id=None),
        Grupo(id=3, codigo="603", sala_id=None),
    ]
    svc = _svc(grupos)

    puerta = svc._p8_aulas_base_unicas(grupos)

    assert puerta.ok is True


def test_validar_incluye_puerta_aulas_base_unicas():
    """validar() ejecuta las 12 puertas del reporte (T11), sin excepciones
    aunque el resto del contexto esté vacío."""
    svc = _svc([])

    reporte = svc.validar(anio_id=1, periodo_id=1, plantilla_id=0)

    ids = [p.id for p in reporte]
    assert len(reporte) == 12
    assert "aulas_base_unicas" in ids
    # puede_generar() solo mira las puertas 'dura'; una advertencia en
    # aulas_base_unicas nunca debe bloquear la generación por sí sola.
    aulas_puerta = next(p for p in reporte if p.id == "aulas_base_unicas")
    assert aulas_puerta.severidad == "advertencia"


def test_validar_orden_de_puertas_es_el_definido_en_t11():
    """El orden del reporte es contractual: la página lo recorre en ese
    orden para pintar la checklist."""
    svc = _svc([])

    reporte = svc.validar(anio_id=1, periodo_id=1, plantilla_id=0)

    assert [p.id for p in reporte] == [
        "anio_periodo",
        "asignaciones_activas",
        "plantilla_suficiente",
        "horas_plan_asignaciones",
        "horas_grupo_vs_slots",
        "capacidad_docente",
        "capacidad_docente_slots",
        "cobertura_asignaciones",
        "disponibilidad_coherente",
        "grupos_con_grado",
        "aulas_base_unicas",
        "salas_suficientes",
    ]


# ===========================================================================
# T9 — horas_plan_asignaciones (reemplaza asignaturas_con_horas)
# ===========================================================================


def test_p_horas_plan_detecta_asignacion_con_cero_horas():
    """Una asignación referencia una asignatura que ya no está en el
    catálogo del tenant (huérfana / de otra institución): `asig_map.get`
    no la encuentra, `global_h=0` y la asignación resuelve a 0 horas. Es
    el caso real que la vieja `asignaturas_con_horas` no podía detectar
    porque `horas_semanales` nunca baja de 1 en el modelo."""
    grupos = [Grupo(id=1, codigo="601", grado=None)]
    asignaciones = [
        Asignacion(id=1, grupo_id=1, asignatura_id=999, usuario_id=1, periodo_id=1, activo=True)
    ]
    svc = _svc(grupos=grupos, asignaturas=[], asignaciones=asignaciones)

    asig_map = {}
    grado_de_grupo = {1: None}
    puerta = svc._p_horas_plan_asignaciones(asignaciones, asig_map, grado_de_grupo, grupos)

    assert puerta.id == "horas_plan_asignaciones"
    assert puerta.severidad == "dura"
    assert puerta.ok is False
    assert puerta.fix_ruta == "/admin/plan-estudios"
    assert "601" in puerta.detalle


def test_p_horas_plan_ok_cuando_todas_resuelven_horas():
    """Asignación cuya asignatura sí existe en el catálogo → resuelve al
    fallback global (horas_semanales de la asignatura) y queda en ok."""
    asignatura = Asignatura(id=5, nombre="Matemáticas", horas_semanales=4)
    grupos = [Grupo(id=1, codigo="601", grado=None)]
    asignaciones = [
        Asignacion(id=1, grupo_id=1, asignatura_id=5, usuario_id=1, periodo_id=1, activo=True)
    ]
    svc = _svc(grupos=grupos, asignaturas=[asignatura], asignaciones=asignaciones)

    asig_map = {5: asignatura}
    grado_de_grupo = {1: None}
    puerta = svc._p_horas_plan_asignaciones(asignaciones, asig_map, grado_de_grupo, grupos)

    assert puerta.ok is True


# ===========================================================================
# T9 — horas_grupo_vs_slots (reescrita sobre asignaciones, no el plan)
# ===========================================================================


def test_p_horas_grupo_usa_asignaciones_no_plan():
    """Grupo con horas asignadas por encima de los cupos y plan de estudios
    vacío (el `_FakePlanService` por defecto siempre cae al fallback global)
    → puerta roja. Antes esta puerta medía `plan.horas_por_grado()` y un
    plan vacío la dejaba en verde aunque las asignaciones reales excedieran
    la plantilla."""
    plantilla = PlantillaFranja(id=1, nombre="Única", dias_activos=["Lunes", "Martes"])
    franjas = [
        Franja(id=1, plantilla_id=1, orden=1, hora_inicio="07:00", hora_fin="08:00"),
    ]  # 1 franja lectiva × 2 días = 2 cupos/semana
    asignatura = Asignatura(id=5, nombre="Matemáticas", horas_semanales=5)
    grupos = [Grupo(id=1, codigo="601", grado=None)]
    asignaciones = [
        Asignacion(id=1, grupo_id=1, asignatura_id=5, usuario_id=1, periodo_id=1, activo=True)
    ]  # 5h asignadas > 2 cupos
    svc = _svc(
        grupos=grupos,
        asignaturas=[asignatura],
        franjas=franjas,
        plantillas=[plantilla],
        asignaciones=asignaciones,
    )

    asig_map = {5: asignatura}
    grado_de_grupo = {1: None}
    puerta = svc._p3_horas_grupo_vs_slots(
        grupos, asignaciones, asig_map, grado_de_grupo, plantilla, franjas
    )

    assert puerta.id == "horas_grupo_vs_slots"
    assert puerta.severidad == "dura"
    assert puerta.ok is False
    assert "601" in puerta.detalle


def test_p_horas_grupo_cubre_grupos_sin_grado():
    """Grupo con grado=None y demanda dentro de los cupos → puerta en ok;
    antes la puerta se saltaba estos grupos con `continue` (nunca los
    validaba, ni en verde ni en rojo)."""
    plantilla = PlantillaFranja(id=1, nombre="Única", dias_activos=["Lunes", "Martes"])
    franjas = [
        Franja(id=1, plantilla_id=1, orden=1, hora_inicio="07:00", hora_fin="08:00"),
        Franja(id=2, plantilla_id=1, orden=2, hora_inicio="08:00", hora_fin="09:00"),
    ]  # 2 franjas × 2 días = 4 cupos/semana
    asignatura = Asignatura(id=5, nombre="Matemáticas", horas_semanales=3)
    grupos = [Grupo(id=1, codigo="601", grado=None)]
    asignaciones = [
        Asignacion(id=1, grupo_id=1, asignatura_id=5, usuario_id=1, periodo_id=1, activo=True)
    ]
    svc = _svc(
        grupos=grupos,
        asignaturas=[asignatura],
        franjas=franjas,
        plantillas=[plantilla],
        asignaciones=asignaciones,
    )

    puerta = svc._p3_horas_grupo_vs_slots(
        grupos, asignaciones, {5: asignatura}, {1: None}, plantilla, franjas
    )

    assert puerta.ok is True


# ===========================================================================
# T10 — capacidad_docente sube a "dura"
# ===========================================================================


def test_p_capacidad_docente_es_dura():
    """La severidad de `capacidad_docente` debe ser "dura": en el motor la
    carga horaria máxima del docente es una restricción dura, no una
    preferencia."""
    docente = Usuario(id=1, usuario="jdocente", nombre_completo="J. Docente", carga_horaria_max=2)
    asignatura = Asignatura(id=5, nombre="Matemáticas", horas_semanales=5)
    asignaciones = [
        Asignacion(id=1, grupo_id=1, asignatura_id=5, usuario_id=1, periodo_id=1, activo=True)
    ]  # 5h > 2h máx
    svc = _svc(asignaturas=[asignatura], asignaciones=asignaciones, usuarios=[docente])

    puerta = svc._p4_capacidad_docente(asignaciones, {5: asignatura}, {})

    assert puerta.severidad == "dura"
    assert puerta.ok is False


def test_p_capacidad_docente_ok_dentro_del_tope():
    docente = Usuario(id=1, usuario="jdocente", nombre_completo="J. Docente", carga_horaria_max=10)
    asignatura = Asignatura(id=5, nombre="Matemáticas", horas_semanales=5)
    asignaciones = [
        Asignacion(id=1, grupo_id=1, asignatura_id=5, usuario_id=1, periodo_id=1, activo=True)
    ]
    svc = _svc(asignaturas=[asignatura], asignaciones=asignaciones, usuarios=[docente])

    puerta = svc._p4_capacidad_docente(asignaciones, {5: asignatura}, {})

    assert puerta.severidad == "dura"
    assert puerta.ok is True


# ===========================================================================
# T11 — asignaciones_activas (nueva)
# ===========================================================================


def test_p_asignaciones_activas_roja_sin_asignaciones():
    svc = _svc()

    puerta = svc._p_asignaciones_activas([])

    assert puerta.id == "asignaciones_activas"
    assert puerta.severidad == "dura"
    assert puerta.ok is False
    assert puerta.fix_ruta == "/admin/asignaciones"


def test_p_asignaciones_activas_ok_con_al_menos_una():
    asignaciones = [
        Asignacion(id=1, grupo_id=1, asignatura_id=1, usuario_id=1, periodo_id=1, activo=True)
    ]
    svc = _svc(asignaciones=asignaciones)

    puerta = svc._p_asignaciones_activas(asignaciones)

    assert puerta.ok is True


def test_p_asignaciones_activas_roja_si_todas_inactivas():
    asignaciones = [
        Asignacion(id=1, grupo_id=1, asignatura_id=1, usuario_id=1, periodo_id=1, activo=False)
    ]
    svc = _svc(asignaciones=asignaciones)

    puerta = svc._p_asignaciones_activas(asignaciones)

    assert puerta.ok is False


# ===========================================================================
# T11 — capacidad_docente_slots (nueva)
# ===========================================================================


def test_p_capacidad_docente_slots_roja_por_vetos():
    """El docente tiene tope declarado amplio (no lo excede) pero vetó
    suficientes franjas de la plantilla: sus slots reales quedan por debajo
    de las horas asignadas."""
    plantilla = PlantillaFranja(id=1, nombre="Única", dias_activos=["Lunes", "Martes"])
    franjas = [
        Franja(id=1, plantilla_id=1, orden=1, hora_inicio="07:00", hora_fin="08:00"),
    ]  # 1 franja lectiva × 2 días = 2 cupos/semana
    docente = Usuario(id=1, usuario="jdocente", nombre_completo="J. Docente", carga_horaria_max=10)
    asignatura = Asignatura(id=5, nombre="Matemáticas", horas_semanales=2)
    asignaciones = [
        Asignacion(id=1, grupo_id=1, asignatura_id=5, usuario_id=1, periodo_id=1, activo=True)
    ]  # 2h asignadas
    disponibilidad = [
        DisponibilidadDocente(usuario_id=1, dia_semana="Lunes", franja_orden=1, disponible=False),
        DisponibilidadDocente(usuario_id=1, dia_semana="Martes", franja_orden=1, disponible=False),
    ]  # veta los 2 únicos cupos → 0 slots disponibles
    svc = _svc(
        asignaturas=[asignatura],
        franjas=franjas,
        plantillas=[plantilla],
        asignaciones=asignaciones,
        usuarios=[docente],
        disponibilidad=disponibilidad,
    )

    puerta = svc._p_capacidad_docente_slots(asignaciones, {5: asignatura}, {}, plantilla, franjas)

    assert puerta.id == "capacidad_docente_slots"
    assert puerta.severidad == "dura"
    assert puerta.ok is False
    assert puerta.fix_ruta == "/admin/disponibilidad-docente"


def test_p_capacidad_docente_slots_ok_sin_vetos():
    plantilla = PlantillaFranja(id=1, nombre="Única", dias_activos=["Lunes", "Martes"])
    franjas = [
        Franja(id=1, plantilla_id=1, orden=1, hora_inicio="07:00", hora_fin="08:00"),
    ]
    docente = Usuario(id=1, usuario="jdocente", nombre_completo="J. Docente", carga_horaria_max=10)
    asignatura = Asignatura(id=5, nombre="Matemáticas", horas_semanales=1)
    asignaciones = [
        Asignacion(id=1, grupo_id=1, asignatura_id=5, usuario_id=1, periodo_id=1, activo=True)
    ]
    svc = _svc(
        asignaturas=[asignatura],
        franjas=franjas,
        plantillas=[plantilla],
        asignaciones=asignaciones,
        usuarios=[docente],
    )

    puerta = svc._p_capacidad_docente_slots(asignaciones, {5: asignatura}, {}, plantilla, franjas)

    assert puerta.ok is True


# ===========================================================================
# T11 — disponibilidad_coherente (nueva)
# ===========================================================================


def test_p_disponibilidad_coherente_detecta_filas_huerfanas():
    plantilla = PlantillaFranja(id=1, nombre="Única", dias_activos=["Lunes"])
    franjas = [Franja(id=1, plantilla_id=1, orden=1, hora_inicio="07:00", hora_fin="08:00")]
    asignaciones = [
        Asignacion(id=1, grupo_id=1, asignatura_id=1, usuario_id=1, periodo_id=1, activo=True)
    ]
    disponibilidad = [
        # "viernes" no está en dias_activos de la plantilla → huérfana
        DisponibilidadDocente(usuario_id=1, dia_semana="Viernes", franja_orden=1, disponible=False),
    ]
    svc = _svc(
        franjas=franjas, plantillas=[plantilla], asignaciones=asignaciones, disponibilidad=disponibilidad
    )

    puerta = svc._p_disponibilidad_coherente(asignaciones, plantilla, franjas)

    assert puerta.id == "disponibilidad_coherente"
    assert puerta.severidad == "advertencia"
    assert puerta.ok is False


def test_p_disponibilidad_coherente_ok_sin_filas_huerfanas():
    plantilla = PlantillaFranja(id=1, nombre="Única", dias_activos=["Lunes"])
    franjas = [Franja(id=1, plantilla_id=1, orden=1, hora_inicio="07:00", hora_fin="08:00")]
    asignaciones = [
        Asignacion(id=1, grupo_id=1, asignatura_id=1, usuario_id=1, periodo_id=1, activo=True)
    ]
    disponibilidad = [
        DisponibilidadDocente(usuario_id=1, dia_semana="Lunes", franja_orden=1, disponible=False),
    ]
    svc = _svc(
        franjas=franjas, plantillas=[plantilla], asignaciones=asignaciones, disponibilidad=disponibilidad
    )

    puerta = svc._p_disponibilidad_coherente(asignaciones, plantilla, franjas)

    assert puerta.ok is True


# ===========================================================================
# T11 — grupos_con_grado (nueva)
# ===========================================================================


def test_p_grupos_con_grado_detecta_sin_grado():
    grupos = [Grupo(id=1, codigo="601", grado=6), Grupo(id=2, codigo="SIN", grado=None)]
    svc = _svc(grupos)

    puerta = svc._p_grupos_con_grado(grupos)

    assert puerta.id == "grupos_con_grado"
    assert puerta.severidad == "advertencia"
    assert puerta.ok is False
    assert puerta.fix_ruta == "/admin/grupos"
    assert "SIN" in puerta.detalle


def test_p_grupos_con_grado_ok_si_todos_tienen_grado():
    grupos = [Grupo(id=1, codigo="601", grado=6)]
    svc = _svc(grupos)

    puerta = svc._p_grupos_con_grado(grupos)

    assert puerta.ok is True


# ===========================================================================
# T8 — validar_config()
# ===========================================================================


def test_validar_config_config_inexistente_da_puerta_dura_roja():
    svc = _svc(config_generacion=None)

    reporte = svc.validar_config(config_id=999)

    assert len(reporte) == 1
    assert reporte[0].severidad == "dura"
    assert reporte[0].ok is False


def test_validar_config_usa_los_datos_de_la_config():
    """`validar_config` deriva anio_id/periodo_id/plantilla_id de la
    ConfigGeneracion, no de parámetros sueltos que puedan no coincidir con
    lo que se va a generar (B3 de la auditoría)."""
    config = ConfigGeneracion(
        id=1, nombre="Generación 2026-1", periodo_id=7, anio_id=3, plantilla_id=9
    )
    svc = _svc(config_generacion=config)

    reporte = svc.validar_config(config_id=1)

    ids = [p.id for p in reporte]
    assert "anio_periodo" in ids
    assert len(reporte) == 12


def test_validar_config_respeta_filtro_de_grupos():
    """Con `config.grupos` no vacío, las puertas que miran grupos (aquí,
    `grupos_con_grado`) solo consideran esos grupos: el grupo sin grado
    que quedó FUERA del filtro no debe aparecer en el reporte."""
    grupos = [
        Grupo(id=1, codigo="601", grado=6),
        Grupo(id=2, codigo="SIN", grado=None),  # fuera del filtro
    ]
    config = ConfigGeneracion(
        id=1,
        nombre="Generación 2026-1",
        periodo_id=1,
        anio_id=1,
        plantilla_id=1,
        grupos=[1],  # solo el grupo 601
    )
    svc = _svc(grupos=grupos, config_generacion=config)

    reporte = svc.validar_config(config_id=1)

    puerta = next(p for p in reporte if p.id == "grupos_con_grado")
    assert puerta.ok is True
    assert "SIN" not in puerta.detalle


# ===========================================================================
# T12 — fix_ruta según el rol
# ===========================================================================


def test_validar_rol_none_conserva_fix_ruta_admin():
    """Comportamiento previo (sin propagar rol): no se retira ningún
    fix_ruta."""
    svc = _svc()

    reporte = svc.validar(anio_id=1, periodo_id=1, plantilla_id=0)

    asignaciones_puerta = next(p for p in reporte if p.id == "asignaciones_activas")
    assert asignaciones_puerta.fix_ruta == "/admin/asignaciones"


def test_validar_rol_coordinador_retira_fix_ruta_admin():
    svc = _svc()

    reporte = svc.validar(anio_id=1, periodo_id=1, plantilla_id=0, rol="coordinador")

    asignaciones_puerta = next(p for p in reporte if p.id == "asignaciones_activas")
    assert asignaciones_puerta.fix_ruta is None
    # una ruta que no está bajo /admin/ se conserva
    plantilla_puerta = next(p for p in reporte if p.id == "plantilla_suficiente")
    assert plantilla_puerta.fix_ruta == "/academico/generar-horario?tab=plantillas"


def test_validar_rol_director_conserva_fix_ruta_admin():
    svc = _svc()

    reporte = svc.validar(anio_id=1, periodo_id=1, plantilla_id=0, rol="director")

    asignaciones_puerta = next(p for p in reporte if p.id == "asignaciones_activas")
    assert asignaciones_puerta.fix_ruta == "/admin/asignaciones"


# ===========================================================================
# puede_generar()
# ===========================================================================


def test_puede_generar_falso_con_cualquier_dura_roja():
    from src.services.preparacion_horario_service import PuertaDTO

    reporte = [
        PuertaDTO(id="a", titulo="A", severidad="dura", ok=True, detalle=""),
        PuertaDTO(id="b", titulo="B", severidad="dura", ok=False, detalle=""),
        PuertaDTO(id="c", titulo="C", severidad="advertencia", ok=False, detalle=""),
    ]

    assert PreparacionHorarioService.puede_generar(reporte) is False


def test_puede_generar_verdadero_si_solo_hay_advertencias_rojas():
    from src.services.preparacion_horario_service import PuertaDTO

    reporte = [
        PuertaDTO(id="a", titulo="A", severidad="dura", ok=True, detalle=""),
        PuertaDTO(id="c", titulo="C", severidad="advertencia", ok=False, detalle=""),
    ]

    assert PreparacionHorarioService.puede_generar(reporte) is True
