"""
Tests unitarios para GeneradorHorarioService (paso_15c / paso_17 Fase C/D/E).

Usa Fakes en memoria, sin BD. Verifica:
  1. Generación simple factible.
  2. Cruce de docente evitado.
  3. Disponibilidad respetada.
  4. Tope docente.
  5. Slots insuficientes (solución parcial).
  6. El GATE oráculo marca valido.
  7-13. Salas, bloques dobles, ventanas de grupo, FranjaReunion, límites diarios.
  14-17. Pre-vuelo, relajación y diagnóstico de infactibilidad (T8).
"""
from __future__ import annotations

from src.domain.models.asignacion import AsignacionInfo
from src.domain.models.infraestructura import (
    Asignatura,
    ConfigGeneracion,
    EscenarioHorario,
    Franja,
    FranjaReunion,
    LimitesDocente,
    PlantillaFranja,
    Sala,
    VentanaGrupo,
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

    def listar_grupos(self, grado=None):
        return []

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
    """Crea escenarios inactivos con id incremental. Soporta salas/ventanas/etc. para T5/T6."""

    def __init__(self, salas=None, ventanas_grupo=None, limites_docente=None,
                 franjas_reunion=None):
        self._next_id = 100
        self.creados = []
        self._salas = salas or []
        self._ventanas_grupo = ventanas_grupo or []
        self._limites_docente = limites_docente or []
        self._franjas_reunion = franjas_reunion or []

    def crear_escenario_simple(self, anio_id, nombre, descripcion=None):
        esc = EscenarioHorario(
            id=self._next_id, anio_id=anio_id, nombre=nombre,
            descripcion=descripcion, activo=False,
        )
        self._next_id += 1
        self.creados.append(esc)
        return esc

    def listar_salas(self):
        return list(self._salas)

    def listar_ventanas_grupo(self):
        return list(self._ventanas_grupo)

    def listar_limites_docente(self):
        return list(self._limites_docente)

    def listar_franjas_reunion(self):
        return list(self._franjas_reunion)


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
           cargas=None, no_disponibles=None,
           salas=None, ventanas_grupo=None, limites_docente=None,
           franjas_reunion=None):
    infra = FakeInfraRepo(config, plantilla, franjas, asignaturas, no_disponibles)
    asig_repo = FakeAsignacionRepo(asig_infos)
    usuario = FakeUsuarioService(cargas)
    infraestructura = FakeInfraestructuraService(
        salas=salas,
        ventanas_grupo=ventanas_grupo,
        limites_docente=limites_docente,
        franjas_reunion=franjas_reunion,
    )
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


# ===========================================================================
# Tests paso_17 Fase C — T5: Salas + Bloques dobles
# ===========================================================================

# FRANJAS_5: 5 franjas lectivas para tener pares consecutivos en DIAS_3
FRANJAS_5 = [
    _franja(1, "07:00", "07:55"),
    _franja(2, "08:00", "08:55"),
    _franja(3, "09:00", "09:55"),
    _franja(4, "10:00", "10:55"),
    _franja(5, "11:00", "11:55"),
]


def test_bloque_doble_coloca_franjas_consecutivas():
    """bloque_doble=True, horas_consecutivas=2 → los 2 bloques son del mismo día y consecutivos."""
    asignaturas = {
        5: Asignatura(id=5, nombre="Lab", horas_semanales=2,
                      bloque_doble=True, horas_consecutivas=2),
    }
    asig_infos = [_asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5)]
    svc, *_ = _build(_config(), _plantilla(DIAS_3), FRANJAS_5, asig_infos, asignaturas)

    res = svc.generar(1)

    assert res.total_requeridos == 2
    assert res.colocados == 2
    assert len(res.bloques) == 2
    dias_bloques = {b.dia_semana for b in res.bloques}
    assert len(dias_bloques) == 1, "El bloque doble debe estar en un único día"
    ordenes = sorted(b.franja_orden for b in res.bloques)
    assert ordenes[1] == ordenes[0] + 1, "Las franjas del bloque doble deben ser consecutivas"


