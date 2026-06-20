"""
HorarioService
==============
Servicio de dominio para la gestión de bloques horarios.

Valida cruces (docente, grupo, sala) y topes (horas_semanales,
carga_horaria_max del docente) antes de insertar o actualizar.
"""
from __future__ import annotations

from src.services.solo_lectura import requiere_escritura

from src.domain.models.infraestructura import (
    CupoDTO,
    Horario,
    NuevoHorarioDTO,
)
from src.domain.ports.infraestructura_repo import IInfraestructuraRepository
from src.domain.ports.asignacion_repo import IAsignacionRepository
from src.domain.models.asignacion import FiltroAsignacionesDTO


# ---------------------------------------------------------------------------
# Constantes y helpers de módulo
# ---------------------------------------------------------------------------

COLUMNAS_HORARIO = [
    "asignacion_id", "grupo", "asignatura", "docente",
    "dia_semana", "hora_inicio", "hora_fin", "sala",
]


def _dia_str(dia) -> str:
    return dia.value if hasattr(dia, "value") else str(dia)


def _hora_str(hora) -> str:
    return hora.strftime("%H:%M") if hasattr(hora, "strftime") else str(hora)


class HorarioService:
    def __init__(
        self,
        infra_repo: IInfraestructuraRepository,
        asignacion_repo: IAsignacionRepository,
        usuario_repo,
        plan_svc=None,
    ):
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
        return getattr(asignatura, "horas_semanales", None)

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
        asig = self._resolver_asignacion(asignacion_id)
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

    def mover_bloque(
        self,
        horario_id: int,
        dia: str,
        hora_inicio: str,
        hora_fin: str,
    ) -> Horario:
        horario = self._infra.get_horario(horario_id)
        if horario is None:
            raise ValueError("Bloque no encontrado.")
        asig = self._resolver_asignacion(horario.asignacion_id)
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
        horario = self._infra.get_horario(horario_id)
        if horario is None:
            raise ValueError("Bloque no encontrado.")
        asig = self._resolver_asignacion(horario.asignacion_id)
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
        return self._infra.eliminar_horario(horario_id)

    # ------------------------------------------------------------------ #
    # Consultas de cupo                                                    #
    # ------------------------------------------------------------------ #

    def disponibilidad_asignacion(
        self, escenario_id: int, asignacion_id: int
    ) -> CupoDTO:
        asig = self._resolver_asignacion(asignacion_id)
        asignatura = self._get_asignatura(asig.asignatura_id)
        usadas = self._infra.contar_bloques_asignacion(escenario_id, asignacion_id)
        return CupoDTO(
            usadas=usadas,
            maximas=getattr(asignatura, "horas_semanales", None),
        )

    def disponibilidad_docente(
        self, escenario_id: int, usuario_id: int
    ) -> CupoDTO:
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
                "asignacion_id": getattr(b, "asignacion_id", "") or "",
                "grupo": getattr(b, "grupo_codigo", None) or getattr(b, "grupo_nombre", None) or str(b.grupo_id),
                "asignatura": b.asignatura_nombre,
                "docente": b.docente_nombre,
                "dia_semana": _dia_str(b.dia_semana),
                "hora_inicio": _hora_str(b.hora_inicio),
                "hora_fin": _hora_str(b.hora_fin),
                "sala": getattr(b, "sala", "Aula") or "Aula",
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
                area_id = getattr(asignatura, "area_id", None)
            if area_id is not None:
                if area_id not in cache_area:
                    area = self._infra.get_area(area_id)
                    cache_area[area_id] = (
                        getattr(area, "color", None) if area else None,
                        getattr(area, "nombre", None) if area else None,
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
            celdas.append({
                "id":                getattr(b, "id", None),
                "asignacion_id":     getattr(b, "asignacion_id", None),
                "grupo_id":          b.grupo_id,
                "grupo_codigo":      getattr(b, "grupo_codigo", None) or str(b.grupo_id),
                "asignatura_id":     b.asignatura_id,
                "asignatura_nombre": b.asignatura_nombre,
                "area_id":           area_id,
                "area_color":        area_color,
                "area_nombre":       area_nombre,
                "usuario_id":        b.usuario_id,
                "docente_nombre":    b.docente_nombre,
                "dia_semana":        dia,
                "hora_inicio":       hi,
                "hora_fin":          hf,
                "sala":              getattr(b, "sala", "Aula") or "Aula",
            })

        # --- Franjas: desde la plantilla activa "UNICA", o derivadas de bloques ---
        franjas: list[dict] = []
        plantilla = None
        try:
            plantilla = self._infra.get_plantilla_activa("UNICA")
        except Exception:
            plantilla = None

        if plantilla is not None and plantilla.id is not None:
            try:
                franjas_plantilla = self._infra.listar_franjas(plantilla.id)
            except Exception:
                franjas_plantilla = []
            for fr in franjas_plantilla:
                franjas.append({
                    "orden":       fr.orden,
                    "etiqueta":    fr.etiqueta or f"{fr.hora_inicio}–{fr.hora_fin}",
                    "hora_inicio": fr.hora_inicio,
                    "hora_fin":    fr.hora_fin,
                    "lectiva":     fr.es_lectiva,
                })

        if not franjas:
            # Derivar de las parejas distintas (hora_inicio, hora_fin) de los bloques
            for orden, (hi, hf) in enumerate(sorted(pares_horas), start=1):
                franjas.append({
                    "orden":       orden,
                    "etiqueta":    f"{hi}–{hf}",
                    "hora_inicio": hi,
                    "hora_fin":    hf,
                    "lectiva":     True,
                })

        # --- Días: de la plantilla si existe, si no los presentes en bloques ---
        if plantilla is not None and getattr(plantilla, "dias_activos", None):
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
        hi_a_idx = {
            f["hora_inicio"]: idx for idx, f in enumerate(franjas_lectivas)
        }
        n_franjas_lectivas = len(franjas_lectivas)

        # Huecos por grupo: ventanas vacías intra-día usando idx compacto.
        idx_grupo_dia: dict[tuple, list[int]] = {}
        for c in celdas:
            idx = hi_a_idx.get(c["hora_inicio"])
            if idx is None:
                continue
            idx_grupo_dia.setdefault(
                (c["grupo_id"], c["dia_semana"]), []
            ).append(idx)

        huecos_grupo = 0
        for indices in idx_grupo_dia.values():
            if not indices:
                continue
            hueco = (max(indices) - min(indices) + 1) - len(indices)
            if hueco > 0:
                huecos_grupo += hueco

        capacidad = len(grupos) * n_franjas_lectivas * len(dias)
        ocupacion_pct = (
            round(len(celdas) / capacidad * 100) if capacidad else 0
        )

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
            escenario_id, dia, hora_inicio, hora_fin,
            usuario_id=asig.usuario_id, **kwargs
        ):
            raise ValueError("El docente ya tiene un bloque en ese horario.")
        if self._infra.existe_cruce(
            escenario_id, dia, hora_inicio, hora_fin,
            grupo_id=asig.grupo_id, **kwargs
        ):
            raise ValueError("El grupo ya tiene un bloque en ese horario.")
        if sala and sala != "Aula":
            if self._infra.existe_cruce(
                escenario_id, dia, hora_inicio, hora_fin,
                sala=sala, **kwargs
            ):
                raise ValueError(f"La sala '{sala}' ya está ocupada en ese horario.")

    def _validar_topes(self, escenario_id: int, asig) -> None:
        asignatura = self._get_asignatura(asig.asignatura_id)
        horas_max = self._horas_max_materia(asig, asignatura)
        if horas_max is not None:
            usadas = self._infra.contar_bloques_asignacion(escenario_id, asig.id)
            if usadas + 1 > horas_max:
                raise ValueError(
                    f"La materia ya tiene {usadas} bloque(s) asignado(s); "
                    f"límite: {horas_max}."
                )
        max_docente = self._usuario.carga_horaria_max(asig.usuario_id)
        if max_docente is not None:
            usadas_doc = self._infra.contar_bloques_docente(escenario_id, asig.usuario_id)
            if usadas_doc + 1 > max_docente:
                raise ValueError(
                    f"El docente superaría su carga máxima de {max_docente} "
                    f"bloques/semana."
                )

    def analizar_lote(
        self,
        escenario_id: int,
        periodo_id: int,
        filas: list[dict],
    ) -> "ReporteLoteDTO":
        from src.domain.models.infraestructura import FilaReporteDTO, ReporteLoteDTO

        resultado: list[FilaReporteDTO] = []
        # Escenario virtual: cruces de bloques existentes + válidos ya procesados del lote
        virtual: list[dict] = []

        try:
            existentes = self._infra.listar_horario_escenario(escenario_id)
            for b in existentes:
                dia = _dia_str(b.dia_semana)
                hi = _hora_str(b.hora_inicio)
                hf = _hora_str(b.hora_fin)
                virtual.append({
                    "usuario_id": b.usuario_id, "grupo_id": b.grupo_id,
                    "sala": getattr(b, "sala", "Aula"),
                    "dia": dia, "hora_inicio": hi, "hora_fin": hf,
                    "asignacion_id": getattr(b, "asignacion_id", None),
                    "es_lote": False,
                })
        except Exception:
            pass

        def _solapan(hi1: str, hf1: str, hi2: str, hf2: str) -> bool:
            return hi1 < hf2 and hf1 > hi2

        for i, fila in enumerate(filas):
            ok = True
            motivo = None

            # Resolver asignación
            try:
                asig_id = int(fila.get("asignacion_id") or 0)
            except (ValueError, TypeError):
                asig_id = 0

            asig = self._asig.get_by_id(asig_id) if asig_id else None
            if asig is None or getattr(asig, "activo", True) is False:
                resultado.append(FilaReporteDTO(
                    indice=i, ok=False,
                    motivo="Asignación no válida o inactiva.",
                    resumen=str(fila),
                ))
                continue

            dia = str(fila.get("dia_semana") or fila.get("dia") or "").strip()
            hora_inicio = str(fila.get("hora_inicio") or "").strip()
            hora_fin = str(fila.get("hora_fin") or "").strip()
            sala = str(fila.get("sala") or "Aula").strip() or "Aula"

            if not dia or not hora_inicio or not hora_fin:
                resultado.append(FilaReporteDTO(
                    indice=i, ok=False,
                    motivo="Campos obligatorios faltantes (dia_semana, hora_inicio, hora_fin).",
                    resumen=str(fila),
                ))
                continue

            # Cruces contra virtual
            for v in virtual:
                if v["dia"] != dia:
                    continue
                if not _solapan(hora_inicio, hora_fin, v["hora_inicio"], v["hora_fin"]):
                    continue
                if v["usuario_id"] == asig.usuario_id:
                    ok = False; motivo = "Cruce: el docente ya tiene bloque en ese horario."; break
                if v["grupo_id"] == asig.grupo_id:
                    ok = False; motivo = "Cruce: el grupo ya tiene bloque en ese horario."; break
                if sala != "Aula" and v.get("sala") == sala:
                    ok = False; motivo = f"Cruce: sala '{sala}' ya ocupada en ese horario."; break

            # Tope materia
            if ok:
                asignatura = self._get_asignatura(asig.asignatura_id)
                horas_max = self._horas_max_materia(asig, asignatura)
                if horas_max is not None:
                    usadas_bd = self._infra.contar_bloques_asignacion(escenario_id, asig.id)
                    usadas_lote = sum(1 for v in virtual if v.get("asignacion_id") == asig.id and v.get("es_lote"))
                    if usadas_bd + usadas_lote + 1 > horas_max:
                        ok = False
                        motivo = f"Tope materia: {usadas_bd + usadas_lote}/{horas_max} bloques."

            # Tope docente
            if ok:
                max_doc = self._usuario.carga_horaria_max(asig.usuario_id)
                if max_doc is not None:
                    usadas_doc_bd = self._infra.contar_bloques_docente(escenario_id, asig.usuario_id)
                    usadas_doc_lote = sum(1 for v in virtual if v.get("usuario_id") == asig.usuario_id and v.get("es_lote"))
                    if usadas_doc_bd + usadas_doc_lote + 1 > max_doc:
                        ok = False
                        motivo = f"Tope docente: superaría {max_doc} bloques/semana."

            asig_nombre = getattr(asig, "asignatura_nombre", None) or str(asig_id)
            resumen = f"{dia} {hora_inicio}–{hora_fin} | {asig_nombre}"
            resultado.append(FilaReporteDTO(indice=i, ok=ok, motivo=motivo, resumen=resumen))

            if ok:
                virtual.append({
                    "usuario_id": asig.usuario_id, "grupo_id": asig.grupo_id,
                    "sala": sala, "dia": dia,
                    "hora_inicio": hora_inicio, "hora_fin": hora_fin,
                    "asignacion_id": asig.id, "es_lote": True,
                })

        return ReporteLoteDTO(filas=resultado)

    @requiere_escritura
    def aplicar_lote(
        self,
        escenario_id: int,
        periodo_id: int,
        filas: list[dict],
        solo_validas: bool = False,
    ) -> "ResultadoLoteDTO":
        from src.domain.models.infraestructura import ResultadoLoteDTO, Horario

        reporte = self.analizar_lote(escenario_id, periodo_id, filas)

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
            hora_inicio = str(fila_dict.get("hora_inicio") or "")
            hora_fin = str(fila_dict.get("hora_fin") or "")
            sala = str(fila_dict.get("sala") or "Aula") or "Aula"
            horarios_nuevos.append(Horario(
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
            ))

        creados = self._infra.crear_bloques_masivo(horarios_nuevos)
        omitidos = len(filas) - creados
        return ResultadoLoteDTO(creados=creados, omitidos=omitidos, reporte=reporte)

    def _get_asignatura(self, asignatura_id: int):
        return self._infra.get_asignatura(asignatura_id)


__all__ = ["HorarioService", "COLUMNAS_HORARIO"]
