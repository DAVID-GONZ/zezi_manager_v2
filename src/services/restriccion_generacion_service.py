"""
src/services/restriccion_generacion_service.py
===============================================
Sub-servicio cohesivo del subdominio de Restricciones y configuración de
generación (mejora_01). Extraído de InfraestructuraService: config_generacion,
ventanas de grupo, bloques anclados, franjas de reunión, límites docente y
disponibilidad docente. Recibe el mismo IInfraestructuraRepository por
inyección; la lógica se movió idéntica (firmas, retornos y `@requiere_escritura`).
"""

from __future__ import annotations

from src.domain.models.infraestructura import (
    BloqueAnclado,
    ConfigGeneracion,
    DisponibilidadDocente,
    FranjaReunion,
    LimitesDocente,
    VentanaGrupo,
)
from src.domain.ports.infraestructura_repo import IInfraestructuraRepository
from src.services.solo_lectura import requiere_escritura


class RestriccionGeneracionService:
    def __init__(self, repo: IInfraestructuraRepository) -> None:
        """Inyecta el repositorio de infraestructura."""
        self._repo = repo

    # ── Disponibilidad docente (paso_15b) ─────────────────────────────────────

    def es_disponible_docente(self, usuario_id: int, dia: str, franja_orden: int) -> bool:
        """Indica si un docente está disponible en una franja (delegado al repositorio)."""
        return self._repo.es_disponible(usuario_id, dia, franja_orden)

    def bloquear_franjas_docente(self, usuario_id: int, slots: list[dict]) -> int:
        """Carga en lote las franjas no disponibles de un docente (delegado al repositorio)."""
        return self._repo.cargar_disponibilidad_lote(usuario_id, slots)

    def limpiar_disponibilidad_docente(self, usuario_id: int) -> int:
        """Borra toda la disponibilidad configurada de un docente (delegado al repositorio)."""
        return self._repo.limpiar_disponibilidad_docente(usuario_id)

    @requiere_escritura
    def guardar_disponibilidad_docente(self, usuario_id: int, slots: list[dict]) -> int:
        """Reemplaza ATÓMICAMENTE la disponibilidad de un docente (borra + carga
        en una sola transacción). `slots` son los bloques NO disponibles, cada uno
        con 'dia_semana' y 'franja_orden'. Retorna cuántos slots quedaron cargados.
        """
        return self._repo.reemplazar_disponibilidad_docente(usuario_id, slots)

    def listar_disponibilidad_docente(self, usuario_id: int) -> list[DisponibilidadDocente]:
        """Lista la disponibilidad configurada de un docente (delegado al repositorio)."""
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
        """Crea una config de generación a partir de primitivos (la UI no importa modelos)."""
        from src.domain.models.infraestructura import (
            NuevaConfigGeneracionDTO,
            PesosGeneracion,
        )

        pesos_obj = PesosGeneracion(**pesos) if isinstance(pesos, dict) else PesosGeneracion()
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

    def listar_configs_generacion(self, periodo_id: int | None = None) -> list[ConfigGeneracion]:
        """Lista las configs de generación, opcionalmente de un periodo (delegado al repositorio)."""
        return self._repo.listar_configs_generacion(periodo_id)

    def get_config_generacion(self, config_id: int) -> ConfigGeneracion | None:
        """Retorna una config de generación por id (delegado al repositorio)."""
        return self._repo.get_config_generacion(config_id)

    @requiere_escritura
    def actualizar_config_generacion(self, config_id: int, **campos) -> ConfigGeneracion:
        """Actualiza los campos indicados de una config de generación (lanza si no existe)."""
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
        """Elimina una config de generación (delegado al repositorio)."""
        return self._repo.eliminar_config_generacion(config_id)

    @requiere_escritura
    def cambiar_estado_config(self, config_id: int, nuevo_estado: str) -> ConfigGeneracion:
        """Cambia el estado de una config de generación (delegado al repositorio)."""
        return self._repo.cambiar_estado_config(config_id, nuevo_estado)

    @requiere_escritura
    def duplicar_config_generacion(self, config_id: int) -> ConfigGeneracion:
        """Duplica una config de generación (delegado al repositorio)."""
        return self._repo.duplicar_config_generacion(config_id)

    # ── VentanaGrupo (paso_17) ────────────────────────────────────────────────

    def listar_ventanas_grupo(self) -> list[VentanaGrupo]:
        """Lista todas las ventanas de grupo (delegado al repositorio)."""
        return self._repo.listar_ventanas_grupo()

    def get_ventanas_por_grupo(self, grupo_id: int) -> list[VentanaGrupo]:
        """Lista las ventanas de un grupo (delegado al repositorio)."""
        return self._repo.get_ventanas_por_grupo(grupo_id)

    def get_ventanas_por_grado(self, grado: int) -> list[VentanaGrupo]:
        """Lista las ventanas de un grado (delegado al repositorio)."""
        return self._repo.get_ventanas_por_grado(grado)

    @requiere_escritura
    def crear_ventana_grupo(self, v: VentanaGrupo) -> VentanaGrupo:
        """Crea una ventana de grupo (delegado al repositorio)."""
        return self._repo.crear_ventana_grupo(v)

    @requiere_escritura
    def eliminar_ventana_grupo(self, ventana_id: int) -> bool:
        """Elimina una ventana de grupo (delegado al repositorio)."""
        return self._repo.eliminar_ventana_grupo(ventana_id)

    # ── BloqueAnclado (paso_17) ───────────────────────────────────────────────

    def listar_bloques_anclados(self, escenario_id: int) -> list[BloqueAnclado]:
        """Lista los bloques anclados de un escenario (delegado al repositorio)."""
        return self._repo.listar_bloques_anclados(escenario_id)

    @requiere_escritura
    def crear_bloque_anclado(self, b: BloqueAnclado) -> BloqueAnclado:
        """Crea un bloque anclado (delegado al repositorio)."""
        return self._repo.crear_bloque_anclado(b)

    @requiere_escritura
    def eliminar_bloque_anclado(self, bloque_id: int) -> bool:
        """Elimina un bloque anclado (delegado al repositorio)."""
        return self._repo.eliminar_bloque_anclado(bloque_id)

    # ── FranjaReunion (paso_17) ───────────────────────────────────────────────

    def listar_franjas_reunion(self) -> list[FranjaReunion]:
        """Lista las franjas de reunión del tenant activo."""
        from src.services.contexto_tenant import institucion_actual

        return self._repo.listar_franjas_reunion(institucion_id=institucion_actual())

    def get_franja_reunion(self, franja_id: int) -> FranjaReunion | None:
        """Retorna una franja de reunión por id (delegado al repositorio)."""
        return self._repo.get_franja_reunion(franja_id)

    @requiere_escritura
    def crear_franja_reunion(self, f: FranjaReunion) -> FranjaReunion:
        """Crea una franja de reunión inyectando el tenant si falta."""
        if f.institucion_id is None:
            from src.services.contexto_tenant import institucion_actual

            inst_id = institucion_actual()
            if inst_id is None:
                try:
                    from container import Container

                    inst_id = Container.institucion_service().id_por_defecto()
                except Exception:
                    pass
            if inst_id is not None:
                f = f.model_copy(update={"institucion_id": inst_id})
        return self._repo.crear_franja_reunion(f)

    @requiere_escritura
    def actualizar_franja_reunion(self, f: FranjaReunion) -> FranjaReunion:
        """Actualiza una franja de reunión (lanza si no tiene id)."""
        if f.id is None:
            raise ValueError("La franja de reunión no tiene id.")
        return self._repo.actualizar_franja_reunion(f)

    @requiere_escritura
    def eliminar_franja_reunion(self, franja_id: int) -> bool:
        """Elimina una franja de reunión (delegado al repositorio)."""
        return self._repo.eliminar_franja_reunion(franja_id)

    # ── LimitesDocente (paso_17) ──────────────────────────────────────────────

    def get_limites_docente(self, usuario_id: int) -> LimitesDocente | None:
        """Retorna los límites diarios de un docente (delegado al repositorio)."""
        return self._repo.get_limites_docente(usuario_id)

    @requiere_escritura
    def set_limites_docente(self, limites: LimitesDocente) -> LimitesDocente:
        """Crea o actualiza los límites diarios de un docente (delegado al repositorio)."""
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
        """Lista los límites diarios de todos los docentes (delegado al repositorio)."""
        return self._repo.listar_limites_docente()


__all__ = ["RestriccionGeneracionService"]
