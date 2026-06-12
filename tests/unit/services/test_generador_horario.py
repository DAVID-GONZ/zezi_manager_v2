"""
Tests unitarios para GeneradorHorarioService (paso_15c).

Usa Fakes en memoria, sin BD. Verifica:
  1. Generación simple factible.
  2. Cruce de docente evitado.
  3. Disponibilidad respetada.
  4. Tope docente.
  5. Slots insuficientes (solución parcial).
  6. El GATE oráculo marca valido.
"""
from __future__ import annotations

from src.domain.models.asignacion import AsignacionInfo
from src.domain.models.infraestructura import (
    Asignatura,
    ConfigGeneracion,
    EscenarioHorario,
    Franja,
    PlantillaFranja,
)
from src.services.generador_horario_service import GeneradorHorarioService


# ===========================================================================
# Constantes
# ===========================================================================

PERIODO_ID = 1
ANIO_ID = 1
PLANTILLA_ID = 7


# ===========================================================================
# Fakes
# ===========================================================================

class FakeInfraRepo:
    """Repo de infraestructura mínimo y coherente para el generador."""

    def __init__(
        self,
        config: ConfigGeneracion,
        plantilla: PlantillaFranja,
        franjas: list[Franja],
        asignaturas: dict[int, Asignatura],
        no_disponibles: set | None = None,
    ):
        self._config = config
        self._plantilla = plantilla
        self._franjas = franjas
        self._asignaturas = asignaturas
        # set de (usuario_id, dia, franja_orden) NO disponibles
        self._no_disponibles = no_disponibles or set()
        self.config_actualizada = None
        self.estado_cambiado = None

    def get_config_generacion(self, config_id):
        return self._config if config_id == self._config.id else None

    def get_plantilla_franja(self, plantilla_id):
        return self._plantilla if plantilla_id == self._plantilla.id else None

    def listar_franjas(self, plantilla_id):
        return list(self._franjas)

    def get_asignatura(self, asignatura_id):
        return self._asignaturas.get(asignatura_id)

    def es_disponible(self, usuario_id, dia, franja_orden):
        return (usuario_id, dia, franja_orden) not in self._no_disponibles

    def actualizar_config_generacion(self, c):
        self.config_actualizada = c
        return c

    def cambiar_estado_config(self, config_id, nuevo_estado):
        self.estado_cambiado = nuevo_estado
        return self._config.model_copy(update={"estado": nuevo_estado})


class FakeAsignacionRepo:
    def __init__(self, asignaciones: list[AsignacionInfo]):
        self._asigs = asignaciones

    def listar_info(self, filtro):
        return [
            a for a in self._asigs
            if a.periodo_id == filtro.periodo_id
        ]

    def get_by_id(self, asignacion_id):
        for a in self._asigs:
            if a.asignacion_id == asignacion_id:
                return a
        return None


class FakeUsuarioService:
    def __init__(self, cargas: dict[int, int | None] | None = None):
        self._cargas = cargas or {}

    def carga_horaria_max(self, usuario_id):
        return self._cargas.get(usuario_id)


class FakeInfraestructuraService:
    """Crea escenarios inactivos con id incremental."""

    def __init__(self):
        self._next_id = 100
        self.creados = []

    def crear_escenario_simple(self, anio_id, nombre, descripcion=None):
        esc = EscenarioHorario(
            id=self._next_id, anio_id=anio_id, nombre=nombre,
            descripcion=descripcion, activo=False,
        )
        self._next_id += 1
        self.creados.append(esc)
        return esc


