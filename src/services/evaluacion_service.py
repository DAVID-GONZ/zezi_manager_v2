"""
EvaluacionService
==================
Orquesta los casos de uso del módulo de Evaluación
(categorías, actividades, notas y puntos extra).
"""
from __future__ import annotations

from src.domain.ports.evaluacion_repo import IEvaluacionRepository
from src.domain.ports.asignacion_repo import IAsignacionRepository
from src.domain.ports.periodo_repo import IPeriodoRepository
from src.domain.ports.auditoria_repo import IAuditoriaRepository
from src.domain.models.evaluacion import (
    Actividad,
    CalculadorNotas,
    Categoria,
    EstadoActividad,
    Nota,
    NuevaCategoriaDTO,
    ActualizarCategoriaDTO,
    NuevaActividadDTO,
    PuntosExtra,
    RegistrarNotaDTO,
    RegistrarNotasMasivasDTO,
    ResultadoEstudianteDTO,
)
from src.domain.models.dtos import ContextoAcademicoDTO
from src.domain.models.auditoria import AccionCambio, RegistroCambio


class EvaluacionService:
    """
    Orquesta los casos de uso del módulo de Evaluación.
    No contiene SQL. No contiene lógica de presentación.
    """

    def __init__(
        self,
        repo: IEvaluacionRepository,
        asignacion_repo: IAsignacionRepository | None = None,
        periodo_repo: IPeriodoRepository | None = None,
        auditoria: IAuditoriaRepository | None = None,
    ) -> None:
        self._repo           = repo
        self._asignacion_repo = asignacion_repo
        self._periodo_repo   = periodo_repo
        self._auditoria      = auditoria

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _auditar(
        self,
        accion: AccionCambio,
        tabla: str,
        registro_id: int | None,
        datos_ant: dict | None,
        datos_nue: dict | None,
        usuario_id: int | None,
    ) -> None:
        if self._auditoria is None:
            return
        if accion == AccionCambio.CREATE:
            cambio = RegistroCambio.para_creacion(
                tabla, datos_nue or {}, registro_id, usuario_id
            )
        elif accion == AccionCambio.UPDATE:
            cambio = RegistroCambio.para_actualizacion(
                tabla, datos_ant or {}, datos_nue or {}, registro_id, usuario_id
            )
        else:
            cambio = RegistroCambio.para_eliminacion(
                tabla, datos_ant or {}, registro_id, usuario_id
            )
        self._auditoria.registrar_cambio(cambio)

    def _verificar_periodo_abierto(self, periodo_id: int) -> None:
        if self._periodo_repo is None:
            return
        periodo = self._periodo_repo.get_by_id(periodo_id)
        if periodo is not None and not periodo.esta_abierto:
            raise ValueError(
                f"El periodo con id {periodo_id} está cerrado. "
                "No se pueden registrar cambios en periodos cerrados."
            )

    def _get_categoria_o_lanzar(self, cat_id: int) -> Categoria:
        cat = self._repo.get_categoria(cat_id)
        if cat is None:
            raise ValueError(f"Categoría con id {cat_id} no existe.")
        return cat

    def _get_actividad_o_lanzar(self, act_id: int) -> Actividad:
        act = self._repo.get_actividad(act_id)
        if act is None:
            raise ValueError(f"Actividad con id {act_id} no existe.")
        return act

    # ------------------------------------------------------------------
    # Categorías
    # ------------------------------------------------------------------

    def agregar_categoria(
        self,
        dto: NuevaCategoriaDTO,
        ctx: ContextoAcademicoDTO,
        usuario_id: int | None = None,
    ) -> Categoria:
        """
        Agrega una categoría de evaluación.

        Verifica que el periodo no esté cerrado y que la suma de pesos
        no supere 1.0 (100%).
        """
        self._verificar_periodo_abierto(dto.periodo_id)

        suma = self._repo.suma_pesos_otras(dto.asignacion_id, dto.periodo_id)
        if suma + dto.peso > 1.001:
            raise ValueError(
                f"La suma de pesos de las categorías superaría el 100% "
                f"(actual: {suma*100:.1f}%, nueva: {dto.peso*100:.1f}%). "
                f"Disponible: {(1.0 - suma)*100:.1f}%."
            )

        categoria = dto.to_categoria()
        categoria = self._repo.guardar_categoria(categoria)
        self._auditar(
            AccionCambio.CREATE, "categorias", categoria.id,
            None, categoria.model_dump(mode="json"), usuario_id,
        )
        return categoria

    def actualizar_categoria(
        self,
        cat_id: int,
        dto: ActualizarCategoriaDTO,
        usuario_id: int | None = None,
    ) -> Categoria:
        """Actualiza nombre y/o peso de una categoría."""
        categoria = self._get_categoria_o_lanzar(cat_id)
        self._verificar_periodo_abierto(categoria.periodo_id)

        if dto.peso is not None and dto.peso != categoria.peso:
            suma_sin_esta = self._repo.suma_pesos_otras(
                categoria.asignacion_id, categoria.periodo_id,
                excluir_id=cat_id,
            )
            if suma_sin_esta + dto.peso > 1.001:
                raise ValueError(
                    f"La suma de pesos superaría el 100% con el nuevo peso "
                    f"({dto.peso*100:.1f}%). Disponible: {(1.0 - suma_sin_esta)*100:.1f}%."
                )

        datos_ant = categoria.model_dump(mode="json")
        categoria_actualizada = dto.aplicar_a(categoria)
        self._repo.actualizar_categoria(categoria_actualizada)
        self._auditar(
            AccionCambio.UPDATE, "categorias", cat_id,
            datos_ant, categoria_actualizada.model_dump(mode="json"), usuario_id,
        )
        return categoria_actualizada

    def eliminar_categoria(
        self,
        cat_id: int,
        usuario_id: int | None = None,
    ) -> None:
        """
        Elimina una categoría y sus actividades y notas asociadas
        (mediante la cascada de la BD).
        """
        categoria = self._get_categoria_o_lanzar(cat_id)
        self._verificar_periodo_abierto(categoria.periodo_id)
        datos_ant = categoria.model_dump(mode="json")
        self._repo.eliminar_categoria(cat_id)
        self._auditar(
            AccionCambio.DELETE, "categorias", cat_id,
            datos_ant, None, usuario_id,
        )

    def listar_categorias(
        self,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[Categoria]:
        """Retorna las categorías de la asignación en el periodo."""
        return self._repo.listar_categorias(asignacion_id, periodo_id)

    # ------------------------------------------------------------------
    # Actividades
    # ------------------------------------------------------------------

    def agregar_actividad(
        self,
        dto: NuevaActividadDTO,
        usuario_id: int | None = None,
    ) -> Actividad:
        """Crea una actividad evaluativa en estado borrador."""
        actividad = dto.to_actividad()
        actividad = self._repo.guardar_actividad(actividad)
        self._auditar(
            AccionCambio.CREATE, "actividades", actividad.id,
            None, actividad.model_dump(mode="json"), usuario_id,
        )
        return actividad

    def publicar_actividad(
        self,
        act_id: int,
        usuario_id: int | None = None,
    ) -> Actividad:
        """Publica una actividad para que los estudiantes puedan verla."""
        actividad = self._get_actividad_o_lanzar(act_id)
        actividad_publicada = actividad.publicar()  # lanza si no está en borrador
        self._repo.actualizar_estado_actividad(act_id, EstadoActividad.PUBLICADA)
        self._auditar(
            AccionCambio.UPDATE, "actividades", act_id,
            actividad.model_dump(mode="json"),
            actividad_publicada.model_dump(mode="json"),
            usuario_id,
        )
        return actividad_publicada

    def cerrar_actividad(
        self,
        act_id: int,
        usuario_id: int | None = None,
    ) -> Actividad:
        """Cierra una actividad para que no acepte más notas."""
        actividad = self._get_actividad_o_lanzar(act_id)
        actividad_cerrada = actividad.cerrar()  # lanza si no está publicada
        self._repo.actualizar_estado_actividad(act_id, EstadoActividad.CERRADA)
        self._auditar(
            AccionCambio.UPDATE, "actividades", act_id,
            actividad.model_dump(mode="json"),
            actividad_cerrada.model_dump(mode="json"),
            usuario_id,
        )
        return actividad_cerrada

    def eliminar_actividad(
        self,
        act_id: int,
        usuario_id: int | None = None,
    ) -> None:
        """
        Elimina una actividad y sus notas asociadas.

        Solo se puede eliminar si no está cerrada.
        """
        actividad = self._get_actividad_o_lanzar(act_id)
        if actividad.estado == EstadoActividad.CERRADA:
            raise ValueError(
                f"No se puede eliminar la actividad '{actividad.nombre}' "
                "porque está cerrada."
            )
        datos_ant = actividad.model_dump(mode="json")
        self._repo.eliminar_actividad(act_id)
        self._auditar(
            AccionCambio.DELETE, "actividades", act_id,
            datos_ant, None, usuario_id,
        )

    def listar_actividades(
        self,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[Actividad]:
        """Retorna las actividades de la asignación en el periodo."""
        return self._repo.listar_actividades(asignacion_id, periodo_id)

    # ------------------------------------------------------------------
    # Notas
    # ------------------------------------------------------------------

    def registrar_nota(
        self,
        dto: RegistrarNotaDTO,
        ctx: ContextoAcademicoDTO,
        usuario_id: int | None = None,
    ) -> Nota:
        """
        Registra la nota de un estudiante en una actividad.

        Verifica que la actividad esté publicada y el periodo abierto.
        """
        actividad = self._get_actividad_o_lanzar(dto.actividad_id)
        if not actividad.acepta_notas:
            raise ValueError(
                f"La actividad '{actividad.nombre}' no acepta notas "
                f"(estado: '{actividad.estado.value}'). "
                "Solo las actividades publicadas aceptan notas."
            )
        self._verificar_periodo_abierto(ctx.periodo_id)

        nota = dto.to_nota(usuario_registro_id=usuario_id)
        nota = self._repo.guardar_nota(nota)
        return nota

    def registrar_notas_masivas(
        self,
        dto: RegistrarNotasMasivasDTO,
        ctx: ContextoAcademicoDTO,
        usuario_id: int | None = None,
    ) -> int:
        """
        Registra las notas de todos los estudiantes de un grupo para una actividad.

        Retorna el número de notas guardadas.
        """
        actividad = self._get_actividad_o_lanzar(dto.actividad_id)
        if not actividad.acepta_notas:
            raise ValueError(
                f"La actividad '{actividad.nombre}' no acepta notas "
                f"(estado: '{actividad.estado.value}')."
            )
        self._verificar_periodo_abierto(ctx.periodo_id)

        notas = dto.to_notas(usuario_registro_id=usuario_id)
        return self._repo.guardar_notas_masivas(notas)

    def obtener_planilla(
        self,
        asignacion_id: int,
        periodo_id: int,
        ctx: ContextoAcademicoDTO,
    ) -> list[ResultadoEstudianteDTO]:
        """
        Retorna la planilla de notas del grupo con definitivas calculadas.

        Para cada estudiante: calcula la definitiva con CalculadorNotas.
        """
        resultados = self._repo.listar_resultados_grupo(asignacion_id, periodo_id)
        categorias = self._repo.listar_categorias(asignacion_id, periodo_id)
        actividades = self._repo.listar_actividades(asignacion_id, periodo_id)

        for resultado in resultados:
            definitiva = CalculadorNotas.calcular_definitiva(
                resultado.notas, actividades, categorias
            )
            promedio_ajustado = CalculadorNotas.calcular_promedio_ajustado(
                resultado.notas, actividades, categorias
            )
            resultado.definitiva = definitiva
            resultado.promedio_ajustado = promedio_ajustado

        return resultados

    def guardar_puntos_extra(
        self,
        puntos: PuntosExtra,
        usuario_id: int | None = None,
    ) -> PuntosExtra:
        """Guarda o actualiza los puntos extra de un estudiante."""
        return self._repo.guardar_puntos_extra(puntos)


__all__ = ["EvaluacionService"]
