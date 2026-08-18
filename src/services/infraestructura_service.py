"""
src/services/infraestructura_service.py
========================================
Fachada sobre IInfraestructuraRepository que expone a la capa de
interfaz las operaciones sobre AreaConocimiento, Asignatura, Grupo,
Horario y Logro sin revelar el repositorio directamente.
"""

from __future__ import annotations

from src.domain.models.infraestructura import (
    AreaConocimiento,
    Asignatura,
    BloqueAnclado,
    ConfigGeneracion,
    DisponibilidadDocente,
    EscenarioHorario,
    Franja,
    FranjaReunion,
    Grupo,
    HorarioInfo,
    LimitesDocente,
    PlantillaFranja,
    Sala,
    VentanaGrupo,
)
from src.domain.ports.infraestructura_repo import IInfraestructuraRepository


class InfraestructuraService:
    def __init__(self, repo: IInfraestructuraRepository) -> None:
        """Inyecta el repositorio de infraestructura."""
        self._repo = repo
        # Fachada por delegación (mejora_01): cada subdominio vive en su propio
        # sub-servicio, construido con ESTE mismo repo (preserva la inyección de
        # los tests y evita el DB global del Container). Cache lazy por nombre.
        self._subservicios: dict = {}

    # ── Sub-servicios delegados (mejora_01 — fachada por delegación) ────────────

    def _sala_service(self):
        """SalaService ligado a este repo (lazy, cacheado en la instancia)."""
        svc = self._subservicios.get("sala")
        if svc is None:
            from src.services.sala_service import SalaService

            svc = SalaService(repo=self._repo)
            self._subservicios["sala"] = svc
        return svc

    def _franja_service(self):
        """FranjaService ligado a este repo (lazy, cacheado en la instancia)."""
        svc = self._subservicios.get("franja")
        if svc is None:
            from src.services.franja_service import FranjaService

            svc = FranjaService(repo=self._repo)
            self._subservicios["franja"] = svc
        return svc

    def _escenario_horario_service(self):
        """EscenarioHorarioService ligado a este repo (lazy, cacheado)."""
        svc = self._subservicios.get("escenario")
        if svc is None:
            from src.services.escenario_horario_service import EscenarioHorarioService

            svc = EscenarioHorarioService(repo=self._repo)
            self._subservicios["escenario"] = svc
        return svc

    def _restriccion_generacion_service(self):
        """RestriccionGeneracionService ligado a este repo (lazy, cacheado)."""
        svc = self._subservicios.get("restriccion")
        if svc is None:
            from src.services.restriccion_generacion_service import (
                RestriccionGeneracionService,
            )

            svc = RestriccionGeneracionService(repo=self._repo)
            self._subservicios["restriccion"] = svc
        return svc

    def _catalogo_academico_service(self):
        """CatalogoAcademicoService ligado a este repo (lazy, cacheado)."""
        svc = self._subservicios.get("catalogo")
        if svc is None:
            from src.services.catalogo_academico_service import CatalogoAcademicoService

            svc = CatalogoAcademicoService(repo=self._repo)
            self._subservicios["catalogo"] = svc
        return svc

    # Nota (mejora_01): los helpers de tenant `_resolver_institucion` y
    # `_verificar_pertenencia_obj` se movieron con su lógica a los sub-servicios
    # (SalaService, FranjaService, CatalogoAcademicoService) que los usan.

    # ── Escenarios — delega en EscenarioHorarioService (mejora_01) ──────────────

    def get_escenario(self, escenario_id: int) -> EscenarioHorario | None:
        """Retorna un escenario por id (delega en EscenarioHorarioService)."""
        return self._escenario_horario_service().get_escenario(escenario_id)

    def listar_escenarios(self, anio_id: int) -> list[EscenarioHorario]:
        """Lista los escenarios de un año lectivo (delega en EscenarioHorarioService)."""
        return self._escenario_horario_service().listar_escenarios(anio_id)

    def get_escenario_activo(self, anio_id: int) -> EscenarioHorario | None:
        """Retorna el escenario activo de un año (delega en EscenarioHorarioService)."""
        return self._escenario_horario_service().get_escenario_activo(anio_id)

    def crear_escenario(self, esc: EscenarioHorario) -> EscenarioHorario:
        """Crea un escenario (delega en EscenarioHorarioService)."""
        return self._escenario_horario_service().crear_escenario(esc)

    def crear_escenario_simple(
        self, anio_id: int, nombre: str, descripcion: str | None = None
    ) -> EscenarioHorario:
        """Crea un escenario desde primitivos (delega en EscenarioHorarioService)."""
        return self._escenario_horario_service().crear_escenario_simple(
            anio_id, nombre, descripcion
        )

    def actualizar_escenario(self, esc: EscenarioHorario) -> EscenarioHorario:
        """Actualiza un escenario (delega en EscenarioHorarioService)."""
        return self._escenario_horario_service().actualizar_escenario(esc)

    def renombrar_escenario(
        self, esc_existente, nombre: str, descripcion: str | None = None
    ) -> EscenarioHorario:
        """Renombra un escenario usando el objeto ya cargado (delega en EscenarioHorarioService)."""
        return self._escenario_horario_service().renombrar_escenario(
            esc_existente, nombre, descripcion
        )

    def activar_escenario(self, escenario_id: int) -> None:
        """Marca un escenario como activo (delega en EscenarioHorarioService)."""
        return self._escenario_horario_service().activar_escenario(escenario_id)

    def eliminar_escenario(self, escenario_id: int) -> bool:
        """Elimina un escenario (delega en EscenarioHorarioService)."""
        return self._escenario_horario_service().eliminar_escenario(escenario_id)

    def duplicar_escenario(self, escenario_id: int, nuevo_nombre: str) -> EscenarioHorario:
        """Duplica un escenario con un nuevo nombre (delega en EscenarioHorarioService)."""
        return self._escenario_horario_service().duplicar_escenario(escenario_id, nuevo_nombre)

    def listar_horario_grupo_escenario(self, grupo_id: int, escenario_id: int) -> list[HorarioInfo]:
        """Lista el horario de un grupo dentro de un escenario (delega en EscenarioHorarioService)."""
        return self._escenario_horario_service().listar_horario_grupo_escenario(
            grupo_id, escenario_id
        )

    def listar_horario_escenario(self, escenario_id: int) -> list[HorarioInfo]:
        """Lista todos los bloques de un escenario (delega en EscenarioHorarioService)."""
        return self._escenario_horario_service().listar_horario_escenario(escenario_id)

    # ── Plantillas de franja (rejilla) — delega en FranjaService (mejora_01) ────

    def crear_plantilla_simple(
        self,
        nombre: str,
        jornada: str = "UNICA",
        dias: list[str] | None = None,
    ) -> PlantillaFranja:
        """Crea una plantilla desde primitivos (delega en FranjaService)."""
        return self._franja_service().crear_plantilla_simple(nombre, jornada, dias)

    def listar_plantillas(self) -> list[PlantillaFranja]:
        """Lista las plantillas de franja del scope actual (delega en FranjaService)."""
        return self._franja_service().listar_plantillas()

    def plantilla_activa(self, jornada: str = "UNICA") -> PlantillaFranja | None:
        """Retorna la plantilla activa de una jornada (delega en FranjaService)."""
        return self._franja_service().plantilla_activa(jornada)

    def guardar_franjas(self, plantilla_id: int, filas: list[dict]) -> int:
        """Reemplaza el set de franjas de una plantilla (delega en FranjaService)."""
        return self._franja_service().guardar_franjas(plantilla_id, filas)

    def listar_franjas(self, plantilla_id: int) -> list[Franja]:
        """Lista las franjas de una plantilla (delega en FranjaService)."""
        return self._franja_service().listar_franjas(plantilla_id)

    def activar_plantilla(self, plantilla_id: int) -> None:
        """Marca una plantilla de franja como activa (delega en FranjaService)."""
        return self._franja_service().activar_plantilla(plantilla_id)

    def eliminar_plantilla(self, plantilla_id: int) -> bool:
        """Elimina una plantilla (delega en FranjaService)."""
        return self._franja_service().eliminar_plantilla(plantilla_id)

    # ── Áreas — delega en CatalogoAcademicoService (mejora_01) ──────────────────

    def listar_areas(self) -> list[AreaConocimiento]:
        """Lista las áreas de conocimiento (delega en CatalogoAcademicoService)."""
        return self._catalogo_academico_service().listar_areas()

    def guardar_area(self, area: AreaConocimiento) -> AreaConocimiento:
        """Crea un área de conocimiento (delega en CatalogoAcademicoService)."""
        return self._catalogo_academico_service().guardar_area(area)

    def actualizar_area(self, area: AreaConocimiento) -> AreaConocimiento:
        """Actualiza un área de conocimiento (delega en CatalogoAcademicoService)."""
        return self._catalogo_academico_service().actualizar_area(area)

    def eliminar_area(self, area_id: int) -> bool:
        """Elimina un área de conocimiento (delega en CatalogoAcademicoService)."""
        return self._catalogo_academico_service().eliminar_area(area_id)

    def set_color_area(self, area_id: int, color: str | None) -> bool:
        """Asigna (o limpia) el color hex de un área (delega en CatalogoAcademicoService)."""
        return self._catalogo_academico_service().set_color_area(area_id, color)

    # ── Asignaturas — delega en CatalogoAcademicoService ────────────────────────

    def listar_asignaturas(self, area_id: int | None = None) -> list[Asignatura]:
        """Lista las asignaturas del scope actual (delega en CatalogoAcademicoService)."""
        return self._catalogo_academico_service().listar_asignaturas(area_id)

    def guardar_asignatura(self, asignatura: Asignatura) -> Asignatura:
        """Crea una asignatura (delega en CatalogoAcademicoService)."""
        return self._catalogo_academico_service().guardar_asignatura(asignatura)

    def actualizar_asignatura(self, asignatura: Asignatura) -> Asignatura:
        """Actualiza una asignatura (delega en CatalogoAcademicoService)."""
        return self._catalogo_academico_service().actualizar_asignatura(asignatura)

    def eliminar_asignatura(self, asignatura_id: int) -> bool:
        """Elimina una asignatura (delega en CatalogoAcademicoService)."""
        return self._catalogo_academico_service().eliminar_asignatura(asignatura_id)

    # ── Grupos — delega en CatalogoAcademicoService ─────────────────────────────

    def get_grupo(self, grupo_id: int) -> Grupo | None:
        """Lee un grupo por id (delega en CatalogoAcademicoService)."""
        return self._catalogo_academico_service().get_grupo(grupo_id)

    def listar_grupos(self, grado: int | None = None) -> list[Grupo]:
        """Lista los grupos del scope actual (delega en CatalogoAcademicoService)."""
        return self._catalogo_academico_service().listar_grupos(grado)

    def guardar_grupo(self, grupo: Grupo) -> Grupo:
        """Crea un grupo (delega en CatalogoAcademicoService)."""
        return self._catalogo_academico_service().guardar_grupo(grupo)

    def asignar_sala_a_grupo(self, grupo_id: int, sala_id: int | None) -> bool:
        """Asigna (o quita, con None) el aula propia de un grupo (delega en SalaService)."""
        return self._sala_service().asignar_sala_a_grupo(grupo_id, sala_id)

    def actualizar_grupo(self, grupo: Grupo) -> Grupo:
        """Actualiza un grupo (delega en CatalogoAcademicoService)."""
        return self._catalogo_academico_service().actualizar_grupo(grupo)

    def eliminar_grupo(self, grupo_id: int) -> bool:
        """Elimina un grupo (delega en CatalogoAcademicoService)."""
        return self._catalogo_academico_service().eliminar_grupo(grupo_id)

    # ── Bloques de horario (mejora_05) ──────────────────────────────────────────
    # Movidos a HorarioService (dueño canónico, R3). Consumir vía
    # `Container.horario_service()`; la fachada ya no expone bloques de horario.

    # ── Disponibilidad docente — delega en RestriccionGeneracionService ─────────

    def es_disponible_docente(self, usuario_id: int, dia: str, franja_orden: int) -> bool:
        """Indica si un docente está disponible en una franja (delega en RestriccionGeneracionService)."""
        return self._restriccion_generacion_service().es_disponible_docente(
            usuario_id, dia, franja_orden
        )

    def bloquear_franjas_docente(self, usuario_id: int, slots: list[dict]) -> int:
        """Carga en lote las franjas no disponibles de un docente (delega en RestriccionGeneracionService)."""
        return self._restriccion_generacion_service().bloquear_franjas_docente(usuario_id, slots)

    def limpiar_disponibilidad_docente(self, usuario_id: int) -> int:
        """Borra toda la disponibilidad configurada de un docente (delega en RestriccionGeneracionService)."""
        return self._restriccion_generacion_service().limpiar_disponibilidad_docente(usuario_id)

    def guardar_disponibilidad_docente(self, usuario_id: int, slots: list[dict]) -> int:
        """Reemplaza ATÓMICAMENTE la disponibilidad de un docente (delega en RestriccionGeneracionService)."""
        return self._restriccion_generacion_service().guardar_disponibilidad_docente(
            usuario_id, slots
        )

    def listar_disponibilidad_docente(self, usuario_id: int) -> list[DisponibilidadDocente]:
        """Lista la disponibilidad configurada de un docente (delega en RestriccionGeneracionService)."""
        return self._restriccion_generacion_service().listar_disponibilidad_docente(usuario_id)

    # ── Config generación — delega en RestriccionGeneracionService ──────────────

    def crear_config_generacion(
        self,
        nombre: str,
        periodo_id: int,
        anio_id: int,
        plantilla_id: int,
        grupos: list[int] | None = None,
        pesos: dict | None = None,
        restricciones: dict | None = None,
    ) -> ConfigGeneracion:
        """Crea una config de generación desde primitivos (delega en RestriccionGeneracionService)."""
        return self._restriccion_generacion_service().crear_config_generacion(
            nombre, periodo_id, anio_id, plantilla_id, grupos, pesos, restricciones
        )

    def construir_restricciones(
        self, min_horas: int, max_horas: int, modo: str = "preferente"
    ) -> dict:
        """Ensambla el payload de restricciones de generación (delega en RestriccionGeneracionService)."""
        return self._restriccion_generacion_service().construir_restricciones(
            min_horas, max_horas, modo
        )

    def listar_configs_generacion(self, periodo_id: int | None = None) -> list[ConfigGeneracion]:
        """Lista las configs de generación (delega en RestriccionGeneracionService)."""
        return self._restriccion_generacion_service().listar_configs_generacion(periodo_id)

    def get_config_generacion(self, config_id: int) -> ConfigGeneracion | None:
        """Retorna una config de generación por id (delega en RestriccionGeneracionService)."""
        return self._restriccion_generacion_service().get_config_generacion(config_id)

    def actualizar_config_generacion(self, config_id: int, **campos) -> ConfigGeneracion:
        """Actualiza los campos indicados de una config de generación (delega en RestriccionGeneracionService)."""
        return self._restriccion_generacion_service().actualizar_config_generacion(
            config_id, **campos
        )

    def eliminar_config_generacion(self, config_id: int) -> bool:
        """Elimina una config de generación (delega en RestriccionGeneracionService)."""
        return self._restriccion_generacion_service().eliminar_config_generacion(config_id)

    def cambiar_estado_config(self, config_id: int, nuevo_estado: str) -> ConfigGeneracion:
        """Cambia el estado de una config de generación (delega en RestriccionGeneracionService)."""
        return self._restriccion_generacion_service().cambiar_estado_config(config_id, nuevo_estado)

    def duplicar_config_generacion(self, config_id: int) -> ConfigGeneracion:
        """Duplica una config de generación (delega en RestriccionGeneracionService)."""
        return self._restriccion_generacion_service().duplicar_config_generacion(config_id)

    # ── Salas (paso_17) — delega en SalaService (mejora_01) ─────────────────────

    def listar_salas(self) -> list[Sala]:
        """Lista las salas del scope actual (delega en SalaService)."""
        return self._sala_service().listar_salas()

    def get_sala(self, sala_id: int) -> Sala | None:
        """Retorna una sala por id (delega en SalaService)."""
        return self._sala_service().get_sala(sala_id)

    def crear_sala(self, sala: Sala) -> Sala:
        """Crea una sala (delega en SalaService)."""
        return self._sala_service().crear_sala(sala)

    def actualizar_sala(self, sala: Sala) -> Sala:
        """Actualiza una sala (delega en SalaService)."""
        return self._sala_service().actualizar_sala(sala)

    def eliminar_sala(self, sala_id: int) -> bool:
        """Elimina una sala (delega en SalaService)."""
        return self._sala_service().eliminar_sala(sala_id)

    # ── VentanaGrupo — delega en RestriccionGeneracionService ───────────────────

    def listar_ventanas_grupo(self) -> list[VentanaGrupo]:
        """Lista todas las ventanas de grupo (delega en RestriccionGeneracionService)."""
        return self._restriccion_generacion_service().listar_ventanas_grupo()

    def get_ventanas_por_grupo(self, grupo_id: int) -> list[VentanaGrupo]:
        """Lista las ventanas de un grupo (delega en RestriccionGeneracionService)."""
        return self._restriccion_generacion_service().get_ventanas_por_grupo(grupo_id)

    def get_ventanas_por_grado(self, grado: int) -> list[VentanaGrupo]:
        """Lista las ventanas de un grado (delega en RestriccionGeneracionService)."""
        return self._restriccion_generacion_service().get_ventanas_por_grado(grado)

    def crear_ventana_grupo(self, v: VentanaGrupo) -> VentanaGrupo:
        """Crea una ventana de grupo (delega en RestriccionGeneracionService)."""
        return self._restriccion_generacion_service().crear_ventana_grupo(v)

    def eliminar_ventana_grupo(self, ventana_id: int) -> bool:
        """Elimina una ventana de grupo (delega en RestriccionGeneracionService)."""
        return self._restriccion_generacion_service().eliminar_ventana_grupo(ventana_id)

    # ── BloqueAnclado — delega en RestriccionGeneracionService ──────────────────

    def listar_bloques_anclados(self, escenario_id: int) -> list[BloqueAnclado]:
        """Lista los bloques anclados de un escenario (delega en RestriccionGeneracionService)."""
        return self._restriccion_generacion_service().listar_bloques_anclados(escenario_id)

    def crear_bloque_anclado(self, b: BloqueAnclado) -> BloqueAnclado:
        """Crea un bloque anclado (delega en RestriccionGeneracionService)."""
        return self._restriccion_generacion_service().crear_bloque_anclado(b)

    def eliminar_bloque_anclado(self, bloque_id: int) -> bool:
        """Elimina un bloque anclado (delega en RestriccionGeneracionService)."""
        return self._restriccion_generacion_service().eliminar_bloque_anclado(bloque_id)

    # ── FranjaReunion — delega en RestriccionGeneracionService ──────────────────

    def listar_franjas_reunion(self) -> list[FranjaReunion]:
        """Lista las franjas de reunión (delega en RestriccionGeneracionService)."""
        return self._restriccion_generacion_service().listar_franjas_reunion()

    def get_franja_reunion(self, franja_id: int) -> FranjaReunion | None:
        """Retorna una franja de reunión por id (delega en RestriccionGeneracionService)."""
        return self._restriccion_generacion_service().get_franja_reunion(franja_id)

    def crear_franja_reunion(self, f: FranjaReunion) -> FranjaReunion:
        """Crea una franja de reunión (delega en RestriccionGeneracionService)."""
        return self._restriccion_generacion_service().crear_franja_reunion(f)

    def actualizar_franja_reunion(self, f: FranjaReunion) -> FranjaReunion:
        """Actualiza una franja de reunión (delega en RestriccionGeneracionService)."""
        return self._restriccion_generacion_service().actualizar_franja_reunion(f)

    def eliminar_franja_reunion(self, franja_id: int) -> bool:
        """Elimina una franja de reunión (delega en RestriccionGeneracionService)."""
        return self._restriccion_generacion_service().eliminar_franja_reunion(franja_id)

    # ── LimitesDocente — delega en RestriccionGeneracionService ─────────────────

    def get_limites_docente(self, usuario_id: int) -> LimitesDocente | None:
        """Retorna los límites diarios de un docente (delega en RestriccionGeneracionService)."""
        return self._restriccion_generacion_service().get_limites_docente(usuario_id)

    def set_limites_docente(self, limites: LimitesDocente) -> LimitesDocente:
        """Crea o actualiza los límites diarios de un docente (delega en RestriccionGeneracionService)."""
        return self._restriccion_generacion_service().set_limites_docente(limites)

    def set_limites_docente_simple(
        self, usuario_id: int, min_horas_dia: int = 0, max_horas_dia: int = 8
    ) -> LimitesDocente:
        """Crea o actualiza los límites diarios de un docente desde primitivos (delega en RestriccionGeneracionService)."""
        return self._restriccion_generacion_service().set_limites_docente_simple(
            usuario_id, min_horas_dia, max_horas_dia
        )

    def listar_limites_docente(self) -> list[LimitesDocente]:
        """Lista los límites diarios de todos los docentes (delega en RestriccionGeneracionService)."""
        return self._restriccion_generacion_service().listar_limites_docente()


__all__ = ["InfraestructuraService"]