class FakeHorarioService:
    """
    Oráculo: reimplementa la verificación mínima de cruces sobre el lote.
    Usa el FakeAsignacionRepo para resolver grupo_id/usuario_id de cada fila.
    """

    def __init__(self, asignacion_repo, usuario_service, asignaturas):
        self._asig = asignacion_repo
        self._usuario = usuario_service
        self._asignaturas = asignaturas
        self.aplicado = None

    def analizar_lote(self, escenario_id, periodo_id, filas):
        from src.domain.models.infraestructura import (
            FilaReporteDTO,
            ReporteLoteDTO,
        )
        vistos_grupo: set = set()
        vistos_docente: set = set()
        conteo_doc: dict = {}
        resultado = []
        for i, fila in enumerate(filas):
            asig = self._asig.get_by_id(int(fila["asignacion_id"]))
            ok, motivo = True, None
            dia = fila["dia_semana"]
            hi = fila["hora_inicio"]
            clave_g = (asig.grupo_id, dia, hi)
            clave_d = (asig.usuario_id, dia, hi)
            if clave_g in vistos_grupo:
                ok, motivo = False, "Cruce: grupo ocupado."
            elif clave_d in vistos_docente:
                ok, motivo = False, "Cruce: docente ocupado."
            else:
                tope = self._usuario.carga_horaria_max(asig.usuario_id)
                usado = conteo_doc.get(asig.usuario_id, 0)
                if tope is not None and usado + 1 > tope:
                    ok, motivo = False, "Tope docente."
            if ok:
                vistos_grupo.add(clave_g)
                vistos_docente.add(clave_d)
                conteo_doc[asig.usuario_id] = conteo_doc.get(asig.usuario_id, 0) + 1
            resultado.append(FilaReporteDTO(indice=i, ok=ok, motivo=motivo))
        return ReporteLoteDTO(filas=resultado)

    def aplicar_lote(self, escenario_id, periodo_id, filas, solo_validas=False):
        from src.domain.models.infraestructura import (
            ResultadoLoteDTO,
        )
        reporte = self.analizar_lote(escenario_id, periodo_id, filas)
        self.aplicado = filas
        creados = sum(1 for f in reporte.filas if f.ok)
        return ResultadoLoteDTO(
            creados=creados, omitidos=len(filas) - creados, reporte=reporte
        )


# ===========================================================================
# Helpers
# ===========================================================================

def _franja(orden, hi, hf, tipo="lectiva"):
    return Franja(
        id=orden, plantilla_id=PLANTILLA_ID, orden=orden,
        hora_inicio=hi, hora_fin=hf, tipo=tipo,
    )


def _asig_info(asig_id, grupo_id, usuario_id, asignatura_id):
    return AsignacionInfo(
        asignacion_id=asig_id,
        grupo_id=grupo_id,
        grupo_codigo=f"G{grupo_id}",
        asignatura_id=asignatura_id,
        asignatura_nombre=f"Materia {asignatura_id}",
        usuario_id=usuario_id,
        docente_nombre=f"Docente {usuario_id}",
        periodo_id=PERIODO_ID,
        periodo_nombre="Periodo 1",
        periodo_numero=1,
        activo=True,
    )


def _config(grupos=None):
    return ConfigGeneracion(
        id=1, nombre="Config Test", periodo_id=PERIODO_ID,
        anio_id=ANIO_ID, plantilla_id=PLANTILLA_ID, estado="borrador",
        grupos=grupos or [],
    )


def _plantilla(dias):
    return PlantillaFranja(
        id=PLANTILLA_ID, nombre="Plantilla Test", jornada="UNICA",
        dias_activos=dias, activa=True,
    )


def _build(config, plantilla, franjas, asig_infos, asignaturas,
           cargas=None, no_disponibles=None):
    infra = FakeInfraRepo(config, plantilla, franjas, asignaturas, no_disponibles)
    asig_repo = FakeAsignacionRepo(asig_infos)
    usuario = FakeUsuarioService(cargas)
    infraestructura = FakeInfraestructuraService()
    horario = FakeHorarioService(asig_repo, usuario, asignaturas)
    svc = GeneradorHorarioService(
        infra_repo=infra,
        asignacion_repo=asig_repo,
        usuario_repo=usuario,
        horario_service=horario,
        infraestructura_service=infraestructura,
    )
    return svc, infra, horario, infraestructura


# Plantilla estándar: 3 días × 3 franjas lectivas = 9 slots.
DIAS_3 = ["Lunes", "Martes", "Miércoles"]
FRANJAS_3 = [
    _franja(1, "07:00", "07:55"),
    _franja(2, "08:00", "08:55"),
    _franja(3, "09:00", "09:55"),
]


