"""
HorarioService
==============
Servicio de dominio para la gestión de bloques horarios.

Valida cruces (docente, grupo, sala) y topes (horas_semanales,
carga_horaria_max del docente) antes de insertar o actualizar.
"""

from __future__ import annotations

from src.domain.models.asignacion import FiltroAsignacionesDTO
from src.domain.models.infraestructura import (
    CupoDTO,
    FilaReporteDTO,
    Horario,
    HorarioInfo,
    NuevoHorarioDTO,
    ReporteLoteDTO,
    ResultadoLoteDTO,
)
from src.domain.ports.asignacion_repo import IAsignacionRepository
from src.domain.ports.infraestructura_repo import IInfraestructuraRepository
from src.services.contexto_tenant import institucion_actual
from src.services.solo_lectura import requiere_escritura

# ---------------------------------------------------------------------------
# Constantes y helpers de módulo
# ---------------------------------------------------------------------------

COLUMNAS_HORARIO = [
    "asignacion_id",
    "grupo",
    "asignatura",
    "docente",
    "dia_semana",
    "hora_inicio",
    "hora_fin",
    "sala",
]

# Valores de "sala" que NO representan un espacio físico exclusivo: no deben
# generar cruce en el oráculo aunque coincidan en día/hora. "Aula" es el
# genérico legacy; "Por asignar" es lo que usa el generador cuando una clase
# con tipo_sala_requerido no consiguió una sala real (paso_17 T1).
SALAS_NO_EXCLUSIVAS: frozenset[str] = frozenset({"", "Aula", "Por asignar"})


def _dia_str(dia) -> str:
    return dia.value if hasattr(dia, "value") else str(dia)


def _hora_str(hora) -> str:
    return hora.strftime("%H:%M") if hasattr(hora, "strftime") else str(hora)


def _normalizar_hora(h: str) -> str:
    """'8:00' → '08:00', '14:5' → '14:05'. Mantiene el original si no parsea."""
    partes = h.split(":")
    if len(partes) >= 2:
        try:
            return f"{int(partes[0]):02d}:{int(partes[1]):02d}"
        except ValueError:
            pass
    return h


def _validar_intervalo(hora_inicio: str, hora_fin: str) -> tuple[str, str]:
    """Normaliza un intervalo HH:MM y exige que su inicio sea anterior al fin."""
    def _hora_valida(valor: str) -> str:
        partes = valor.strip().split(":")
        if len(partes) != 2:
            raise ValueError("Use el formato HH:MM.")
        try:
            hora, minuto = int(partes[0]), int(partes[1])
        except ValueError as exc:
            raise ValueError("Use el formato HH:MM.") from exc
        if not 0 <= hora <= 23 or not 0 <= minuto <= 59:
            raise ValueError("La hora está fuera de rango.")
        return f"{hora:02d}:{minuto:02d}"

    inicio = _hora_valida(hora_inicio)
    fin = _hora_valida(hora_fin)
    if inicio >= fin:
        raise ValueError("hora_inicio debe ser anterior a hora_fin.")
    return inicio, fin


