"""
ConvivenciaService
===================
Orquesta los casos de uso del módulo de Convivencia.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from src.domain.models.alerta import Alerta, NivelAlerta, TipoAlerta
from src.domain.models.convivencia import (
    ConceptoComportamientoDTO,
    FiltroConvivenciaDTO,
    NotaComportamiento,
    NuevaNotaComportamientoDTO,
    NuevaObservacionDTO,
    NuevoRegistroComportamientoDTO,
    ObservacionPeriodo,
    RegistroComportamiento,
    ReporteConvivenciaFilaDTO,
    TipoRegistro,
)
from src.domain.ports.alerta_repo import IAlertaRepository
from src.domain.ports.convivencia_repo import IConvivenciaRepository
from src.services.solo_lectura import requiere_escritura

if TYPE_CHECKING:
    from src.services.catalogo_academico_service import CatalogoAcademicoService
    from src.services.configuracion_service import ConfiguracionService
    from src.services.estudiante_service import EstudianteService
    from src.services.periodo_service import PeriodoService


class ConvivenciaService:
    """
    Orquesta los casos de uso del módulo de Convivencia.
    No contiene SQL. No contiene lógica de presentación.
    """

    def __init__(
        self,
        repo: IConvivenciaRepository,
        alerta_repo: IAlertaRepository | None = None,
        catalogo_academico_svc_provider: Callable[[], "CatalogoAcademicoService"] | None = None,
        configuracion_svc_provider: Callable[[], "ConfiguracionService"] | None = None,
        periodo_svc_provider: Callable[[], "PeriodoService"] | None = None,
        estudiante_svc_provider: Callable[[], "EstudianteService"] | None = None,
    ) -> None:
        """Inyecta el repositorio de convivencia y el de alertas (opcional).

        `catalogo_academico_svc_provider` es un proveedor lazy que devuelve el
        `CatalogoAcademicoService`; si es None, el enforcement de autorización
        queda desactivado (compat retro para scripts/seed/tests).

        `configuracion_svc_provider`, `periodo_svc_provider` y
        `estudiante_svc_provider` son proveedores lazy usados por
        `get_concepto_periodo` / `listar_conceptos_grupo` para resolver
        niveles de desempeño (por rango o por id) y el estudiantado del
        grupo respectivamente. Si son None, los métodos correspondientes
        lanzan RuntimeError.
        """
        self._repo        = repo
        self._alerta_repo = alerta_repo
        self._catalogo_academico_svc_provider = catalogo_academico_svc_provider
        self._configuracion_svc_provider = configuracion_svc_provider
        self._periodo_svc_provider = periodo_svc_provider
        self._estudiante_svc_provider = estudiante_svc_provider

    # ------------------------------------------------------------------
    # Autorización (defensa en profundidad — convivencia_04b)
    # ------------------------------------------------------------------

    def _verificar_autorizacion(
        self,
        usuario_rol: str | None,
        usuario_id: int | None,
        grupo_id: int | None,
    ) -> None:
        """Rechaza la mutación si el rol/usuario no puede gestionar el grupo.

        Sin provider inyectado → no-op (compat retro con scripts/tests).
        """
        if self._catalogo_academico_svc_provider is None:
            return
        if usuario_rol is None or usuario_id is None or grupo_id is None:
            # Sin información suficiente para autorizar → no bloqueamos (compat).
            return
        svc = self._catalogo_academico_svc_provider()
        if not svc.puede_gestionar_comportamiento_en_grupo(
            usuario_rol, usuario_id, grupo_id
        ):
            raise PermissionError(
                "No autorizado para gestionar el comportamiento de este grupo."
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_registro_o_lanzar(self, registro_id: int) -> RegistroComportamiento:
        reg = self._repo.get_registro(registro_id)
        if reg is None:
            raise ValueError(
                f"Registro de comportamiento con id {registro_id} no existe."
            )
        return reg

    def _get_observacion_o_lanzar(self, observacion_id: int) -> ObservacionPeriodo:
        obs = self._repo.get_observacion(observacion_id)
        if obs is None:
            raise ValueError(
                f"Observación con id {observacion_id} no existe."
            )
        return obs

    def _verificar_alerta_comportamiento(
        self,
        estudiante_id: int,
        anio_id: int,
        filtro: FiltroConvivenciaDTO,
    ) -> None:
        """
        Genera una alerta si el número de registros negativos supera el umbral.
        Solo actúa si el repositorio de alertas está disponible.
        """
        if self._alerta_repo is None:
            return

        cfg = self._alerta_repo.get_configuracion(
            anio_id, TipoAlerta.PLAN_MEJORAMIENTO_VENCIDO
        )
        # Reutilizamos un tipo de alerta apropiado; en ausencia de tipo específico
        # para comportamiento, se omite la alerta.
        if cfg is None or not cfg.activa:
            return

        conteo = self._repo.contar_registros(filtro)
        if conteo < cfg.umbral:
            return

        if self._alerta_repo.existe_pendiente(
            estudiante_id, TipoAlerta.PLAN_MEJORAMIENTO_VENCIDO
        ):
            return

        nivel = (
            NivelAlerta.CRITICA
            if conteo >= cfg.umbral * 2
            else NivelAlerta.ADVERTENCIA
        )
        alerta = Alerta(
            estudiante_id=estudiante_id,
            tipo_alerta=TipoAlerta.PLAN_MEJORAMIENTO_VENCIDO,
            nivel=nivel,
            descripcion=(
                f"El estudiante tiene {conteo} registro(s) negativos de comportamiento "
                f"(umbral configurado: {int(cfg.umbral)})."
            ),
        )
        self._alerta_repo.guardar_alerta(alerta)

    # ------------------------------------------------------------------
    # Observaciones de periodo
    # ------------------------------------------------------------------

    @requiere_escritura
    def registrar_observacion(
        self,
        dto: NuevaObservacionDTO,
        usuario_id: int | None = None,
    ) -> ObservacionPeriodo:
        """
        Registra una observación narrativa de un estudiante en un periodo.

        Si ya existe una observación para esa asignación/periodo/estudiante,
        se actualiza; si no, se crea una nueva.
        """
        existente = self._repo.get_observacion_por_asignacion(
            dto.estudiante_id, dto.asignacion_id, dto.periodo_id
        )

        if existente is not None:
            obs_actualizada = existente.model_copy(
                update={"texto": dto.texto, "es_publica": dto.es_publica}
            )
            return self._repo.actualizar_observacion(obs_actualizada)

        observacion = dto.to_observacion(usuario_id=usuario_id)
        return self._repo.guardar_observacion(observacion)

    def listar_observaciones(
        self,
        estudiante_id: int,
        periodo_id: int | None = None,
        solo_publicas: bool = False,
    ) -> list[ObservacionPeriodo]:
        """Retorna las observaciones de un estudiante."""
        return self._repo.listar_observaciones_por_estudiante(
            estudiante_id, periodo_id, solo_publicas
        )

    @requiere_escritura
    def eliminar_observacion(self, observacion_id: int) -> bool:
        """Elimina una observación. Retorna True si fue eliminada."""
        self._get_observacion_o_lanzar(observacion_id)
        return self._repo.eliminar_observacion(observacion_id)

    # ------------------------------------------------------------------
    # Registros de comportamiento
    # ------------------------------------------------------------------

    @requiere_escritura
    def registrar_comportamiento(
        self,
        dto: NuevoRegistroComportamientoDTO,
        usuario_id: int | None = None,
        anio_id: int | None = None,
        usuario_rol: str | None = None,
    ) -> RegistroComportamiento:
        """
        Registra un evento puntual de comportamiento.

        Después de guardar, verifica si se deben generar alertas para
        el estudiante (si hay repositorio de alertas y anio_id disponibles).
        """
        self._verificar_autorizacion(usuario_rol, usuario_id, dto.grupo_id)
        registro = dto.to_registro(usuario_id=usuario_id)
        registro = self._repo.guardar_registro(registro)

        # Verificar alertas si el registro es negativo
        if anio_id is not None and registro.es_negativo:
            filtro = FiltroConvivenciaDTO(
                estudiante_id=dto.estudiante_id,
                periodo_id=dto.periodo_id,
                solo_negativos=True,
            )
            self._verificar_alerta_comportamiento(
                dto.estudiante_id, anio_id, filtro
            )

        return registro

    def notificar_acudiente(
        self,
        registro_id: int,
        usuario_id: int | None = None,
        usuario_rol: str | None = None,
    ) -> RegistroComportamiento:
        """
        Marca un registro de comportamiento como notificado al acudiente.

        Transición de estado: acudiente_notificado=False → True.
        Lanza si el registro no existe o ya fue notificado.
        """
        registro = self._get_registro_o_lanzar(registro_id)
        self._verificar_autorizacion(usuario_rol, usuario_id, registro.grupo_id)
        registro_notificado = registro.registrar_notificacion()
        return self._repo.actualizar_registro(registro_notificado)

    @requiere_escritura
    def agregar_seguimiento(
        self,
        registro_id: int,
        texto: str,
        usuario_id: int | None = None,
        usuario_rol: str | None = None,
    ) -> RegistroComportamiento:
        """Agrega o actualiza el texto de seguimiento de un registro."""
        registro = self._get_registro_o_lanzar(registro_id)
        self._verificar_autorizacion(usuario_rol, usuario_id, registro.grupo_id)
        registro_con_seguimiento = registro.agregar_seguimiento(texto)
        return self._repo.actualizar_registro(registro_con_seguimiento)

    def listar_registros(
        self,
        filtro: FiltroConvivenciaDTO,
    ) -> list[RegistroComportamiento]:
        """Retorna registros de comportamiento según los filtros indicados.

        Multi-tenant (paso_32, T4): cuando el listado cruza grupos (filtro sin
        grupo ni estudiante) se acota por la institución del scope (director →
        su institución; admin / arranque → None = todas) vía join a `grupos`.
        """
        from src.services.contexto_tenant import institucion_actual
        return self._repo.listar_registros(
            filtro, institucion_id=institucion_actual()
        )

    @requiere_escritura
    def eliminar_registro(
        self,
        registro_id: int,
        usuario_id: int | None = None,
        usuario_rol: str | None = None,
    ) -> bool:
        """Elimina un registro de comportamiento. Retorna True si fue eliminado."""
        registro = self._get_registro_o_lanzar(registro_id)
        self._verificar_autorizacion(usuario_rol, usuario_id, registro.grupo_id)
        return self._repo.eliminar_registro(registro_id)

    # ------------------------------------------------------------------
    # Notas de comportamiento
    # ------------------------------------------------------------------

    @requiere_escritura
    def registrar_nota_comportamiento(
        self,
        dto: NuevaNotaComportamientoDTO,
        usuario_id: int | None = None,
        usuario_rol: str | None = None,
    ) -> NotaComportamiento:
        """
        Registra o actualiza la nota de comportamiento de un estudiante
        en un periodo (upsert: una nota por estudiante/grupo/periodo).
        """
        self._verificar_autorizacion(usuario_rol, usuario_id, dto.grupo_id)
        nota = dto.to_nota(usuario_id=usuario_id)
        return self._repo.guardar_nota(nota)

    def get_nota_comportamiento(
        self,
        estudiante_id: int,
        periodo_id: int,
    ) -> NotaComportamiento | None:
        """Retorna la nota de comportamiento de un estudiante en un periodo."""
        return self._repo.get_nota(estudiante_id, periodo_id)

    def listar_notas_grupo(
        self,
        grupo_id: int,
        periodo_id: int,
    ) -> list[NotaComportamiento]:
        """Retorna las notas de comportamiento de todos los estudiantes del grupo."""
        return self._repo.listar_notas_por_grupo(grupo_id, periodo_id)

    # ------------------------------------------------------------------
    # Concepto consolidado (cuant + cualit)  —  convivencia_05
    # ------------------------------------------------------------------

    def _resolver_niveles_del_periodo(self, periodo_id: int):
        """Retorna (anio_id, list[NivelDesempeno]) del año del periodo."""
        if self._periodo_svc_provider is None or self._configuracion_svc_provider is None:
            raise RuntimeError(
                "ConvivenciaService requiere periodo_svc_provider y "
                "configuracion_svc_provider para consolidar conceptos."
            )
        anio_id = self._periodo_svc_provider().get_by_id(periodo_id).anio_id
        niveles = self._configuracion_svc_provider().listar_niveles(anio_id)
        return anio_id, niveles

    @staticmethod
    def _elegir_nivel(nota: NotaComportamiento, niveles: list):
        """Nivel explícito por desempeno_id si está seteado; si no, por rango."""
        if nota.desempeno_id is not None:
            for n in niveles:
                if n.id == nota.desempeno_id:
                    return n
        for n in niveles:
            if n.rango_min <= nota.valor <= n.rango_max:
                return n
        return None

    def get_concepto_periodo(
        self,
        estudiante_id: int,
        periodo_id: int,
        nota_minima: float = 60.0,
    ) -> ConceptoComportamientoDTO:
        """
        Consolida el comportamiento (cuant + cualit) de un estudiante en un
        periodo. Si no hay nota registrada, devuelve DTO con `valor=None`.
        """
        nota = self._repo.get_nota(estudiante_id, periodo_id)
        if nota is None:
            return ConceptoComportamientoDTO(
                estudiante_id=estudiante_id,
                periodo_id=periodo_id,
                grupo_id=0,
                valor=None,
                aprobado=False,
            )
        _, niveles = self._resolver_niveles_del_periodo(periodo_id)
        nivel = self._elegir_nivel(nota, niveles)
        return ConceptoComportamientoDTO(
            estudiante_id=estudiante_id,
            periodo_id=periodo_id,
            grupo_id=nota.grupo_id,
            valor=nota.valor,
            nivel_nombre=nivel.nombre if nivel else None,
            nivel_descripcion=nivel.descripcion if nivel else None,
            concepto=nota.observacion,
            aprobado=nota.valor >= nota_minima,
        )

    def listar_conceptos_grupo(
        self,
        grupo_id: int,
        periodo_id: int,
        nota_minima: float = 60.0,
    ) -> list[ConceptoComportamientoDTO]:
        """
        Devuelve un `ConceptoComportamientoDTO` por cada estudiante del grupo,
        incluidos los que aún no tienen nota (DTO con valor=None).
        """
        if self._estudiante_svc_provider is None:
            raise RuntimeError(
                "ConvivenciaService requiere estudiante_svc_provider para "
                "listar conceptos por grupo."
            )
        estudiantes = self._estudiante_svc_provider().listar_por_grupo(grupo_id)
        notas = {
            n.estudiante_id: n
            for n in self._repo.listar_notas_por_grupo(grupo_id, periodo_id)
        }
        # Resolvemos niveles una sola vez si hay al menos una nota.
        niveles: list = []
        if notas:
            _, niveles = self._resolver_niveles_del_periodo(periodo_id)

        resultado: list[ConceptoComportamientoDTO] = []
        for est in estudiantes:
            nota = notas.get(est.id)
            if nota is None:
                resultado.append(ConceptoComportamientoDTO(
                    estudiante_id=est.id,
                    periodo_id=periodo_id,
                    grupo_id=grupo_id,
                    valor=None,
                    aprobado=False,
                ))
                continue
            nivel = self._elegir_nivel(nota, niveles)
            resultado.append(ConceptoComportamientoDTO(
                estudiante_id=est.id,
                periodo_id=periodo_id,
                grupo_id=grupo_id,
                valor=nota.valor,
                nivel_nombre=nivel.nombre if nivel else None,
                nivel_descripcion=nivel.descripcion if nivel else None,
                concepto=nota.observacion,
                aprobado=nota.valor >= nota_minima,
            ))
        return resultado


    # ------------------------------------------------------------------
    # Reporte por grupo/periodo (convivencia_06)
    # ------------------------------------------------------------------

    def reporte_periodo_grupo(
        self,
        grupo_id: int,
        periodo_id: int,
    ) -> list[ReporteConvivenciaFilaDTO]:
        """
        Reporte del director de grupo (convivencia_06): por cada estudiante
        del grupo, combina el concepto consolidado (nota + nivel + concepto
        narrativo) con la lista de textos de observaciones del periodo.

        Reutiliza `listar_conceptos_grupo` (que ya cubre estudiantes sin
        nota) y `listar_observaciones_por_estudiante` (por periodo). El
        nombre del estudiante se resuelve con el `estudiante_svc_provider`.

        Estudiantes sin nota y sin observaciones aparecen igualmente,
        con `valor=None` y `observaciones=[]`.
        """
        if self._estudiante_svc_provider is None:
            raise RuntimeError(
                "ConvivenciaService requiere estudiante_svc_provider para "
                "generar el reporte de periodo por grupo."
            )
        estudiantes = self._estudiante_svc_provider().listar_por_grupo(grupo_id)
        conceptos_por_est = {
            c.estudiante_id: c
            for c in self.listar_conceptos_grupo(grupo_id, periodo_id)
        }

        filas: list[ReporteConvivenciaFilaDTO] = []
        for est in estudiantes:
            est_id = getattr(est, "id", None)
            if est_id is None:
                continue
            concepto = conceptos_por_est.get(est_id)
            observaciones = self._repo.listar_observaciones_por_estudiante(
                est_id, periodo_id, False
            )
            textos_obs = [o.texto for o in observaciones]
            nombre = f"{getattr(est, 'apellido', '')} {getattr(est, 'nombre', '')}".strip() or str(est_id)
            filas.append(ReporteConvivenciaFilaDTO(
                estudiante_id=est_id,
                nombre=nombre,
                valor=concepto.valor if concepto else None,
                nivel_nombre=concepto.nivel_nombre if concepto else None,
                concepto=concepto.concepto if concepto else None,
                observaciones=textos_obs,
            ))
        return filas


__all__ = ["ConvivenciaService", "TipoRegistro"]