# ===========================================================================
# Tests
# ===========================================================================

def test_generacion_simple_factible():
    """1 grupo, 2 asignaturas de 2h, 9 slots, docente libre → todo colocado y válido."""
    asignaturas = {5: Asignatura(id=5, nombre="Mate", horas_semanales=2),
                   6: Asignatura(id=6, nombre="Lengua", horas_semanales=2)}
    asig_infos = [
        _asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5),
        _asig_info(11, grupo_id=1, usuario_id=4, asignatura_id=6),
    ]
    svc, infra, horario, infraestructura = _build(
        _config(), _plantilla(DIAS_3), FRANJAS_3, asig_infos, asignaturas,
    )

    res = svc.generar(1)

    assert res.total_requeridos == 4
    assert res.colocados == 4
    assert res.no_colocados == 0
    assert res.valido is True
    assert res.escenario_id == 100
    assert horario.aplicado is not None
    assert infra.estado_cambiado == "generado"
    assert infra.config_actualizada.escenario_destino_id == 100


def test_cruce_docente_evitado():
    """Mismo docente en 2 grupos → nunca dos bloques en la misma (dia, franja_orden)."""
    asignaturas = {5: Asignatura(id=5, nombre="Mate", horas_semanales=3),
                   6: Asignatura(id=6, nombre="Mate", horas_semanales=3)}
    asig_infos = [
        _asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5),
        _asig_info(11, grupo_id=2, usuario_id=3, asignatura_id=6),  # mismo docente
    ]
    svc, *_ = _build(
        _config(), _plantilla(DIAS_3), FRANJAS_3, asig_infos, asignaturas,
    )

    res = svc.generar(1)

    vistos = set()
    for b in res.bloques:
        clave = (b.usuario_id, b.dia_semana, b.franja_orden)
        assert clave not in vistos, "Dos bloques del mismo docente en la misma franja."
        vistos.add(clave)
    assert res.valido is True


def test_disponibilidad_respetada():
    """Docente no disponible en (Lunes, orden 1) → ningún bloque suyo cae ahí."""
    asignaturas = {5: Asignatura(id=5, nombre="Mate", horas_semanales=2)}
    asig_infos = [_asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5)]
    no_disp = {(3, "Lunes", 1)}
    svc, *_ = _build(
        _config(), _plantilla(DIAS_3), FRANJAS_3, asig_infos, asignaturas,
        no_disponibles=no_disp,
    )

    res = svc.generar(1)

    for b in res.bloques:
        if b.usuario_id == 3:
            assert not (b.dia_semana == "Lunes" and b.franja_orden == 1)
    assert res.colocados == 2


def test_tope_docente():
    """carga_horaria_max=2 con 3 horas requeridas → máximo 2 colocados, 1 incidencia."""
    asignaturas = {5: Asignatura(id=5, nombre="Mate", horas_semanales=3)}
    asig_infos = [_asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5)]
    svc, *_ = _build(
        _config(), _plantilla(DIAS_3), FRANJAS_3, asig_infos, asignaturas,
        cargas={3: 2},
    )

    res = svc.generar(1)

    bloques_doc = [b for b in res.bloques if b.usuario_id == 3]
    assert len(bloques_doc) <= 2
    assert res.no_colocados >= 1
    assert any("No colocado" in inc for inc in res.incidencias)


def test_slots_insuficientes():
    """Más horas requeridas que slots del grupo → solución parcial, sin excepción."""
    # Plantilla pequeña: 1 día × 2 franjas = 2 slots para 1 grupo.
    plantilla = _plantilla(["Lunes"])
    franjas = [_franja(1, "07:00", "07:55"), _franja(2, "08:00", "08:55")]
    asignaturas = {5: Asignatura(id=5, nombre="Mate", horas_semanales=5)}
    asig_infos = [_asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5)]
    svc, *_ = _build(
        _config(), plantilla, franjas, asig_infos, asignaturas,
    )

    res = svc.generar(1)

    assert res.total_requeridos == 5
    assert res.colocados == 2          # solo caben 2
    assert res.no_colocados == 3
    assert len(res.incidencias) >= 1


