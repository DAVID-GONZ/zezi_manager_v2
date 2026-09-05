"""
GeneradorHorarioService (paso_17 Fase C)
=========================================
Motor de generación de horarios con restricciones configurables.

Extiende v1 (paso_15c) + v2 (paso_15d) con:

  T5 — Salas reales + bloques dobles/consecutivos
    - ocupado_sala: Counter[(sala_id, dia, orden)] — evita conflictos de sala.
    - Asignatura.tipo_sala_requerido: elige una sala libre del tipo correcto.
    - Asignatura.bloque_doble / horas_consecutivas: macro-lección contigua.
    - König deshabilitado cuando hay restricción de sala, bloque doble,
      ventanas de grupo, franjas de reunión o límites diarios estrictos.

  T6 — Ventanas de grupo + híbridas estrictas
    - VentanaGrupo.franjas_permitidas (por grupo_id): filtra slots factibles.
    - FranjaReunion.modo="estricta": bloquea la franja para los docentes.
    - LimitesDocente + config.restricciones["min_max_diario"]:
        max_horas_dia se aplica como restricción dura (estricta).
        min_horas_dia se verifica post-colocación y genera incidencia.

El default sin configurar = comportamiento idéntico al motor anterior (R16).
Lógica pura: sin NiceGUI, sin src.db, sin instanciación de repos.
"""

from __future__ import annotations

import logging
from collections import Counter

from src.domain.models.asignacion import FiltroAsignacionesDTO
from src.domain.models.infraestructura import (
    BloqueGeneradoDTO,
    MetricasCalidadDTO,
    ResultadoGeneracionDTO,
)

logger = logging.getLogger("GENERADOR_HORARIO")

# ---------------------------------------------------------------------------
# Catálogo de pesos del motor (parámetros del optimizador).
# Cada entrada es (clave, etiqueta, descripción). La capa de interfaz los
# consume para construir los sliders de la configuración; viven aquí porque
# son parámetros del motor de generación, no de la vista.
# ---------------------------------------------------------------------------
PESOS_PRINCIPALES: list[tuple[str, str, str]] = [
    (
        "huecos",
        "Evitar huecos",
        "Reduce las horas libres entre clases de un grupo o docente. Mayor = horarios más compactos, sin ventanas.",
    ),
    (
        "distribucion",
        "Repartir en la semana",
        "Separa las clases de una misma materia en días distintos. Mayor = menos materias repetidas el mismo día.",
    ),
    (
        "compactacion",
        "Compactar al docente",
        "Concentra las clases del docente en menos jornadas. Mayor = el docente viene menos días o en bloques.",
    ),
]

CAUSA_INFO: dict[str, tuple[str, str | None]] = {
    "sin_slots": ("Sin franjas disponibles", "/academico/generar-horario?tab=plantillas"),
    "docente_ocupado": ("Docente ya ocupado en otra clase", None),
    "sin_disponibilidad": (
        "Docente marcado no disponible en ese horario",
        "/admin/disponibilidad-docente",
    ),
    "tope_carga": ("Carga horaria máxima del docente superada", "/admin/asignaciones"),
    "max_dia": ("Tope de horas diarias del docente", None),
    "grupo_saturado": (
        "Grupo sin franjas libres para esta clase",
        "/academico/generar-horario?tab=plantillas",
    ),
    "sala_pendiente": ("Sala pendiente de asignar", "/admin/salas"),
    "min_dia_docente": ("Por debajo del mínimo de horas diarias", None),
    # Causas adicionales que _diagnosticar_no_colocado también puede reportar.
    "grupo_ocupado_parcial": ("Grupo ya ocupado en esa franja", None),
    "reunion_bloqueada": ("Franja de reunión bloqueada para el docente", None),
    "sin_consecutividad": (
        "Sin franjas consecutivas suficientes",
        "/academico/generar-horario?tab=plantillas",
    ),
    "desconocido": ("Motivo no determinado", None),
}

PESOS_AVANZADOS: list[tuple[str, str, str]] = [
    (
        "balance_diario",
        "Equilibrar horas por día",
        "Iguala cuántas horas dicta el docente cada día. Mayor = días más parejos, sin uno cargado y otro vacío.",
    ),
    (
        "franja_preferida",
        "Respetar franja preferida",
        "Ubica las materias en su franja preferida (mañana/tarde). Mayor = más respeto a esa preferencia.",
    ),
    (
        "dia_libre",
        "Dar un día libre",
        "Intenta dejar al docente un día completo sin clases. Mayor = más prioridad a lograr ese día libre.",
    ),
    (
        "hueco_comun",
        "Proteger franja de reunión",
        "Evita programar clases en la franja de reunión configurada. Mayor = más respeto a ese espacio común.",
    ),
]


class _Leccion:
    """Una unidad de bloque a colocar de una asignación (una hora o macro-bloque)."""

    __slots__ = (
        "asignacion_id",
        "docente_nombre",
        "etiqueta",
        "grupo_id",
        "n_horas",
        "tipo_sala_req",
        "usuario_id",
    )

    def __init__(
        self,
        asignacion_id,
        grupo_id,
        usuario_id,
        etiqueta,
        tipo_sala_req=None,
        n_horas=1,
        docente_nombre=None,
    ):
        """Inicializa la unidad de bloque con su asignación, grupo, docente,
        etiqueta, tipo de sala requerido y número de horas consecutivas.

        `docente_nombre` (T7): nombre legible del docente, para construir
        incidencias sin exponer ids crudos. None = no disponible (tests
        antiguos que no lo pasan); se hace fallback al usuario_id.
        """
        self.asignacion_id = asignacion_id
        self.grupo_id = grupo_id
        self.usuario_id = usuario_id
        self.etiqueta = etiqueta
        self.tipo_sala_req = tipo_sala_req  # str | None
        self.n_horas = n_horas  # int >= 1
        self.docente_nombre = docente_nombre  # str | None