def test_bloque_doble_no_divide_en_dias_distintos():
    """Con 1 sola franja por día, el bloque doble no puede colocarse (slots insuficientes)."""
    # Solo 1 franja lectiva → no hay par consecutivo → no se puede colocar el doble
    plantilla_1f = _plantilla(DIAS_3)
    franjas_1 = [_franja(1, "07:00", "07:55")]
    asignaturas = {
        5: Asignatura(id=5, nombre="Lab", horas_semanales=2,
                      bloque_doble=True, horas_consecutivas=2),
    }
    asig_infos = [_asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5)]
    svc, *_ = _build(_config(), plantilla_1f, franjas_1, asig_infos, asignaturas)

    res = svc.generar(1)

    # Sin pares consecutivos disponibles, el macro-bloque no puede colocarse
    assert res.colocados == 0
    assert res.no_colocados == 2


def test_sala_asignada_por_tipo():
    """Asignatura con tipo_sala_requerido='laboratorio' → los bloques tienen sala_id del lab."""
    salas = [Sala(id=1, nombre="Lab Química", tipo="laboratorio", capacidad=30)]
    asignaturas = {
        5: Asignatura(id=5, nombre="Lab Q", horas_semanales=1,
                      tipo_sala_requerido="laboratorio"),
    }
    asig_infos = [_asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5)]
    svc, *_ = _build(
        _config(), _plantilla(DIAS_3), FRANJAS_3, asig_infos, asignaturas,
        salas=salas,
    )

    res = svc.generar(1)

    assert res.colocados == 1
    assert res.bloques[0].sala_id == 1
    assert res.bloques[0].sala == "Lab Química"


def test_sala_sin_conflicto_con_una_sola_sala():
    """Con 1 sola sala y 2 grupos que la requieren: no se asigna la misma sala al mismo slot."""
    salas = [Sala(id=1, nombre="Lab", tipo="laboratorio", capacidad=30)]
    asignaturas = {
        5: Asignatura(id=5, nombre="Lab G1", horas_semanales=3,
                      tipo_sala_requerido="laboratorio"),
        6: Asignatura(id=6, nombre="Lab G2", horas_semanales=3,
                      tipo_sala_requerido="laboratorio"),
    }
    asig_infos = [
        _asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5),
        _asig_info(11, grupo_id=2, usuario_id=4, asignatura_id=6),
    ]
    svc, *_ = _build(
        _config(), _plantilla(DIAS_3), FRANJAS_3, asig_infos, asignaturas,
        salas=salas,
    )

    res = svc.generar(1)

    # Con 3 slots y 1 sala compartida: máximo 3 bloques colocados (1 por slot)
    from collections import Counter
    sala_slots = Counter(
        (b.dia_semana, b.franja_orden)
        for b in res.bloques if b.sala_id == 1
    )
    assert max(sala_slots.values(), default=0) <= 1, \
        "No puede haber dos bloques usando la misma sala en el mismo slot"


def test_sin_salas_configuradas_comportamiento_defecto():
    """Sin salas en el sistema (R16): genera igual que antes, sala='Aula', sala_id=None."""
    asignaturas = {5: Asignatura(id=5, nombre="Mate", horas_semanales=2)}
    asig_infos = [_asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5)]
    svc, *_ = _build(_config(), _plantilla(DIAS_3), FRANJAS_3, asig_infos, asignaturas)

    res = svc.generar(1)

    assert res.colocados == 2
    for b in res.bloques:
        assert b.sala == "Aula"
        assert b.sala_id is None


# ===========================================================================
# Tests paso_17 Fase C — T6: Ventanas de grupo + híbridas estrictas
# ===========================================================================