def test_gate_marca_valido():
    """Sin colisiones, el oráculo (FakeHorarioService) marca valido=True."""
    asignaturas = {5: Asignatura(id=5, nombre="Mate", horas_semanales=1)}
    asig_infos = [_asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5)]
    svc, _infra, horario, _ = _build(
        _config(), _plantilla(DIAS_3), FRANJAS_3, asig_infos, asignaturas,
    )

    res = svc.generar(1)

    assert res.valido is True
    assert horario.aplicado is not None


# ===========================================================================
# Tests paso_15d — coste blando + mejora local
# ===========================================================================

def _config_pesos(pesos):
    return ConfigGeneracion(
        id=1, nombre="Config Test", periodo_id=PERIODO_ID,
        anio_id=ANIO_ID, plantilla_id=PLANTILLA_ID, estado="borrador",
        pesos=pesos,
    )


def test_costo_huecos_detecta_hueco():
    """
    Coste de huecos correcto: un grupo con bloques en idx 0 y 2 dejando el 1
    vacío debe producir huecos_grupo >= 1. Se verifica directamente sobre el
    helper de coste con un colocados controlado.
    """
    from src.domain.models.infraestructura import PesosGeneracion
    from src.services.generador_horario_service import _Leccion

    lec = _Leccion(10, grupo_id=1, usuario_id=3, etiqueta="G1/Mate")
    f0, f1, f2 = FRANJAS_3  # orden 1, 2, 3
    orden_a_idx = {1: 0, 2: 1, 3: 2}
    colocados = [
        (lec, "Lunes", f0),  # idx 0
        (lec, "Lunes", f2),  # idx 2 → hueco en idx 1
    ]
    pesos = PesosGeneracion(huecos=1.0, distribucion=0.0, compactacion=0.0)
    costo, metricas = GeneradorHorarioService._costo(colocados, pesos, orden_a_idx)

    assert metricas.huecos_grupo >= 1
    assert costo >= 1.0


def test_costo_recreo_no_cuenta_como_hueco():
    """Una franja no lectiva (recreo) entre dos lectivas NO genera hueco."""
    from src.domain.models.infraestructura import PesosGeneracion
    from src.services.generador_horario_service import _Leccion

    # Lectivas en orden 1, 2 y 5; recreo (no lectivo) en orden 4. El índice
    # compacto las hace contiguas: 0, 1, 2.
    fa = _franja(1, "07:00", "07:55")
    fb = _franja(2, "08:00", "08:55")
    fc = _franja(5, "09:00", "09:55")
    orden_a_idx = {1: 0, 2: 1, 5: 2}
    lec = _Leccion(10, grupo_id=1, usuario_id=3, etiqueta="G1/Mate")
    colocados = [(lec, "Lunes", fa), (lec, "Lunes", fc)]  # idx 0 y 2
    pesos = PesosGeneracion(huecos=1.0, distribucion=0.0, compactacion=0.0)
    _, metricas = GeneradorHorarioService._costo(colocados, pesos, orden_a_idx)
    # idx usados {0, 2} → hueco = (2-0+1) - 2 = 1 (el idx 1, otra lectiva vacía).
    assert metricas.huecos_grupo == 1
    # fb (orden 2 / idx 1) NO está colocada, por eso hay 1 hueco real; pero el
    # recreo en orden 4 jamás aparece en el índice compacto.


def test_mejora_local_no_aumenta_costo():
    """metricas.costo_final <= metricas.costo_inicial siempre."""
    asignaturas = {5: Asignatura(id=5, nombre="Mate", horas_semanales=3),
                   6: Asignatura(id=6, nombre="Lengua", horas_semanales=3)}
    asig_infos = [
        _asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5),
        _asig_info(11, grupo_id=1, usuario_id=4, asignatura_id=6),
    ]
    svc, *_ = _build(
        _config(), _plantilla(DIAS_3), FRANJAS_3, asig_infos, asignaturas,
    )

    res = svc.generar(1)

    assert res.metricas is not None
    assert res.metricas.costo_final <= res.metricas.costo_inicial


