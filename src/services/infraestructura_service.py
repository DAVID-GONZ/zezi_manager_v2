"""
src/services/infraestructura_service.py
========================================
Fachada sobre IInfraestructuraRepository que expone a la capa de
interfaz las operaciones sobre AreaConocimiento, Asignatura, Grupo,
Horario y Logro sin revelar el repositorio directamente.
"""
from __future__ import annotations

from src.domain.ports.infraestructura_repo import IInfraestructuraRepository
from src.domain.models.infraestructura import (
    AreaConocimiento,
    Asignatura,
    BloqueAnclado,
    ConfigGeneracion,
    DiaSemana,
    DisponibilidadDocente,
    EscenarioHorario,
    Franja,
    FranjaReunion,
    Grupo,
    Horario,
    HorarioEstadisticasDTO,
    HorarioInfo,
    Jornada,
    LimitesDocente,
    NuevoHorarioDTO,
    PlantillaFranja,
    Sala,
    VentanaGrupo,
)


class InfraestructuraService:

    def __init__(self, repo: IInfraestructuraRepository) -> None:
        self._repo = repo

    # ── Escenarios ────────────────────────────────────────────────────────────

    def get_escenario(self, escenario_id: int) -> EscenarioHorario | None:
        return self._repo.get_escenario(escenario_id)

    def listar_escenarios(self, anio_id: int) -> list[EscenarioHorario]:
        return self._repo.listar_escenarios(anio_id)

    def get_escenario_activo(self, anio_id: int) -> EscenarioHorario | None:
        return self._repo.get_escenario_activo(anio_id)

    def crear_escenario(self, esc: EscenarioHorario) -> EscenarioHorario:
        return self._repo.crear_escenario(esc)

    def crear_escenario_simple(
        self, anio_id: int, nombre: str, descripcion: str | None = None
    ) -> EscenarioHorario:
        """Crea un escenario a partir de parámetros primitivos (sin importar el modelo en la UI)."""
        from src.domain.models.infraestructura import NuevoEscenarioDTO
        dto = NuevoEscenarioDTO(anio_id=anio_id, nombre=nombre, descripcion=descripcion)
        return self._repo.crear_escenario(dto.to_escenario())

    def actualizar_escenario(self, esc: EscenarioHorario) -> EscenarioHorario:
        return self._repo.actualizar_escenario(esc)

    def renombrar_escenario(
        self, esc_existente, nombre: str, descripcion: str | None = None
    ) -> EscenarioHorario:
        """Actualiza nombre/descripción de un escenario usando el objeto ya cargado."""
        updated = esc_existente.model_copy(update={
            "nombre": nombre,
            "descripcion": descripcion if descripcion is not None else esc_existente.descripcion,
        })
        return self._repo.actualizar_escenario(updated)

    def activar_escenario(self, escenario_id: int) -> None:
        return self._repo.activar_escenario(escenario_id)

    def eliminar_escenario(self, escenario_id: int) -> bool:
        return self._repo.eliminar_escenario(escenario_id)

    def duplicar_escenario(self, escenario_id: int, nuevo_nombre: str) -> EscenarioHorario:
        return self._repo.duplicar_escenario(escenario_id, nuevo_nombre)

    def listar_horario_grupo_escenario(
        self, grupo_id: int, escenario_id: int
    ) -> list[HorarioInfo]:
        return self._repo.listar_horario_grupo_escenario(grupo_id, escenario_id)

    def listar_horario_escenario(self, escenario_id: int) -> list[HorarioInfo]:
        return self._repo.listar_horario_escenario(escenario_id)

    # ── Plantillas de franja (rejilla) ─────────────────────────────────────────

    def crear_plantilla_simple(
        self,
        nombre: str,
        jornada: str = "UNICA",
        dias: list[str] | None = None,
    ) -> PlantillaFranja:
        """Crea una plantilla a partir de parámetros primitivos (la UI no importa modelos)."""
        from src.domain.models.infraestructura import (
            DIAS_VALIDOS,
            NuevaPlantillaFranjaDTO,
        )
        dto = NuevaPlantillaFranjaDTO(
            nombre=nombre,
            jornada=jornada,
            dias_activos=dias if dias is not None else list(DIAS_VALIDOS[:5]),
        )
        return self._repo.crear_plantilla_franja(dto.to_plantilla())

    def listar_plantillas(self) -> list[PlantillaFranja]:
        return self._repo.listar_plantillas_franja()

    def plantilla_activa(self, jornada: str = "UNICA") -> PlantillaFranja | None:
        return self._repo.get_plantilla_activa(jornada)

    def guardar_franjas(self, plantilla_id: int, filas: list[dict]) -> int:
        """
        Reemplaza el set de franjas de una plantilla. `filas` son dicts con claves
        orden, hora_inicio, hora_fin, tipo, etiqueta (los DTOs se construyen aquí).
        """
        from src.domain.models.infraestructura import NuevaFranjaDTO
        franjas: list[Franja] = []
        for fila in filas:
            dto = NuevaFranjaDTO(
                plantilla_id=plantilla_id,
                orden=fila["orden"],
                hora_inicio=fila["hora_inicio"],
                hora_fin=fila["hora_fin"],
                tipo=fila.get("tipo", "lectiva"),
                etiqueta=fila.get("etiqueta"),
            )
            franjas.append(dto.to_franja())
        return self._repo.reemplazar_franjas(plantilla_id, franjas)

    def listar_franjas(self, plantilla_id: int) -> list[Franja]:
        return self._repo.listar_franjas(plantilla_id)

    def activar_plantilla(self, plantilla_id: int) -> None:
        return self._repo.activar_plantilla_franja(plantilla_id)

    def eliminar_plantilla(self, plantilla_id: int) -> bool:
        return self._repo.eliminar_plantilla_franja(plantilla_id)

    # ── Áreas ─────────────────────────────────────────────────────────────────

    def listar_areas(self) -> list[AreaConocimiento]:
        return self._repo.listar_areas()

    def guardar_area(self, area: AreaConocimiento) -> AreaConocimiento:
        return self._repo.guardar_area(area)

    def actualizar_area(self, area: AreaConocimiento) -> AreaConocimiento:
        return self._repo.actualizar_area(area)

    def eliminar_area(self, area_id: int) -> bool:
        return self._repo.eliminar_area(area_id)

    def set_color_area(self, area_id: int, color: str | None) -> bool:
        """Asigna (o limpia) el color hex de un área. Valida vía el modelo."""
        normalizado = AreaConocimiento(id=area_id, nombre="_", color=color).color
        return self._repo.actualizar_color_area(area_id, normalizado)

    # ── Asignaturas ───────────────────────────────────────────────────────────

    def listar_asignaturas(self, area_id: int | None = None) -> list[Asignatura]:
        return self._repo.listar_asignaturas(area_id=area_id)

    def guardar_asignatura(self, asignatura: Asignatura) -> Asignatura:
        return self._repo.guardar_asignatura(asignatura)

    def actualizar_asignatura(self, asignatura: Asignatura) -> Asignatura:
        return self._repo.actualizar_asignatura(asignatura)

    def eliminar_asignatura(self, asignatura_id: int) -> bool:
        return self._repo.eliminar_asignatura(asignatura_id)

    # ── Grupos ────────────────────────────────────────────────────────────────

    def listar_grupos(self, grado: int | None = None) -> list[Grupo]:
        return self._repo.listar_grupos(grado=grado)

    def guardar_grupo(self, grupo: Grupo) -> Grupo:
        return self._repo.guardar_grupo(grupo)

    def asignar_sala_a_grupo(self, grupo_id: int, sala_id: int | None) -> bool:
        """Asigna (o quita, con None) el aula propia de un grupo."""
        return self._repo.asignar_sala_a_grupo(grupo_id, sala_id)

    def actualizar_grupo(self, grupo: Grupo) -> Grupo:
        return self._repo.actualizar_grupo(grupo)

    def eliminar_grupo(self, grupo_id: int) -> bool:
        return self._repo.eliminar_grupo(grupo_id)

    # ── Horarios ──────────────────────────────────────────────────────────────

    def listar_horario_grupo(
        self, grupo_id: int, periodo_id: int
    ) -> list[HorarioInfo]:
        return self._repo.listar_horario_grupo(grupo_id, periodo_id)

    def listar_horario_docente(
        self, usuario_id: int, periodo_id: int
    ) -> list[HorarioInfo]:
        return self._repo.listar_horario_docente(usuario_id, periodo_id)

    def guardar_horario(self, horario: Horario) -> Horario:
        return self._repo.guardar_horario(horario)

    def eliminar_horario(self, horario_id: int) -> bool:
        return self._repo.eliminar_horario(horario_id)

    def existe_conflicto_horario(
        self,
        usuario_id: int,
        periodo_id: int,
        dia_semana: str,
        hora_inicio: str,
        hora_fin: str,
        excluir_horario_id: int | None = None,
    ) -> bool:
        return self._repo.existe_conflicto_horario(
            usuario_id,
            periodo_id,
            dia_semana,
            hora_inicio,
            hora_fin,
            excluir_horario_id,
        )

    def get_estadisticas(self, periodo_id: int) -> HorarioEstadisticasDTO:
        return self._repo.get_estadisticas(periodo_id)

    # ── Disponibilidad docente (paso_15b) ─────────────────────────────────────

    def es_disponible_docente(
        self, usuario_id: int, dia: str, franja_orden: int
    ) -> bool:
        return self._repo.es_disponible(usuario_id, dia, franja_orden)

    def bloquear_franjas_docente(
        self, usuario_id: int, slots: list[dict]
    ) -> int:
        return self._repo.cargar_disponibilidad_lote(usuario_id, slots)

    def limpiar_disponibilidad_docente(self, usuario_id: int) -> int:
        return self._repo.limpiar_disponibilidad_docente(usuario_id)

    def listar_disponibilidad_docente(
        self, usuario_id: int
    ) -> list[DisponibilidadDocente]:
        return self._repo.listar_disponibilidad_docente(usuario_id)

    # ── Config generación (paso_15b) ──────────────────────────────────────────

    def crear_config_generacion(
        self,
        nombre: str,
        periodo_id: int,
        anio_id: int,
        plantilla_id: int,
        grupos: list[int] | None = None,
        pesos: dict | None = None,
    ) -> ConfigGeneracion:
        from src.domain.models.infraestructura import (
            NuevaConfigGeneracionDTO,
            PesosGeneracion,
        )
        pesos_obj = (
            PesosGeneracion(**pesos) if isinstance(pesos, dict) else PesosGeneracion()
        )
        dto = NuevaConfigGeneracionDTO(
            nombre=nombre,
            periodo_id=periodo_id,
            anio_id=anio_id,
            plantilla_id=plantilla_id,
            grupos=grupos if grupos is not None else [],
            pesos=pesos_obj,
        )
        return self._repo.crear_config_generacion(dto.to_config())

    def listar_configs_generacion(
        self, periodo_id: int | None = None
    ) -> list[ConfigGeneracion]:
        return self._repo.listar_configs_generacion(periodo_id)

    def get_config_generacion(self, config_id: int) -> ConfigGeneracion | None:
        return self._repo.get_config_generacion(config_id)

    def actualizar_config_generacion(
        self, config_id: int, **campos
    ) -> ConfigGeneracion:
        config = self._repo.get_config_generacion(config_id)
        if config is None:
            raise ValueError(f"Config {config_id} no existe.")
        if "pesos" in campos and isinstance(campos["pesos"], dict):
            from src.domain.models.infraestructura import PesosGeneracion
            campos = {**campos, "pesos": PesosGeneracion(**campos["pesos"])}
        updated = config.model_copy(update=campos)
        return self._repo.actualizar_config_generacion(updated)

    def eliminar_config_generacion(self, config_id: int) -> bool:
        return self._repo.eliminar_config_generacion(config_id)

    def cambiar_estado_config(
        self, config_id: int, nuevo_estado: str
    ) -> ConfigGeneracion:
        return self._repo.cambiar_estado_config(config_id, nuevo_estado)

    def duplicar_config_generacion(self, config_id: int) -> ConfigGeneracion:
        return self._repo.duplicar_config_generacion(config_id)

    # ── Salas (paso_17) ───────────────────────────────────────────────────────

    def listar_salas(self) -> list[Sala]:
        return self._repo.listar_salas()

    def get_sala(self, sala_id: int) -> Sala | None:
        return self._repo.get_sala(sala_id)

    def crear_sala(self, sala: Sala) -> Sala:
        return self._repo.crear_sala(sala)

    def actualizar_sala(self, sala: Sala) -> Sala:
        if sala.id is None:
            raise ValueError("La sala no tiene id.")
        return self._repo.actualizar_sala(sala)

    def eliminar_sala(self, sala_id: int) -> bool:
        return self._repo.eliminar_sala(sala_id)

    # ── VentanaGrupo (paso_17) ────────────────────────────────────────────────

    def listar_ventanas_grupo(self) -> list[VentanaGrupo]:
        return self._repo.listar_ventanas_grupo()

    def get_ventanas_por_grupo(self, grupo_id: int) -> list[VentanaGrupo]:
        return self._repo.get_ventanas_por_grupo(grupo_id)

    def get_ventanas_por_grado(self, grado: int) -> list[VentanaGrupo]:
        return self._repo.get_ventanas_por_grado(grado)

    def crear_ventana_grupo(self, v: VentanaGrupo) -> VentanaGrupo:
        return self._repo.crear_ventana_grupo(v)

    def eliminar_ventana_grupo(self, ventana_id: int) -> bool:
        return self._repo.eliminar_ventana_grupo(ventana_id)

    # ── BloqueAnclado (paso_17) ───────────────────────────────────────────────

    def listar_bloques_anclados(self, escenario_id: int) -> list[BloqueAnclado]:
        return self._repo.listar_bloques_anclados(escenario_id)

    def crear_bloque_anclado(self, b: BloqueAnclado) -> BloqueAnclado:
        return self._repo.crear_bloque_anclado(b)

    def eliminar_bloque_anclado(self, bloque_id: int) -> bool:
        return self._repo.eliminar_bloque_anclado(bloque_id)

    # ── FranjaReunion (paso_17) ───────────────────────────────────────────────

    def listar_franjas_reunion(self) -> list[FranjaReunion]:
        return self._repo.listar_franjas_reunion()

    def get_franja_reunion(self, franja_id: int) -> FranjaReunion | None:
        return self._repo.get_franja_reunion(franja_id)

    def crear_franja_reunion(self, f: FranjaReunion) -> FranjaReunion:
        return self._repo.crear_franja_reunion(f)

    def actualizar_franja_reunion(self, f: FranjaReunion) -> FranjaReunion:
        if f.id is None:
            raise ValueError("La franja de reunión no tiene id.")
        return self._repo.actualizar_franja_reunion(f)

    def eliminar_franja_reunion(self, franja_id: int) -> bool:
        return self._repo.eliminar_franja_reunion(franja_id)

    # ── LimitesDocente (paso_17) ──────────────────────────────────────────────

    def get_limites_docente(self, usuario_id: int) -> LimitesDocente | None:
        return self._repo.get_limites_docente(usuario_id)

    def set_limites_docente(self, limites: LimitesDocente) -> LimitesDocente:
        return self._repo.set_limites_docente(limites)

    def set_limites_docente_simple(
        self, usuario_id: int, min_horas_dia: int = 0, max_horas_dia: int = 8
    ) -> LimitesDocente:
        """Crea o actualiza los límites diarios de un docente a partir de primitivos."""
        limites = LimitesDocente(
            usuario_id=usuario_id,
            min_horas_dia=min_horas_dia,
            max_horas_dia=max_horas_dia,
        )
        return self._repo.set_limites_docente(limites)

    def listar_limites_docente(self) -> list[LimitesDocente]:
        return self._repo.listar_limites_docente()


__all__ = ["InfraestructuraService"]
