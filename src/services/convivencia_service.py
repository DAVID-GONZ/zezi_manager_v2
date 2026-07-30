"""
ConvivenciaService
===================
Orquesta los casos de uso del módulo de Convivencia.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from src.domain.models.alerta import Alerta, FiltroAlertasDTO, NivelAlerta, TipoAlerta
from src.domain.models.convivencia import (
    CategoriaObservacion,
    ConceptoComportamientoDTO,
    FiltroConvivenciaDTO,
    NotaComportamiento,
    NuevaCategoriaDTO,
    NuevaAlertaSeguimientoDTO,
    NuevaNotaComportamientoDTO,
    NuevaObservacionDTO,
    NuevaPlantillaDTO,
    NuevoRegistroComportamientoDTO,
    ObservacionPeriodo,
    PlantillaObservacion,
    RegistroComportamiento,
    ReporteConvivenciaFilaDTO,
    Seguimiento360DTO,
    TipoRegistro,
)
from src.domain.ports.alerta_repo import IAlertaRepository
from src.domain.ports.convivencia_repo import IConvivenciaRepository
from src.domain.ports.service_ports import IExporterService
from src.services.solo_lectura import requiere_escritura

if TYPE_CHECKING:
    from src.services.asignacion_service import AsignacionService
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
        exporter: IExporterService | None = None,
        asignacion_svc_provider: Callable[[], "AsignacionService"] | None = None,
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

        `exporter` es la implementación de `IExporterService` (puerto de
        infraestructura) usada por `exportar_reporte_periodo_grupo`. Si es
        None, la exportación lanza RuntimeError.
        """
        self._repo        = repo
        self._alerta_repo = alerta_repo
        self._catalogo_academico_svc_provider = catalogo_academico_svc_provider
        self._configuracion_svc_provider = configuracion_svc_provider
        self._periodo_svc_provider = periodo_svc_provider
        self._estudiante_svc_provider = estudiante_svc_provider
        self._exporter    = exporter
        self._asignacion_svc_provider = asignacion_svc_provider

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
            anio_id, TipoAlerta.SEGUIMIENTO_REQUERIDO
        )
        if cfg is None or not cfg.activa:
            return

        conteo = self._repo.contar_registros(filtro)
        if conteo < cfg.umbral:
            return

        if self._alerta_repo.existe_pendiente(
            estudiante_id, TipoAlerta.SEGUIMIENTO_REQUERIDO
        ):
            return

        nivel = (
            NivelAlerta.CRITICA
            if conteo >= cfg.umbral * 2
            else NivelAlerta.ADVERTENCIA
        )
        alerta = Alerta(
            estudiante_id=estudiante_id,
            tipo_alerta=TipoAlerta.SEGUIMIENTO_REQUERIDO,
            nivel=nivel,
            descripcion=(
                f"El estudiante tiene {conteo} registro(s) negativo(s) de comportamiento "
                f"(umbral: {int(cfg.umbral)}). Se recomienda seguimiento."
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
        usuario_rol: str | None = None,
    ) -> ObservacionPeriodo:
        """
        Registra una observación narrativa de un estudiante en un periodo.

        Si ya existe una observación para esa asignación/periodo/estudiante,
        se actualiza; si no, se crea una nueva.

        Autorización por objeto (convivencia_11):
        - profesor → solo puede registrar/actualizar observaciones de sus
          propias asignaciones (asignacion.usuario_id == usuario_id).
          Si no es titular, lanza PermissionError.
        - director / coordinador → acceso pleno sin restricción adicional.
        """
        # Autorización por objeto para profesores
        if (
            usuario_rol == "profesor"
            and usuario_id is not None
            and self._asignacion_svc_provider is not None
        ):
            svc_asig = self._asignacion_svc_provider()
            try:
                asig = svc_asig.get_by_id(dto.asignacion_id)
            except Exception:
                asig = None
            if asig is None or asig.usuario_id != usuario_id:
                raise PermissionError(
                    "Solo puedes registrar observaciones de tus asignaciones"
                )

        existente = self._repo.get_observacion_por_asignacion(
            dto.estudiante_id, dto.asignacion_id, dto.periodo_id
        )

        if existente is not None:
            obs_actualizada = existente.model_copy(
                update={
                    "texto": dto.texto,
                    "es_publica": dto.es_publica,
                    "categoria_id": dto.categoria_id,
                }
            )
            return self._repo.actualizar_observacion(obs_actualizada)

        observacion = dto.to_observacion(usuario_id=usuario_id)
        return self._repo.guardar_observacion(observacion)

    def listar_observaciones(
        self,
        estudiante_id: int,
        periodo_id: int | None = None,
        solo_publicas: bool = False,
        usuario_id: int | None = None,
        usuario_rol: str | None = None,
    ) -> list[ObservacionPeriodo]:
        """Retorna las observaciones de un estudiante.

        Si `usuario_rol` es "profesor" y hay `asignacion_svc_provider`,
        filtra para devolver solo las observaciones pertenecientes a las
        asignaciones del profesor (asignacion_id en sus asignaciones).
        Directivo/coordinador ve todas.
        """
        observaciones = self._repo.listar_observaciones_por_estudiante(
            estudiante_id, periodo_id, solo_publicas
        )
        if (
            usuario_rol == "profesor"
            and usuario_id is not None
            and self._asignacion_svc_provider is not None
        ):
            svc_asig = self._asignacion_svc_provider()
            try:
                asignaciones_docente = svc_asig.listar_por_docente(
                    usuario_id, periodo_id
                )
                ids_docente = {
                    getattr(a, "id", None) for a in asignaciones_docente
                } - {None}
            except Exception:
                ids_docente = set()
            observaciones = [
                obs for obs in observaciones
                if obs.asignacion_id in ids_docente
            ]
        return observaciones

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

    # ------------------------------------------------------------------
    # Exportación del reporte (convivencia_06b)
    # ------------------------------------------------------------------

    # Definición de columnas del reporte de periodo. Fuente única de verdad:
    # (clave, encabezado). El servicio decide qué se exporta y en qué orden;
    # la página no participa en esa decisión.
    _COLUMNAS_REPORTE_PERIODO: tuple[tuple[str, str], ...] = (
        ("estudiante",   "Estudiante"),
        ("nota",         "Nota"),
        ("nivel",        "Nivel"),
        ("concepto",     "Concepto"),
        ("observaciones", "Observaciones"),
    )

    def _fila_a_dict_exportacion(
        self, fila: ReporteConvivenciaFilaDTO,
    ) -> dict:
        """Aplana un DTO a un dict con las columnas del reporte."""
        return {
            "estudiante":   fila.nombre,
            "nota":         "" if fila.valor is None else fila.valor,
            "nivel":        fila.nivel_nombre or "",
            "concepto":     fila.concepto or "",
            "observaciones": "\n".join(fila.observaciones) if fila.observaciones else "",
        }

    def _reporte_periodo_a_html(
        self,
        filas: list[ReporteConvivenciaFilaDTO],
        titulo: str,
    ) -> str:
        """HTML compacto del reporte para el exporter PDF (puerto HTML → PDF)."""
        heads_html = "".join(f"<th>{h}</th>" for _, h in self._COLUMNAS_REPORTE_PERIODO)
        if not filas:
            cuerpo = "<p>Sin datos.</p>"
        else:
            filas_html: list[str] = []
            for fila in filas:
                d = self._fila_a_dict_exportacion(fila)
                cells = "".join(
                    f"<td>{str(d[k]).replace(chr(10), '<br/>')}</td>"
                    for k, _ in self._COLUMNAS_REPORTE_PERIODO
                )
                filas_html.append(f"<tr>{cells}</tr>")
            cuerpo = (
                f"<table><thead><tr>{heads_html}</tr></thead>"
                f"<tbody>{''.join(filas_html)}</tbody></table>"
            )
        return (
            f"<html><head><meta charset='utf-8'><title>{titulo}</title>"
            "<style>table{border-collapse:collapse;width:100%;"
            "font-family:Arial,sans-serif;font-size:11px}"
            "th,td{border:1px solid #999;padding:4px;vertical-align:top;text-align:left}"
            "th{background:#eee}</style></head>"
            f"<body><h2>{titulo}</h2>{cuerpo}</body></html>"
        )

    def exportar_reporte_periodo_grupo(
        self,
        grupo_id: int,
        periodo_id: int,
        formato: str,
        titulo: str = "Reporte de convivencia",
    ) -> bytes:
        """
        Genera el reporte de periodo del grupo y lo exporta a `formato`
        (`"excel"` o `"pdf"`). Retorna bytes listos para descarga.

        Toda la lógica de composición (qué columnas, cómo aplanar los DTOs,
        cómo construir el HTML para PDF) vive AQUÍ, no en la página. La
        página solo pide los bytes y ofrece la descarga.

        Args:
            grupo_id, periodo_id: contexto del reporte.
            formato: "excel" | "pdf".
            titulo: encabezado para el PDF y nombre de hoja del Excel.

        Raises:
            RuntimeError: si no hay exporter inyectado.
            ValueError:   si `formato` no es soportado.
        """
        if self._exporter is None:
            raise RuntimeError(
                "ConvivenciaService no tiene exporter inyectado; "
                "no puede exportar reportes."
            )
        formato_norm = (formato or "").strip().lower()
        if formato_norm not in ("excel", "pdf"):
            raise ValueError(
                f"Formato no soportado: {formato!r}. Usa 'excel' o 'pdf'."
            )

        filas = self.reporte_periodo_grupo(grupo_id, periodo_id)

        if formato_norm == "excel":
            datos = [self._fila_a_dict_exportacion(f) for f in filas]
            return self._exporter.exportar_excel(datos, nombre_hoja=titulo[:31])

        html = self._reporte_periodo_a_html(filas, titulo=titulo)
        return self._exporter.exportar_pdf(html)


    # ------------------------------------------------------------------
    # Catálogo de categorías de observación (convivencia_09 / _10)
    # ------------------------------------------------------------------

    def listar_categorias(
        self,
        solo_activas: bool = True,
    ) -> list[CategoriaObservacion]:
        """Retorna el catálogo de categorías de observación."""
        return self._repo.listar_categorias(solo_activas=solo_activas)

    @requiere_escritura
    def crear_categoria(
        self,
        dto: NuevaCategoriaDTO,
    ) -> CategoriaObservacion:
        """Crea una nueva categoría de observación."""
        categoria = CategoriaObservacion(
            nombre=dto.nombre,
            es_comportamental=dto.es_comportamental,
        )
        return self._repo.guardar_categoria(categoria)

    @requiere_escritura
    def actualizar_categoria(
        self,
        categoria_id: int,
        dto: NuevaCategoriaDTO,
    ) -> CategoriaObservacion:
        """Actualiza el nombre y tipo de una categoría existente."""
        categoria = self._repo.get_categoria(categoria_id)
        if categoria is None:
            raise ValueError(
                f"Categoría con id {categoria_id} no existe."
            )
        actualizada = categoria.model_copy(
            update={
                "nombre": dto.nombre,
                "es_comportamental": dto.es_comportamental,
            }
        )
        return self._repo.actualizar_categoria(actualizada)

    @requiere_escritura
    def desactivar_categoria(
        self,
        categoria_id: int,
    ) -> CategoriaObservacion:
        """Desactiva una categoría (activa=False) sin eliminarla."""
        categoria = self._repo.get_categoria(categoria_id)
        if categoria is None:
            raise ValueError(
                f"Categoría con id {categoria_id} no existe."
            )
        desactivada = categoria.model_copy(update={"activa": False})
        return self._repo.actualizar_categoria(desactivada)

    def listar_todas_plantillas(
        self, categoria_id: int | None = None
    ) -> list[PlantillaObservacion]:
        """Retorna TODAS las plantillas (activas e inactivas), opcionalmente filtradas por categoría."""
        return self._repo.listar_plantillas(categoria_id=categoria_id, solo_activas=False)

    @requiere_escritura
    def crear_plantilla(
        self,
        dto: NuevaPlantillaDTO,
        usuario_id: int | None = None,
        usuario_rol: str | None = None,
    ) -> PlantillaObservacion:
        """Crea una nueva plantilla de observación. Solo director y coordinador."""
        if usuario_rol not in ("director", "coordinador"):
            raise PermissionError("Solo directores y coordinadores pueden crear plantillas.")
        plantilla = PlantillaObservacion(texto=dto.texto, categoria_id=dto.categoria_id)
        return self._repo.guardar_plantilla(plantilla)

    @requiere_escritura
    def actualizar_plantilla(
        self,
        plantilla_id: int,
        dto: NuevaPlantillaDTO,
        usuario_id: int | None = None,
        usuario_rol: str | None = None,
    ) -> PlantillaObservacion:
        """Actualiza texto y/o categoría de una plantilla. Solo director y coordinador."""
        if usuario_rol not in ("director", "coordinador"):
            raise PermissionError("Solo directores y coordinadores pueden actualizar plantillas.")
        plantilla = self._repo.get_plantilla(plantilla_id)
        if plantilla is None:
            raise ValueError(f"Plantilla con id {plantilla_id} no existe.")
        actualizada = plantilla.model_copy(update={"texto": dto.texto, "categoria_id": dto.categoria_id})
        return self._repo.actualizar_plantilla(actualizada)

    @requiere_escritura
    def desactivar_plantilla(
        self,
        plantilla_id: int,
        usuario_id: int | None = None,
        usuario_rol: str | None = None,
    ) -> None:
        """Desactiva una plantilla (la oculta del selector). Solo director y coordinador."""
        if usuario_rol not in ("director", "coordinador"):
            raise PermissionError("Solo directores y coordinadores pueden desactivar plantillas.")
        plantilla = self._repo.get_plantilla(plantilla_id)
        if plantilla is None:
            raise ValueError(f"Plantilla con id {plantilla_id} no existe.")
        desactivada = plantilla.model_copy(update={"activa": False})
        self._repo.actualizar_plantilla(desactivada)

    # ------------------------------------------------------------------
    # Catálogo de plantillas de observación (convivencia_12)
    # ------------------------------------------------------------------

    def listar_plantillas(
        self, categoria_id: int | None = None
    ) -> list[PlantillaObservacion]:
        """Retorna las plantillas activas, opcionalmente filtradas por categoría."""
        return self._repo.listar_plantillas(
            categoria_id=categoria_id, solo_activas=True
        )

    @requiere_escritura
    def registrar_observacion_desde_plantilla(
        self,
        dto: NuevaObservacionDTO,
        plantilla_id: int,
        usuario_id: int | None = None,
        usuario_rol: str | None = None,
    ) -> ObservacionPeriodo:
        """
        Registra una observación a partir de una plantilla del catálogo.

        Aplica la misma autorización por objeto que `registrar_observacion`
        (profesores solo en sus asignaciones). Marca el origen como 'plantilla'
        e incrementa el uso_count de la plantilla utilizada.
        """
        # Autorización por objeto para profesores
        if (
            usuario_rol == "profesor"
            and usuario_id is not None
            and self._asignacion_svc_provider is not None
        ):
            svc_asig = self._asignacion_svc_provider()
            try:
                asig = svc_asig.get_by_id(dto.asignacion_id)
            except Exception:
                asig = None
            if asig is None or asig.usuario_id != usuario_id:
                raise PermissionError(
                    "Solo puedes registrar observaciones de tus asignaciones"
                )

        # Upsert con origen="plantilla"
        existente = self._repo.get_observacion_por_asignacion(
            dto.estudiante_id, dto.asignacion_id, dto.periodo_id
        )
        if existente is not None:
            obs_actualizada = existente.model_copy(
                update={
                    "texto":        dto.texto,
                    "es_publica":   dto.es_publica,
                    "categoria_id": dto.categoria_id,
                    "origen":       "plantilla",
                }
            )
            obs = self._repo.actualizar_observacion(obs_actualizada)
        else:
            obs = ObservacionPeriodo(
                **dto.model_dump(),
                usuario_id=usuario_id,
                origen="plantilla",
            )
            obs = self._repo.guardar_observacion(obs)

        # Incrementar el contador de uso de la plantilla
        self._repo.incrementar_uso_plantilla(plantilla_id)
        return obs

    # ------------------------------------------------------------------
    # Catálogo de retroalimentación (convivencia_13)
    # ------------------------------------------------------------------

    @requiere_escritura
    def promover_observacion_a_plantilla(
        self,
        observacion_id: int,
        usuario_id: int | None = None,
        usuario_rol: str | None = None,
    ) -> PlantillaObservacion:
        """
        Crea una nueva PlantillaObservacion a partir del texto y categoria_id
        de una ObservacionPeriodo existente.
        RBAC: solo DIRECTOR y COORDINADOR pueden promover.
        """
        if usuario_rol not in ("director", "coordinador"):
            raise PermissionError(
                "Solo directores y coordinadores pueden promover observaciones a plantillas."
            )
        obs = self._get_observacion_o_lanzar(observacion_id)
        plantilla = PlantillaObservacion(texto=obs.texto, categoria_id=obs.categoria_id)
        return self._repo.guardar_plantilla(plantilla)

    def listar_plantillas_sugeridas(
        self,
        categoria_id: int | None = None,
        limite: int = 5,
    ) -> list[PlantillaObservacion]:
        """
        Retorna las plantillas activas más usadas, opcionalmente filtradas
        por categoría. Limitado a `limite` resultados (default 5).
        """
        return self._repo.listar_plantillas(categoria_id=categoria_id, solo_activas=True)[:limite]

    # ------------------------------------------------------------------
    # Promoción a comportamiento (convivencia_14)
    # ------------------------------------------------------------------

    @requiere_escritura
    def promover_a_comportamiento(
        self,
        observacion_id: int,
        usuario_id: int | None = None,
        usuario_rol: str | None = None,
    ) -> RegistroComportamiento:
        """
        Solo para observaciones con categoria.es_comportamental=True.
        Crea un RegistroComportamiento y enlaza la observación al registro.
        RBAC: DIRECTOR, COORDINADOR.

        Pasos:
          1. Verifica RBAC: solo director/coordinador → PermissionError.
          2. Carga la observación → ValueError si no existe.
          3. Verifica que la categoría sea comportamental → ValueError si no.
          4. Crea el RegistroComportamiento (grupo_id resuelto vía
             asignacion_svc_provider si disponible, o 0 como fallback).
          5. Persiste el registro y enlaza la observación (FK).
          6. Retorna el registro creado.
        """
        if usuario_rol not in ("director", "coordinador"):
            raise PermissionError(
                "Solo directores y coordinadores pueden promover "
                "observaciones a registros de comportamiento."
            )

        obs = self._get_observacion_o_lanzar(observacion_id)

        if obs.categoria_id is None:
            raise ValueError(
                "La observación no tiene categoría asignada; "
                "solo se pueden promover observaciones clasificadas."
            )

        categoria = self._repo.get_categoria(obs.categoria_id)
        if categoria is None or not categoria.es_comportamental:
            raise ValueError("La categoría no es comportamental")

        # Resolver grupo_id desde la asignación (mejor esfuerzo)
        grupo_id: int = 0
        if self._asignacion_svc_provider is not None:
            try:
                svc_asig = self._asignacion_svc_provider()
                asig = svc_asig.get_by_id(obs.asignacion_id)
                if asig is not None and hasattr(asig, "grupo_id"):
                    grupo_id = int(asig.grupo_id)
            except Exception:
                pass  # fallback a 0

        registro_nuevo = RegistroComportamiento(
            estudiante_id=obs.estudiante_id,
            grupo_id=grupo_id,
            periodo_id=obs.periodo_id,
            descripcion=obs.texto,
            usuario_registro_id=usuario_id,
            tipo=TipoRegistro.DIFICULTAD,
        )
        registro = self._repo.guardar_registro(registro_nuevo)

        obs_actualizada = obs.model_copy(
            update={"registro_comportamiento_id": registro.id}
        )
        self._repo.actualizar_observacion(obs_actualizada)

        return registro


    # ------------------------------------------------------------------
    # Alertas de seguimiento manual (convivencia_16)
    # ------------------------------------------------------------------

    @requiere_escritura
    def crear_alerta_seguimiento_manual(
        self,
        dto: NuevaAlertaSeguimientoDTO,
        usuario_id: int | None = None,
        usuario_rol: str | None = None,
    ) -> Alerta:
        """
        Crea una alerta de seguimiento manual dirigida a un profesor.
        RBAC: solo DIRECTOR y COORDINADOR pueden crearla.
        """
        if usuario_rol not in ("director", "coordinador"):
            raise PermissionError(
                "Solo directores y coordinadores pueden crear alertas de seguimiento."
            )
        if self._alerta_repo is None:
            raise RuntimeError(
                "ConvivenciaService no tiene alerta_repo inyectado; "
                "no puede crear alertas de seguimiento."
            )
        alerta = Alerta(
            tipo_alerta=TipoAlerta.SEGUIMIENTO_REQUERIDO,
            estudiante_id=dto.estudiante_id,
            descripcion=dto.descripcion,
            nivel=dto.nivel,
            usuario_destino_id=dto.usuario_destino_id,
        )
        return self._alerta_repo.guardar_alerta(alerta)


    # ------------------------------------------------------------------
    # Vista 360° del estudiante (convivencia_18)
    # ------------------------------------------------------------------

    def vista_360(
        self,
        estudiante_id: int,
        periodo_id: int,
        usuario_id: int | None = None,
        usuario_rol: str | None = None,
    ) -> Seguimiento360DTO:
        """
        Consolida la visión completa de convivencia de un estudiante en un
        periodo: nota de comportamiento, concepto narrativo, nivel de desempeño,
        observaciones públicas y alertas activas de seguimiento.

        RBAC:
          - director / coordinador → acceso pleno.
          - director_de_grupo / director_grupo → solo si es director del grupo
            del estudiante (verificado con catalogo_academico_svc_provider cuando
            está disponible; compat retro cuando no lo está).
          - cualquier otro rol → PermissionError.
        """
        _roles_plenos    = ("director", "coordinador")
        _roles_dir_grupo = ("director_de_grupo", "director_grupo")

        if usuario_rol not in _roles_plenos:
            if usuario_rol in _roles_dir_grupo:
                # Verificar que el usuario es director del grupo del estudiante.
                if (
                    self._catalogo_academico_svc_provider is not None
                    and usuario_id is not None
                    and self._estudiante_svc_provider is not None
                ):
                    try:
                        est = self._estudiante_svc_provider().get_by_id(estudiante_id)
                        grupo_id_est = getattr(est, "grupo_id", None)
                        if grupo_id_est is not None:
                            autorizado = (
                                self._catalogo_academico_svc_provider()
                                .puede_gestionar_comportamiento_en_grupo(
                                    usuario_rol, usuario_id, grupo_id_est
                                )
                            )
                            if not autorizado:
                                raise PermissionError(
                                    "Solo director, coordinador o director de grupo "
                                    "pueden ver el seguimiento 360°"
                                )
                    except PermissionError:
                        raise
                    except Exception:
                        pass  # compat retro: providers disponibles pero falla → permitir
            else:
                raise PermissionError(
                    "Solo director, coordinador o director de grupo "
                    "pueden ver el seguimiento 360°"
                )

        # ── Nombre del estudiante ────────────────────────────────────────────
        nombre = str(estudiante_id)
        if self._estudiante_svc_provider is not None:
            try:
                est = self._estudiante_svc_provider().get_by_id(estudiante_id)
                nombre = (
                    f"{getattr(est, 'apellido', '')} {getattr(est, 'nombre', '')}".strip()
                    or nombre
                )
            except Exception:
                pass

        # ── Nota de comportamiento y concepto ───────────────────────────────
        nota_comportamiento: float | None = None
        concepto: str | None = None
        nivel_comportamiento: str | None = None
        try:
            concepto_dto = self.get_concepto_periodo(estudiante_id, periodo_id)
            nota_comportamiento  = concepto_dto.valor
            concepto             = concepto_dto.concepto
            nivel_comportamiento = concepto_dto.nivel_nombre
        except RuntimeError:
            # Providers de niveles no disponibles; extrae la nota directamente.
            try:
                nota = self._repo.get_nota(estudiante_id, periodo_id)
                if nota is not None:
                    nota_comportamiento = nota.valor
                    concepto            = nota.observacion
            except Exception:
                pass
        except Exception:
            pass

        # ── Observaciones públicas del periodo ──────────────────────────────
        textos_obs: list[str] = []
        try:
            obs_list = self._repo.listar_observaciones_por_estudiante(
                estudiante_id, periodo_id, solo_publicas=True
            )
            textos_obs = [o.texto for o in obs_list]
        except Exception:
            pass

        # ── Alertas activas ─────────────────────────────────────────────────
        alertas_activas: list[str] = []
        if self._alerta_repo is not None:
            try:
                filtro_alertas = FiltroAlertasDTO(
                    estudiante_id=estudiante_id,
                    solo_pendientes=True,
                )
                alertas = self._alerta_repo.listar_alertas(filtro_alertas)
                alertas_activas = [
                    str(getattr(a, "descripcion", a)) for a in alertas
                ]
            except Exception:
                pass

        return Seguimiento360DTO(
            estudiante_id=estudiante_id,
            estudiante_nombre=nombre,
            periodo_id=periodo_id,
            nota_comportamiento=nota_comportamiento,
            concepto=concepto,
            nivel_comportamiento=nivel_comportamiento,
            observaciones=textos_obs,
            alertas_activas=alertas_activas,
            promedio_notas=None,
        )


__all__ = ["ConvivenciaService", "NuevaCategoriaDTO", "NuevaAlertaSeguimientoDTO", "NuevaPlantillaDTO", "PlantillaObservacion", "Seguimiento360DTO", "TipoRegistro"]