class GeneradorHorarioService:
    def __init__(
        self,
        infra_repo,
        asignacion_repo,
        usuario_repo,
        horario_service,
        infraestructura_service,
        plan_svc=None,
    ):
        """Inyecta los repos de infraestructura, asignación y usuario, los
        servicios de horario e infraestructura, y el plan de estudios (opcional)."""
        self._infra = infra_repo
        self._asig = asignacion_repo
        self._usuario = usuario_repo
        self._horario = horario_service
        self._infraestructura = infraestructura_service
        self._plan = plan_svc

    # ------------------------------------------------------------------ #
    # Catálogo de pesos + generabilidad (capa de interfaz delega aquí)   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def catalogo_pesos() -> dict[str, list[tuple[str, str, str]]]:
        """Devuelve el catálogo de pesos del motor para construir la UI.

        Estructura: {"principales": [...], "avanzados": [...]} donde cada
        entrada es (clave, etiqueta, descripción). La vista NO debe mantener
        estas tuplas: son parámetros del optimizador.
        """
        return {
            "principales": list(PESOS_PRINCIPALES),
            "avanzados": list(PESOS_AVANZADOS),
        }

    def plantilla_generable(self, plantilla_id: int | None) -> tuple[bool, str]:
        """¿Se puede generar un horario con esta plantilla?

        Inspecciona la plantilla (días activos) y sus franjas (al menos una
        lectiva) y devuelve (ok, motivo). Si ok=True, motivo="". Centraliza la
        lógica de dominio que antes vivía en la vista.
        """
        if plantilla_id is None:
            return False, "La configuración no tiene plantilla asignada."
        plantilla = self._infra.get_plantilla_franja(plantilla_id)
        if plantilla is None:
            return False, "La plantilla de la configuración ya no existe."
        if not getattr(plantilla, "dias_activos", None):
            return False, "La plantilla no tiene días activos."
        franjas = self._infra.listar_franjas(plantilla_id)
        if not any(f.es_lectiva for f in franjas):
            return False, "La plantilla no tiene franjas lectivas."
        return True, ""

    # ------------------------------------------------------------------ #
    # Coste blando (paso_15d) — sin cambios en T5/T6; T7 lo amplía       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _costo(colocados, pesos, orden_a_idx, *, n_dias_total: int = 0):
        """
        Calcula el coste blando ponderado de una solución.

        `colocados` es list[(_Leccion, dia, franja)]. `orden_a_idx` mapea
        el `orden` crudo de cada franja lectiva a un índice compacto 0..L-1.

        `n_dias_total`: nº de días activos de la plantilla; necesario para
        calcular `dia_libre`. Si 0, ese término no se activa.

        Para macro-lecciones (n_horas > 1) solo se registra la franja
        de inicio; el error de cómputo es mínimo y no afecta hill-climbing
        (que omite esas lecciones vía skip_lec_fn).

        Términos (paso_17 T7):
          balance_diario  — varianza de horas/día por docente
          dia_libre       — penaliza docentes sin ningún día libre
          franja_preferida, hueco_comun — stubs (implementados en T8+)
        """
        idx_grupo: dict[tuple, list[int]] = {}
        idx_docente: dict[tuple, list[int]] = {}
        conteo_asig: dict[tuple, int] = {}
        dias_por_docente: dict[int, set] = {}

        for lec, dia, franja in colocados:
            idx = orden_a_idx[franja.orden]
            idx_grupo.setdefault((lec.grupo_id, dia), []).append(idx)
            idx_docente.setdefault((lec.usuario_id, dia), []).append(idx)
            conteo_asig[(lec.asignacion_id, dia)] = conteo_asig.get((lec.asignacion_id, dia), 0) + 1
            dias_por_docente.setdefault(lec.usuario_id, set()).add(dia)

        def _huecos(idx_map):
            total = 0
            for indices in idx_map.values():
                if not indices:
                    continue
                hueco = (max(indices) - min(indices) + 1) - len(indices)
                if hueco > 0:
                    total += hueco
            return total

        huecos_grupo = _huecos(idx_grupo)
        huecos_docente = _huecos(idx_docente)
        solapes_distribucion = sum(max(0, c - 1) for c in conteo_asig.values())
        dias_docente = sum(len(d) for d in dias_por_docente.values())

        # T7: balance_diario — penaliza la concentración de horas en pocos días.
        # Métrica: suma de (count_dia)^2 por docente. Para un total fijo de bloques,
        # este valor se minimiza cuando los bloques se distribuyen equitativamente
        # entre días y se maximiza cuando todos caen en un único día.
        # Funciona correctamente incluso cuando hay un solo día con datos.
        balance_diario_cost = 0.0
        peso_bd = getattr(pesos, "balance_diario", 0.0)
        if peso_bd > 0.0:
            doc_counts: dict[int, list[int]] = {}
            for (uid, _dia), indices in idx_docente.items():
                doc_counts.setdefault(uid, []).append(len(indices))
            for counts in doc_counts.values():
                balance_diario_cost += sum(c * c for c in counts)

        # T7: dia_libre — penaliza docentes que trabajan todos los días (sin día libre).
        # Requiere n_dias_total para detectar "todos los días ocupados".
        dia_libre_cost = 0.0
        peso_dl = getattr(pesos, "dia_libre", 0.0)
        if peso_dl > 0.0 and n_dias_total > 0:
            dia_libre_cost = sum(
                1 for dias_set in dias_por_docente.values() if len(dias_set) >= n_dias_total
            )

        # T7 stubs: franja_preferida y hueco_comun se implementan con datos
        # de ConfigGeneracion.restricciones y FranjaReunion (paso_17 T8+).
        franja_preferida_cost = 0.0
        hueco_comun_cost = 0.0

        costo_total = (
            pesos.huecos * (huecos_grupo + huecos_docente)
            + pesos.distribucion * solapes_distribucion
            + pesos.compactacion * dias_docente
            + peso_bd * balance_diario_cost
            + peso_dl * dia_libre_cost
            + getattr(pesos, "franja_preferida", 0.0) * franja_preferida_cost
            + getattr(pesos, "hueco_comun", 0.0) * hueco_comun_cost
        )

        metricas = MetricasCalidadDTO(
            huecos_grupo=huecos_grupo,
            huecos_docente=huecos_docente,
            solapes_distribucion=solapes_distribucion,
            dias_docente=dias_docente,
        )
        return costo_total, metricas

    # ------------------------------------------------------------------ #
    # Mejora local (paso_15d) — extendida en T5/T6 con params opcionales  #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _mejorar_local(
        colocados,
        slots,
        ocupado_grupo,
        ocupado_docente,
        pesos,
        orden_a_idx,
        es_disponible_fn,
        max_pasos=5000,
        skip_lec_fn=None,
        slots_para_lec_fn=None,
        extra_check_fn=None,
        horas_dia_docente=None,
        n_dias_total: int = 0,
    ) -> int:
        """
        Hill-climbing best-improvement sobre coste blando.

        Parámetros opcionales (default None/0 = sin efecto):
          skip_lec_fn:       fn(lec)->bool; True → omite la lección
          slots_para_lec_fn: fn(lec)->list; slots filtrados por ventana
          extra_check_fn:    fn(lec,dia,franja,dia_actual)->bool; checks extra
          horas_dia_docente: dict[(uid,dia),int] mutable; tracking diario
          n_dias_total:      días activos de la plantilla (para dia_libre T7)
        """
        pasos = 0

        def _costo_actual():
            return GeneradorHorarioService._costo(
                colocados, pesos, orden_a_idx, n_dias_total=n_dias_total
            )[0]

        mejoró_alguna_pasada = True
        while mejoró_alguna_pasada and pasos < max_pasos:
            mejoró_alguna_pasada = False
            for i in range(len(colocados)):
                if pasos >= max_pasos:
                    break
                lec, dia_act, franja_act = colocados[i]
                if skip_lec_fn and skip_lec_fn(lec):
                    continue
                costo_base = _costo_actual()
                mejor_delta = 0.0
                mejor_slot = None

                clave_g_act = (lec.grupo_id, dia_act, franja_act.orden)
                clave_d_act = (lec.usuario_id, dia_act, franja_act.orden)

                candidate_slots = slots_para_lec_fn(lec) if slots_para_lec_fn else slots

                for dia2, franja2 in candidate_slots:
                    if dia2 == dia_act and franja2.orden == franja_act.orden:
                        continue
                    clave_g2 = (lec.grupo_id, dia2, franja2.orden)
                    clave_d2 = (lec.usuario_id, dia2, franja2.orden)
                    if clave_g2 in ocupado_grupo:
                        continue
                    if clave_d2 in ocupado_docente:
                        continue
                    if not es_disponible_fn(lec.usuario_id, dia2, franja2.orden):
                        continue
                    if extra_check_fn and not extra_check_fn(lec, dia2, franja2, dia_act):
                        continue

                    colocados[i] = (lec, dia2, franja2)
                    nuevo_costo = _costo_actual()
                    delta = nuevo_costo - costo_base
                    colocados[i] = (lec, dia_act, franja_act)

                    if delta < mejor_delta:
                        mejor_delta = delta
                        mejor_slot = (dia2, franja2)

                if mejor_slot is not None:
                    dia2, franja2 = mejor_slot
                    ocupado_grupo.discard(clave_g_act)
                    ocupado_docente.discard(clave_d_act)
                    ocupado_grupo.add((lec.grupo_id, dia2, franja2.orden))
                    ocupado_docente.add((lec.usuario_id, dia2, franja2.orden))
                    if horas_dia_docente is not None:
                        k_act = (lec.usuario_id, dia_act)
                        k_new = (lec.usuario_id, dia2)
                        horas_dia_docente[k_act] = max(0, horas_dia_docente.get(k_act, 0) - 1)
                        horas_dia_docente[k_new] = horas_dia_docente.get(k_new, 0) + 1
                    colocados[i] = (lec, dia2, franja2)
                    pasos += 1
                    mejoró_alguna_pasada = True

        return pasos

    # ------------------------------------------------------------------ #
    # API pública                                                          #
    # ------------------------------------------------------------------ #

    def generar(
        self,
        config_id: int,
        *,
        crear_escenario: bool = True,
        max_iteraciones: int = 200_000,
        optimizar: bool = True,
    ) -> ResultadoGeneracionDTO:
        """Genera un horario para una config: carga asignaciones y restricciones,
        coloca las lecciones por coloreo o backtracking, aplica mejora local,
        valida el lote contra el oráculo y lo persiste en el escenario destino.

        Devuelve un ResultadoGeneracionDTO con bloques, métricas e incidencias.
        """
        config = self._infra.get_config_generacion(config_id)
        if config is None:
            raise ValueError(f"Config de generación {config_id} no existe.")

        # --- Resolver plantilla y slots lectivos -----------------------
        plantilla = self._infra.get_plantilla_franja(config.plantilla_id)
        if plantilla is None:
            return ResultadoGeneracionDTO(
                total_requeridos=0,
                incidencias=[f"La plantilla {config.plantilla_id} no existe."],
            )

        franjas = [f for f in self._infra.listar_franjas(config.plantilla_id) if f.es_lectiva]
        franjas.sort(key=lambda f: f.orden)
        orden_a_idx = {f.orden: idx for idx, f in enumerate(franjas)}
        dias = list(plantilla.dias_activos)
        slots = [(dia, franja) for dia in dias for franja in franjas]

        if not slots:
            return ResultadoGeneracionDTO(
                total_requeridos=0,
                incidencias=["La plantilla no tiene franjas lectivas en días activos."],
            )

        # --- Estructura para bloques consecutivos (T5) ----------------
        ordenes_lectivas = [f.orden for f in franjas]
        franja_by_orden = {f.orden: f for f in franjas}
        orden_siguiente: dict[int, int | None] = {}
        for i, o in enumerate(ordenes_lectivas):
            orden_siguiente[o] = ordenes_lectivas[i + 1] if i + 1 < len(ordenes_lectivas) else None

        def _ordenes_n(orden_start: int, n: int) -> list[int] | None:
            """Lista de n órdenes lectivos consecutivos desde orden_start, o None."""
            result = [orden_start]
            cur = orden_start
            for _ in range(n - 1):
                nxt = orden_siguiente.get(cur)
                if nxt is None:
                    return None
                result.append(nxt)
                cur = nxt
            return result

        _slots_n_cache: dict[int, list] = {}

        def _slots_para_n(n: int) -> list:
            if n in _slots_n_cache:
                return _slots_n_cache[n]
            if n == 1:
                _slots_n_cache[1] = slots
                return slots
            result = []
            for dia in dias:
                for f in franjas:
                    if _ordenes_n(f.orden, n) is not None:
                        result.append((dia, f))
            _slots_n_cache[n] = result
            return result

        # --- Disponibilidad del docente en memoria (T9) ---------------
        # `es_disponible` del repo consulta SQLite en CADA llamada, y se invoca
        # dentro del bucle caliente del backtracking: eran cientos de miles de
        # round-trips por corrida. Memoizar por (docente, día, orden) deja el
        # coste en n_docentes * n_slots consultas como mucho.
        _disp_cache: dict[tuple, bool] = {}
        _disp_precargados: set[int] = set()
        _disp_huerfanas = [0]
        _listar_disp = getattr(self._infra, "listar_disponibilidad_docente", None)

        def _precargar_disp(usuario_id: int) -> bool:
            """Trae en UNA consulta todos los vetos del docente.

            Cada `es_disponible` del repo abre su propia conexión (~2 ms), así
            que resolver los 30 slots de un docente uno a uno costaba más que
            todo el resto del motor junto. Devuelve False si el repo no ofrece
            la consulta en lote (fakes de test), para caer al camino de siempre.
            """
            if not callable(_listar_disp):
                return False
            if usuario_id in _disp_precargados:
                return True
            vetos: set[tuple[str, int]] = set()
            for fila in _listar_disp(usuario_id) or []:
                if getattr(fila, "disponible", True):
                    continue
                vetos.add((fila.dia_semana, fila.franja_orden))
                # Un veto sobre un día o una franja que no existen en la
                # plantilla no restringe nada; hasta ahora se ignoraba en
                # silencio y parecía aplicado.
                if fila.dia_semana not in dias or fila.franja_orden not in franja_by_orden:
                    _disp_huerfanas[0] += 1
            for dia_p, franja_p in slots:
                _disp_cache[(usuario_id, dia_p, franja_p.orden)] = (
                    dia_p,
                    franja_p.orden,
                ) not in vetos
            _disp_precargados.add(usuario_id)
            return True

        def _es_disponible(usuario_id: int, dia: str, orden: int) -> bool:
            clave = (usuario_id, dia, orden)
            valor = _disp_cache.get(clave)
            if valor is None:
                if _precargar_disp(usuario_id):
                    valor = _disp_cache.get(clave)
                if valor is None:
                    valor = bool(self._infra.es_disponible(usuario_id, dia, orden))
                    _disp_cache[clave] = valor
            return valor

        _asignatura_cache: dict[int, object] = {}

        def _get_asignatura(asignatura_id: int):
            """Memoiza el catálogo: ~140 asignaciones comparten ~20 asignaturas."""
            if asignatura_id not in _asignatura_cache:
                _asignatura_cache[asignatura_id] = self._infra.get_asignatura(asignatura_id)
            return _asignatura_cache[asignatura_id]

        # --- Cargar restricciones T5/T6 via infraestructura_service ---

        # Salas (T5)
        todas_salas = self._infraestructura.listar_salas()
        salas_por_tipo: dict[str, list[int]] = {}
        sala_nombre_map: dict[int, str] = {}
        for sala in todas_salas:
            salas_por_tipo.setdefault(sala.tipo, []).append(sala.id)
            sala_nombre_map[sala.id] = sala.nombre
        hay_salas = bool(todas_salas)

        # Aula propia (salón base) por grupo + grado de cada grupo (para las
        # horas del plan de estudios). Multi-tenant (paso_32, T5): `self._infra`
        # es el repo (sin scope); `self._infraestructura.listar_salas()` ya viene
        # acotado por institución, así que se acotan los grupos al mismo tenant
        # para que `sala_id` resuelva contra el mismo conjunto de salas.
        from src.services.contexto_tenant import institucion_actual

        sala_grupo_nombre: dict[int, str] = {}
        # T2 (horario_01): aula base por grupo, para que `ocupado_sala` la
        # contabilice como ocupada aunque la lección no requiera tipo de sala
        # (evita que el generador reasigne esa aula a un laboratorio de otro
        # grupo que sí está en clase a esa hora).
        sala_base_de_grupo: dict[int, int] = {}
        grado_de_grupo: dict[int, int | None] = {}
        # T7: nombres legibles para las incidencias (PRE-VUELO usa ids crudos
        # de grupo/docente porque están fuera del bucle por asignación).
        grupo_codigo_map: dict[int, str] = {}
        for g in self._infra.listar_grupos(institucion_id=institucion_actual() or "*"):
            grado_de_grupo[g.id] = g.grado
            grupo_codigo_map[g.id] = g.codigo
            sid_g = getattr(g, "sala_id", None)
            if sid_g and sid_g in sala_nombre_map:
                sala_grupo_nombre[g.id] = sala_nombre_map[sid_g]
                sala_base_de_grupo[g.id] = sid_g

        def _horas_de(grupo_id: int, asignatura_id: int, asignatura) -> int:
            """Horas semanales de la (grupo, asignatura): plan del grado del grupo
            con fallback a las horas globales de la asignatura."""
            grado = grado_de_grupo.get(grupo_id)
            if self._plan is not None and grado is not None:
                return self._plan.horas_de(grado, asignatura_id)
            return getattr(asignatura, "horas_semanales", None) or 1

        # Ventanas de grupo (T6) — solo por grupo_id; ventanas por grado diferidas
        ventanas_raw = self._infraestructura.listar_ventanas_grupo()
        franjas_perm_grupo: dict[int, set[int]] = {}
        for v in ventanas_raw:
            if v.grupo_id is not None:
                franjas_perm_grupo[v.grupo_id] = set(v.franjas_permitidas)

        # FranjaReunion estrictas (T6)
        franjas_reunion_raw = self._infraestructura.listar_franjas_reunion()
        bloqueadas_reunion: set[tuple] = set()
        for fr in franjas_reunion_raw:
            if fr.modo == "estricta":
                for uid in fr.docentes:
                    bloqueadas_reunion.add((uid, fr.dia_semana, fr.franja_orden))

        # Límites docente (T6)
        limites_raw = self._infraestructura.listar_limites_docente()
        limites_por_docente: dict[int, tuple[int, int]] = {}
        for ld in limites_raw:
            limites_por_docente[ld.usuario_id] = (ld.min_horas_dia, ld.max_horas_dia)

        # Config restricciones min_max_diario
        config_minmax = (config.restricciones or {}).get("min_max_diario", {})
        config_max_dia_global: int | None = config_minmax.get("max")
        config_min_dia_global: int | None = config_minmax.get("min")
        config_modo_minmax: str = config_minmax.get("modo", "preferente")
        aplicar_max_dia_estricto: bool = bool(limites_por_docente) or (
            config_modo_minmax == "estricta" and config_max_dia_global is not None
        )

        def _max_horas_dia(usuario_id: int) -> int | None:
            if usuario_id in limites_por_docente:
                return limites_por_docente[usuario_id][1]
            return config_max_dia_global if config_modo_minmax == "estricta" else None

        def _min_horas_dia(usuario_id: int) -> int | None:
            if usuario_id in limites_por_docente:
                return limites_por_docente[usuario_id][0]
            return config_min_dia_global

        # --- Cargar asignaciones --------------------------------------
        asignaciones = []
        _pagina = 1
        _por_pagina = 500
        while True:
            _lote = self._asig.listar_info(
                FiltroAsignacionesDTO(
                    periodo_id=config.periodo_id,
                    solo_activas=True,
                    pagina=_pagina,
                    por_pagina=_por_pagina,
                )
            )
            asignaciones.extend(_lote)
            if len(_lote) < _por_pagina:
                break
            _pagina += 1
        if config.grupos:
            grupos_filtro = set(config.grupos)
            asignaciones = [a for a in asignaciones if a.grupo_id in grupos_filtro]

        # --- Construir lecciones por asignación -----------------------
        slots_disp_docente: dict[int, int] = {}

        def _slots_disponibles_docente(usuario_id: int) -> int:
            if usuario_id not in slots_disp_docente:
                n = sum(
                    1 for (dia, franja) in slots if _es_disponible(usuario_id, dia, franja.orden)
                )
                slots_disp_docente[usuario_id] = n
            return slots_disp_docente[usuario_id]

        carga_max_cache: dict[int, int | None] = {}

        def _carga_max(usuario_id: int) -> int | None:
            if usuario_id not in carga_max_cache:
                carga_max_cache[usuario_id] = self._usuario.carga_horaria_max(usuario_id)
            return carga_max_cache[usuario_id]

        grupos_asig = []
        total_requeridos = 0
        incidencias: list[str] = []
        causas: dict[str, int] = {}

        demanda_grupo: dict[int, int] = {}
        demanda_docente: dict[int, int] = {}
        docentes_involucrados: set[int] = set()
        docente_nombre_map: dict[int, str] = {}  # T7: para incidencias PRE-VUELO
        hay_bloque_doble = False

        # T4 — incidencia explícita cuando no hay nada que generar (evita un
        # resultado inválido sin ninguna explicación).
        if not asignaciones:
            if config.grupos:
                incidencias.append(
                    f"Los {len(config.grupos)} grupo(s) seleccionados no tienen "
                    "asignaciones activas."
                )
            else:
                incidencias.append(
                    f"No hay asignaciones activas en el periodo {config.periodo_id}."
                )

        for a in asignaciones:
            asignatura = _get_asignatura(a.asignatura_id)
            horas = _horas_de(a.grupo_id, a.asignatura_id, asignatura)
            total_requeridos += horas
            demanda_grupo[a.grupo_id] = demanda_grupo.get(a.grupo_id, 0) + horas
            demanda_docente[a.usuario_id] = demanda_docente.get(a.usuario_id, 0) + horas
            docentes_involucrados.add(a.usuario_id)
            docente_nombre_map[a.usuario_id] = a.docente_nombre

            tipo_sala = getattr(asignatura, "tipo_sala_requerido", None)
            es_bloque = getattr(asignatura, "bloque_doble", False)
            n_h = getattr(asignatura, "horas_consecutivas", 1) if es_bloque else 1
            if n_h > 1:
                hay_bloque_doble = True

            n_macro = horas // n_h
            n_sueltas = horas % n_h
            lecciones = [
                _Leccion(
                    a.asignacion_id,
                    a.grupo_id,
                    a.usuario_id,
                    f"{a.grupo_codigo}/{a.asignatura_nombre}",
                    tipo_sala_req=tipo_sala if hay_salas else None,
                    n_horas=n_h,
                    docente_nombre=a.docente_nombre,
                )
                for _ in range(n_macro)
            ]
            lecciones += [
                _Leccion(
                    a.asignacion_id,
                    a.grupo_id,
                    a.usuario_id,
                    f"{a.grupo_codigo}/{a.asignatura_nombre}",
                    tipo_sala_req=tipo_sala if hay_salas else None,
                    n_horas=1,
                    docente_nombre=a.docente_nombre,
                )
                for _ in range(n_sueltas)
            ]

            disp = _slots_disponibles_docente(a.usuario_id)
            grupos_asig.append(((disp, -horas), lecciones, a))

        # T4 — asignaciones existen pero ninguna tiene horas configuradas.
        if asignaciones and total_requeridos == 0:
            incidencias.append(
                f"Las asignaciones del periodo {config.periodo_id} tienen 0 horas "
                "semanales configuradas; no hay nada que colocar."
            )

        grupos_asig.sort(key=lambda t: t[0])
        lecciones_ordenadas: list[_Leccion] = []
        for _, lecciones, _a in grupos_asig:
            lecciones_ordenadas.extend(lecciones)

        # Filas de disponibilidad que apuntan a un día o una franja que no
        # existen en la plantilla: no restringen nada y hasta ahora se ignoraban
        # en silencio, dando la falsa impresión de que el veto estaba aplicado.
        for uid in docentes_involucrados:
            _precargar_disp(uid)
        if _disp_huerfanas[0]:
            incidencias.append(
                f"Aviso: {_disp_huerfanas[0]} restricción(es) de disponibilidad apuntan a un "
                "día o una franja que no existe en la plantilla; no se aplican."
            )

        # --- T8: Pre-vuelo de cotas O(n) — detecta infactibilidad antes de backtrack ---
        for g, demanda in demanda_grupo.items():
            perm = franjas_perm_grupo.get(g)
            if perm is not None:
                slots_g = sum(1 for (_, f) in slots if f.orden in perm)
            else:
                slots_g = len(slots)
            if demanda > slots_g:
                nombre_g = grupo_codigo_map.get(g, str(g))
                incidencias.append(
                    f"PRE-VUELO: grupo {nombre_g} requiere {demanda}h pero solo hay "
                    f"{slots_g} franjas disponibles — posible infactibilidad."
                )
        for uid, demanda in demanda_docente.items():
            nombre_doc = docente_nombre_map.get(uid, str(uid))
            disp = _slots_disponibles_docente(uid)
            if demanda > disp:
                incidencias.append(
                    f"PRE-VUELO: docente {nombre_doc} requiere {demanda}h pero solo tiene "
                    f"{disp} franjas disponibles."
                )
            tope = _carga_max(uid)
            if tope is not None and demanda > tope:
                incidencias.append(
                    f"PRE-VUELO: docente {nombre_doc} requiere {demanda}h pero su carga "
                    f"máxima es {tope}h."
                )

        # Slots por lección: combina n_horas + ventana de grupo
        _slots_lec_cache: dict[tuple, list] = {}

        def _slots_para_lec(lec: _Leccion) -> list:
            key = (lec.n_horas, lec.grupo_id)
            if key in _slots_lec_cache:
                return _slots_lec_cache[key]
            base = _slots_para_n(lec.n_horas)
            perm = franjas_perm_grupo.get(lec.grupo_id)
            if perm is not None:
                base = [(d, f) for (d, f) in base if f.orden in perm]
            _slots_lec_cache[key] = base
            return base

        # --- Grids de backtracking ------------------------------------
        ocupado_grupo: set = set()  # (grupo_id, dia, orden)
        ocupado_docente: set = set()  # (usuario_id, dia, orden)
        # Conteo, no set: una misma sala puede quedar marcada por dos lecciones
        # distintas (p. ej. un aula base que además está tipificada como
        # laboratorio). Con un set, el `discard` de una liberaba la ocupación
        # de la otra y la sala se reservaba dos veces en el mismo slot.
        ocupado_sala: Counter[tuple] = Counter()  # (sala_id, dia, orden) -> n
        carga_docente: dict[int, int] = {}
        horas_dia_docente: dict[tuple, int] = {}  # (usuario_id, dia) -> count
        colocados: list[tuple[_Leccion, str, object]] = []
        lec_sala: dict[int, int | None] = {}  # id(lec) -> sala_id asignada

        presupuesto = [max_iteraciones]

        def _liberar_sala(clave: tuple) -> None:
            """Decrementa el conteo de ocupación y borra la clave al llegar a 0."""
            n_actual = ocupado_sala.get(clave, 0)
            if n_actual <= 1:
                ocupado_sala.pop(clave, None)
            else:
                ocupado_sala[clave] = n_actual - 1

        def _elegir_sala(tipo: str, dia: str, orden_start: int, n: int) -> int | None:
            ordenes = _ordenes_n(orden_start, n)
            if ordenes is None:
                return None
            for sid in salas_por_tipo.get(tipo, []):
                if all(ocupado_sala.get((sid, dia, o), 0) == 0 for o in ordenes):
                    return sid
            return None

        def _puede_colocar(lec: _Leccion, dia: str, franja) -> bool:
            ordenes = _ordenes_n(franja.orden, lec.n_horas)
            if ordenes is None:
                return False
            for o in ordenes:
                if (lec.grupo_id, dia, o) in ocupado_grupo:
                    return False
                if (lec.usuario_id, dia, o) in ocupado_docente:
                    return False
                if not _es_disponible(lec.usuario_id, dia, o):
                    return False
                if (lec.usuario_id, dia, o) in bloqueadas_reunion:
                    return False
            tope = _carga_max(lec.usuario_id)
            if tope is not None and carga_docente.get(lec.usuario_id, 0) + lec.n_horas > tope:
                return False
            if aplicar_max_dia_estricto:
                max_hd = _max_horas_dia(lec.usuario_id)
                if max_hd is not None:
                    actual = horas_dia_docente.get((lec.usuario_id, dia), 0)
                    if actual + lec.n_horas > max_hd:
                        return False
            # La sala NO bloquea la colocación: si no hay una disponible del tipo
            # requerido, la clase se coloca igual y la sala queda pendiente de
            # asignar. El horario no debe depender de la disponibilidad de salas.
            return True

        def _colocar(lec: _Leccion, dia: str, franja) -> None:
            ordenes = _ordenes_n(franja.orden, lec.n_horas)
            for o in ordenes:
                ocupado_grupo.add((lec.grupo_id, dia, o))
                ocupado_docente.add((lec.usuario_id, dia, o))
            carga_docente[lec.usuario_id] = carga_docente.get(lec.usuario_id, 0) + lec.n_horas
            k_dia = (lec.usuario_id, dia)
            horas_dia_docente[k_dia] = horas_dia_docente.get(k_dia, 0) + lec.n_horas
            if lec.tipo_sala_req:
                sid = _elegir_sala(lec.tipo_sala_req, dia, franja.orden, lec.n_horas)
                lec_sala[id(lec)] = sid
                if sid:
                    for o in ordenes:
                        ocupado_sala[(sid, dia, o)] += 1
            else:
                # T2: la clase usa el aula base del grupo (no un tipo de sala
                # especial) — se contabiliza como ocupada para que ningún
                # laboratorio la elija a esta misma hora.
                sid_base = sala_base_de_grupo.get(lec.grupo_id)
                if sid_base:
                    for o in ordenes:
                        ocupado_sala[(sid_base, dia, o)] += 1
            colocados.append((lec, dia, franja))

        def _quitar(lec: _Leccion, dia: str, franja) -> None:
            ordenes = _ordenes_n(franja.orden, lec.n_horas) or []
            for o in ordenes:
                ocupado_grupo.discard((lec.grupo_id, dia, o))
                ocupado_docente.discard((lec.usuario_id, dia, o))
            carga_docente[lec.usuario_id] -= lec.n_horas
            k_dia = (lec.usuario_id, dia)
            horas_dia_docente[k_dia] = max(0, horas_dia_docente.get(k_dia, 0) - lec.n_horas)
            sid = lec_sala.pop(id(lec), None)
            if sid:
                for o in ordenes:
                    _liberar_sala((sid, dia, o))
            elif not lec.tipo_sala_req:
                sid_base = sala_base_de_grupo.get(lec.grupo_id)
                if sid_base:
                    for o in ordenes:
                        _liberar_sala((sid_base, dia, o))
            colocados.pop()

        def _desocupar(lec: _Leccion, dia: str, franja) -> None:
            """Como `_quitar`, pero para una lección cualquiera de `colocados`.

            `_quitar` hace `colocados.pop()` porque el backtracking es una pila;
            la reparación por desplazamiento necesita sacar del medio.
            """
            ordenes = _ordenes_n(franja.orden, lec.n_horas) or []
            for o in ordenes:
                ocupado_grupo.discard((lec.grupo_id, dia, o))
                ocupado_docente.discard((lec.usuario_id, dia, o))
            carga_docente[lec.usuario_id] = max(
                0, carga_docente.get(lec.usuario_id, 0) - lec.n_horas
            )
            k_dia = (lec.usuario_id, dia)
            horas_dia_docente[k_dia] = max(0, horas_dia_docente.get(k_dia, 0) - lec.n_horas)
            sid = lec_sala.pop(id(lec), None)
            if sid:
                for o in ordenes:
                    _liberar_sala((sid, dia, o))
            elif not lec.tipo_sala_req:
                sid_base = sala_base_de_grupo.get(lec.grupo_id)
                if sid_base:
                    for o in ordenes:
                        _liberar_sala((sid_base, dia, o))
            for pos, (otra, _d, _f) in enumerate(colocados):
                if otra is lec:
                    del colocados[pos]
                    break

        def _colocar_por_desplazamiento(lec: _Leccion) -> bool:
            """Libera un slot moviendo otra lección del mismo grupo.

            Cadena de expulsión de profundidad 1. Cuando un grupo ya tiene todas
            sus franjas ocupadas no queda ningún hueco libre y la única jugada
            posible es permutar — que es justo lo que el voraz first-fit nunca
            intentaba, y de ahí los "docente_ocupado" en instancias factibles.
            """
            if lec.n_horas != 1:
                return False
            ocupadas = {
                (d, f.orden): (otra, d, f)
                for (otra, d, f) in colocados
                if otra.grupo_id == lec.grupo_id and otra.n_horas == 1
            }
            for dia, franja in _slots_para_lec(lec):
                actual = ocupadas.get((dia, franja.orden))
                if actual is None:
                    continue
                otra, dia_o, franja_o = actual
                _desocupar(otra, dia_o, franja_o)
                if _puede_colocar(lec, dia, franja):
                    _colocar(lec, dia, franja)
                    for dia2, franja2 in _slots_para_lec(otra):
                        if _puede_colocar(otra, dia2, franja2):
                            _colocar(otra, dia2, franja2)
                            return True
                    _quitar(lec, dia, franja)  # lec es el último colocado
                _colocar(otra, dia_o, franja_o)
            return False

        def _reset_estado() -> None:
            ocupado_grupo.clear()
            ocupado_docente.clear()
            ocupado_sala.clear()
            carga_docente.clear()
            horas_dia_docente.clear()
            lec_sala.clear()
            colocados.clear()
            presupuesto[0] = max_iteraciones

        def _diagnosticar_no_colocado(lec: _Leccion) -> str:
            from collections import Counter

            motivos_reales: Counter[str] = Counter()
            slots_grupo_llenos = 0
            total_slots_chequeados = 0
            for dia, franja in _slots_para_lec(lec):
                ordenes = _ordenes_n(franja.orden, lec.n_horas)
                if ordenes is None:
                    motivos_reales["sin_consecutividad"] += 1
                    total_slots_chequeados += 1
                    continue
                total_slots_chequeados += 1
                if (lec.grupo_id, dia, ordenes[0]) in ocupado_grupo:
                    slots_grupo_llenos += 1
                    continue
                causa_slot: str | None = None
                for o in ordenes:
                    if (lec.grupo_id, dia, o) in ocupado_grupo:
                        causa_slot = "grupo_ocupado_parcial"
                        break
                    if (lec.usuario_id, dia, o) in ocupado_docente:
                        causa_slot = "docente_ocupado"
                        break
                    if not _es_disponible(lec.usuario_id, dia, o):
                        causa_slot = "sin_disponibilidad"
                        break
                    if (lec.usuario_id, dia, o) in bloqueadas_reunion:
                        causa_slot = "reunion_bloqueada"
                        break
                if causa_slot is not None:
                    motivos_reales[causa_slot] += 1
                    continue
                tope = _carga_max(lec.usuario_id)
                if tope is not None and carga_docente.get(lec.usuario_id, 0) + lec.n_horas > tope:
                    motivos_reales["tope_carga"] += 1
                    continue
                if aplicar_max_dia_estricto:
                    max_hd = _max_horas_dia(lec.usuario_id)
                    if max_hd is not None and horas_dia_docente.get((lec.usuario_id, dia), 0) + lec.n_horas > max_hd:
                        motivos_reales["max_dia"] += 1
                        continue
                # T16: no se comprueba sala aquí — `_puede_colocar` nunca
                # bloquea por sala (comentario en esa función), así que si el
                # flujo llegó hasta este punto la lección SÍ se habría podido
                # colocar; esta rama era código muerto ("sin_sala").
                motivos_reales["desconocido"] += 1
            if motivos_reales:
                return motivos_reales.most_common(1)[0][0]
            if slots_grupo_llenos == total_slots_chequeados and total_slots_chequeados > 0:
                return "grupo_saturado"
            return "sin_slots"

        # Mejor parcial visto por el DFS. Sin esto, al agotar el presupuesto la
        # pila se desenrolla llamando `_quitar` en cada nivel y `colocados` queda
        # VACÍO: se tiraba todo el trabajo y el voraz arrancaba de cero.
        mejor_parcial: list[tuple[_Leccion, str, object]] = []

        def _backtrack(idx: int) -> bool:
            if len(colocados) > len(mejor_parcial):
                mejor_parcial[:] = colocados
            if idx >= len(lecciones_ordenadas):
                return True
            if presupuesto[0] <= 0:
                return False
            lec = lecciones_ordenadas[idx]
            for dia, franja in _slots_para_lec(lec):
                presupuesto[0] -= 1
                if presupuesto[0] <= 0:
                    return False
                if not _puede_colocar(lec, dia, franja):
                    continue
                _colocar(lec, dia, franja)
                if _backtrack(idx + 1):
                    return True
                _quitar(lec, dia, franja)
            return False

        # --- Camino rápido por coloreo de aristas (König) --------------
        n_slots = len(slots)
        construido_por_coloreo = False

        def _coloreo_activable() -> bool:
            """¿Puede König construir la solución base?

            Solo bloquean las restricciones que un coloreo no sabe representar
            (un color = una franja suelta) o que ninguna reparación posterior
            podría arreglar por falta material de cupo. La indisponibilidad del
            docente, las franjas de reunión y los topes diarios YA NO bloquean:
            König siembra y `reparar_coloreo` los corrige por intercambio.

            Antes bastaba UNA celda vetada para tumbar el único algoritmo
            completo del motor y caer al backtracking, que en instancias reales
            agota el presupuesto sin llegar a ninguna parte.
            """
            if n_slots == 0:
                return False
            # Una macro-lección ocupa varias franjas seguidas: no es un color.
            if hay_bloque_doble:
                return False
            # Una ventana de grupo restringe QUÉ colores valen, y el coloreo es
            # ciego a la identidad del color.
            if franjas_perm_grupo:
                return False
            # König exige grado máximo <= nº de colores en ambos lados.
            if demanda_grupo and max(demanda_grupo.values()) > n_slots:
                return False
            if demanda_docente and max(demanda_docente.values()) > n_slots:
                return False
            for uid in docentes_involucrados:
                tope = _carga_max(uid)
                if tope is not None and demanda_docente.get(uid, 0) > tope:
                    return False
            return True

        viol_coloreo: dict[str, int] = {}

        def _intentar_coloreo() -> bool:
            """Coloreo de aristas bipartito (König) + reparación por intercambio.

            König coloca SIEMPRE todas las lecciones sin choques de grupo ni de
            docente, pero es ciego a disponibilidad, reunión y topes diarios;
            `reparar_coloreo` corrige eso permutando lecciones dentro de la fila
            de cada grupo. Devuelve True solo si el resultado respeta la
            disponibilidad declarada, que el motor no relaja nunca.
            """
            if not _coloreo_activable():
                return False
            from src.domain.models.scheduling import (
                colorear_aristas_bipartito,
                reparar_coloreo,
            )

            aristas = [(lec.grupo_id, lec.usuario_id) for lec in lecciones_ordenadas]
            colores = colorear_aristas_bipartito(aristas, n_slots)
            if not all(c is not None for c in colores):
                return False

            vetos_duros: set[tuple[int, int]] = set()
            vetos_blandos: set[tuple[int, int]] = set()
            for uid in docentes_involucrados:
                for color, (dia_c, franja_c) in enumerate(slots):
                    if not _es_disponible(uid, dia_c, franja_c.orden):
                        vetos_duros.add((uid, color))
                    if (uid, dia_c, franja_c.orden) in bloqueadas_reunion:
                        vetos_blandos.add((uid, color))

            max_por_dia: dict[int, int] = {}
            if aplicar_max_dia_estricto:
                for uid in docentes_involucrados:
                    tope_dia = _max_horas_dia(uid)
                    if tope_dia is not None:
                        max_por_dia[uid] = tope_dia
            min_por_dia: dict[int, int] = {}
            for uid in docentes_involucrados:
                piso_dia = _min_horas_dia(uid)
                if piso_dia:
                    min_por_dia[uid] = piso_dia

            idx_dia = {d: i for i, d in enumerate(dias)}
            dia_de_color = [idx_dia[d] for (d, _f) in slots]

            colores, viol = reparar_coloreo(
                aristas,
                colores,
                n_slots,
                dia_de_color,
                vetos_duros=frozenset(vetos_duros),
                vetos_blandos=frozenset(vetos_blandos),
                max_por_dia=max_por_dia,
                min_por_dia=min_por_dia,
            )
            # La disponibilidad del docente es dura: si la reparación no llega a
            # satisfacerla, se cede el turno al backtracking antes que persistir
            # un horario que pone a un docente donde declaró no estar.
            if viol["indisponibilidad"]:
                return False

            viol_coloreo.clear()
            viol_coloreo.update(viol)
            _reset_estado()
            for lec, color in zip(lecciones_ordenadas, colores, strict=False):
                dia, franja = slots[color]
                _colocar(lec, dia, franja)
            return True

        construido_por_coloreo = _intentar_coloreo()

        relajadas: list[str] = []

        if construido_por_coloreo:
            todas = True
        else:
            todas = _backtrack(0)

            # T8: Relajación ordenada de restricciones duras. Tras relajar, se
            # reintenta primero el coloreo óptimo (completo); si no aplica, se
            # vuelve al backtracking.
            if not todas and aplicar_max_dia_estricto:
                aplicar_max_dia_estricto = False
                relajadas.append("max_horas_dia_estricta")
                _reset_estado()
                if _intentar_coloreo():
                    todas = True
                    construido_por_coloreo = True
                else:
                    todas = _backtrack(0)

            if not todas and bloqueadas_reunion:
                bloqueadas_reunion.clear()
                relajadas.append("franjas_reunion_estricta")
                _reset_estado()
                if _intentar_coloreo():
                    todas = True
                    construido_por_coloreo = True
                else:
                    todas = _backtrack(0)

        if construido_por_coloreo and viol_coloreo:
            exceso = viol_coloreo.get("exceso_max_dia", 0)
            if exceso:
                if "max_horas_dia_estricta" not in relajadas:
                    relajadas.append("max_horas_dia_estricta")
                causas["max_dia"] = causas.get("max_dia", 0) + exceso
                incidencias.append(
                    f"Aviso: {exceso} hora(s) por encima del tope diario de algún docente; "
                    "era la única forma de completar el horario."
                )
            reunion = viol_coloreo.get("reunion", 0)
            if reunion:
                if "franjas_reunion_estricta" not in relajadas:
                    relajadas.append("franjas_reunion_estricta")
                causas["reunion_bloqueada"] = causas.get("reunion_bloqueada", 0) + reunion
                incidencias.append(
                    f"Aviso: {reunion} bloque(s) caen en una franja de reunión estricta; "
                    "era la única forma de completar el horario."
                )

        budget_exhausted = not construido_por_coloreo and presupuesto[0] <= 0

        if not construido_por_coloreo and not todas:
            # Recuperar el mejor parcial del DFS antes de rellenar: al agotarse
            # el presupuesto `colocados` queda vacío y arrancar de cero tira
            # cientos de colocaciones ya validadas.
            if len(mejor_parcial) > len(colocados):
                _reset_estado()
                for lec_p, dia_p, franja_p in mejor_parcial:
                    _colocar(lec_p, dia_p, franja_p)

            colocadas_ids = {id(c[0]) for c in colocados}
            for lec in lecciones_ordenadas:
                if id(lec) in colocadas_ids:
                    continue
                ubicada = False
                for dia, franja in _slots_para_lec(lec):
                    if _puede_colocar(lec, dia, franja):
                        _colocar(lec, dia, franja)
                        ubicada = True
                        break
                if not ubicada:
                    ubicada = _colocar_por_desplazamiento(lec)
                if not ubicada:
                    causa = _diagnosticar_no_colocado(lec)
                    causas[causa] = causas.get(causa, 0) + 1
                    # T7: nombres legibles (docente) en vez del id crudo de la
                    # asignación; la etiqueta del motor ya trae grupo/materia.
                    causa_label = CAUSA_INFO.get(causa, (causa, None))[0]
                    docente_txt = lec.docente_nombre or f"docente {lec.usuario_id}"
                    incidencias.append(
                        f"No colocado: {lec.etiqueta} ({docente_txt}) — {causa_label}."
                    )

        # --- Post-solve: verificar min_horas_dia ----------------------
        for uid in docentes_involucrados:
            min_hd = _min_horas_dia(uid)
            if min_hd and min_hd > 0:
                for dia in dias:
                    actual = horas_dia_docente.get((uid, dia), 0)
                    if 0 < actual < min_hd:
                        incidencias.append(
                            f"Aviso: docente {uid} tiene {actual}h el {dia} "
                            f"(mínimo esperado {min_hd}h)."
                        )
                        causas["min_dia_docente"] = causas.get("min_dia_docente", 0) + 1

        # --- Aviso: clases sin sala del tipo requerido (no bloquea) ---
        sin_sala = sum(
            1 for (lec, _d, _f) in colocados if lec.tipo_sala_req and lec_sala.get(id(lec)) is None
        )
        if sin_sala:
            incidencias.append(
                f"Aviso: {sin_sala} clase(s) quedaron sin sala del tipo requerido; "
                "se colocaron igual y la sala queda pendiente de asignar."
            )
            causas["sala_pendiente"] = sin_sala

        # --- Mejora local (hill-climbing) sobre coste blando ----------
        pesos = config.pesos
        n_dias = len(dias)
        costo_inicial, _ = self._costo(colocados, pesos, orden_a_idx, n_dias_total=n_dias)
        pasos_mejora = 0

        def _skip_lec(lec):
            return lec.n_horas > 1 or bool(lec.tipo_sala_req)

        def _extra_check(lec, dia, franja, dia_origen=None):
            if (lec.usuario_id, dia, franja.orden) in bloqueadas_reunion:
                return False
            if aplicar_max_dia_estricto:
                max_hd = _max_horas_dia(lec.usuario_id)
                if max_hd is not None and horas_dia_docente.get((lec.usuario_id, dia), 0) >= max_hd:
                    return False
            # No deshacer el piso diario que la reparación acaba de conseguir:
            # vaciar el día de origen por debajo del mínimo reintroduce los
            # avisos "docente X tiene 2h el Jueves (mínimo esperado 3h)".
            if dia_origen is not None and dia_origen != dia:
                min_hd = _min_horas_dia(lec.usuario_id)
                if min_hd:
                    quedan = horas_dia_docente.get((lec.usuario_id, dia_origen), 0) - 1
                    if 0 < quedan < min_hd:
                        return False
            return True

        if optimizar and len(colocados) >= 2:
            pasos_mejora = self._mejorar_local(
                colocados,
                slots,
                ocupado_grupo,
                ocupado_docente,
                pesos,
                orden_a_idx,
                _es_disponible,
                skip_lec_fn=_skip_lec,
                slots_para_lec_fn=_slots_para_lec,
                extra_check_fn=_extra_check,
                horas_dia_docente=horas_dia_docente,
                n_dias_total=n_dias,
            )
        costo_final, metricas = self._costo(colocados, pesos, orden_a_idx, n_dias_total=n_dias)
        metricas.costo_inicial = costo_inicial
        metricas.costo_final = costo_final
        metricas.pasos_mejora = pasos_mejora

        # --- Mapear a bloques generados (expandir macro-lecciones) ----
        bloques: list[BloqueGeneradoDTO] = []
        for lec, dia, franja_start in colocados:
            sid = lec_sala.get(id(lec))
            if sid:
                sala_nombre = sala_nombre_map.get(sid, "Aula")
            elif lec.tipo_sala_req:
                sala_nombre = "Por asignar"
            else:
                # Clase normal: aula propia del grupo, o genérica si no tiene.
                sala_nombre = sala_grupo_nombre.get(lec.grupo_id, "Aula")
            cur_franja = franja_start
            for k in range(lec.n_horas):
                bloques.append(
                    BloqueGeneradoDTO(
                        asignacion_id=lec.asignacion_id,
                        grupo_id=lec.grupo_id,
                        usuario_id=lec.usuario_id,
                        dia_semana=dia,
                        franja_orden=cur_franja.orden,
                        hora_inicio=cur_franja.hora_inicio,
                        hora_fin=cur_franja.hora_fin,
                        sala=sala_nombre,
                        sala_id=sid,
                    )
                )
                if k < lec.n_horas - 1:
                    nxt_o = orden_siguiente[cur_franja.orden]
                    cur_franja = franja_by_orden[nxt_o]

        if construido_por_coloreo:
            metodo = "konig"
        elif not todas:
            metodo = "backtrack+greedy"
        else:
            metodo = "backtrack"

        n_grupos_procesados = len({a.grupo_id for a in asignaciones})

        resultado = ResultadoGeneracionDTO(
            total_requeridos=total_requeridos,
            colocados=len(bloques),
            no_colocados=total_requeridos - len(bloques),
            bloques=bloques,
            incidencias=incidencias,
            metricas=metricas,
            causas=causas,
            relajadas=relajadas,
            total_slots=len(slots),
            grupos_procesados=n_grupos_procesados,
            demanda_por_grupo={str(k): v for k, v in demanda_grupo.items()},
            metodo_usado=metodo,
            presupuesto_agotado=budget_exhausted,
        )

        # --- T5: nada que persistir ni activar sin bloques -------------
        # Sin bloques no hay nada que colocar en un escenario: no se crea
        # escenario nuevo, no se borra el anterior, no se toca la config ni
        # su estado. `escenario_id` queda None (default del DTO).
        if not bloques:
            if not resultado.incidencias:
                resultado.incidencias.append(
                    "No se generó ningún bloque de horario; revise la configuración."
                )
            resultado.valido = False
            return resultado

        # --- Resolver escenario destino --------------------------------
        if crear_escenario:
            if config.escenario_destino_id is not None:
                self._infraestructura.eliminar_escenario(config.escenario_destino_id)
            escenario = self._infraestructura.crear_escenario_simple(
                config.anio_id,
                nombre=f"Generado {config.nombre}",
                descripcion=f"Escenario generado automáticamente desde la config '{config.nombre}'.",
            )
            escenario_id = escenario.id
        else:
            escenario_id = config.escenario_destino_id
            if escenario_id is None:
                resultado.incidencias.append(
                    "No hay escenario destino: crear_escenario=False y la config "
                    "no tiene escenario_destino_id."
                )
                return resultado

        resultado.escenario_id = escenario_id

        # --- GATE oráculo: analizar_lote ------------------------------
        # salas_bloquean=False: el generador ya evita choques reales de sala
        # vía `ocupado_sala`; un cruce de sala aquí no debe invalidar el lote
        # (paso_17 T1). Los cruces de docente y grupo siguen siendo duros.
        filas = [
            {
                "asignacion_id": b.asignacion_id,
                "dia_semana": b.dia_semana,
                "hora_inicio": b.hora_inicio,
                "hora_fin": b.hora_fin,
                "sala": b.sala,
            }
            for b in bloques
        ]

        reporte = self._horario.analizar_lote(
            escenario_id, config.periodo_id, filas, salas_bloquean=False
        )
        # El oráculo solo certifica que los bloques colocados no se cruzan.
        # Un horario parcial nunca es apto para persistir/activar.
        resultado.valido = reporte.todo_ok and resultado.no_colocados == 0
        for f in reporte.filas:
            if not f.ok:
                resultado.incidencias.append(
                    f"Oráculo rechazó fila {f.indice}: {f.motivo or 'motivo desconocido'}."
                )
        resultado.incidencias.extend(reporte.avisos)
        if resultado.no_colocados:
            resultado.incidencias.append(
                f"Resultado parcial: faltan {resultado.no_colocados} bloque(s); no se persistió."
            )

        # --- Persistir solo si válido ---------------------------------
        if resultado.valido:
            self._horario.aplicar_lote(
                escenario_id,
                config.periodo_id,
                filas,
                solo_validas=False,
                salas_bloquean=False,
            )

        # --- Actualizar config (solo si se resolvió un escenario) -----
        config_actualizada = config.model_copy(update={"escenario_destino_id": escenario_id})
        self._infra.actualizar_config_generacion(config_actualizada)
        # T5: solo transiciona a "generado" si el resultado es válido y algo
        # quedó efectivamente colocado; nunca sobre un resultado inválido o vacío.
        if resultado.valido and resultado.colocados > 0 and config.puede_transicionar_a("generado"):
            self._infra.cambiar_estado_config(config_id, "generado")

        logger.info(
            "Generacion config=%d: requeridos=%d colocados=%d slots=%d "
            "grupos=%d metodo=%s presupuesto_agotado=%s valido=%s causas=%s",
            config_id,
            resultado.total_requeridos,
            resultado.colocados,
            resultado.total_slots,
            resultado.grupos_procesados,
            resultado.metodo_usado,
            resultado.presupuesto_agotado,
            resultado.valido,
            resultado.causas,
        )

        return resultado


__all__ = [
    "CAUSA_INFO",
    "PESOS_AVANZADOS",
    "PESOS_PRINCIPALES",
    "GeneradorHorarioService",
]