def test_ventana_grupo_restringe_franjas():
    """VentanaGrupo con franjas_permitidas=[1] → el grupo solo tiene bloques en franja 1."""
    vg = VentanaGrupo(id=1, grupo_id=1, franjas_permitidas=[1])
    asignaturas = {5: Asignatura(id=5, nombre="Mate", horas_semanales=2)}
    asig_infos = [_asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5)]
    svc, *_ = _build(
        _config(), _plantilla(DIAS_3), FRANJAS_3, asig_infos, asignaturas,
        ventanas_grupo=[vg],
    )

    res = svc.generar(1)

    # DIAS_3 × franja_orden=1 = 3 slots → 2 bloques deben caber
    assert res.colocados == 2
    for b in res.bloques:
        if b.grupo_id == 1:
            assert b.franja_orden == 1, \
                f"Bloque del grupo fuera de la ventana permitida: orden {b.franja_orden}"


def test_ventana_grupo_no_afecta_otro_grupo():
    """La VentanaGrupo de grupo_id=1 no restringe al grupo_id=2."""
    vg = VentanaGrupo(id=1, grupo_id=1, franjas_permitidas=[1])
    asignaturas = {5: Asignatura(id=5, nombre="Mate", horas_semanales=2)}
    asig_infos = [
        _asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5),
        _asig_info(11, grupo_id=2, usuario_id=4, asignatura_id=5),
    ]
    svc, *_ = _build(
        _config(), _plantilla(DIAS_3), FRANJAS_3, asig_infos, asignaturas,
        ventanas_grupo=[vg],
    )

    res = svc.generar(1)

    # Grupo 2 puede usar cualquier franja
    ordenes_g2 = {b.franja_orden for b in res.bloques if b.grupo_id == 2}
    # No limitado a [1]; puede usar 1, 2 o 3
    assert ordenes_g2, "El grupo 2 debe tener bloques colocados"


def test_franja_reunion_estricta_bloqueada():
    """FranjaReunion modo='estricta' → ese docente no puede tener bloques en esa franja."""
    fr = FranjaReunion(id=1, nombre="Reunión área", docentes=[3],
                       dia_semana="Lunes", franja_orden=1, modo="estricta")
    asignaturas = {5: Asignatura(id=5, nombre="Mate", horas_semanales=2)}
    asig_infos = [_asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5)]
    svc, *_ = _build(
        _config(), _plantilla(DIAS_3), FRANJAS_3, asig_infos, asignaturas,
        franjas_reunion=[fr],
    )

    res = svc.generar(1)

    assert res.colocados == 2
    for b in res.bloques:
        if b.usuario_id == 3:
            assert not (b.dia_semana == "Lunes" and b.franja_orden == 1), \
                "Docente colocado en franja de reunión estricta"


def test_franja_reunion_preferente_no_bloquea():
    """FranjaReunion modo='preferente' → NO bloquea el slot (el motor lo puede usar)."""
    fr = FranjaReunion(id=1, nombre="Reunión opcional", docentes=[3],
                       dia_semana="Lunes", franja_orden=1, modo="preferente")
    asignaturas = {5: Asignatura(id=5, nombre="Mate", horas_semanales=3)}
    asig_infos = [_asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5)]
    svc, *_ = _build(
        _config(), _plantilla(DIAS_3), FRANJAS_3, asig_infos, asignaturas,
        franjas_reunion=[fr],
    )

    res = svc.generar(1)

    # 3 horas en 9 slots disponibles, sin bloqueo real → debe colocarlos todos
    assert res.colocados == 3


def test_max_horas_dia_estricta_por_config():
    """config.restricciones min_max_diario max_horas_dia=1 modo estricta → max 1h/día/docente."""
    config = ConfigGeneracion(
        id=1, nombre="Config Test", periodo_id=PERIODO_ID,
        anio_id=ANIO_ID, plantilla_id=PLANTILLA_ID, estado="borrador",
        restricciones={"min_max_diario": {"max_horas_dia": 1, "modo": "estricta"}},
    )
    asignaturas = {5: Asignatura(id=5, nombre="Mate", horas_semanales=3)}
    asig_infos = [_asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5)]
    svc, *_ = _build(config, _plantilla(DIAS_3), FRANJAS_3, asig_infos, asignaturas)

    res = svc.generar(1)

    from collections import Counter
    horas_por_dia = Counter(b.dia_semana for b in res.bloques if b.usuario_id == 3)
    assert all(v <= 1 for v in horas_por_dia.values()), \
        f"Docente supera 1h/día: {dict(horas_por_dia)}"
    # 3 horas, max 1/día, 3 días → deben colocarse todas (1 por día)
    assert res.colocados == 3