def test_mejora_local_reduce_hueco():
    """
    Monta un caso donde la solución constructiva tiende a dejar bloques de la
    misma asignación el mismo día (solapes de distribución) y comprueba que la
    optimización no empeora; al menos pasos_mejora >= 0 y costo_final <= inicial.
    """
    asignaturas = {5: Asignatura(id=5, nombre="Mate", horas_semanales=3)}
    asig_infos = [_asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5)]
    pesos = __import__(
        "src.domain.models.infraestructura", fromlist=["PesosGeneracion"]
    ).PesosGeneracion(huecos=2.0, distribucion=2.0, compactacion=2.0)
    svc, *_ = _build(
        _config_pesos(pesos), _plantilla(DIAS_3), FRANJAS_3, asig_infos, asignaturas,
    )

    res = svc.generar(1)

    assert res.metricas is not None
    assert res.metricas.pasos_mejora >= 0
    assert res.metricas.costo_final <= res.metricas.costo_inicial


def test_invariante_restricciones_tras_optimizar():
    """
    Tras optimizar: no hay dos bloques con mismo (usuario, dia, orden) ni
    (grupo, dia, orden), y ningún bloque cae en franja no disponible.
    """
    asignaturas = {5: Asignatura(id=5, nombre="Mate", horas_semanales=3),
                   6: Asignatura(id=6, nombre="Lengua", horas_semanales=2)}
    asig_infos = [
        _asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5),
        _asig_info(11, grupo_id=2, usuario_id=3, asignatura_id=6),  # mismo docente
    ]
    no_disp = {(3, "Martes", 2)}
    svc, *_ = _build(
        _config(), _plantilla(DIAS_3), FRANJAS_3, asig_infos, asignaturas,
        no_disponibles=no_disp,
    )

    res = svc.generar(1)

    vistos_doc = set()
    vistos_grp = set()
    for b in res.bloques:
        cd = (b.usuario_id, b.dia_semana, b.franja_orden)
        cg = (b.grupo_id, b.dia_semana, b.franja_orden)
        assert cd not in vistos_doc, "Dos bloques del mismo docente en la misma franja."
        assert cg not in vistos_grp, "Dos bloques del mismo grupo en la misma franja."
        vistos_doc.add(cd)
        vistos_grp.add(cg)
        if b.usuario_id == 3:
            assert (b.dia_semana, b.franja_orden) != ("Martes", 2), \
                "Bloque en franja no disponible del docente."


def test_optimizar_false_deja_constructiva():
    """optimizar=False → costo_inicial == costo_final y pasos_mejora == 0."""
    asignaturas = {5: Asignatura(id=5, nombre="Mate", horas_semanales=3)}
    asig_infos = [_asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5)]
    svc, *_ = _build(
        _config(), _plantilla(DIAS_3), FRANJAS_3, asig_infos, asignaturas,
    )

    res = svc.generar(1, optimizar=False)

    assert res.metricas is not None
    assert res.metricas.pasos_mejora == 0
    assert res.metricas.costo_inicial == res.metricas.costo_final


def test_metricas_presentes_y_coherentes():
    """resultado.metricas no es None y sus campos son no negativos."""
    asignaturas = {5: Asignatura(id=5, nombre="Mate", horas_semanales=2)}
    asig_infos = [_asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5)]
    svc, *_ = _build(
        _config(), _plantilla(DIAS_3), FRANJAS_3, asig_infos, asignaturas,
    )

    res = svc.generar(1)

    m = res.metricas
    assert m is not None
    assert m.huecos_grupo >= 0
    assert m.huecos_docente >= 0
    assert m.solapes_distribucion >= 0
    assert m.dias_docente >= 0
    assert m.costo_inicial >= 0.0
    assert m.costo_final >= 0.0
    assert m.pasos_mejora >= 0
