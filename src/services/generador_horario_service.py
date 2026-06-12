"""
GeneradorHorarioService (paso_15c)
===================================
Motor de generación de horarios v1: búsqueda constructiva con backtracking.

Dada una ConfigGeneracion, coloca los bloques de cada asignación en las
franjas lectivas de la plantilla respetando TODAS las restricciones duras:

  - Sin cruce de grupo  (un grupo no puede tener dos bloques en la misma franja).
  - Sin cruce de docente (un docente no puede dictar a dos grupos a la vez).
  - Disponibilidad del docente (es_disponible por franja).
  - Tope de carga docente (carga_horaria_max).

v1 NO optimiza huecos ni calidad (eso es paso_15d). Busca una solución
factible colocando tantos bloques como sea posible y reportando los no
colocados como solución parcial.

La búsqueda es 100% en memoria (grids O(1)). `HorarioService.analizar_lote`
se usa solo como GATE oráculo al final, antes de persistir.

Lógica pura: este servicio NO importa NiceGUI ni librerías de UI, ni
`src.db`, ni instancia repositorios.
"""
from __future__ import annotations

from src.domain.models.asignacion import FiltroAsignacionesDTO
from src.domain.models.infraestructura import (
    BloqueGeneradoDTO,
    MetricasCalidadDTO,
    ResultadoGeneracionDTO,
)


class _Leccion:
    """Una unidad de bloque a colocar de una asignación (una de sus horas)."""

    __slots__ = ("asignacion_id", "grupo_id", "usuario_id", "etiqueta")

    def __init__(self, asignacion_id, grupo_id, usuario_id, etiqueta):
        self.asignacion_id = asignacion_id
        self.grupo_id = grupo_id
        self.usuario_id = usuario_id
        self.etiqueta = etiqueta


