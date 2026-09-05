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
    Grupo,
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
        grupos: list | None = None,
    ):
        self._config = config
        self._plantilla = plantilla
        self._franjas = franjas
        self._asignaturas = asignaturas
        # set de (usuario_id, dia, franja_orden) NO disponibles
        self._no_disponibles = no_disponibles or set()
        self._grupos = grupos or []
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

    def listar_grupos(self, grado=None, institucion_id=None):
        return list(self._grupos)

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

    def listar_salas(self, institucion_id=None):
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

    Incorpora la regla de sala del oráculo real (SALAS_NO_EXCLUSIVAS +
    `salas_bloquean`, paso_17 T1) para que los tests que ejercitan esa
    relajación sean fidedignos frente a src.services.horario_service.
    """

    def __init__(self, asignacion_repo, usuario_service, asignaturas):
        self._asig = asignacion_repo
        self._usuario = usuario_service
        self._asignaturas = asignaturas
        self.aplicado = None

    def analizar_lote(self, escenario_id, periodo_id, filas, salas_bloquean=True):
        from src.domain.models.infraestructura import (
            FilaReporteDTO,
            ReporteLoteDTO,
        )
        from src.services.horario_service import SALAS_NO_EXCLUSIVAS

        vistos_grupo: set = set()
        vistos_docente: set = set()
        vistos_sala: set = set()
        conteo_doc: dict = {}
        resultado = []
        avisos: list[str] = []
        for i, fila in enumerate(filas):
            asig = self._asig.get_by_id(int(fila["asignacion_id"]))
            ok, motivo = True, None
            dia = fila["dia_semana"]
            hi = fila["hora_inicio"]
            sala = str(fila.get("sala") or "Aula")
            clave_g = (asig.grupo_id, dia, hi)
            clave_d = (asig.usuario_id, dia, hi)
            clave_s = (sala, dia, hi)

            if clave_g in vistos_grupo:
                ok, motivo = False, "Cruce: grupo ocupado."
            elif clave_d in vistos_docente:
                ok, motivo = False, "Cruce: docente ocupado."
            else:
                if sala not in SALAS_NO_EXCLUSIVAS and clave_s in vistos_sala:
                    if salas_bloquean:
                        ok, motivo = False, f"Cruce: sala '{sala}' ya ocupada."
                    else:
                        avisos.append(f"Fila {i}: sala '{sala}' ya ocupada (no bloquea).")
                if ok:
                    tope = self._usuario.carga_horaria_max(asig.usuario_id)
                    usado = conteo_doc.get(asig.usuario_id, 0)
                    if tope is not None and usado + 1 > tope:
                        ok, motivo = False, "Tope docente."
            if ok:
                vistos_grupo.add(clave_g)
                vistos_docente.add(clave_d)
                if sala not in SALAS_NO_EXCLUSIVAS:
                    vistos_sala.add(clave_s)
                conteo_doc[asig.usuario_id] = conteo_doc.get(asig.usuario_id, 0) + 1
            resultado.append(FilaReporteDTO(indice=i, ok=ok, motivo=motivo))
        return ReporteLoteDTO(filas=resultado, avisos=avisos)

    def aplicar_lote(
        self, escenario_id, periodo_id, filas, solo_validas=False, salas_bloquean=True
    ):
        from src.domain.models.infraestructura import (
            ResultadoLoteDTO,
        )
        reporte = self.analizar_lote(
            escenario_id, periodo_id, filas, salas_bloquean=salas_bloquean
        )
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
           franjas_reunion=None, grupos=None):
    infra = FakeInfraRepo(config, plantilla, franjas, asignaturas, no_disponibles, grupos)
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
    svc, infra, horario, _infraestructura = _build(
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


def test_resultado_parcial_no_es_valido_ni_se_persiste():
    """El oráculo no convierte un horario incompleto en un resultado activable."""
    asignaturas = {5: Asignatura(id=5, nombre="Mate", horas_semanales=3)}
    asig_infos = [_asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5)]
    svc, _infra, horario, _ = _build(
        _config(),
        _plantilla(["Lunes"]),
        [_franja(1, "07:00", "07:55")],
        asig_infos,
        asignaturas,
    )

    res = svc.generar(1)

    assert res.no_colocados == 2
    assert res.valido is False
    assert horario.aplicado is None
    assert any("Resultado parcial" in incidencia for incidencia in res.incidencias)


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
    f0, _f1, f2 = FRANJAS_3  # orden 1, 2, 3
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
    _franja(2, "08:00", "08:55")
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
    """config.restricciones min_max_diario max=1 modo estricta → max 1h/día/docente."""
    config = ConfigGeneracion(
        id=1, nombre="Config Test", periodo_id=PERIODO_ID,
        anio_id=ANIO_ID, plantilla_id=PLANTILLA_ID, estado="borrador",
        restricciones={"min_max_diario": {"max": 1, "modo": "estricta"}},
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
    f1, f2, _f3 = FRANJAS_3
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

    # T7: el mensaje usa el nombre del docente (AsignacionInfo.docente_nombre),
    # no el id crudo.
    prevuelo_msgs = [i for i in res.incidencias if i.startswith("PRE-VUELO")]
    assert any("Docente 3" in m for m in prevuelo_msgs), \
        f"No se encontró PRE-VUELO para Docente 3: {res.incidencias}"


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
    assert res.causas.get("grupo_saturado", 0) >= 1, \
        f"Causa 'grupo_saturado' no registrada: {res.causas}"


# ===========================================================================
# T9 — König como semilla + reparación por intercambio
#
# Regresión del fallo real: 12 grupos * 30h = 360h con la capacidad exacta,
# 3 celdas de indisponibilidad y topes diarios. El motor daba 333/360 con 27
# "docente_ocupado" pese a existir solución. Causa: una sola celda vetada
# desactivaba König y el backtracking agotaba el presupuesto, tras lo cual el
# voraz first-fit arrancaba desde una rejilla VACÍA.
# ===========================================================================

def test_coloreo_sobrevive_a_una_indisponibilidad():
    """Una celda vetada ya no tumba el coloreo: siembra y se repara.

    Los grupos estan saturados (4h en 4 slots), asi que no hay ningun hueco
    libre y la unica jugada posible es permutar. El docente 3 si tiene holgura
    (2 lecciones en 4 slots), que es lo que hace satisfacible el veto: si un
    docente tuviera grado igual al numero de slots ocupariara todos por
    definicion y ninguna indisponibilidad seria satisfacible.
    """
    asignaturas = {
        5: Asignatura(id=5, nombre="Mate", horas_semanales=2),
        6: Asignatura(id=6, nombre="Lengua", horas_semanales=2),
    }
    asig_infos = [
        _asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5),
        _asig_info(11, grupo_id=1, usuario_id=4, asignatura_id=6),
        _asig_info(12, grupo_id=2, usuario_id=5, asignatura_id=5),
        _asig_info(13, grupo_id=2, usuario_id=4, asignatura_id=6),
    ]
    franjas = [_franja(1, "07:00", "07:55"), _franja(2, "08:00", "08:55")]
    svc, infra, *_ = _build(
        _config(), _plantilla(["Lunes", "Martes"]), franjas, asig_infos, asignaturas,
        no_disponibles={(3, "Lunes", 1)},
    )

    res = svc.generar(1)

    assert res.no_colocados == 0, f"Horario incompleto: {res.incidencias}"
    assert res.metodo_usado == "konig", f"No se usó el coloreo: {res.metodo_usado}"
    for b in res.bloques:
        assert infra.es_disponible(b.usuario_id, b.dia_semana, b.franja_orden), (
            f"Bloque en franja vetada: docente {b.usuario_id} {b.dia_semana}/{b.franja_orden}"
        )


def test_limite_diario_no_desactiva_el_coloreo():
    """Con LimitesDocente el motor ya no cae al backtracking: König + reparación."""
    ld = LimitesDocente(id=1, usuario_id=3, min_horas_dia=0, max_horas_dia=2)
    asignaturas = {5: Asignatura(id=5, nombre="Mate", horas_semanales=3)}
    asig_infos = [_asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5)]
    svc, *_ = _build(
        _config(), _plantilla(DIAS_3), FRANJAS_3, asig_infos, asignaturas,
        limites_docente=[ld],
    )

    res = svc.generar(1)

    assert res.no_colocados == 0, f"Horario incompleto: {res.incidencias}"
    assert res.metodo_usado == "konig", f"No se usó el coloreo: {res.metodo_usado}"
    # 3h con tope de 2h/día: la reparación las reparte en días distintos.
    por_dia: dict[str, int] = {}
    for b in res.bloques:
        por_dia[b.dia_semana] = por_dia.get(b.dia_semana, 0) + 1
    assert max(por_dia.values()) <= 2, f"Tope diario violado: {por_dia}"


def test_reparacion_respeta_la_propiedad_del_coloreo():
    """`reparar_coloreo` nunca introduce un choque de grupo ni de docente."""
    from src.domain.models.scheduling import colorear_aristas_bipartito, reparar_coloreo

    # 3 grupos x 3 docentes en 4 colores: cada nodo tiene grado 3, luego a
    # todos les queda un color libre y los vetos son satisfacibles.
    aristas = [(g, d) for g in (1, 2, 3) for d in (10, 20, 30)]
    colores = colorear_aristas_bipartito(aristas, 4)
    assert all(c is not None for c in colores)

    reparado, viol = reparar_coloreo(
        aristas, colores, 4, [0, 0, 1, 1],
        vetos_duros=frozenset({(10, 0), (20, 1)}),
        semilla=3,
    )

    assert viol["indisponibilidad"] == 0, f"No resolvió los vetos: {viol}"
    vistos_g: set = set()
    vistos_d: set = set()
    for (g, d), color in zip(aristas, reparado, strict=True):
        assert (g, color) not in vistos_g, f"Choque de grupo en color {color}"
        assert (d, color) not in vistos_d, f"Choque de docente en color {color}"
        vistos_g.add((g, color))
        vistos_d.add((d, color))


def test_reparacion_nunca_empeora_la_entrada():
    """Sin movimiento posible que mejore, devuelve el estado inicial intacto."""
    from src.domain.models.scheduling import reparar_coloreo

    aristas = [(1, 10), (1, 20)]
    reparado, viol = reparar_coloreo(aristas, [0, 1], 2, [0, 0], max_intentos=500)

    assert reparado == [0, 1]
    assert viol == {
        "indisponibilidad": 0,
        "reunion": 0,
        "exceso_max_dia": 0,
        "deficit_min_dia": 0,
    }


def test_voraz_conserva_el_mejor_parcial_del_backtracking():
    """Con ventanas de grupo (König inactivo) no se pierde lo ya colocado.

    La ventana deja 2 franjas utiles para 3 horas: una queda fuera, pero las
    otras dos deben aparecer igual. Antes, al fallar el DFS, `colocados` se
    vaciaba y el voraz reconstruia desde cero.
    """
    ventanas = [VentanaGrupo(id=1, grupo_id=1, franjas_permitidas=[1, 2])]
    asignaturas = {5: Asignatura(id=5, nombre="Mate", horas_semanales=3)}
    asig_infos = [_asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5)]
    svc, *_ = _build(
        _config(), _plantilla(["Lunes"]), FRANJAS_3, asig_infos, asignaturas,
        ventanas_grupo=ventanas,
    )

    res = svc.generar(1)

    assert res.colocados == 2, f"Se perdieron colocaciones válidas: {res.colocados}"
    assert res.no_colocados == 1
    assert {b.franja_orden for b in res.bloques} == {1, 2}


# ===========================================================================
# horario_01_validacion_generacion — T17: regresión T1/T4/T5
# ===========================================================================

def test_sala_faltante_no_invalida_el_horario():
    """Caso E1 (T1): 3 grupos con materia 'laboratorio' y 1 sola sala real.

    Con un único slot disponible los 3 grupos comparten forzosamente el mismo
    (día, franja); solo uno consigue la sala real y los otros dos quedan con
    sala='Por asignar' en el mismo horario. Antes del fix, el oráculo trataba
    'Por asignar' como una sala exclusiva y marcaba un cruce falso entre esos
    dos, invalidando un horario perfectamente colocado.
    """
    salas = [Sala(id=1, nombre="Lab Química", tipo="laboratorio", capacidad=30)]
    asignaturas = {
        5: Asignatura(
            id=5, nombre="Lab", horas_semanales=1, tipo_sala_requerido="laboratorio"
        ),
    }
    asig_infos = [
        _asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5),
        _asig_info(11, grupo_id=2, usuario_id=4, asignatura_id=5),
        _asig_info(12, grupo_id=3, usuario_id=5, asignatura_id=5),
    ]
    plantilla_1slot = _plantilla(["Lunes"])
    franjas_1slot = [_franja(1, "07:00", "07:55")]
    svc, _infra, horario, _infraestructura = _build(
        _config(), plantilla_1slot, franjas_1slot, asig_infos, asignaturas,
        salas=salas,
    )

    res = svc.generar(1)

    assert res.no_colocados == 0, f"No todos colocados: {res.incidencias}"
    assert res.valido is True, f"Debe ser válido pese a la sala faltante: {res.incidencias}"
    assert res.causas.get("sala_pendiente", 0) == 2, res.causas
    assert horario.aplicado is not None, "El lote debe persistirse cuando valido=True"


def test_sin_asignaciones_no_crea_escenario():
    """Caso E2 (T4/T5): sin asignaciones activas no se crea escenario ni se
    transiciona la config; el resultado trae una incidencia explícita."""
    svc, infra, horario, infraestructura = _build(
        _config(), _plantilla(DIAS_3), FRANJAS_3, [], {},
    )

    res = svc.generar(1)

    assert res.escenario_id is None
    assert res.valido is False
    assert res.incidencias, "Debe explicar por qué no hay nada que generar."
    assert any("No hay asignaciones activas" in inc for inc in res.incidencias)
    assert infra.estado_cambiado is None, "No debe transicionar la config sin bloques."
    assert infra.config_actualizada is None, "No debe tocar la config sin bloques."
    assert infraestructura.creados == [], "No debe crear ningún escenario sin bloques."
    assert horario.aplicado is None


def test_resultado_invalido_siempre_tiene_incidencias():
    """Invariante de T4: not resultado.valido ⇒ len(resultado.incidencias) > 0."""
    # Caso 1: sin asignaciones en absoluto.
    svc1, *_ = _build(_config(), _plantilla(DIAS_3), FRANJAS_3, [], {})
    res1 = svc1.generar(1)
    assert res1.valido is False
    assert len(res1.incidencias) > 0

    # Caso 2: slots insuficientes → resultado parcial, inválido.
    asignaturas = {5: Asignatura(id=5, nombre="Mate", horas_semanales=3)}
    asig_infos = [_asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5)]
    svc2, *_ = _build(
        _config(), _plantilla(["Lunes"]), [_franja(1, "07:00", "07:55")],
        asig_infos, asignaturas,
    )
    res2 = svc2.generar(1)
    assert res2.valido is False
    assert len(res2.incidencias) > 0

    # Caso 3: grupos filtrados que no tienen ninguna asignación activa.
    svc3, *_ = _build(_config(grupos=[99]), _plantilla(DIAS_3), FRANJAS_3, [], {})
    res3 = svc3.generar(1)
    assert res3.valido is False
    assert len(res3.incidencias) > 0
    assert any("seleccionados no tienen asignaciones activas" in i for i in res3.incidencias)


# ===========================================================================
# horario_01_validacion_generacion — T2: aula base ocupada no se reasigna
# ===========================================================================

def test_sala_base_no_se_reasigna_a_laboratorio():
    """`_elegir_sala` ya no elige una sala que es el aula base ocupada de otro
    grupo, aunque esa sala esté tipificada como el tipo requerido (caso real:
    un salón multiuso que a la vez es el homeroom de un grupo).

    Con un único slot en la plantilla, el grupo 1 (clase normal, sin tipo de
    sala) y el grupo 2 (laboratorio) quedan forzados al mismo (día, franja).
    La única sala del sistema es a la vez tipo 'laboratorio' Y el aula base
    del grupo 1: antes del fix, `ocupado_sala` no sabía que esa sala estaba
    ocupada por el grupo 1 y se la asignaba igual al laboratorio del grupo 2.
    """
    salas = [Sala(id=1, nombre="Aula Multiuso", tipo="laboratorio", capacidad=30)]
    grupos = [
        Grupo(id=1, codigo="G1", sala_id=1),  # aula base = la única sala real
        Grupo(id=2, codigo="G2"),
    ]
    asignaturas = {
        5: Asignatura(id=5, nombre="Sociales", horas_semanales=1),  # sin tipo_sala_req
        6: Asignatura(
            id=6, nombre="Lab Física", horas_semanales=1, tipo_sala_requerido="laboratorio"
        ),
    }
    asig_infos = [
        _asig_info(10, grupo_id=1, usuario_id=3, asignatura_id=5),
        _asig_info(11, grupo_id=2, usuario_id=4, asignatura_id=6),
    ]
    plantilla_1slot = _plantilla(["Lunes"])
    franjas_1slot = [_franja(1, "07:00", "07:55")]
    svc, *_ = _build(
        _config(), plantilla_1slot, franjas_1slot, asig_infos, asignaturas,
        salas=salas, grupos=grupos,
    )

    res = svc.generar(1)

    assert res.no_colocados == 0, res.incidencias
    bloque_g1 = next(b for b in res.bloques if b.grupo_id == 1)
    bloque_lab = next(b for b in res.bloques if b.grupo_id == 2)
    # El grupo 1 usa su aula propia (contabilidad normal, sin cambios).
    assert bloque_g1.sala == "Aula Multiuso"
    # El laboratorio NO puede reutilizar esa misma sala en el mismo slot: al
    # ser la única sala del tipo requerido y estar ocupada como aula base,
    # queda "Por asignar" en vez de robarle el salón al grupo 1.
    assert bloque_lab.sala_id is None, (
        f"El laboratorio reutilizó el aula base ocupada del grupo 1: "
        f"sala_id={bloque_lab.sala_id}"
    )
    assert bloque_lab.sala == "Por asignar"
    assert res.causas.get("sala_pendiente", 0) == 1


def test_ocupacion_de_sala_es_un_conteo_no_un_set():
    """Regresión: `ocupado_sala` debe contar, no marcar presencia.

    Escenario: la única sala del sistema está tipificada como 'laboratorio' Y es
    a la vez el aula base del grupo 1. El laboratorio del grupo 2 la toma en
    (Lunes, franja 1); después una clase normal del grupo 1 se coloca en ese
    mismo slot y marca la misma clave. Cuando el backtracking retira esa clase
    normal, un `set` borraba la marca entera y la sala quedaba «libre» pese a
    que el laboratorio del grupo 2 seguía dentro: el siguiente laboratorio la
    elegía y se persistían dos clases en la misma habitación a la misma hora.

    La ventana de grupo (permisiva, no restringe nada) desactiva el camino de
    König para forzar el backtracking, que es donde vive el `_quitar` que
    destapa el defecto.
    """
    salas = [Sala(id=1, nombre="Aula Multiuso", tipo="laboratorio", capacidad=30)]
    grupos = [
        Grupo(id=1, codigo="G1", sala_id=1),  # aula base = la única sala real
        Grupo(id=2, codigo="G2"),
    ]
    asignaturas = {
        5: Asignatura(
            id=5, nombre="Lab Física", horas_semanales=1, tipo_sala_requerido="laboratorio"
        ),
        6: Asignatura(id=6, nombre="Sociales", horas_semanales=1),  # sin tipo de sala
        7: Asignatura(
            id=7, nombre="Lab Química", horas_semanales=1, tipo_sala_requerido="laboratorio"
        ),
    }
    asig_infos = [
        _asig_info(10, grupo_id=2, usuario_id=4, asignatura_id=5),  # lab que toma la sala
        _asig_info(11, grupo_id=1, usuario_id=3, asignatura_id=6),  # clase normal en su aula
        _asig_info(12, grupo_id=1, usuario_id=6, asignatura_id=7),  # lab que la reclama
    ]
    # El docente 6 tiene reunión estricta en la franja 2: su laboratorio solo
    # cabe en la franja 1, así que la clase normal del grupo 1 tiene que
    # retroceder de la franja 1 a la 2 (ahí ocurre el `_quitar` crítico).
    reunion = FranjaReunion(
        id=1, nombre="Reunión de área", docentes=[6],
        dia_semana="Lunes", franja_orden=2, modo="estricta",
    )
    # Ventana permisiva: no recorta ningún slot, solo desactiva König.
    ventana = VentanaGrupo(id=1, grupo_id=2, franjas_permitidas=[1, 2])
    plantilla = _plantilla(["Lunes"])
    franjas = [_franja(1, "07:00", "07:55"), _franja(2, "08:00", "08:55")]

    svc, *_ = _build(
        _config(), plantilla, franjas, asig_infos, asignaturas,
        salas=salas, grupos=grupos, franjas_reunion=[reunion],
        ventanas_grupo=[ventana],
    )

    res = svc.generar(1)

    assert res.no_colocados == 0, res.incidencias
    reservas = [
        (b.sala_id, b.dia_semana, b.franja_orden) for b in res.bloques if b.sala_id
    ]
    assert len(reservas) == len(set(reservas)), (
        f"Una sala quedó reservada dos veces en el mismo slot: {reservas}"
    )
    # El segundo laboratorio no roba la sala ocupada: queda pendiente de asignar.
    assert res.causas.get("sala_pendiente", 0) == 1, res.causas