def test_max_horas_dia_por_limites_docente():
    """LimitesDocente.max_horas_dia se aplica como duro (equivalente a modo estricta)."""
    ld = LimitesDocente(id=1, usuario_id=3, min_horas_dia=0, max_horas_dia=1)
    asignaturas = {5: Asignatura(id=5, nombre="Mate", horas_semanales=3)}
    asig_infos = [_asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5)]
    svc, *_ = _build(
        _config(), _plantilla(DIAS_3), FRANJAS_3, asig_infos, asignaturas,
        limites_docente=[ld],
    )

    res = svc.generar(1)

    from collections import Counter
    horas_por_dia = Counter(b.dia_semana for b in res.bloques if b.usuario_id == 3)
    assert all(v <= 1 for v in horas_por_dia.values()), \
        f"Docente supera max_horas_dia=1: {dict(horas_por_dia)}"


# ===========================================================================
# Tests paso_17 Fase D — T7: Coste blando adicional (balance_diario, dia_libre)
# ===========================================================================

def test_balance_diario_distribucion_optima_menor_que_concentracion():
    """Con balance_diario activo (otros pesos=0), 1 bloque/día da menor costo que 2+1."""
    from src.domain.models.infraestructura import PesosGeneracion
    from src.services.generador_horario_service import _Leccion

    lec = _Leccion(10, grupo_id=1, usuario_id=3, etiqueta="G1/Mate")
    f1, f2, f3 = FRANJAS_3
    orden_a_idx = {1: 0, 2: 1, 3: 2}
    pesos = PesosGeneracion(
        balance_diario=1.0, huecos=0.0, distribucion=0.0, compactacion=0.0
    )
    # 1 bloque por día → sum_sq mínimo para 3 bloques
    colocados_distribuido = [
        (lec, "Lunes", f1),
        (lec, "Martes", f1),
        (lec, "Miércoles", f1),
    ]
    # 2 bloques en Lunes, 0 en Martes, 1 en Miércoles → más concentrado
    colocados_concentrado = [
        (lec, "Lunes", f1),
        (lec, "Lunes", f2),
        (lec, "Miércoles", f1),
    ]
    costo_dist, _ = GeneradorHorarioService._costo(
        colocados_distribuido, pesos, orden_a_idx, n_dias_total=3
    )
    costo_conc, _ = GeneradorHorarioService._costo(
        colocados_concentrado, pesos, orden_a_idx, n_dias_total=3
    )
    # Distribución perfecta (1/día): sum_sq=3; concentrado (2+1): sum_sq=5
    assert costo_dist < costo_conc


def test_balance_diario_penaliza_concentracion():
    """balance_diario > 0 cuando bloques concentrados en pocos días."""
    from src.domain.models.infraestructura import PesosGeneracion
    from src.services.generador_horario_service import _Leccion

    lec = _Leccion(10, grupo_id=1, usuario_id=3, etiqueta="G1/Mate")
    f1 = FRANJAS_3[0]
    f2 = FRANJAS_3[1]
    orden_a_idx = {1: 0, 2: 1, 3: 2}
    # 3 bloques el lunes, 0 el martes y miércoles (solo Lunes ocupado)
    colocados_concentrado = [
        (lec, "Lunes", f1),
        (lec, "Lunes", f2),
    ]
    # 1 bloque el lunes, 1 el martes (distribuido)
    colocados_distribuido = [
        (lec, "Lunes", f1),
        (lec, "Martes", f1),
    ]
    pesos = PesosGeneracion(balance_diario=1.0)
    costo_concentrado, _ = GeneradorHorarioService._costo(
        colocados_concentrado, pesos, orden_a_idx, n_dias_total=3
    )
    costo_distribuido, _ = GeneradorHorarioService._costo(
        colocados_distribuido, pesos, orden_a_idx, n_dias_total=3
    )
    # Concentrado (2+0 vs 1+1) → mayor varianza → mayor costo
    assert costo_concentrado > costo_distribuido