class HorarioService:
    def __init__(
        self,
        infra_repo: IInfraestructuraRepository,
        asignacion_repo: IAsignacionRepository,
        usuario_repo,
        plan_svc=None,
    ):
        """Inyecta los repos de infraestructura, asignación y usuario, más el
        servicio de plan de estudios (opcional) para los topes de horas."""
        self._infra = infra_repo
        self._asig = asignacion_repo
        self._usuario = usuario_repo
        self._plan = plan_svc

    def _horas_max_materia(self, asig, asignatura) -> int | None:
        """Tope de bloques de una (grupo, asignatura): horas del plan del grado
        del grupo, con fallback a las horas globales de la asignatura."""
        if self._plan is not None and asig is not None:
            grupo = self._infra.get_grupo(asig.grupo_id)
            if grupo is not None and grupo.grado is not None:
                return self._plan.horas_de(grupo.grado, asig.asignatura_id)
        return asignatura.horas_semanales if asignatura is not None else None

    # ------------------------------------------------------------------ #
    # Escritura                                                            #
    # ------------------------------------------------------------------ #

    @requiere_escritura
    def crear_bloque(
        self,
        escenario_id: int,
        asignacion_id: int,
        dia: str,
        hora_inicio: str,
        hora_fin: str,
        sala: str = "Aula",
    ) -> Horario:
        """Crea un bloque de horario tras validar cruces (docente, grupo, sala)
        y topes de horas de la materia y del docente."""
        asig = self._resolver_asignacion(asignacion_id)
        hora_inicio, hora_fin = _validar_intervalo(hora_inicio, hora_fin)
        self._validar_cruces(escenario_id, dia, hora_inicio, hora_fin, asig, sala)
        self._validar_topes(escenario_id, asig)
        dto = NuevoHorarioDTO(
            escenario_id=escenario_id,
            asignacion_id=asignacion_id,
            grupo_id=asig.grupo_id,
            asignatura_id=asig.asignatura_id,
            usuario_id=asig.usuario_id,
            dia_semana=dia,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            sala=sala,
        )
        return self._infra.guardar_horario(dto.to_horario())

    @requiere_escritura
    def mover_bloque(
        self,
        horario_id: int,
        dia: str,
        hora_inicio: str,
        hora_fin: str,
    ) -> Horario:
        """Mueve un bloque a otro día/hora (misma sala) validando cruces."""
        horario = self._infra.get_horario(horario_id)
        if horario is None:
            raise ValueError("Bloque no encontrado.")
        asig = self._resolver_asignacion(horario.asignacion_id)
        hora_inicio, hora_fin = _validar_intervalo(hora_inicio, hora_fin)
        self._validar_cruces(
            horario.escenario_id,
            dia,
            hora_inicio,
            hora_fin,
            asig,
            horario.sala,
            excluir_id=horario_id,
        )
        updated = Horario(
            **{
                **horario.model_dump(),
                "dia_semana": dia,
                "hora_inicio": hora_inicio,
                "hora_fin": hora_fin,
            }
        )
        return self._infra.actualizar_horario(updated)

    @requiere_escritura
    def actualizar_bloque(
        self,
        horario_id: int,
        *,
        dia: str,
        hora_inicio: str,
        hora_fin: str,
        sala: str,
    ) -> Horario:
        """Actualiza día, horas y sala de un bloque validando cruces."""
        horario = self._infra.get_horario(horario_id)
        if horario is None:
            raise ValueError("Bloque no encontrado.")
        asig = self._resolver_asignacion(horario.asignacion_id)
        hora_inicio, hora_fin = _validar_intervalo(hora_inicio, hora_fin)
        self._validar_cruces(
            horario.escenario_id,
            dia,
            hora_inicio,
            hora_fin,
            asig,
            sala,
            excluir_id=horario_id,
        )
        updated = Horario(
            **{
                **horario.model_dump(),
                "dia_semana": dia,
                "hora_inicio": hora_inicio,
                "hora_fin": hora_fin,
                "sala": sala,
            }
        )
        return self._infra.actualizar_horario(updated)

    @requiere_escritura
    def eliminar_bloque(self, horario_id: int) -> bool:
        """Elimina un bloque de horario (delegado al repositorio)."""
        return self._infra.eliminar_horario(horario_id)

    # ------------------------------------------------------------------ #
    # Consultas de bloques por periodo (mejora_05 — dueño canónico R3)     #
    # ------------------------------------------------------------------ #

    def listar_horario_grupo(self, grupo_id: int, periodo_id: int) -> list[HorarioInfo]:
        """Lista el horario de un grupo en un periodo (delegado al repositorio)."""
        return self._infra.listar_horario_grupo(grupo_id, periodo_id)

    # ------------------------------------------------------------------ #
    # Consultas de cupo                                                    #
    # ------------------------------------------------------------------ #

    def disponibilidad_asignacion(self, escenario_id: int, asignacion_id: int) -> CupoDTO:
        """Cupo de bloques de una asignación: usados vs. horas de la asignatura."""
        asig = self._resolver_asignacion(asignacion_id)
        asignatura = self._get_asignatura(asig.asignatura_id)
        usadas = self._infra.contar_bloques_asignacion(escenario_id, asignacion_id)
        return CupoDTO(
            usadas=usadas,
            maximas=self._horas_max_materia(asig, asignatura),
        )

    def disponibilidad_docente(self, escenario_id: int, usuario_id: int) -> CupoDTO:
        """Cupo de bloques de un docente: usados vs. su carga horaria máxima."""
        usadas = self._infra.contar_bloques_docente(escenario_id, usuario_id)
        max_horas = self._usuario.carga_horaria_max(usuario_id)
        return CupoDTO(usadas=usadas, maximas=max_horas)

    def plantilla_filas(self, periodo_id: int) -> list[dict]:
        """Genera filas prellenadas (sin horario) para cada asignación del periodo."""
        asignaciones = self._asig.listar_info(FiltroAsignacionesDTO(periodo_id=periodo_id))
        return [
            {
                "asignacion_id": a.asignacion_id,
                "grupo": a.grupo_codigo,
                "asignatura": a.asignatura_nombre,
                "docente": a.docente_nombre,
                "dia_semana": "",
                "hora_inicio": "",
                "hora_fin": "",
                "sala": "Aula",
            }
            for a in asignaciones
        ]

    def filas_exportables(self, escenario_id: int, grupo_id: int | None = None) -> list[dict]:
        """Exporta los bloques de un escenario como filas de dict con COLUMNAS_HORARIO."""
        bloques = self._infra.listar_horario_escenario(escenario_id)
        if grupo_id is not None:
            bloques = [b for b in bloques if b.grupo_id == grupo_id]
        return [
            {
                "asignacion_id": b.asignacion_id or "",
                "grupo": b.grupo_codigo,
                "asignatura": b.asignatura_nombre,
                "docente": b.docente_nombre,
                "dia_semana": _dia_str(b.dia_semana),
                "hora_inicio": _hora_str(b.hora_inicio),
                "hora_fin": _hora_str(b.hora_fin),
                "sala": b.sala or "Aula",
            }
            for b in bloques
        ]

    # ------------------------------------------------------------------ #
    # Datos de parrilla visual (paso_15e)                                  #
    # ------------------------------------------------------------------ #

    def datos_parrilla(self, escenario_id: int) -> dict:
        """
        Devuelve la estructura UI-agnóstica para pintar la parrilla visual
        de un escenario: días activos, franjas (desde la plantilla activa
        o derivadas de los bloques) y celdas enriquecidas con área/color.

        Estructura:
            {
              "dias":    list[str],
              "franjas": list[{orden, etiqueta, hora_inicio, hora_fin, lectiva}],
              "celdas":  list[{grupo_id, grupo_codigo, asignatura_id,
                               asignatura_nombre, area_id, area_color,
                               usuario_id, docente_nombre, dia_semana,
                               hora_inicio, hora_fin, sala}],
            }
        """
        # Orden canónico Lunes→Sábado
        orden_dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
        idx_dia = {d: i for i, d in enumerate(orden_dias)}

        bloques = self._infra.listar_horario_escenario(escenario_id)

        # --- Caché de áreas (asignatura_id → (area_id, area_color, area_nombre)) ---
        cache_asig: dict[int, tuple[int | None, str | None, str | None]] = {}
        cache_area: dict[int, tuple[str | None, str | None]] = {}

        def _resolver_area(
            asignatura_id: int,
        ) -> tuple[int | None, str | None, str | None]:
            if asignatura_id in cache_asig:
                return cache_asig[asignatura_id]
            area_id: int | None = None
            area_color: str | None = None
            area_nombre: str | None = None
            asignatura = self._infra.get_asignatura(asignatura_id)
            if asignatura is not None:
                area_id = asignatura.area_id
            if area_id is not None:
                if area_id not in cache_area:
                    area = self._infra.get_area(area_id)
                    cache_area[area_id] = (
                        area.color if area else None,
                        area.nombre if area else None,
                    )
                area_color, area_nombre = cache_area[area_id]
            cache_asig[asignatura_id] = (area_id, area_color, area_nombre)
            return area_id, area_color, area_nombre

        # --- Celdas ---
        celdas: list[dict] = []
        dias_presentes: set[str] = set()
        pares_horas: set[tuple[str, str]] = set()

        for b in bloques:
            dia = _dia_str(b.dia_semana)
            hi = _hora_str(b.hora_inicio)
            hf = _hora_str(b.hora_fin)
            dias_presentes.add(dia)
            pares_horas.add((hi, hf))
            area_id, area_color, area_nombre = _resolver_area(b.asignatura_id)
            celdas.append(
                {
                    "id": b.id,
                    "asignacion_id": b.asignacion_id,
                    "grupo_id": b.grupo_id,
                    "grupo_codigo": b.grupo_codigo,
                    "asignatura_id": b.asignatura_id,
                    "asignatura_nombre": b.asignatura_nombre,
                    "area_id": area_id,
                    "area_color": area_color,
                    "area_nombre": area_nombre,
                    "usuario_id": b.usuario_id,
                    "docente_nombre": b.docente_nombre,
                    "dia_semana": dia,
                    "hora_inicio": hi,
                    "hora_fin": hf,
                    "sala": b.sala or "Aula",
                }
            )

        # --- Franjas: de la plantilla que encaja con los bloques del escenario ---
        # Multi-tenant (paso_32, T5): `self._infra` es el repo (sin scope). La
        # parrilla es de un grupo/escenario ya scopeado, así que la rejilla de
        # franjas debe venir de una plantilla de la MISMA institución.
        #
        # Antes se pedía siempre la plantilla activa de jornada "UNICA". Un
        # escenario generado con una plantilla de otra jornada (o de otro horario
        # de timbres) pintaba una rejilla cuyas horas no coincidían con las de
        # ningún bloque: la parrilla salía VACÍA aunque el escenario tuviera sus
        # 360 bloques. La rejilla tiene que describir los datos que muestra, así
        # que se elige la plantilla cuyas franjas cubren las horas de los bloques.
        franjas: list[dict] = []
        plantilla = None

        def _cubre(candidata) -> bool:
            """¿Las franjas de la plantilla cubren todas las horas de los bloques?"""
            if candidata is None or candidata.id is None:
                return False
            if not pares_horas:
                return True
            horas_plantilla = {
                (fr.hora_inicio, fr.hora_fin) for fr in self._infra.listar_franjas(candidata.id)
            }
            return pares_horas <= horas_plantilla

        inst = institucion_actual()
        try:
            activa = self._infra.get_plantilla_activa("UNICA", institucion_id=inst)
        except (LookupError, ValueError, TypeError):
            activa = None
        if _cubre(activa):
            plantilla = activa
        else:
            # Buscar entre las plantillas de la institución la que sí encaje.
            try:
                candidatas = self._infra.listar_plantillas_franja(inst if inst is not None else "*")
            except (LookupError, ValueError, TypeError):
                candidatas = []
            # Con varias compatibles, gana la activa.
            for cand in sorted(candidatas, key=lambda p: not getattr(p, "activa", False)):
                if _cubre(cand):
                    plantilla = cand
                    break

        if plantilla is not None and plantilla.id is not None:
            franjas_plantilla = self._infra.listar_franjas(plantilla.id)
            for fr in franjas_plantilla:
                franjas.append(
                    {
                        "orden": fr.orden,
                        "etiqueta": fr.etiqueta or f"{fr.hora_inicio}–{fr.hora_fin}",
                        "hora_inicio": fr.hora_inicio,
                        "hora_fin": fr.hora_fin,
                        "lectiva": fr.es_lectiva,
                    }
                )

        if not franjas:
            # Derivar de las parejas distintas (hora_inicio, hora_fin) de los bloques
            for orden, (hi, hf) in enumerate(sorted(pares_horas), start=1):
                franjas.append(
                    {
                        "orden": orden,
                        "etiqueta": f"{hi}–{hf}",
                        "hora_inicio": hi,
                        "hora_fin": hf,
                        "lectiva": True,
                    }
                )

        # --- Días: de la plantilla si existe, si no los presentes en bloques ---
        if plantilla is not None and plantilla.dias_activos:
            dias = [d for d in orden_dias if d in set(plantilla.dias_activos)]
        else:
            dias = sorted(dias_presentes, key=lambda d: idx_dia.get(d, 99))

        return {"dias": dias, "franjas": franjas, "celdas": celdas}

    def metricas_parrilla(self, escenario_id: int) -> dict:
        """
        Agregados del escenario para el panel de métricas de la parrilla.

        Devuelve:
            total_bloques  — nº de celdas (bloques colocados).
            n_grupos       — grupos distintos con al menos un bloque.
            n_docentes     — docentes distintos.
            n_salas        — salas distintas.
            huecos_grupo   — suma de ventanas vacías intra-día por grupo,
                             usando el índice compacto de franjas lectivas
                             (un recreo entre clases NO cuenta como hueco),
                             igual que el generador.
            ocupacion_pct  — bloques colocados ÷ capacidad teórica × 100,
                             redondeado. Capacidad = n_grupos × nº franjas
                             lectivas × nº días activos. 0 si no hay capacidad.
        """
        datos = self.datos_parrilla(escenario_id)
        celdas = datos["celdas"]
        franjas = datos["franjas"]
        dias = datos["dias"]

        grupos = {c["grupo_id"] for c in celdas}
        docentes = {c["usuario_id"] for c in celdas}
        salas = {c["sala"] for c in celdas}

        # Índice compacto de franjas lectivas (orden → idx 0..L-1).
        franjas_lectivas = sorted(
            (f for f in franjas if f["lectiva"]),
            key=lambda f: f["orden"],
        )
        hi_a_idx = {f["hora_inicio"]: idx for idx, f in enumerate(franjas_lectivas)}
        n_franjas_lectivas = len(franjas_lectivas)

        # Huecos por grupo: ventanas vacías intra-día usando idx compacto.
        idx_grupo_dia: dict[tuple, list[int]] = {}
        for c in celdas:
            idx = hi_a_idx.get(c["hora_inicio"])
            if idx is None:
                continue
            idx_grupo_dia.setdefault((c["grupo_id"], c["dia_semana"]), []).append(idx)

        huecos_grupo = 0
        for indices in idx_grupo_dia.values():
            if not indices:
                continue
            hueco = (max(indices) - min(indices) + 1) - len(indices)
            if hueco > 0:
                huecos_grupo += hueco

        capacidad = len(grupos) * n_franjas_lectivas * len(dias)
        ocupacion_pct = round(len(celdas) / capacidad * 100) if capacidad else 0

        return {
            "total_bloques": len(celdas),
            "n_grupos": len(grupos),
            "n_docentes": len(docentes),
            "n_salas": len(salas),
            "huecos_grupo": huecos_grupo,
            "ocupacion_pct": ocupacion_pct,
        }

    def areas_parrilla(self, escenario_id: int) -> list[dict]:
        """
        Áreas presentes en el escenario, deduplicadas y ordenadas por nombre.

        Devuelve list[{area_id, area_nombre, color}]. Las celdas sin área
        (area_id None) se omiten. El nombre/color se toma de las celdas de
        `datos_parrilla` (que ya resuelven el área desde la asignatura).
        """
        datos = self.datos_parrilla(escenario_id)
        areas: dict[int, dict] = {}
        for c in datos["celdas"]:
            area_id = c.get("area_id")
            if area_id is None or area_id in areas:
                continue
            areas[area_id] = {
                "area_id": area_id,
                "area_nombre": c.get("area_nombre") or f"Área {area_id}",
                "color": c.get("area_color"),
            }
        return sorted(areas.values(), key=lambda a: str(a["area_nombre"]))

    # ------------------------------------------------------------------ #
    # Helpers privados                                                     #
    # ------------------------------------------------------------------ #

    def _resolver_asignacion(self, asignacion_id: int):
        asig = self._asig.get_by_id(asignacion_id)
        if asig is None:
            raise ValueError("La asignación no existe o está inactiva.")
        if not asig.activo:
            raise ValueError("La asignación no existe o está inactiva.")
        return asig

    def _validar_cruces(
        self,
        escenario_id: int,
        dia: str,
        hora_inicio: str,
        hora_fin: str,
        asig,
        sala: str,
        excluir_id: int | None = None,
    ) -> None:
        kwargs = {"excluir_horario_id": excluir_id} if excluir_id else {}
        if self._infra.existe_cruce(
            escenario_id, dia, hora_inicio, hora_fin, usuario_id=asig.usuario_id, **kwargs
        ):
            raise ValueError("El docente ya tiene un bloque en ese horario.")
        if self._infra.existe_cruce(
            escenario_id, dia, hora_inicio, hora_fin, grupo_id=asig.grupo_id, **kwargs
        ):
            raise ValueError("El grupo ya tiene un bloque en ese horario.")
        if (
            sala
            and sala != "Aula"
            and self._infra.existe_cruce(
                escenario_id, dia, hora_inicio, hora_fin, sala=sala, **kwargs
            )
        ):
            raise ValueError(f"La sala '{sala}' ya está ocupada en ese horario.")

    def _validar_topes(self, escenario_id: int, asig) -> None:
        asignatura = self._get_asignatura(asig.asignatura_id)
        horas_max = self._horas_max_materia(asig, asignatura)
        if horas_max is not None:
            usadas = self._infra.contar_bloques_asignacion(escenario_id, asig.id)
            if usadas + 1 > horas_max:
                raise ValueError(
                    f"La materia ya tiene {usadas} bloque(s) asignado(s); límite: {horas_max}."
                )
        max_docente = self._usuario.carga_horaria_max(asig.usuario_id)
        if max_docente is not None:
            usadas_doc = self._infra.contar_bloques_docente(escenario_id, asig.usuario_id)
            if usadas_doc + 1 > max_docente:
                raise ValueError(
                    f"El docente superaría su carga máxima de {max_docente} bloques/semana."
                )

    def analizar_lote(
        self,
        escenario_id: int,
        periodo_id: int,
        filas: list[dict],
        salas_bloquean: bool = True,
    ) -> ReporteLoteDTO:
        """Analiza un lote de filas como escenario virtual (sin persistir):
        valida asignación, campos obligatorios, cruces (docente/grupo/sala) y
        topes de materia y docente, y devuelve un reporte fila por fila.

        `salas_bloquean=False` (paso_17 T1, usado por el generador): un cruce
        de sala NO invalida la fila (ok sigue True); se registra como aviso
        en `ReporteLoteDTO.avisos`. Los cruces de docente y grupo siguen
        siendo duros siempre, sin importar este parámetro."""
        resultado: list[FilaReporteDTO] = []
        virtual: list[dict] = []
        avisos: list[str] = []

        existentes = self._infra.listar_horario_escenario(escenario_id)
        for b in existentes:
            dia = _dia_str(b.dia_semana)
            hi = _hora_str(b.hora_inicio)
            hf = _hora_str(b.hora_fin)
            virtual.append(
                {
                    "usuario_id": b.usuario_id,
                    "grupo_id": b.grupo_id,
                    "sala": b.sala,
                    "dia": dia,
                    "hora_inicio": hi,
                    "hora_fin": hf,
                    "asignacion_id": b.asignacion_id,
                    "es_lote": False,
                }
            )

        def _solapan(hi1: str, hf1: str, hi2: str, hf2: str) -> bool:
            return hi1 < hf2 and hf1 > hi2

        for i, fila in enumerate(filas):
            ok = True
            motivo = None

            try:
                asig_id = int(fila.get("asignacion_id") or 0)
            except (ValueError, TypeError):
                asig_id = 0

            asig = self._asig.get_by_id(asig_id) if asig_id else None
            if asig is None or not asig.activo:
                resultado.append(
                    FilaReporteDTO(
                        indice=i,
                        ok=False,
                        motivo="Asignación no válida o inactiva.",
                        resumen=str(fila),
                    )
                )
                continue

            if asig.periodo_id != periodo_id:
                resultado.append(
                    FilaReporteDTO(
                        indice=i,
                        ok=False,
                        motivo="La asignación no pertenece al período indicado.",
                        resumen=str(fila),
                    )
                )
                continue

            dia = str(fila.get("dia_semana") or fila.get("dia") or "").strip()
            hora_inicio = str(fila.get("hora_inicio") or "").strip()
            hora_fin = str(fila.get("hora_fin") or "").strip()
            sala = str(fila.get("sala") or "Aula").strip() or "Aula"

            if not dia or not hora_inicio or not hora_fin:
                resultado.append(
                    FilaReporteDTO(
                        indice=i,
                        ok=False,
                        motivo="Campos obligatorios faltantes (dia_semana, hora_inicio, hora_fin).",
                        resumen=str(fila),
                    )
                )
                continue

            try:
                hora_inicio, hora_fin = _validar_intervalo(hora_inicio, hora_fin)
            except ValueError as exc:
                resultado.append(
                    FilaReporteDTO(
                        indice=i,
                        ok=False,
                        motivo=f"Horario inválido: {exc}",
                        resumen=str(fila),
                    )
                )
                continue

            asignatura = self._get_asignatura(asig.asignatura_id)

            # Cruces contra virtual
            for v in virtual:
                if v["dia"] != dia:
                    continue
                if not _solapan(hora_inicio, hora_fin, v["hora_inicio"], v["hora_fin"]):
                    continue
                if v["usuario_id"] == asig.usuario_id:
                    ok = False
                    motivo = "Cruce: el docente ya tiene bloque en ese horario."
                    break
                if v["grupo_id"] == asig.grupo_id:
                    ok = False
                    motivo = "Cruce: el grupo ya tiene bloque en ese horario."
                    break
                if sala not in SALAS_NO_EXCLUSIVAS and v.get("sala") == sala:
                    if salas_bloquean:
                        ok = False
                        motivo = f"Cruce: sala '{sala}' ya ocupada en ese horario."
                        break
                    avisos.append(
                        f"Fila {i}: sala '{sala}' ya ocupada en ese horario (no bloquea)."
                    )

            # Tope materia
            if ok:
                horas_max = self._horas_max_materia(asig, asignatura)
                if horas_max is not None:
                    usadas_bd = self._infra.contar_bloques_asignacion(escenario_id, asig.id)
                    usadas_lote = sum(
                        1 for v in virtual if v.get("asignacion_id") == asig.id and v.get("es_lote")
                    )
                    if usadas_bd + usadas_lote + 1 > horas_max:
                        ok = False
                        motivo = f"Tope materia: {usadas_bd + usadas_lote}/{horas_max} bloques."

            # Tope docente
            if ok:
                max_doc = self._usuario.carga_horaria_max(asig.usuario_id)
                if max_doc is not None:
                    usadas_doc_bd = self._infra.contar_bloques_docente(
                        escenario_id, asig.usuario_id
                    )
                    usadas_doc_lote = sum(
                        1
                        for v in virtual
                        if v.get("usuario_id") == asig.usuario_id and v.get("es_lote")
                    )
                    if usadas_doc_bd + usadas_doc_lote + 1 > max_doc:
                        ok = False
                        motivo = f"Tope docente: superaría {max_doc} bloques/semana."

            asig_nombre = getattr(asignatura, "nombre", str(asig_id))
            resumen = f"{dia} {hora_inicio}–{hora_fin} | {asig_nombre}"
            resultado.append(FilaReporteDTO(indice=i, ok=ok, motivo=motivo, resumen=resumen))

            if ok:
                virtual.append(
                    {
                        "usuario_id": asig.usuario_id,
                        "grupo_id": asig.grupo_id,
                        "sala": sala,
                        "dia": dia,
                        "hora_inicio": hora_inicio,
                        "hora_fin": hora_fin,
                        "asignacion_id": asig.id,
                        "es_lote": True,
                    }
                )

        return ReporteLoteDTO(filas=resultado, avisos=avisos)

    @requiere_escritura
    def aplicar_lote(
        self,
        escenario_id: int,
        periodo_id: int,
        filas: list[dict],
        solo_validas: bool = False,
        salas_bloquean: bool = True,
    ) -> ResultadoLoteDTO:
        """Persiste un lote de bloques: lo analiza y, si es válido (o si
        `solo_validas`), crea de forma masiva solo las filas OK; devuelve el
        conteo de creados/omitidos junto con el reporte.

        `salas_bloquean` se propaga a `analizar_lote` (ver su docstring)."""
        reporte = self.analizar_lote(escenario_id, periodo_id, filas, salas_bloquean=salas_bloquean)

        if not solo_validas and not reporte.todo_ok:
            return ResultadoLoteDTO(creados=0, omitidos=len(filas), reporte=reporte)

        filas_ok = [(filas[f.indice], f) for f in reporte.filas if f.ok]
        if not filas_ok:
            return ResultadoLoteDTO(creados=0, omitidos=len(filas), reporte=reporte)

        horarios_nuevos = []
        for fila_dict, _ in filas_ok:
            asig_id = int(fila_dict.get("asignacion_id") or 0)
            asig = self._asig.get_by_id(asig_id)
            dia = str(fila_dict.get("dia_semana") or fila_dict.get("dia") or "")
            hora_inicio, hora_fin = _validar_intervalo(
                str(fila_dict.get("hora_inicio") or ""),
                str(fila_dict.get("hora_fin") or ""),
            )
            sala = str(fila_dict.get("sala") or "Aula") or "Aula"
            horarios_nuevos.append(
                Horario(
                    escenario_id=escenario_id,
                    asignacion_id=asig_id,
                    grupo_id=asig.grupo_id,
                    asignatura_id=asig.asignatura_id,
                    usuario_id=asig.usuario_id,
                    dia_semana=dia,
                    hora_inicio=hora_inicio,
                    hora_fin=hora_fin,
                    sala=sala,
                    periodo_id=None,
                )
            )

        creados = self._infra.crear_bloques_masivo(horarios_nuevos)
        omitidos = len(filas) - creados
        return ResultadoLoteDTO(creados=creados, omitidos=omitidos, reporte=reporte)

    def _get_asignatura(self, asignatura_id: int):
        return self._infra.get_asignatura(asignatura_id)


__all__ = ["COLUMNAS_HORARIO", "HorarioService"]
