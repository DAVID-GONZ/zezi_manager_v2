"""
src/services/infraestructura_service.py
========================================
Fachada sobre IInfraestructuraRepository que expone a la capa de
interfaz las operaciones sobre AreaConocimiento, Asignatura, Grupo,
Horario y Logro sin revelar el repositorio directamente.
"""
from __future__ import annotations

from src.services.solo_lectura import requiere_escritura

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

    # ── Resolución de institución (multi-tenant — paso_29, frente B1) ──────────

    @staticmethod
    def _resolver_institucion(institucion_id: int | None) -> int | None:
        """
        Resuelve el tenant en este orden (espejo de configuracion_service):
          1. `institucion_id` explícito (el caller manda y no se toca).
          2. `institucion_actual()` — scope de la sesión (director → su
             institución; admin → None, ve todo).
          3. `id_por_defecto()` (#1) — fallback de arranque/seed sin sesión.

        Devuelve None si no hay catálogo de instituciones todavía (single-tenant
        temprano) o si el Container no está disponible (tests con repos falsos).
        """
        if institucion_id is not None:
            return institucion_id
        from src.services.contexto_tenant import institucion_actual
        scope = institucion_actual()
        if scope is not None:
            return scope
        try:
            from container import Container
            return Container.institucion_service().id_por_defecto()
        except Exception:
            return None

    # ── Autorización a nivel de objeto (paso_36 — hallazgo E) ───────────────────

    @staticmethod
    def _verificar_pertenencia_obj(obj, etiqueta: str) -> None:
        """
        Verifica que `obj` (leído del repo por su id) pertenezca a la institución
        activa. `obj` None → ValueError (no existe). Scope None (admin/seed) → pasa.
        """
        if obj is None:
            raise ValueError(f"{etiqueta} no existe.")
        from src.services.contexto_tenant import verificar_pertenencia
        verificar_pertenencia(obj.institucion_id)

    # ── Escenarios ────────────────────────────────────────────────────────────

    def get_escenario(self, escenario_id: int) -> EscenarioHorario | None:
        return self._repo.get_escenario(escenario_id)

    def listar_escenarios(self, anio_id: int) -> list[EscenarioHorario]:
        return self._repo.listar_escenarios(anio_id)

    def get_escenario_activo(self, anio_id: int) -> EscenarioHorario | None:
        return self._repo.get_escenario_activo(anio_id)

    @requiere_escritura
    def crear_escenario(self, esc: EscenarioHorario) -> EscenarioHorario:
        return self._repo.crear_escenario(esc)

    @requiere_escritura
    def crear_escenario_simple(
        self, anio_id: int, nombre: str, descripcion: str | None = None
    ) -> EscenarioHorario:
        """Crea un escenario a partir de parámetros primitivos (sin importar el modelo en la UI)."""
        from src.domain.models.infraestructura import NuevoEscenarioDTO
        dto = NuevoEscenarioDTO(anio_id=anio_id, nombre=nombre, descripcion=descripcion)
        return self._repo.crear_escenario(dto.to_escenario())

    @requiere_escritura
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

    @requiere_escritura
    def activar_escenario(self, escenario_id: int) -> None:
        return self._repo.activar_escenario(escenario_id)

    @requiere_escritura
    def eliminar_escenario(self, escenario_id: int) -> bool:
        return self._repo.eliminar_escenario(escenario_id)

    @requiere_escritura
    def duplicar_escenario(self, escenario_id: int, nuevo_nombre: str) -> EscenarioHorario:
        return self._repo.duplicar_escenario(escenario_id, nuevo_nombre)

    def listar_horario_grupo_escenario(
        self, grupo_id: int, escenario_id: int
    ) -> list[HorarioInfo]:
        return self._repo.listar_horario_grupo_escenario(grupo_id, escenario_id)

    def listar_horario_escenario(self, escenario_id: int) -> list[HorarioInfo]:
        return self._repo.listar_horario_escenario(escenario_id)

    # ── Plantillas de franja (rejilla) ─────────────────────────────────────────

    @requiere_escritura
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
        # Multi-tenant (paso_32): asigna la institución del scope (o #1 en
        # seed/arranque) si no viene ya en la plantilla.
        plantilla = dto.to_plantilla()
        institucion_id = self._resolver_institucion(plantilla.institucion_id)
        plantilla = plantilla.model_copy(update={"institucion_id": institucion_id})
        return self._repo.crear_plantilla_franja(plantilla)

    def listar_plantillas(self) -> list[PlantillaFranja]:
        # Scope multi-tenant (paso_32): None (admin / arranque) → sin filtro;
        # director → su institución.
        from src.services.contexto_tenant import institucion_actual
        return self._repo.listar_plantillas_franja(
            institucion_id=institucion_actual()
        )

    def plantilla_activa(self, jornada: str = "UNICA") -> PlantillaFranja | None:
        # Scope multi-tenant (paso_32): la plantilla activa es por institución.
        from src.services.contexto_tenant import institucion_actual
        return self._repo.get_plantilla_activa(
            jornada, institucion_id=institucion_actual()
        )

    @requiere_escritura
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

    @requiere_escritura
    def activar_plantilla(self, plantilla_id: int) -> None:
        return self._repo.activar_plantilla_franja(plantilla_id)

    @requiere_escritura
    def eliminar_plantilla(self, plantilla_id: int) -> bool:
        # Autorización a nivel de objeto (paso_36): la plantilla debe ser del
        # tenant activo (se lee del repo por id; scope None → cross-tenant).
        self._verificar_pertenencia_obj(
            self._repo.get_plantilla_franja(plantilla_id), "La plantilla"
        )
        return self._repo.eliminar_plantilla_franja(plantilla_id)

    # ── Áreas ─────────────────────────────────────────────────────────────────

    def listar_areas(self) -> list[AreaConocimiento]:
        return self._repo.listar_areas()

    @requiere_escritura
    def guardar_area(self, area: AreaConocimiento) -> AreaConocimiento:
        return self._repo.guardar_area(area)

    @requiere_escritura
    def actualizar_area(self, area: AreaConocimiento) -> AreaConocimiento:
        return self._repo.actualizar_area(area)

    @requiere_escritura
    def eliminar_area(self, area_id: int) -> bool:
        return self._repo.eliminar_area(area_id)

    @requiere_escritura
    def set_color_area(self, area_id: int, color: str | None) -> bool:
        """Asigna (o limpia) el color hex de un área. Valida vía el modelo."""
        normalizado = AreaConocimiento(id=area_id, nombre="_", color=color).color
        return self._repo.actualizar_color_area(area_id, normalizado)

    # ── Asignaturas ───────────────────────────────────────────────────────────

    def listar_asignaturas(self, area_id: int | None = None) -> list[Asignatura]:
        # Scope multi-tenant (paso_29): None (admin / arranque) → sin filtro de
        # institución (ve todo); director → su institución. NO se cae al
        # id_por_defecto aquí: admin debe ver todas las instituciones.
        from src.services.contexto_tenant import institucion_actual
        return self._repo.listar_asignaturas(
            area_id=area_id, institucion_id=institucion_actual()
        )

    @requiere_escritura
    def guardar_asignatura(self, asignatura: Asignatura) -> Asignatura:
        # Asigna la institución del scope (o #1 en seed/arranque) si no viene ya.
        institucion_id = self._resolver_institucion(asignatura.institucion_id)
        asignatura = asignatura.model_copy(update={"institucion_id": institucion_id})
        return self._repo.guardar_asignatura(asignatura)

    @requiere_escritura
    def actualizar_asignatura(self, asignatura: Asignatura) -> Asignatura:
        # Autorización a nivel de objeto (paso_36): se lee la asignatura
        # persistida por id y se verifica su tenant; NO se confía en el
        # institucion_id del objeto recibido (podría venir forjado). Además se
        # preserva la institución existente (un update no puede mover de tenant).
        actual = self._repo.get_asignatura(asignatura.id)
        self._verificar_pertenencia_obj(actual, "La asignatura")
        asignatura = asignatura.model_copy(
            update={"institucion_id": actual.institucion_id}
        )
        return self._repo.actualizar_asignatura(asignatura)

    @requiere_escritura
    def eliminar_asignatura(self, asignatura_id: int) -> bool:
        self._verificar_pertenencia_obj(
            self._repo.get_asignatura(asignatura_id), "La asignatura"
        )
        return self._repo.eliminar_asignatura(asignatura_id)

    # ── Grupos ────────────────────────────────────────────────────────────────

    def listar_grupos(self, grado: int | None = None) -> list[Grupo]:
        # Scope multi-tenant (paso_29): None (admin / arranque) → sin filtro;
        # director → su institución.
        from src.services.contexto_tenant import institucion_actual
        return self._repo.listar_grupos(
            grado=grado, institucion_id=institucion_actual()
        )

    @requiere_escritura
    def guardar_grupo(self, grupo: Grupo) -> Grupo:
        # Asigna la institución del scope (o #1 en seed/arranque) si no viene ya.
        institucion_id = self._resolver_institucion(grupo.institucion_id)
        grupo = grupo.model_copy(update={"institucion_id": institucion_id})
        return self._repo.guardar_grupo(grupo)

    @requiere_escritura
    def asignar_sala_a_grupo(self, grupo_id: int, sala_id: int | None) -> bool:
        """Asigna (o quita, con None) el aula propia de un grupo."""
        return self._repo.asignar_sala_a_grupo(grupo_id, sala_id)

    @requiere_escritura
    def actualizar_grupo(self, grupo: Grupo) -> Grupo:
        # Autorización a nivel de objeto (paso_36): tenant verificado contra el
        # grupo persistido; institución preservada (no se permite mover de tenant).
        actual = self._repo.get_grupo(grupo.id)
        self._verificar_pertenencia_obj(actual, "El grupo")
        grupo = grupo.model_copy(update={"institucion_id": actual.institucion_id})
        return self._repo.actualizar_grupo(grupo)

    @requiere_escritura
    def eliminar_grupo(self, grupo_id: int) -> bool:
        self._verificar_pertenencia_obj(
            self._repo.get_grupo(grupo_id), "El grupo"
        )
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

    @requiere_escritura
    def guardar_horario(self, horario: Horario) -> Horario:
        return self._repo.guardar_horario(horario)

    @requiere_escritura
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

    @requiere_escritura
    def guardar_disponibilidad_docente(
        self, usuario_id: int, slots: list[dict]
    ) -> int:
        """Reemplaza ATÓMICAMENTE la disponibilidad de un docente (borra + carga
        en una sola transacción). `slots` son los bloques NO disponibles, cada uno
        con 'dia_semana' y 'franja_orden'. Retorna cuántos slots quedaron cargados.
        """
        return self._repo.reemplazar_disponibilidad_docente(usuario_id, slots)

    def listar_disponibilidad_docente(
        self, usuario_id: int
    ) -> list[DisponibilidadDocente]:
        return self._repo.listar_disponibilidad_docente(usuario_id)

    # ── Config generación (paso_15b) ──────────────────────────────────────────

    @requiere_escritura
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
            restricciones=restricciones if restricciones is not None else {},
        )
        return self._repo.crear_config_generacion(dto.to_config())

    def construir_restricciones(
        self, min_horas: int, max_horas: int, modo: str = "preferente"
    ) -> dict:
        """Ensambla el payload de restricciones de generación a partir de
        primitivas, para que la interfaz no construya el dict anidado.

        Solo incluye ``min_max_diario`` cuando el rango difiere del default
        (mín > 0 o máx < 8); de lo contrario devuelve ``{}`` (sin restricción).
        """
        min_h = int(min_horas or 0)
        max_h = int(max_horas if max_horas is not None else 8)
        restricciones: dict = {}
        if min_h > 0 or max_h < 8:
            restricciones["min_max_diario"] = {
                "modo": modo,
                "min": min_h,
                "max": max_h,
            }
        return restricciones

    def listar_configs_generacion(
        self, periodo_id: int | None = None
    ) -> list[ConfigGeneracion]:
        return self._repo.listar_configs_generacion(periodo_id)

    def get_config_generacion(self, config_id: int) -> ConfigGeneracion | None:
        return self._repo.get_config_generacion(config_id)

    @requiere_escritura
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

    @requiere_escritura
    def eliminar_config_generacion(self, config_id: int) -> bool:
        return self._repo.eliminar_config_generacion(config_id)

    @requiere_escritura
    def cambiar_estado_config(
        self, config_id: int, nuevo_estado: str
    ) -> ConfigGeneracion:
        return self._repo.cambiar_estado_config(config_id, nuevo_estado)

    @requiere_escritura
    def duplicar_config_generacion(self, config_id: int) -> ConfigGeneracion:
        return self._repo.duplicar_config_generacion(config_id)

    # ── Salas (paso_17) ───────────────────────────────────────────────────────

    def listar_salas(self) -> list[Sala]:
        # Scope multi-tenant (paso_32): None (admin / arranque) → sin filtro;
        # director → su institución.
        from src.services.contexto_tenant import institucion_actual
        return self._repo.listar_salas(institucion_id=institucion_actual())

    def get_sala(self, sala_id: int) -> Sala | None:
        return self._repo.get_sala(sala_id)

    @requiere_escritura
    def crear_sala(self, sala: Sala) -> Sala:
        # Asigna la institución del scope (o #1 en seed/arranque) si no viene ya.
        institucion_id = self._resolver_institucion(sala.institucion_id)
        sala = sala.model_copy(update={"institucion_id": institucion_id})
        return self._repo.crear_sala(sala)

    @requiere_escritura
    def actualizar_sala(self, sala: Sala) -> Sala:
        if sala.id is None:
            raise ValueError("La sala no tiene id.")
        # Autorización a nivel de objeto (paso_36): tenant verificado contra la
        # sala persistida; institución preservada (no se permite mover de tenant).
        actual = self._repo.get_sala(sala.id)
        self._verificar_pertenencia_obj(actual, "La sala")
        sala = sala.model_copy(update={"institucion_id": actual.institucion_id})
        return self._repo.actualizar_sala(sala)

    @requiere_escritura
    def eliminar_sala(self, sala_id: int) -> bool:
        self._verificar_pertenencia_obj(
            self._repo.get_sala(sala_id), "La sala"
        )
        return self._repo.eliminar_sala(sala_id)

    # ── VentanaGrupo (paso_17) ────────────────────────────────────────────────

    def listar_ventanas_grupo(self) -> list[VentanaGrupo]:
        return self._repo.listar_ventanas_grupo()

    def get_ventanas_por_grupo(self, grupo_id: int) -> list[VentanaGrupo]:
        return self._repo.get_ventanas_por_grupo(grupo_id)

    def get_ventanas_por_grado(self, grado: int) -> list[VentanaGrupo]:
        return self._repo.get_ventanas_por_grado(grado)

    @requiere_escritura
    def crear_ventana_grupo(self, v: VentanaGrupo) -> VentanaGrupo:
        return self._repo.crear_ventana_grupo(v)

    @requiere_escritura
    def eliminar_ventana_grupo(self, ventana_id: int) -> bool:
        return self._repo.eliminar_ventana_grupo(ventana_id)

    # ── BloqueAnclado (paso_17) ───────────────────────────────────────────────

    def listar_bloques_anclados(self, escenario_id: int) -> list[BloqueAnclado]:
        return self._repo.listar_bloques_anclados(escenario_id)

    @requiere_escritura
    def crear_bloque_anclado(self, b: BloqueAnclado) -> BloqueAnclado:
        return self._repo.crear_bloque_anclado(b)

    @requiere_escritura
    def eliminar_bloque_anclado(self, bloque_id: int) -> bool:
        return self._repo.eliminar_bloque_anclado(bloque_id)

    # ── FranjaReunion (paso_17) ───────────────────────────────────────────────

    def listar_franjas_reunion(self) -> list[FranjaReunion]:
        return self._repo.listar_franjas_reunion()

    def get_franja_reunion(self, franja_id: int) -> FranjaReunion | None:
        return self._repo.get_franja_reunion(franja_id)

    @requiere_escritura
    def crear_franja_reunion(self, f: FranjaReunion) -> FranjaReunion:
        return self._repo.crear_franja_reunion(f)

    @requiere_escritura
    def actualizar_franja_reunion(self, f: FranjaReunion) -> FranjaReunion:
        if f.id is None:
            raise ValueError("La franja de reunión no tiene id.")
        return self._repo.actualizar_franja_reunion(f)

    @requiere_escritura
    def eliminar_franja_reunion(self, franja_id: int) -> bool:
        return self._repo.eliminar_franja_reunion(franja_id)

    # ── LimitesDocente (paso_17) ──────────────────────────────────────────────

    def get_limites_docente(self, usuario_id: int) -> LimitesDocente | None:
        return self._repo.get_limites_docente(usuario_id)

    @requiere_escritura
    def set_limites_docente(self, limites: LimitesDocente) -> LimitesDocente:
        return self._repo.set_limites_docente(limites)

    @requiere_escritura
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
