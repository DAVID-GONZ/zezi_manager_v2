"""
src/services/escenario_horario_service.py
==========================================
Sub-servicio cohesivo del subdominio de Escenarios de horario (mejora_01).
Extraído de InfraestructuraService: get/listar/crear/actualizar/activar/
eliminar/duplicar escenario + listar_horario_*_escenario. Recibe el mismo
IInfraestructuraRepository por inyección; la lógica se movió idéntica.
"""

from __future__ import annotations

from src.domain.models.infraestructura import EscenarioHorario, HorarioInfo
from src.domain.ports.infraestructura_repo import IInfraestructuraRepository
from src.services.solo_lectura import requiere_escritura


class EscenarioHorarioService:
    def __init__(self, repo: IInfraestructuraRepository) -> None:
        """Inyecta el repositorio de infraestructura."""
        self._repo = repo

    # ── Escenarios ────────────────────────────────────────────────────────────

    def get_escenario(self, escenario_id: int) -> EscenarioHorario | None:
        """Retorna un escenario por id (delegado al repositorio)."""
        return self._repo.get_escenario(escenario_id)

    def listar_escenarios(self, anio_id: int) -> list[EscenarioHorario]:
        """Lista los escenarios de un año lectivo (delegado al repositorio)."""
        return self._repo.listar_escenarios(anio_id)

    def get_escenario_activo(self, anio_id: int) -> EscenarioHorario | None:
        """Retorna el escenario activo de un año (delegado al repositorio)."""
        return self._repo.get_escenario_activo(anio_id)

    @requiere_escritura
    def crear_escenario(self, esc: EscenarioHorario) -> EscenarioHorario:
        """Crea un escenario (delegado al repositorio)."""
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
        """Actualiza un escenario (delegado al repositorio)."""
        return self._repo.actualizar_escenario(esc)

    def renombrar_escenario(
        self, esc_existente, nombre: str, descripcion: str | None = None
    ) -> EscenarioHorario:
        """Actualiza nombre/descripción de un escenario usando el objeto ya cargado."""
        updated = esc_existente.model_copy(
            update={
                "nombre": nombre,
                "descripcion": descripcion
                if descripcion is not None
                else esc_existente.descripcion,
            }
        )
        return self._repo.actualizar_escenario(updated)

    @requiere_escritura
    def activar_escenario(self, escenario_id: int) -> None:
        """Marca un escenario como activo (delegado al repositorio)."""
        return self._repo.activar_escenario(escenario_id)

    @requiere_escritura
    def eliminar_escenario(self, escenario_id: int) -> bool:
        """Elimina un escenario (delegado al repositorio)."""
        return self._repo.eliminar_escenario(escenario_id)

    @requiere_escritura
    def duplicar_escenario(self, escenario_id: int, nuevo_nombre: str) -> EscenarioHorario:
        """Duplica un escenario con un nuevo nombre (delegado al repositorio)."""
        return self._repo.duplicar_escenario(escenario_id, nuevo_nombre)

    def listar_horario_grupo_escenario(self, grupo_id: int, escenario_id: int) -> list[HorarioInfo]:
        """Lista el horario de un grupo dentro de un escenario (delegado al repositorio)."""
        return self._repo.listar_horario_grupo_escenario(grupo_id, escenario_id)

    def listar_horario_escenario(self, escenario_id: int) -> list[HorarioInfo]:
        """Lista todos los bloques de un escenario (delegado al repositorio)."""
        return self._repo.listar_horario_escenario(escenario_id)

    def contar_bloques(self, escenario_id: int) -> int:
        """Número de bloques horarios persistidos en un escenario.

        DEUDA (horario_01 T6): el puerto solo expone conteos acotados
        (`contar_bloques_asignacion`, `contar_bloques_docente`); no hay un
        `COUNT(*)` por escenario, así que aquí se traen las filas y se cuentan
        en memoria. Cuando se añada la consulta de conteo al repositorio,
        sustituir por la delegación directa sin cambiar esta firma.
        """
        if not escenario_id:
            return 0
        return len(self._repo.listar_horario_escenario(escenario_id))

    def tiene_bloques(self, escenario_id: int) -> bool:
        """¿El escenario tiene al menos un bloque persistido?

        Un escenario `"generado"` pero vacío no es activable (principio P3 de
        `horario_01_validacion_generacion`): activarlo desactivaría el horario
        real del año lectivo sin poner nada en su lugar.
        """
        return self.contar_bloques(escenario_id) > 0


__all__ = ["EscenarioHorarioService"]
