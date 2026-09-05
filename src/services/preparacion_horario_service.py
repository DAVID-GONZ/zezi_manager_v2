"""
PreparacionHorarioService — validadores de preparación para generar horarios (paso_19).

Expone:
  validar_config(config_id, rol=None) -> ReportePreparacionDTO
  validar(anio_id, periodo_id, plantilla_id, rol=None) -> ReportePreparacionDTO  (envoltorio)
  puede_generar(reporte) -> bool

Cada puerta es una función pura que devuelve un PuertaDTO; nunca lanza excepciones.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from src.domain.models.asignacion import FiltroAsignacionesDTO
from src.domain.ports.asignacion_repo import IAsignacionRepository
from src.domain.ports.configuracion_repo import IConfiguracionRepository
from src.domain.ports.infraestructura_repo import IInfraestructuraRepository
from src.domain.ports.periodo_repo import IPeriodoRepository
from src.domain.ports.usuario_repo import IUsuarioRepository

if TYPE_CHECKING:
    from src.services.plan_estudios_service import PlanEstudiosService


@dataclass(frozen=True)
class PuertaDTO:
    id: str
    titulo: str
    severidad: str  # "dura" | "advertencia"
    ok: bool
    detalle: str
    fix_ruta: str | None = None


ReportePreparacionDTO = list[PuertaDTO]

# T12 — solo el rol director puede abrir rutas bajo /admin/*; el resto de la
# app (/academico/..., /director/...) es accesible para todo el "aula"
# (director/coordinador/profesor). Simplificación deliberada: no reimplementa
# la matriz completa de `main.py::registrar_rutas_ui()`, solo distingue lo
# que necesita esta puerta (evitar mandar a un coordinador/profesor a una
# ruta que el guard de rutas le va a rechazar).
_PREFIJO_SOLO_DIRECTOR = "/admin/"


class PreparacionHorarioService:
    def __init__(
        self,
        infra_repo: IInfraestructuraRepository,
        asignacion_repo: IAsignacionRepository,
        config_repo: IConfiguracionRepository,
        periodo_repo: IPeriodoRepository,
        usuario_repo: IUsuarioRepository,
        plan_svc: PlanEstudiosService,
    ) -> None:
        """Inyecta los repos de infraestructura, asignación, configuración,
        periodo y usuario, más el servicio de plan de estudios."""
        self._infra = infra_repo
        self._asigs = asignacion_repo
        self._cfg = config_repo
        self._periodos = periodo_repo
        self._usuarios = usuario_repo
        self._plan = plan_svc

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def validar_config(
        self,
        config_id: int,
        rol: str | None = None,
    ) -> ReportePreparacionDTO:
        """Evalúa las puertas contra la ConfigGeneracion real: su anio_id,
        periodo_id, plantilla_id y filtro de grupos (config.grupos).

        T8 (B3 de la auditoría): antes la checklist evaluaba un año/periodo/
        plantilla sueltos que podían no coincidir con los de la config que
        realmente se iba a generar. Esta es la forma preferida de validar
        cuando ya existe la config; `validar()` queda como envoltorio de
        compatibilidad para quien todavía no tiene un config_id.
        """
        config = self._infra.get_config_generacion(config_id)
        if config is None:
            return [
                PuertaDTO(
                    id="config_generacion",
                    titulo="Configuración de generación",
                    severidad="dura",
                    ok=False,
                    detalle=f"No existe una configuración de generación con id={config_id}.",
                    fix_ruta="/academico/generar-horario",
                )
            ]
        grupos_filtro = set(config.grupos) if config.grupos else None
        return self._construir_reporte(
            anio_id=config.anio_id,
            periodo_id=config.periodo_id,
            plantilla_id=config.plantilla_id,
            grupos_filtro=grupos_filtro,
            rol=rol,
        )

    def validar(
        self,
        anio_id: int,
        periodo_id: int,
        plantilla_id: int,
        rol: str | None = None,
    ) -> ReportePreparacionDTO:
        """Envoltorio de compatibilidad (T8): evalúa un año/periodo/plantilla
        sueltos, sin restringir a los grupos de ninguna ConfigGeneracion.
        Preferir `validar_config(config_id)` cuando ya existe la config que
        se va a generar."""
        return self._construir_reporte(
            anio_id=anio_id,
            periodo_id=periodo_id,
            plantilla_id=plantilla_id,
            grupos_filtro=None,
            rol=rol,
        )

    def _construir_reporte(
        self,
        anio_id: int,
        periodo_id: int,
        plantilla_id: int,
        grupos_filtro: set[int] | None,
        rol: str | None,
    ) -> ReportePreparacionDTO:
        """Ejecuta las puertas en orden y devuelve el reporte, acotado al
        tenant activo y, si `grupos_filtro` no es None, a esos grupos."""
        # Multi-tenant (paso_32, T5; corregido T12): `self._infra` es el
        # repositorio (no el servicio), así que el scope NO viene aplicado.
        # `institucion_actual()` es None para admin/arranque; los repos
        # exigen un TenantScope explícito, así que se normaliza a "*"
        # (equivalente a "sin filtrar", coherente con el resto del código
        # multi-tenant — ver generador_horario_service).
        from src.services.contexto_tenant import institucion_actual

        scope = institucion_actual() or "*"

        asignaciones = self._listar_asignaciones(periodo_id)
        if grupos_filtro is not None:
            asignaciones = [a for a in asignaciones if a.grupo_id in grupos_filtro]

        grupos = self._infra.listar_grupos(institucion_id=scope)
        if grupos_filtro is not None:
            grupos = [g for g in grupos if g.id in grupos_filtro]

        asignaturas = self._infra.listar_asignaturas(institucion_id=scope)
        salas = self._infra.listar_salas(institucion_id=scope)
        franjas = self._infra.listar_franjas(plantilla_id) if plantilla_id else []
        plantilla = (
            next(
                (
                    p
                    for p in self._infra.listar_plantillas_franja(institucion_id=scope)
                    if p.id == plantilla_id
                ),
                None,
            )
            if plantilla_id
            else None
        )

        asig_map = {a.id: a for a in asignaturas}
        grado_de_grupo = {g.id: g.grado for g in grupos}

        reporte = [
            self._p1_anio_periodo(anio_id, periodo_id),
            self._p_asignaciones_activas(asignaciones),
            self._p6_plantilla_suficiente(plantilla_id, plantilla, franjas),
            self._p_horas_plan_asignaciones(asignaciones, asig_map, grado_de_grupo, grupos),
            self._p3_horas_grupo_vs_slots(
                grupos, asignaciones, asig_map, grado_de_grupo, plantilla, franjas
            ),
            self._p4_capacidad_docente(asignaciones, asig_map, grado_de_grupo),
            self._p_capacidad_docente_slots(
                asignaciones, asig_map, grado_de_grupo, plantilla, franjas
            ),
            self._p5_cobertura_asignaciones(grupos, asignaciones, asig_map),
            self._p_disponibilidad_coherente(asignaciones, plantilla, franjas),
            self._p_grupos_con_grado(grupos),
            self._p8_aulas_base_unicas(grupos),
            self._p7_salas_suficientes(asignaturas, salas),
        ]
        return self._filtrar_fix_ruta(reporte, rol)

    @staticmethod
    def _filtrar_fix_ruta(reporte: ReportePreparacionDTO, rol: str | None) -> ReportePreparacionDTO:
        """T12 — algunos `fix_ruta` apuntan a `/admin/...`, inaccesibles para
        un coordinador o un profesor (el guard de rutas de `main.py` los
        rechaza). Cuando se conoce el rol del usuario actual se retira el
        `fix_ruta` de las puertas que apuntarían a una de esas rutas, en vez
        de mandarlo a una pantalla que no puede abrir. `rol=None` (llamador
        que no propaga el rol) preserva el comportamiento anterior."""
        if rol is None or rol == "director":
            return reporte
        return [
            replace(p, fix_ruta=None)
            if p.fix_ruta and p.fix_ruta.startswith(_PREFIJO_SOLO_DIRECTOR)
            else p
            for p in reporte
        ]

    def _listar_asignaciones(self, periodo_id: int) -> list:
        """Devuelve TODAS las asignaciones del periodo recorriendo las páginas.

        `IAsignacionRepository.listar` está paginado (máx. 500/página); las
        puertas de preparación necesitan el conjunto completo, de lo contrario
        las asignaciones más allá de la primera página parecen inexistentes
        (cobertura del plan y carga docente quedarían mal calculadas).
        """
        todas: list = []
        pagina = 1
        while True:
            lote = self._asigs.listar(
                FiltroAsignacionesDTO(periodo_id=periodo_id, pagina=pagina, por_pagina=500)
            )
            todas.extend(lote)
            if len(lote) < 500:
                break
            pagina += 1
        return todas

    def _horas_asignacion(self, asignacion, asig_map: dict, grado_de_grupo: dict) -> int:
        """Horas semanales de una asignación según el plan de estudios del grado
        (con fallback a las horas globales de la asignatura). Misma resolución
        que usa el motor (`GeneradorHorarioService._horas_de`), para que las
        puertas midan exactamente lo que se va a generar."""
        grado = grado_de_grupo.get(asignacion.grupo_id)
        asignatura = asig_map.get(asignacion.asignatura_id)
        global_h = (asignatura.horas_semanales or 0) if asignatura else 0
        if grado is None:
            return global_h
        try:
            # El valor del plan tal cual, igual que `GeneradorHorarioService._horas_de`.
            # `PlanEstudiosService.horas_de` ya cae al `horas_semanales` global
            # cuando el grado no tiene la asignatura en su plan; un `or global_h`
            # extra sería una segunda capa de fallback que enmascara un 0
            # legítimo y haría que la puerta midiera algo distinto del motor.
            return self._plan.horas_de(grado, asignacion.asignatura_id)
        except Exception:
            return global_h

    # Cupos lectivos semanales = franjas lectivas × días activos de la plantilla.
    @staticmethod
    def _cupos_semana(plantilla, franjas) -> tuple[int, int, int]:
        n_lectivas = sum(1 for f in franjas if getattr(f, "es_lectiva", True))
        n_dias = len(getattr(plantilla, "dias_activos", None) or []) if plantilla else 0
        return n_lectivas * n_dias, n_lectivas, n_dias

    @staticmethod
    def puede_generar(reporte: ReportePreparacionDTO) -> bool:
        """True si todas las puertas 'dura' están en ok."""
        return all(p.ok for p in reporte if p.severidad == "dura")

    # ------------------------------------------------------------------
    # Puerta — año y periodo existen y son coherentes
    # ------------------------------------------------------------------

    def _p1_anio_periodo(self, anio_id: int, periodo_id: int) -> PuertaDTO:
        config = self._cfg.get_by_id(anio_id)
        if config is None:
            return PuertaDTO(
                id="anio_periodo",
                titulo="Año lectivo configurado",
                severidad="dura",
                ok=False,
                detalle=f"No existe una configuración para el año con id={anio_id}.",
                fix_ruta="/admin/configuracion",
            )
        periodo = self._periodos.get_by_id(periodo_id)
        if periodo is None:
            return PuertaDTO(
                id="anio_periodo",
                titulo="Año lectivo configurado",
                severidad="dura",
                ok=False,
                detalle=f"No existe el periodo con id={periodo_id}.",
                fix_ruta="/admin/configuracion",
            )
        if periodo.anio_id != anio_id:
            return PuertaDTO(
                id="anio_periodo",
                titulo="Año lectivo configurado",
                severidad="dura",
                ok=False,
                detalle=(f"El periodo {periodo_id} no pertenece al año {config.anio}."),
                fix_ruta="/admin/configuracion",
            )
        return PuertaDTO(
            id="anio_periodo",
            titulo="Año lectivo configurado",
            severidad="dura",
            ok=True,
            detalle=f"Año {config.anio}, periodo {periodo.numero} — OK.",
        )

    # ------------------------------------------------------------------
    # Puerta — asignaciones activas en el alcance (T11, nueva)
    # ------------------------------------------------------------------
    # Sin asignaciones activas el motor no tiene nada que colocar; sin esta
    # puerta el reporte podía salir todo en verde (plan/cobertura vacíos no
    # bloquean nada) y `puede_generar()` decir que sí con una generación que
    # produce un horario vacío.

    def _p_asignaciones_activas(self, asignaciones) -> PuertaDTO:
        activas = [a for a in asignaciones if a.activo]
        if not activas:
            return PuertaDTO(
                id="asignaciones_activas",
                titulo="Asignaciones activas",
                severidad="dura",
                ok=False,
                detalle="No hay asignaciones activas en el alcance seleccionado (periodo y, "
                "si aplica, grupos de la config).",
                fix_ruta="/admin/asignaciones",
            )
        return PuertaDTO(
            id="asignaciones_activas",
            titulo="Asignaciones activas",
            severidad="dura",
            ok=True,
            detalle=f"{len(activas)} asignación(es) activa(s) en el alcance seleccionado.",
        )

    # ------------------------------------------------------------------
    # Puerta — horas del plan por asignación (T9, reemplaza asignaturas_con_horas)
    # ------------------------------------------------------------------
    # `Asignatura.horas_semanales` es `Field(default=1, ge=1)`: la vieja
    # puerta `asignaturas_con_horas` comprobaba `horas_semanales < 1`, algo
    # estructuralmente imposible → siempre verde, puerta muerta. Esta mide lo
    # que de verdad importa: cada ASIGNACIÓN resuelve horas > 0 con la misma
    # función que el motor (`_horas_asignacion`). El caso real que detecta:
    # la asignatura referenciada por la asignación ya no está en el catálogo
    # del tenant (huérfana o de otra institución) → global_h=0 → 0 horas.

    def _p_horas_plan_asignaciones(
        self, asignaciones, asig_map: dict, grado_de_grupo: dict, grupos
    ) -> PuertaDTO:
        grupo_map = {g.id: g for g in grupos}
        activas = [a for a in asignaciones if a.activo]
        sin_horas = []
        for a in activas:
            horas = self._horas_asignacion(a, asig_map, grado_de_grupo)
            if horas < 1:
                g = grupo_map.get(a.grupo_id)
                asignatura = asig_map.get(a.asignatura_id)
                nombre_g = g.codigo if g else f"grupo {a.grupo_id}"
                nombre_a = asignatura.nombre if asignatura else f"asignatura {a.asignatura_id}"
                sin_horas.append(f"{nombre_g} — {nombre_a}")
        if sin_horas:
            ejemplos = "; ".join(sin_horas[:5])
            resto = f" y {len(sin_horas) - 5} más" if len(sin_horas) > 5 else ""
            return PuertaDTO(
                id="horas_plan_asignaciones",
                titulo="Horas del plan por asignación",
                severidad="dura",
                ok=False,
                detalle=(
                    f"{len(sin_horas)} asignación(es) resuelven a 0 horas semanales: "
                    f"{ejemplos}{resto}. El motor las generaría sin ninguna hora."
                ),
                fix_ruta="/admin/plan-estudios",
            )
        return PuertaDTO(
            id="horas_plan_asignaciones",
            titulo="Horas del plan por asignación",
            severidad="dura",
            ok=True,
            detalle=f"Las {len(activas)} asignación(es) activas resuelven horas > 0.",
        )

    # ------------------------------------------------------------------
    # Puerta — horas asignadas por grupo vs. slots (T9, reescrita)
    # ------------------------------------------------------------------
    # Antes medía el PLAN de estudios declarado por grado; el motor no
    # genera el plan, genera las ASIGNACIONES. Ahora suma la demanda real
    # (misma resolución de horas que el motor) por grupo y la compara contra
    # los cupos de la plantilla. Cubre también los grupos con grado=None
    # (antes se saltaban con `continue` y quedaban sin validar).

    def _p3_horas_grupo_vs_slots(
        self, grupos, asignaciones, asig_map: dict, grado_de_grupo: dict, plantilla, franjas
    ) -> PuertaDTO:
        ruta = "/academico/generar-horario?tab=plantillas"
        cupos, n_lectivas, n_dias = self._cupos_semana(plantilla, franjas)
        if cupos == 0:
            return PuertaDTO(
                id="horas_grupo_vs_slots",
                titulo="Horas asignadas vs. capacidad de la plantilla",
                severidad="dura",
                ok=False,
                detalle="La plantilla no tiene cupos lectivos (faltan franjas lectivas o días activos).",
                fix_ruta=ruta,
            )
        grupo_map = {g.id: g for g in grupos}
        demanda: dict[int, int] = {}
        for a in asignaciones:
            if not a.activo:
                continue
            demanda[a.grupo_id] = demanda.get(a.grupo_id, 0) + self._horas_asignacion(
                a, asig_map, grado_de_grupo
            )

        problemas = []
        for gid, total in demanda.items():
            if total > cupos:
                g = grupo_map.get(gid)
                nombre = g.codigo if g else f"grupo {gid}"
                problemas.append(f"{nombre}: {total}h")
        if problemas:
            detalle = (
                f"{len(problemas)} grupo(s) tienen más horas asignadas de las que caben en la "
                f"plantilla ({cupos} cupos lectivos/semana = {n_lectivas} franjas × {n_dias} días): "
                + "; ".join(problemas[:3])
            )
            if len(problemas) > 3:
                detalle += f" y {len(problemas) - 3} más"
            detalle += ". Revisa las asignaciones del grupo o amplía la plantilla (más franjas o días)."
            return PuertaDTO(
                id="horas_grupo_vs_slots",
                titulo="Horas asignadas vs. capacidad de la plantilla",
                severidad="dura",
                ok=False,
                detalle=detalle,
                fix_ruta=ruta,
            )
        return PuertaDTO(
            id="horas_grupo_vs_slots",
            titulo="Horas asignadas vs. capacidad de la plantilla",
            severidad="dura",
            ok=True,
            detalle=(
                f"Los {len(demanda)} grupo(s) con asignaciones caben en los {cupos} cupos "
                f"lectivos semanales ({n_lectivas} franjas × {n_dias} días)."
            ),
        )

    # ------------------------------------------------------------------
    # Puerta — docentes con carga_horaria_max no excedida (T10: ahora dura)
    # ------------------------------------------------------------------
    # En el motor la carga horaria máxima del docente es una restricción
    # dura (nunca se coloca una lección que la exceda), no una preferencia;
    # dejarla en "advertencia" permitía declarar `puede_generar()=True` con
    # una config que el motor iba a rechazar o a dejar incompleta.

    def _p4_capacidad_docente(self, asignaciones, asig_map: dict, grado_de_grupo: dict) -> PuertaDTO:
        carga_por_docente: dict[int, int] = {}
        for a in asignaciones:
            if not a.activo:
                continue
            horas = self._horas_asignacion(a, asig_map, grado_de_grupo)
            carga_por_docente[a.usuario_id] = carga_por_docente.get(a.usuario_id, 0) + horas

        excedidos = []
        for uid, carga in carga_por_docente.items():
            usuario = self._usuarios.get_by_id(uid)
            if usuario and usuario.carga_horaria_max and carga > usuario.carga_horaria_max:
                excedidos.append(
                    f"{usuario.nombre_completo or usuario.usuario}: {carga}h > {usuario.carga_horaria_max}h max"
                )
        if excedidos:
            return PuertaDTO(
                id="capacidad_docente",
                titulo="Capacidad de docentes",
                severidad="dura",
                ok=False,
                detalle=f"{len(excedidos)} docente(s) exceden su carga máxima (restricción dura "
                "del generador): " + "; ".join(excedidos[:3]) + ("…" if len(excedidos) > 3 else "") + ".",
                fix_ruta="/admin/asignaciones",
            )
        return PuertaDTO(
            id="capacidad_docente",
            titulo="Capacidad de docentes",
            severidad="dura",
            ok=True,
            detalle="Ningún docente excede su carga horaria máxima.",
        )

    # ------------------------------------------------------------------
    # Puerta — slots disponibles por docente vs. demanda (T11, nueva)
    # ------------------------------------------------------------------
    # `capacidad_docente` compara la demanda contra el tope DECLARADO. Un
    # docente puede estar por debajo de su tope y aun así no caber: si vetó
    # suficientes franjas en su disponibilidad, los slots donde SÍ puede
    # dictar pueden ser menos que sus horas asignadas. Esta puerta lo mide.

    def _p_capacidad_docente_slots(
        self, asignaciones, asig_map: dict, grado_de_grupo: dict, plantilla, franjas
    ) -> PuertaDTO:
        ruta = "/admin/disponibilidad-docente"
        cupos, _n_lectivas, _n_dias = self._cupos_semana(plantilla, franjas)
        if cupos == 0:
            return PuertaDTO(
                id="capacidad_docente_slots",
                titulo="Slots disponibles por docente",
                severidad="dura",
                ok=True,
                detalle="Sin cupos lectivos en la plantilla; ver «Horas asignadas vs. capacidad "
                "de la plantilla».",
            )
        ordenes_lectivos = {f.orden for f in franjas if getattr(f, "es_lectiva", True)}
        dias_activos = set(getattr(plantilla, "dias_activos", None) or [])

        demanda: dict[int, int] = {}
        for a in asignaciones:
            if not a.activo:
                continue
            demanda[a.usuario_id] = demanda.get(a.usuario_id, 0) + self._horas_asignacion(
                a, asig_map, grado_de_grupo
            )

        listar_disp = getattr(self._infra, "listar_disponibilidad_docente", None)
        problemas = []
        for uid, horas in demanda.items():
            vetos = 0
            if callable(listar_disp):
                for fila in listar_disp(uid) or []:
                    if getattr(fila, "disponible", True):
                        continue
                    if fila.dia_semana in dias_activos and fila.franja_orden in ordenes_lectivos:
                        vetos += 1
            slots_disp = max(cupos - vetos, 0)
            usuario = self._usuarios.get_by_id(uid)
            nombre = (usuario.nombre_completo or usuario.usuario) if usuario else f"docente {uid}"
            tope = usuario.carga_horaria_max if usuario else None
            if horas > slots_disp:
                problemas.append(
                    f"{nombre}: {horas}h asignadas > {slots_disp} slot(s) disponibles "
                    f"(de {cupos}, {vetos} vetado(s))"
                )
            elif tope is not None and horas > tope:
                problemas.append(f"{nombre}: {horas}h asignadas > {tope}h máx")

        if problemas:
            ejemplos = "; ".join(problemas[:3])
            resto = f" y {len(problemas) - 3} más" if len(problemas) > 3 else ""
            return PuertaDTO(
                id="capacidad_docente_slots",
                titulo="Slots disponibles por docente",
                severidad="dura",
                ok=False,
                detalle=(
                    f"{len(problemas)} docente(s) no tienen slots suficientes para sus horas "
                    f"asignadas: {ejemplos}{resto}."
                ),
                fix_ruta=ruta,
            )
        return PuertaDTO(
            id="capacidad_docente_slots",
            titulo="Slots disponibles por docente",
            severidad="dura",
            ok=True,
            detalle="Todos los docentes tienen slots suficientes para sus horas asignadas.",
        )

    # ------------------------------------------------------------------
    # Puerta — plan de estudios cubierto por asignaciones
    # ------------------------------------------------------------------

    def _p5_cobertura_asignaciones(self, grupos, asignaciones, asig_map: dict) -> PuertaDTO:
        activas = [a for a in asignaciones if a.activo]
        grupo_map = {g.id: g for g in grupos}

        cubiertos: set[tuple[int, int]] = set()
        for a in activas:
            g = grupo_map.get(a.grupo_id)
            if g and g.grado is not None:
                cubiertos.add((g.grado, a.asignatura_id))

        plan_total = self._plan.listar()
        sin_cubrir = [p for p in plan_total if (p.grado, p.asignatura_id) not in cubiertos]

        if not plan_total:
            return PuertaDTO(
                id="cobertura_asignaciones",
                titulo="Plan de estudios cubierto",
                severidad="advertencia",
                ok=True,
                detalle="No hay plan de estudios definido; se omite la validación de cobertura.",
            )

        if sin_cubrir:
            ejemplos = []
            for p in sin_cubrir[:3]:
                asig = asig_map.get(p.asignatura_id)
                nombre = asig.nombre if asig else f"asignatura {p.asignatura_id}"
                ejemplos.append(f"grado {p.grado} — {nombre}")
            return PuertaDTO(
                id="cobertura_asignaciones",
                titulo="Plan de estudios cubierto",
                severidad="advertencia",
                ok=False,
                detalle=f"{len(sin_cubrir)} combinación(es) del plan sin asignación: "
                + "; ".join(ejemplos)
                + ("…" if len(sin_cubrir) > 3 else "")
                + ".",
                fix_ruta="/admin/asignaciones",
            )

        return PuertaDTO(
            id="cobertura_asignaciones",
            titulo="Plan de estudios cubierto",
            severidad="advertencia",
            ok=True,
            detalle=f"Las {len(plan_total)} combinaciones del plan tienen asignación.",
        )

    # ------------------------------------------------------------------
    # Puerta — disponibilidad coherente con la plantilla (T11, nueva)
    # ------------------------------------------------------------------
    # `GeneradorHorarioService._precargar_disp` ya detecta y cuenta en
    # silencio ("huérfanas") las filas de disponibilidad_docente cuyo
    # día/franja no existen en la plantilla activa: no restringen nada y el
    # docente parece vetado sin estarlo. Esta puerta hace ese conteo visible
    # antes de generar, para que se pueda depurar en vez de descubrirlo en
    # los logs del motor.

    def _p_disponibilidad_coherente(self, asignaciones, plantilla, franjas) -> PuertaDTO:
        ruta = "/admin/disponibilidad-docente"
        dias_activos = set(getattr(plantilla, "dias_activos", None) or [])
        ordenes = {f.orden for f in franjas}
        docentes = {a.usuario_id for a in asignaciones if a.activo}
        listar_disp = getattr(self._infra, "listar_disponibilidad_docente", None)
        huerfanas = 0
        if callable(listar_disp):
            for uid in docentes:
                for fila in listar_disp(uid) or []:
                    if fila.dia_semana not in dias_activos or fila.franja_orden not in ordenes:
                        huerfanas += 1
        if huerfanas:
            return PuertaDTO(
                id="disponibilidad_coherente",
                titulo="Disponibilidad coherente con la plantilla",
                severidad="advertencia",
                ok=False,
                detalle=(
                    f"{huerfanas} fila(s) de disponibilidad docente referencian un día o franja "
                    "fuera de la plantilla activa; el generador las ignora en silencio."
                ),
                fix_ruta=ruta,
            )
        return PuertaDTO(
            id="disponibilidad_coherente",
            titulo="Disponibilidad coherente con la plantilla",
            severidad="advertencia",
            ok=True,
            detalle="La disponibilidad registrada coincide con los días y franjas de la plantilla.",
        )

    # ------------------------------------------------------------------
    # Puerta — plantilla existe y tiene franjas suficientes
    # ------------------------------------------------------------------

    def _p6_plantilla_suficiente(self, plantilla_id: int, plantilla, franjas) -> PuertaDTO:
        ruta = "/academico/generar-horario?tab=plantillas"

        def _falla(detalle: str) -> PuertaDTO:
            return PuertaDTO(
                id="plantilla_suficiente",
                titulo="Plantilla de franjas lista",
                severidad="dura",
                ok=False,
                detalle=detalle,
                fix_ruta=ruta,
            )

        if not plantilla_id or plantilla is None:
            return _falla("No hay una plantilla de franjas seleccionada o no existe.")
        if not franjas:
            return _falla("La plantilla seleccionada no tiene franjas horarias definidas.")
        if not (getattr(plantilla, "dias_activos", None) or []):
            return _falla("La plantilla no tiene días activos configurados.")
        n_lectivas = sum(1 for f in franjas if getattr(f, "es_lectiva", True))
        if n_lectivas == 0:
            return _falla("La plantilla solo tiene franjas de descanso; añade franjas lectivas.")
        return PuertaDTO(
            id="plantilla_suficiente",
            titulo="Plantilla de franjas lista",
            severidad="dura",
            ok=True,
            detalle=(
                f"Plantilla con {n_lectivas} franja(s) lectiva(s) en "
                f"{len(plantilla.dias_activos)} día(s) activo(s)."
            ),
        )

    # ------------------------------------------------------------------
    # Puerta — salas disponibles para tipos requeridos
    # ------------------------------------------------------------------

    def _p7_salas_suficientes(self, asignaturas, salas) -> PuertaDTO:
        if not salas:
            return PuertaDTO(
                id="salas_suficientes",
                titulo="Salas disponibles",
                severidad="advertencia",
                ok=True,
                detalle="No hay salas registradas; el generador asignará sin restricción de sala.",
                fix_ruta="/admin/salas",
            )
        tipos_requeridos = {
            a.tipo_sala_requerido for a in asignaturas if getattr(a, "tipo_sala_requerido", None)
        }
        tipos_disponibles = {s.tipo for s in salas}
        faltantes = tipos_requeridos - tipos_disponibles
        if faltantes:
            return PuertaDTO(
                id="salas_suficientes",
                titulo="Salas disponibles",
                severidad="advertencia",
                ok=False,
                detalle=f"Tipos de sala requeridos sin sala disponible: {', '.join(sorted(faltantes))}.",
                fix_ruta="/admin/salas",
            )
        return PuertaDTO(
            id="salas_suficientes",
            titulo="Salas disponibles",
            severidad="advertencia",
            ok=True,
            detalle=f"{len(salas)} sala(s) disponibles, tipos requeridos cubiertos.",
        )

    # ------------------------------------------------------------------
    # Puerta — aulas base (sala_id) únicas por grupo (horario_01, T3)
    # ------------------------------------------------------------------
    # Sin esta puerta, dos grupos con la misma aula base pasan desapercibidos
    # hasta que el generador coloca un laboratorio sobre un aula que en
    # realidad está ocupada por el otro grupo a esa hora (ver T2 en
    # generador_horario_service._colocar).

    def _p8_aulas_base_unicas(self, grupos) -> PuertaDTO:
        por_sala: dict[int, list[str]] = {}
        for g in grupos:
            sid = getattr(g, "sala_id", None)
            if sid is None:
                continue
            por_sala.setdefault(sid, []).append(g.codigo)

        afectados = [
            f"{', '.join(codigos)} (aula {sid})"
            for sid, codigos in por_sala.items()
            if len(codigos) > 1
        ]
        if afectados:
            ejemplos = "; ".join(afectados[:3])
            resto = f" y {len(afectados) - 3} más" if len(afectados) > 3 else ""
            return PuertaDTO(
                id="aulas_base_unicas",
                titulo="Aulas base sin duplicar",
                severidad="advertencia",
                ok=False,
                detalle=(
                    f"{len(afectados)} aula(s) base compartidas entre grupos: "
                    f"{ejemplos}{resto}. El generador puede colocar un laboratorio "
                    "sobre un aula que ya está ocupada como salón de otro grupo."
                ),
                fix_ruta="/admin/salas",
            )
        return PuertaDTO(
            id="aulas_base_unicas",
            titulo="Aulas base sin duplicar",
            severidad="advertencia",
            ok=True,
            detalle="Cada grupo con aula asignada tiene un aula base distinta.",
        )

    # ------------------------------------------------------------------
    # Puerta — grupos con grado asignado (T11, nueva)
    # ------------------------------------------------------------------
    # Un grupo con grado=None no tiene plan de estudios aplicable; el motor
    # cae al fallback de horas globales de la asignatura (`_horas_de`) y la
    # cobertura del plan (P8) ni siquiera lo evalúa. No bloquea la
    # generación, pero explica por qué esos grupos no aparecen cubiertos.

    def _p_grupos_con_grado(self, grupos) -> PuertaDTO:
        sin_grado = [g for g in grupos if g.grado is None]
        if sin_grado:
            nombres = ", ".join(g.codigo for g in sin_grado[:5])
            resto = f" y {len(sin_grado) - 5} más" if len(sin_grado) > 5 else ""
            return PuertaDTO(
                id="grupos_con_grado",
                titulo="Grupos con grado asignado",
                severidad="advertencia",
                ok=False,
                detalle=(
                    f"{len(sin_grado)} grupo(s) sin grado: {nombres}{resto}. El plan de estudios "
                    "no aplica para ellos; el motor usará las horas globales de la asignatura."
                ),
                fix_ruta="/admin/grupos",
            )
        return PuertaDTO(
            id="grupos_con_grado",
            titulo="Grupos con grado asignado",
            severidad="advertencia",
            ok=True,
            detalle=f"Los {len(grupos)} grupo(s) tienen grado asignado.",
        )


__all__ = ["PreparacionHorarioService", "PuertaDTO", "ReportePreparacionDTO"]