class GeneradorHorarioService:

    def __init__(
        self,
        infra_repo,
        asignacion_repo,
        usuario_repo,
        horario_service,
        infraestructura_service,
    ):
        self._infra = infra_repo
        self._asig = asignacion_repo
        self._usuario = usuario_repo
        self._horario = horario_service
        self._infraestructura = infraestructura_service

    # ------------------------------------------------------------------ #
    # Coste blando y mejora local (paso_15d)                               #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _costo(colocados, pesos, orden_a_idx):
        """
        Calcula el coste blando ponderado de una solución.

        `colocados` es list[(_Leccion, dia, franja)]. `orden_a_idx` mapea
        el `orden` crudo de cada franja lectiva a un índice compacto 0..L-1
        (para que un recreo entre clases no cuente como hueco).

        Devuelve (costo_total: float, MetricasCalidadDTO) sin rellenar
        costo_inicial / costo_final / pasos_mejora (eso se hace fuera).
        """
        # idx compactos por (grupo, dia) y (docente, dia)
        idx_grupo: dict[tuple, list[int]] = {}
        idx_docente: dict[tuple, list[int]] = {}
        # conteo por (asignacion, dia) para distribución
        conteo_asig: dict[tuple, int] = {}
        # días distintos por docente
        dias_por_docente: dict[int, set] = {}

        for (lec, dia, franja) in colocados:
            idx = orden_a_idx[franja.orden]
            idx_grupo.setdefault((lec.grupo_id, dia), []).append(idx)
            idx_docente.setdefault((lec.usuario_id, dia), []).append(idx)
            conteo_asig[(lec.asignacion_id, dia)] = (
                conteo_asig.get((lec.asignacion_id, dia), 0) + 1
            )
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

        costo_total = (
            pesos.huecos * (huecos_grupo + huecos_docente)
            + pesos.distribucion * solapes_distribucion
            + pesos.compactacion * dias_docente
        )

        metricas = MetricasCalidadDTO(
            huecos_grupo=huecos_grupo,
            huecos_docente=huecos_docente,
            solapes_distribucion=solapes_distribucion,
            dias_docente=dias_docente,
        )
        return costo_total, metricas

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
    ) -> int:
        """
        Hill-climbing best-improvement: mueve bloques ya colocados a slots
        vacíos factibles para reducir el coste blando, sin romper ninguna
        restricción dura y sin des-colocar bloques.

        Devuelve el nº de movimientos aplicados. El coste es monótonamente
        no creciente: costo_final <= costo_inicial siempre.
        """
        pasos = 0

        def _costo_actual():
            return GeneradorHorarioService._costo(colocados, pesos, orden_a_idx)[0]

        mejoró_alguna_pasada = True
        while mejoró_alguna_pasada and pasos < max_pasos:
            mejoró_alguna_pasada = False
            for i in range(len(colocados)):
                if pasos >= max_pasos:
                    break
                lec, dia_act, franja_act = colocados[i]
                costo_base = _costo_actual()
                mejor_delta = 0.0
                mejor_slot = None  # (dia2, franja2)

                # Quitar tentativamente la ocupación actual para evaluar slots.
                clave_g_act = (lec.grupo_id, dia_act, franja_act.orden)
                clave_d_act = (lec.usuario_id, dia_act, franja_act.orden)

                for (dia2, franja2) in slots:
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

                    # Aplicar movimiento tentativo.
                    colocados[i] = (lec, dia2, franja2)
                    nuevo_costo = _costo_actual()
                    delta = nuevo_costo - costo_base
                    # Revertir.
                    colocados[i] = (lec, dia_act, franja_act)

                    if delta < mejor_delta:
                        mejor_delta = delta
                        mejor_slot = (dia2, franja2)

                if mejor_slot is not None:
                    dia2, franja2 = mejor_slot
                    # Aplicar definitivamente: actualizar grids y colocados.
                    ocupado_grupo.discard(clave_g_act)
                    ocupado_docente.discard(clave_d_act)
                    ocupado_grupo.add((lec.grupo_id, dia2, franja2.orden))
                    ocupado_docente.add((lec.usuario_id, dia2, franja2.orden))
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

        franjas = [f for f in self._infra.listar_franjas(config.plantilla_id)
                   if f.es_lectiva]
        franjas.sort(key=lambda f: f.orden)
        # Índice compacto 0..L-1 según posición en la lista de lectivas
        # ordenada por orden (un recreo entre clases NO cuenta como hueco).
        orden_a_idx = {f.orden: idx for idx, f in enumerate(franjas)}
        dias = list(plantilla.dias_activos)
        slots = [(dia, franja) for dia in dias for franja in franjas]

        if not slots:
            return ResultadoGeneracionDTO(
                total_requeridos=0,
                incidencias=["La plantilla no tiene franjas lectivas en días activos."],
            )

        # --- Cargar asignaciones --------------------------------------
        asignaciones = self._asig.listar_info(
            FiltroAsignacionesDTO(periodo_id=config.periodo_id, solo_activas=True)
        )
        if config.grupos:
            grupos_filtro = set(config.grupos)
            asignaciones = [a for a in asignaciones if a.grupo_id in grupos_filtro]

        # --- Construir lecciones (horas) por asignación ---------------
        # Cache de disponibilidad y carga por docente para no repetir queries.
        slots_disp_docente: dict[int, int] = {}

        def _slots_disponibles_docente(usuario_id: int) -> int:
            if usuario_id not in slots_disp_docente:
                n = sum(
                    1 for (dia, franja) in slots
                    if self._infra.es_disponible(usuario_id, dia, franja.orden)
                )
                slots_disp_docente[usuario_id] = n
            return slots_disp_docente[usuario_id]

        carga_max_cache: dict[int, int | None] = {}

        def _carga_max(usuario_id: int) -> int | None:
            if usuario_id not in carga_max_cache:
                carga_max_cache[usuario_id] = self._usuario.carga_horaria_max(usuario_id)
            return carga_max_cache[usuario_id]

        # Agrupar lecciones por asignación; ordenar asignaciones MRV.
        grupos_asig = []  # list[ (info_orden_key, lecciones[]) ]
        total_requeridos = 0
        incidencias: list[str] = []

        for a in asignaciones:
            asignatura = self._infra.get_asignatura(a.asignatura_id)
            horas = getattr(asignatura, "horas_semanales", None) or 1
            total_requeridos += horas
            lecciones = [
                _Leccion(
                    a.asignacion_id, a.grupo_id, a.usuario_id,
                    f"{a.grupo_codigo}/{a.asignatura_nombre}",
                )
                for _ in range(horas)
            ]
            # Clave MRV: docente con menos slots disponibles primero,
            # y con más horas requeridas primero (más restringido => antes).
            disp = _slots_disponibles_docente(a.usuario_id)
            grupos_asig.append(((disp, -horas), lecciones, a))

        grupos_asig.sort(key=lambda t: t[0])

        # Aplanar lecciones en orden MRV. Las lecciones de una misma
        # asignación quedan contiguas, lo que ayuda al backtracking.
        lecciones_ordenadas: list[_Leccion] = []
        for _, lecciones, _a in grupos_asig:
            lecciones_ordenadas.extend(lecciones)

        # --- Backtracking ---------------------------------------------
        ocupado_grupo: set = set()      # (grupo_id, dia, orden)
        ocupado_docente: set = set()    # (usuario_id, dia, orden)
        carga_docente: dict[int, int] = {}  # usuario_id -> bloques colocados
        colocados: list[tuple[_Leccion, str, object]] = []  # (leccion, dia, franja)

        # Presupuesto de iteraciones compartido (mutable vía lista).
        presupuesto = [max_iteraciones]

        def _puede_colocar(lec: _Leccion, dia: str, franja) -> bool:
            orden = franja.orden
            if (lec.grupo_id, dia, orden) in ocupado_grupo:
                return False
            if (lec.usuario_id, dia, orden) in ocupado_docente:
                return False
            if not self._infra.es_disponible(lec.usuario_id, dia, orden):
                return False
            tope = _carga_max(lec.usuario_id)
            if tope is not None and carga_docente.get(lec.usuario_id, 0) >= tope:
                return False
            return True

        def _colocar(lec: _Leccion, dia: str, franja) -> None:
            orden = franja.orden
            ocupado_grupo.add((lec.grupo_id, dia, orden))
            ocupado_docente.add((lec.usuario_id, dia, orden))
            carga_docente[lec.usuario_id] = carga_docente.get(lec.usuario_id, 0) + 1
            colocados.append((lec, dia, franja))

        def _quitar(lec: _Leccion, dia: str, franja) -> None:
            orden = franja.orden
            ocupado_grupo.discard((lec.grupo_id, dia, orden))
            ocupado_docente.discard((lec.usuario_id, dia, orden))
            carga_docente[lec.usuario_id] -= 1
            colocados.pop()

        def _backtrack(idx: int) -> bool:
            """Intenta colocar TODAS las lecciones desde idx. True si todas caben."""
            if idx >= len(lecciones_ordenadas):
                return True
            if presupuesto[0] <= 0:
                return False
            lec = lecciones_ordenadas[idx]
            for (dia, franja) in slots:
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

        todas = _backtrack(0)

        if not todas:
            # Solución parcial: greedy con el presupuesto restante. Coloca
            # cada lección no colocada en el primer slot factible; las que no
            # quepan quedan como no colocadas (incidencia).
            colocadas_ids = {id(c[0]) for c in colocados}
            for lec in lecciones_ordenadas:
                if id(lec) in colocadas_ids:
                    continue
                ubicada = False
                for (dia, franja) in slots:
                    if _puede_colocar(lec, dia, franja):
                        _colocar(lec, dia, franja)
                        ubicada = True
                        break
                if not ubicada:
                    incidencias.append(
                        f"No colocado: {lec.etiqueta} (asignación {lec.asignacion_id}) "
                        f"— sin franja factible (cruce/disponibilidad/tope)."
                    )

        # --- Mejora local (hill-climbing) sobre coste blando ----------
        pesos = config.pesos
        costo_inicial, _ = self._costo(colocados, pesos, orden_a_idx)
        pasos_mejora = 0
        if optimizar and len(colocados) >= 2:
            pasos_mejora = self._mejorar_local(
                colocados,
                slots,
                ocupado_grupo,
                ocupado_docente,
                pesos,
                orden_a_idx,
                self._infra.es_disponible,
            )
        costo_final, metricas = self._costo(colocados, pesos, orden_a_idx)
        metricas.costo_inicial = costo_inicial
        metricas.costo_final = costo_final
        metricas.pasos_mejora = pasos_mejora

        # --- Mapear a bloques generados -------------------------------
        bloques = [
            BloqueGeneradoDTO(
                asignacion_id=lec.asignacion_id,
                grupo_id=lec.grupo_id,
                usuario_id=lec.usuario_id,
                dia_semana=dia,
                franja_orden=franja.orden,
                hora_inicio=franja.hora_inicio,
                hora_fin=franja.hora_fin,
                sala="Aula",
            )
            for (lec, dia, franja) in colocados
        ]

        resultado = ResultadoGeneracionDTO(
            total_requeridos=total_requeridos,
            colocados=len(bloques),
            no_colocados=total_requeridos - len(bloques),
            bloques=bloques,
            incidencias=incidencias,
            metricas=metricas,
        )

        # --- Resolver escenario destino -------------------------------
        if crear_escenario:
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

        if filas:
            reporte = self._horario.analizar_lote(escenario_id, config.periodo_id, filas)
            resultado.valido = reporte.todo_ok
            for f in reporte.filas:
                if not f.ok:
                    resultado.incidencias.append(
                        f"Oráculo rechazó fila {f.indice}: {f.motivo or 'motivo desconocido'}."
                    )
        else:
            # Nada que colocar; el lote vacío no es "válido" en sentido positivo.
            resultado.valido = False

        # --- Persistir solo si válido ---------------------------------
        if resultado.valido and filas:
            self._horario.aplicar_lote(
                escenario_id, config.periodo_id, filas, solo_validas=False
            )

        # --- Actualizar config ----------------------------------------
        config_actualizada = config.model_copy(
            update={"escenario_destino_id": escenario_id}
        )
        self._infra.actualizar_config_generacion(config_actualizada)
        if config.puede_transicionar_a("generado"):
            self._infra.cambiar_estado_config(config_id, "generado")

        return resultado


__all__ = ["GeneradorHorarioService"]