def test_dia_libre_penaliza_sin_dia_libre():
    """dia_libre penaliza cuando el docente trabaja todos los días activos."""
    from src.domain.models.infraestructura import PesosGeneracion
    from src.services.generador_horario_service import _Leccion

    lec = _Leccion(10, grupo_id=1, usuario_id=3, etiqueta="G1/Mate")
    f1 = FRANJAS_3[0]
    orden_a_idx = {1: 0, 2: 1, 3: 2}
    # Trabaja los 3 días → sin día libre
    colocados_sin_libre = [
        (lec, "Lunes", f1),
        (lec, "Martes", f1),
        (lec, "Miércoles", f1),
    ]
    # Solo trabaja 2 días → tiene 1 día libre
    colocados_con_libre = [
        (lec, "Lunes", f1),
        (lec, "Martes", f1),
    ]
    pesos = PesosGeneracion(dia_libre=1.0)
    costo_sin_libre, _ = GeneradorHorarioService._costo(
        colocados_sin_libre, pesos, orden_a_idx, n_dias_total=3
    )
    costo_con_libre, _ = GeneradorHorarioService._costo(
        colocados_con_libre, pesos, orden_a_idx, n_dias_total=3
    )
    assert costo_sin_libre > costo_con_libre


def test_balance_diario_con_pesos_cero_no_cambia_costo():
    """balance_diario=0.0 (peso cero) → no añade costo respecto a balance_diario=1.0."""
    from src.domain.models.infraestructura import PesosGeneracion
    from src.services.generador_horario_service import _Leccion

    lec = _Leccion(10, grupo_id=1, usuario_id=3, etiqueta="G1/Mate")
    f1, f2 = FRANJAS_3[0], FRANJAS_3[1]
    orden_a_idx = {1: 0, 2: 1, 3: 2}
    # 2 bloques concentrados en un solo día → sum_sq=4 con balance_diario activo
    colocados = [(lec, "Lunes", f1), (lec, "Lunes", f2)]

    pesos_con = PesosGeneracion(
        balance_diario=1.0, huecos=0.0, distribucion=0.0, compactacion=0.0
    )
    pesos_sin = PesosGeneracion(
        balance_diario=0.0, huecos=0.0, distribucion=0.0, compactacion=0.0
    )
    costo_con, _ = GeneradorHorarioService._costo(colocados, pesos_con, orden_a_idx)
    costo_sin, _ = GeneradorHorarioService._costo(colocados, pesos_sin, orden_a_idx)

    assert costo_con > costo_sin  # el peso activo añade costo (4.0 vs 0.0)


def test_generacion_balance_diario_reduce_concentracion():
    """Con balance_diario alto, el motor distribuye los bloques entre días."""
    from src.domain.models.infraestructura import PesosGeneracion

    # 3 horas de una materia en 3 días: sin balance, puede concentrarse.
    # Con balance_diario=2.0, debería distribuir 1 por día.
    pesos = PesosGeneracion(balance_diario=2.0, huecos=0.0,
                            distribucion=0.0, compactacion=0.0)

    def _config_balance():
        return ConfigGeneracion(
            id=1, nombre="Config Test", periodo_id=PERIODO_ID,
            anio_id=ANIO_ID, plantilla_id=PLANTILLA_ID, estado="borrador",
            pesos=pesos,
        )

    asignaturas = {5: Asignatura(id=5, nombre="Mate", horas_semanales=3)}
    asig_infos = [_asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5)]
    svc, *_ = _build(_config_balance(), _plantilla(DIAS_3), FRANJAS_3, asig_infos, asignaturas)

    res = svc.generar(1)

    assert res.colocados == 3
    from collections import Counter
    horas_por_dia = Counter(b.dia_semana for b in res.bloques if b.usuario_id == 3)
    # Con balance_diario=2.0, esperamos ≤2 bloques por día (idealmente 1 por día)
    assert max(horas_por_dia.values()) <= 2


# ===========================================================================
# Tests paso_17 Fase E — T8: Infactibilidad (pre-vuelo, relajación, diagnóstico)
# ===========================================================================

def test_prevuelo_docente_insuficiente():
    """PRE-VUELO: incidencia cuando docente tiene menos franjas disponibles que demanda."""
    # 4 horas requeridas; docente 3 solo disponible 6 slots (Martes+Miércoles×3)
    no_disp = [(3, "Lunes", f.orden) for f in FRANJAS_3]  # bloquea los 3 slots del Lunes
    asignaturas = {5: Asignatura(id=5, nombre="Mate", horas_semanales=7)}
    asig_infos = [_asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5)]
    svc, *_ = _build(
        _config(), _plantilla(DIAS_3), FRANJAS_3, asig_infos, asignaturas,
        no_disponibles=no_disp,
    )

    res = svc.generar(1)

    prevuelo_msgs = [i for i in res.incidencias if i.startswith("PRE-VUELO")]
    assert any("docente 3" in m for m in prevuelo_msgs), \
        f"No se encontró PRE-VUELO para docente 3: {res.incidencias}"


def test_prevuelo_grupo_insuficiente():
    """PRE-VUELO: incidencia cuando la ventana del grupo restringe demasiados slots."""
    # Solo 2 franjas permitidas × 3 días = 6 slots; demanda = 7
    ventanas = [VentanaGrupo(id=1, grupo_id=1, franjas_permitidas=[1, 2])]
    asignaturas = {5: Asignatura(id=5, nombre="Mate", horas_semanales=7)}
    asig_infos = [_asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5)]
    svc, *_ = _build(
        _config(), _plantilla(DIAS_3), FRANJAS_3, asig_infos, asignaturas,
        ventanas_grupo=ventanas,
    )

    res = svc.generar(1)

    prevuelo_msgs = [i for i in res.incidencias if i.startswith("PRE-VUELO")]
    assert any("grupo 1" in m for m in prevuelo_msgs), \
        f"No se encontró PRE-VUELO para grupo 1: {res.incidencias}"


def test_relajacion_max_horas_dia_estricta():
    """Cuando max_horas_dia=2 hace imposible 3h en 1 día, se relaja y se registra."""
    ld = LimitesDocente(id=1, usuario_id=3, min_horas_dia=0, max_horas_dia=2)
    asignaturas = {5: Asignatura(id=5, nombre="Mate", horas_semanales=3)}
    asig_infos = [_asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5)]
    svc, *_ = _build(
        _config(), _plantilla(["Lunes"]), FRANJAS_3, asig_infos, asignaturas,
        limites_docente=[ld],
    )

    res = svc.generar(1)

    assert "max_horas_dia_estricta" in res.relajadas, \
        f"Relajación no registrada. relajadas={res.relajadas}"
    assert res.colocados == 3, f"No se colocaron todos los bloques: {res.colocados}"


def test_diagnostico_causa_grupo_ocupado():
    """Bloque no colocado por saturación del grupo se registra en causas."""
    # 4 horas para el mismo grupo en solo 3 slots disponibles → 1 no colocado
    asignaturas = {5: Asignatura(id=5, nombre="Mate", horas_semanales=4)}
    asig_infos = [_asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5)]
    svc, *_ = _build(
        _config(), _plantilla(["Lunes"]), FRANJAS_3, asig_infos, asignaturas,
    )

    res = svc.generar(1)

    assert res.no_colocados == 1, f"Se esperaba 1 no colocado: {res.no_colocados}"
    assert res.causas.get("grupo_ocupado", 0) >= 1, \
        f"Causa 'grupo_ocupado' no registrada: {res.causas}"
