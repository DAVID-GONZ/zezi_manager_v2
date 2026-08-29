"""
ConvivenciaService
===================
Orquesta los casos de uso del módulo de Convivencia.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from src.domain.models.alerta import Alerta, FiltroAlertasDTO, NivelAlerta, TipoAlerta
from src.domain.models.convivencia import (
    CategoriaObservacion,
    ConceptoComportamientoDTO,
    EntradaSeguimiento,
    FiltroConvivenciaDTO,
    MedidaPedagogica,
    NotaComportamiento,
    NuevaAlertaSeguimientoDTO,
    NuevaCategoriaDTO,
    NuevaEntradaSeguimientoDTO,
    NuevaMedidaPedagogicaDTO,
    NuevaNotaComportamientoDTO,
    NuevaObservacionDTO,
    NuevaPlantillaDTO,
    NuevoRegistroComportamientoDTO,
    NuevoTipoSituacionDTO,
    ObservacionPeriodo,
    PlantillaObservacion,
    PuntoSerieDTO,
    RegistroComportamiento,
    ReporteConvivenciaFilaDTO,
    ResumenConvivenciaDTO,
    Seguimiento360DTO,
    TipoRegistro,
    TipoSituacion,
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
    from src.services.preferencias_institucion_service import (
        PreferenciasInstitucionService,
    )


class ConvivenciaService:
    """
    Orquesta los casos de uso del módulo de Convivencia.
    No contiene SQL. No contiene lógica de presentación.
    """

    def __init__(
        self,
        repo: IConvivenciaRepository,
        alerta_repo: IAlertaRepository | None = None,
        catalogo_academico_svc_provider: Callable[[], CatalogoAcademicoService] | None = None,
        configuracion_svc_provider: Callable[[], ConfiguracionService] | None = None,
        periodo_svc_provider: Callable[[], PeriodoService] | None = None,
        estudiante_svc_provider: Callable[[], EstudianteService] | None = None,
        exporter: IExporterService | None = None,
        asignacion_svc_provider: Callable[[], AsignacionService] | None = None,
        preferencias_svc_provider: Callable[[], PreferenciasInstitucionService] | None = None,
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

        `preferencias_svc_provider` es un proveedor lazy de
        `PreferenciasInstitucionService` para leer la política de registros
        en boletín (convivencia_29). Si es None, `_get_prefs_convivencia`
        retorna los defaults del DTO (compat retro scripts/tests sin wiring).
        """
        self._repo = repo
        self._alerta_repo = alerta_repo
        self._catalogo_academico_svc_provider = catalogo_academico_svc_provider
        self._configuracion_svc_provider = configuracion_svc_provider
        self._periodo_svc_provider = periodo_svc_provider
        self._estudiante_svc_provider = estudiante_svc_provider
        self._exporter = exporter
        self._asignacion_svc_provider = asignacion_svc_provider
        self._preferencias_svc_provider = preferencias_svc_provider

    # ── Resolución de institución (multi-tenant — mejora_07-T3) ─────────────────

    @staticmethod
    def _resolver_institucion(institucion_id: int | None) -> int | None:
        """Resuelve tenant: explícito → sesión → id_por_defecto → None."""
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
        if not svc.puede_gestionar_comportamiento_en_grupo(usuario_rol, usuario_id, grupo_id):
            raise PermissionError("No autorizado para gestionar el comportamiento de este grupo.")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_registro_o_lanzar(self, registro_id: int) -> RegistroComportamiento:
        reg = self._repo.get_registro(registro_id)
        if reg is None:
            raise ValueError(f"Registro de comportamiento con id {registro_id} no existe.")
        return reg

    def _get_observacion_o_lanzar(self, observacion_id: int) -> ObservacionPeriodo:
        obs = self._repo.get_observacion(observacion_id)
        if obs is None:
            raise ValueError(f"Observación con id {observacion_id} no existe.")
        return obs

    def _get_prefs_convivencia(self):
        """Retorna las preferencias de convivencia del tenant activo.

        Si `_preferencias_svc_provider` no está disponible o el tenant no
        se puede resolver, retorna una instancia ``PreferenciasDTO()`` con
        los defaults conservadores (compat retro scripts/tests sin wiring).
        """
        from src.domain.models.preferencia_institucion import PreferenciasDTO

        if self._preferencias_svc_provider is None:
            return PreferenciasDTO()
        try:
            from src.services.contexto_tenant import institucion_actual

            inst_id = institucion_actual()
            if inst_id is None:
                return PreferenciasDTO()
            return self._preferencias_svc_provider().get_dto(inst_id)
        except Exception:
            return PreferenciasDTO()

    def _registros_informables_periodo(
        self,
        estudiante_id: int,
        periodo_id: int,
        excluir_ids: set[int] | None = None,
        *,
        _tipos_map: dict[int, str] | None = None,
        _medidas_map: dict[int, str] | None = None,
    ) -> list[dict]:
        """Registros de comportamiento del estudiante en el periodo que deben
        aparecer en el boletín, aplicando la política configurada por tenant.

        Returns:
            Lista de dicts ``{"fecha": str, "tipo": str, "descripcion": str}``
            ordenada por ``fecha`` ascendente.

        Si `excluir_ids` se proporciona y `registros_boletin_dedup_observaciones`
        está activo, los registros cuyo ``id`` esté en el conjunto se omiten
        (ya aparecen como observación pública y duplicarlos no aporta valor).
        """
        from src.domain.models.convivencia import TIPO_REGISTRO_DISPLAY
        from src.services.contexto_tenant import institucion_actual

        prefs = self._get_prefs_convivencia()
        tipos = set(prefs.registros_boletin_tipos)
        if not prefs.registros_boletin_incluye_descargo:
            tipos.discard("descargo")
        filtro = FiltroConvivenciaDTO(
            estudiante_id=estudiante_id, periodo_id=periodo_id, por_pagina=None,
        )
        _scope = institucion_actual() or "*"
        regs = self._repo.listar_registros(filtro, institucion_id=_scope)
        excluir = excluir_ids or set()

        tipos_map = _tipos_map if _tipos_map is not None else {
            t.id: t.nombre
            for t in self._repo.listar_tipos_situacion(institucion_id=_scope, solo_activas=False)
            if t.id is not None
        }
        medidas_map = _medidas_map if _medidas_map is not None else {
            m.id: m.nombre
            for m in self._repo.listar_medidas(institucion_id=_scope, solo_activas=False)
            if m.id is not None
        }

        resultado: list[dict] = []
        for r in regs:
            if r.tipo.value not in tipos:
                continue
            if (
                r.tipo.value == "dificultad"
                and prefs.registros_boletin_dificultad_requiere_notificacion
                and not r.acudiente_notificado
            ):
                continue
            if prefs.registros_boletin_dedup_observaciones and r.id in excluir:
                continue
            resultado.append(
                {
                    "fecha": str(r.fecha),
                    "tipo": TIPO_REGISTRO_DISPLAY.get(r.tipo.value, r.tipo.value),
                    "descripcion": r.descripcion,
                    "tipo_situacion": tipos_map.get(r.tipo_situacion_id)
                    if getattr(r, "tipo_situacion_id", None) is not None
                    else None,
                    "medida": medidas_map.get(r.medida_id)
                    if getattr(r, "medida_id", None) is not None
                    else None,
                }
            )
        resultado.sort(key=lambda d: d["fecha"])
        return resultado

    # ------------------------------------------------------------------
    # Paquetes de convivencia para boletín (convivencia_32)
    # ------------------------------------------------------------------

    def _agrupar_obs_por_categoria(self, obs: list[ObservacionPeriodo]) -> list[dict]:
        """Agrupa observaciones por categoría con nombre resuelto.

        Orden: activas A-Z → inactivas → "Sin categoría".
        Items incluyen fecha, autor y texto (para boletín de periodo).
        """
        from src.services.contexto_tenant import institucion_actual

        categorias = self._repo.listar_categorias(institucion_id=institucion_actual() or "*", solo_activas=False)
        cat_map = {c.id: c for c in categorias if c.id is not None}

        obs_por_cat: dict[int | None, list[dict]] = {}
        for o in obs:
            autor: str = getattr(o, "usuario", "") or ""
            fecha_str = str(o.fecha) if getattr(o, "fecha", None) is not None else ""
            item = {
                "fecha": fecha_str,
                "autor": autor,
                "texto": o.texto,
            }
            obs_por_cat.setdefault(o.categoria_id, []).append(item)

        def _sort_key(cat_id: int | None) -> tuple:
            if cat_id is None:
                return (2, "")
            cat = cat_map.get(cat_id)
            if cat is None:
                return (2, "")
            return (0 if cat.activa else 1, cat.nombre.lower())

        sorted_ids = sorted(obs_por_cat.keys(), key=_sort_key)
        resultado: list[dict] = []
        for cat_id in sorted_ids:
            if cat_id is None:
                cat_nombre = "Sin categoría"
            else:
                cat = cat_map.get(cat_id)
                cat_nombre = cat.nombre if cat else "Sin categoría"
            resultado.append(
                {
                    "categoria": cat_nombre,
                    "items": obs_por_cat[cat_id],
                }
            )
        return resultado

    def paquete_boletin_periodo(self, estudiante_id: int, periodo_id: int) -> dict:
        """Retorna el paquete de convivencia para el boletín de un periodo.

        Claves:
          nota:                        float | None
          nota_observacion:            str   | None
          observaciones:               list[str]   (textos planos — compat retro PDF)
          observaciones_por_categoria: list[dict]  (formato rico con fecha/autor/texto)
          registros:                   list[dict]  (política convivencia_29)
        """
        nota = self._repo.get_nota(estudiante_id, periodo_id)
        obs = self._repo.listar_observaciones_por_estudiante(
            estudiante_id, periodo_id, solo_publicas=True
        )
        excluir_ids: set[int] = {
            o.registro_comportamiento_id for o in obs if o.registro_comportamiento_id is not None
        }
        return {
            "nota": nota.valor if nota else None,
            "nota_observacion": nota.observacion if nota else None,
            "observaciones": [o.texto for o in obs],
            "observaciones_por_categoria": self._agrupar_obs_por_categoria(obs),
            "registros": self._registros_informables_periodo(
                estudiante_id, periodo_id, excluir_ids
            ),
        }

    def paquete_boletin_anual(self, estudiante_id: int, anio_id: int) -> dict:
        """Retorna el paquete de convivencia para el boletín anual.

        Requiere ``periodo_svc_provider``. Si no está disponible, retorna vacío.

        Claves:
          periodos:                    list[{"id", "nombre"}]
          notas_por_periodo:           dict[periodo_id, float | None]
          definitiva:                  float | None
          concepto:                    str   | None
          observaciones_por_categoria: list[dict] (items con "periodo" en vez de "fecha")
          registros:                   list[dict]  (política convivencia_29, agregado anual)
        """
        _empty: dict = {
            "periodos": [],
            "notas_por_periodo": {},
            "definitiva": None,
            "concepto": None,
            "observaciones_por_categoria": [],
            "registros": [],
        }
        if self._periodo_svc_provider is None:
            return _empty

        periodos = self._periodo_svc_provider().listar_por_anio(anio_id)
        if not periodos:
            return _empty

        periodo_lista = [{"id": p.id, "nombre": p.nombre} for p in periodos]
        periodo_nombre_map: dict[int, str] = {p.id: p.nombre for p in periodos}

        # ── Notas por periodo ─────────────────────────────────────────
        notas_dict = {
            n.periodo_id: n for n in self._repo.listar_notas_por_estudiante(estudiante_id)
        }
        notas_por_periodo: dict[int, float | None] = {}
        ultimo_con_nota = None

        for p in periodos:
            nota_obj = notas_dict.get(p.id)
            if nota_obj is not None:
                notas_por_periodo[p.id] = nota_obj.valor
                ultimo_con_nota = nota_obj
            else:
                notas_por_periodo[p.id] = None

        notas_presentes = [v for v in notas_por_periodo.values() if v is not None]
        definitiva = (
            round(sum(notas_presentes) / len(notas_presentes), 2) if notas_presentes else None
        )
        concepto: str | None = None
        if ultimo_con_nota is not None and ultimo_con_nota.observacion:
            concepto = ultimo_con_nota.observacion

        # ── Observaciones públicas agrupadas por categoría ─────────
        from src.services.contexto_tenant import institucion_actual

        _scope = institucion_actual() or "*"
        categorias = self._repo.listar_categorias(institucion_id=_scope, solo_activas=False)
        cat_map = {c.id: c for c in categorias if c.id is not None}

        obs_por_cat: dict[int | None, list[dict]] = {}
        excluir_ids_anual: set[int] = set()
        for p in periodos:
            obs_list = self._repo.listar_observaciones_por_estudiante(
                estudiante_id, p.id, solo_publicas=True
            )
            for obs in obs_list:
                cat_id = obs.categoria_id
                autor: str = getattr(obs, "usuario", "") or ""
                item = {
                    "periodo": periodo_nombre_map[p.id],
                    "autor": autor,
                    "texto": obs.texto,
                }
                obs_por_cat.setdefault(cat_id, []).append(item)
                if obs.registro_comportamiento_id is not None:
                    excluir_ids_anual.add(obs.registro_comportamiento_id)

        def _cat_sort_key(cat_id: int | None) -> tuple:
            if cat_id is None:
                return (2, "")
            cat = cat_map.get(cat_id)
            if cat is None:
                return (2, "")
            return (0 if cat.activa else 1, cat.nombre.lower())

        sorted_cat_ids = sorted(obs_por_cat.keys(), key=_cat_sort_key)
        observaciones_por_categoria: list[dict] = []
        for cat_id in sorted_cat_ids:
            if cat_id is None:
                cat_nombre = "Sin categoría"
            else:
                cat = cat_map.get(cat_id)
                cat_nombre = cat.nombre if cat else "Sin categoría"
            observaciones_por_categoria.append(
                {
                    "categoria": cat_nombre,
                    "items": obs_por_cat[cat_id],
                }
            )

        # ── Registros de comportamiento (convivencia_29) ──────────
        _tipos_map = {
            t.id: t.nombre
            for t in self._repo.listar_tipos_situacion(institucion_id=_scope, solo_activas=False)
            if t.id is not None
        }
        _medidas_map = {
            m.id: m.nombre
            for m in self._repo.listar_medidas(institucion_id=_scope, solo_activas=False)
            if m.id is not None
        }
        registros_anual: list[dict] = []
        for p in periodos:
            regs_p = self._registros_informables_periodo(
                estudiante_id, p.id, excluir_ids_anual,
                _tipos_map=_tipos_map, _medidas_map=_medidas_map,
            )
            registros_anual.extend(regs_p)
        registros_anual.sort(key=lambda d: d["fecha"])

        return {
            "periodos": periodo_lista,
            "notas_por_periodo": notas_por_periodo,
            "definitiva": definitiva,
            "concepto": concepto,
            "observaciones_por_categoria": observaciones_por_categoria,
            "registros": registros_anual,
        }

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

        cfg = self._alerta_repo.get_configuracion(anio_id, TipoAlerta.SEGUIMIENTO_REQUERIDO)
        if cfg is None or not cfg.activa:
            return

        from src.services.contexto_tenant import institucion_actual

        conteo = self._repo.contar_registros(filtro, institucion_id=institucion_actual() or "*")
        if conteo < cfg.umbral:
            return

        if self._alerta_repo.existe_pendiente(estudiante_id, TipoAlerta.SEGUIMIENTO_REQUERIDO):
            return

        nivel = NivelAlerta.CRITICA if conteo >= cfg.umbral * 2 else NivelAlerta.ADVERTENCIA
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
                raise PermissionError("Solo puedes registrar observaciones de tus asignaciones")

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
                asignaciones_docente = svc_asig.listar_por_docente(usuario_id, periodo_id)
                ids_docente = {getattr(a, "asignacion_id", None) for a in asignaciones_docente} - {
                    None
                }
            except Exception:
                ids_docente = set()
            observaciones = [obs for obs in observaciones if obs.asignacion_id in ids_docente]
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
        prefs = self._get_prefs_convivencia()
        if prefs.tipo_situacion_obligatorio and dto.tipo_situacion_id is None:
            raise ValueError("La clasificacion de situacion es obligatoria.")
        registro = dto.to_registro(usuario_id=usuario_id)
        registro = self._repo.guardar_registro(registro)

        # Verificar alertas si el registro es negativo
        if anio_id is not None and registro.es_negativo:
            filtro = FiltroConvivenciaDTO(
                estudiante_id=dto.estudiante_id,
                periodo_id=dto.periodo_id,
                solo_negativos=True,
            )
            self._verificar_alerta_comportamiento(dto.estudiante_id, anio_id, filtro)

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
    def agregar_entrada_seguimiento(
        self,
        dto: NuevaEntradaSeguimientoDTO,
        usuario_id: int | None = None,
        usuario_rol: str | None = None,
    ) -> EntradaSeguimiento:
        """Agrega una entrada al historial cronológico de seguimiento (R2, R3, R5, R6)."""
        registro = self._get_registro_o_lanzar(dto.registro_id)
        self._verificar_autorizacion(usuario_rol, usuario_id, registro.grupo_id)
        entrada = EntradaSeguimiento(
            registro_id=dto.registro_id,
            texto=dto.texto,
            usuario_id=usuario_id,
        )
        entrada = self._repo.guardar_entrada_seguimiento(entrada)
        # Denormalización R3: actualizar campo legacy con el texto de la última entrada.
        registro_actualizado = registro.agregar_seguimiento(dto.texto)
        self._repo.actualizar_registro(registro_actualizado)
        return entrada

    def listar_entradas_seguimiento(self, registro_id: int) -> list[EntradaSeguimiento]:
        """Retorna entradas de seguimiento de un registro, orden cronológico ASC."""
        return self._repo.listar_entradas_seguimiento(registro_id)

    @requiere_escritura
    def agregar_seguimiento(
        self,
        registro_id: int,
        texto: str,
        usuario_id: int | None = None,
        usuario_rol: str | None = None,
    ) -> RegistroComportamiento:
        """Método legacy — delega en agregar_entrada_seguimiento (R8)."""
        dto = NuevaEntradaSeguimientoDTO(registro_id=registro_id, texto=texto)
        self.agregar_entrada_seguimiento(dto, usuario_id=usuario_id, usuario_rol=usuario_rol)
        return self._get_registro_o_lanzar(registro_id)

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

        return self._repo.listar_registros(filtro, institucion_id=institucion_actual() or "*")

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
            n.estudiante_id: n for n in self._repo.listar_notas_por_grupo(grupo_id, periodo_id)
        }
        # Resolvemos niveles una sola vez si hay al menos una nota.
        niveles: list = []
        if notas:
            _, niveles = self._resolver_niveles_del_periodo(periodo_id)

        resultado: list[ConceptoComportamientoDTO] = []
        for est in estudiantes:
            nota = notas.get(est.id)
            if nota is None:
                resultado.append(
                    ConceptoComportamientoDTO(
                        estudiante_id=est.id,
                        periodo_id=periodo_id,
                        grupo_id=grupo_id,
                        valor=None,
                        aprobado=False,
                    )
                )
                continue
            nivel = self._elegir_nivel(nota, niveles)
            resultado.append(
                ConceptoComportamientoDTO(
                    estudiante_id=est.id,
                    periodo_id=periodo_id,
                    grupo_id=grupo_id,
                    valor=nota.valor,
                    nivel_nombre=nivel.nombre if nivel else None,
                    nivel_descripcion=nivel.descripcion if nivel else None,
                    concepto=nota.observacion,
                    aprobado=nota.valor >= nota_minima,
                )
            )
        return resultado

    # ------------------------------------------------------------------
    # Agregados para el hub de Seguimiento (convivencia_21)
    # ------------------------------------------------------------------

    def serie_notas_comportamiento(
        self,
        estudiante_id: int,
        anio_id: int,
    ) -> list[PuntoSerieDTO]:
        """
        Evolución de la nota de comportamiento de un estudiante a lo largo de
        los periodos del año, como serie ordenada con un punto por periodo.

        Los periodos sin nota registrada aparecen con `valor=None` (huecos),
        preservando el eje completo de periodos.

        Requiere `periodo_svc_provider`; si es None → RuntimeError.
        """
        if self._periodo_svc_provider is None:
            raise RuntimeError(
                "ConvivenciaService requiere periodo_svc_provider para "
                "construir la serie de notas de comportamiento."
            )
        periodos = self._periodo_svc_provider().listar_por_anio(anio_id)
        notas = {n.periodo_id: n for n in self._repo.listar_notas_por_estudiante(estudiante_id)}
        serie: list[PuntoSerieDTO] = []
        for periodo in periodos:
            nota = notas.get(periodo.id)
            serie.append(
                PuntoSerieDTO(
                    periodo_id=periodo.id,
                    periodo_nombre=periodo.nombre,
                    valor=nota.valor if nota is not None else None,
                )
            )
        return serie

    def resumen_convivencia_grupo(
        self,
        grupo_id: int,
        periodo_id: int,
    ) -> list[ResumenConvivenciaDTO]:
        """
        Resumen agregado por estudiante del grupo en un periodo: número de
        observaciones, número de registros negativos, nota de comportamiento,
        nivel de desempeño y si supera el umbral de alerta configurado.

        Se compone con un número acotado de consultas (sin N+1 por estudiante):
        una para conceptos/notas, una para registros y una para observaciones.

        Requiere `estudiante_svc_provider` (vía `listar_conceptos_grupo`); si es
        None → RuntimeError.
        """
        # Conceptos (nota + nivel) por estudiante — cubre estudiantes sin nota.
        conceptos = {c.estudiante_id: c for c in self.listar_conceptos_grupo(grupo_id, periodo_id)}
        estudiantes = self._estudiante_svc_provider().listar_por_grupo(grupo_id)

        # Registros negativos por estudiante (1 consulta).
        from src.services.contexto_tenant import institucion_actual

        registros = self._repo.listar_registros(
            FiltroConvivenciaDTO(grupo_id=grupo_id, periodo_id=periodo_id, por_pagina=None),
            institucion_id=institucion_actual() or "*",
        )
        negativos_por_est: dict[int, int] = {}
        for reg in registros:
            if reg.es_negativo:
                negativos_por_est[reg.estudiante_id] = (
                    negativos_por_est.get(reg.estudiante_id, 0) + 1
                )

        # Observaciones por estudiante (1 consulta batch).
        observaciones = self._repo.listar_observaciones_por_grupo(grupo_id, periodo_id)
        obs_por_est: dict[int, int] = {}
        for obs in observaciones:
            obs_por_est[obs.estudiante_id] = obs_por_est.get(obs.estudiante_id, 0) + 1

        # Umbral de alerta (una sola resolución de configuración por grupo).
        umbral: float | None = None
        if self._alerta_repo is not None and self._periodo_svc_provider is not None:
            try:
                anio_id = self._periodo_svc_provider().get_by_id(periodo_id).anio_id
                cfg = self._alerta_repo.get_configuracion(anio_id, TipoAlerta.SEGUIMIENTO_REQUERIDO)
                if cfg is not None and cfg.activa:
                    umbral = cfg.umbral
            except Exception:
                umbral = None

        resultado: list[ResumenConvivenciaDTO] = []
        for est in estudiantes:
            est_id = getattr(est, "id", None)
            if est_id is None:
                continue
            concepto = conceptos.get(est_id)
            num_neg = negativos_por_est.get(est_id, 0)
            nombre = f"{getattr(est, 'apellido', '')} {getattr(est, 'nombre', '')}".strip() or str(
                est_id
            )
            supera = umbral is not None and num_neg >= umbral
            resultado.append(
                ResumenConvivenciaDTO(
                    estudiante_id=est_id,
                    nombre=nombre,
                    num_observaciones=obs_por_est.get(est_id, 0),
                    num_registros_negativos=num_neg,
                    nota=concepto.valor if concepto else None,
                    nivel_nombre=concepto.nivel_nombre if concepto else None,
                    supera_umbral=supera,
                )
            )
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
            c.estudiante_id: c for c in self.listar_conceptos_grupo(grupo_id, periodo_id)
        }

        from src.services.contexto_tenant import institucion_actual

        _scope = institucion_actual() or "*"
        tipos_situacion = self._repo.listar_tipos_situacion(institucion_id=_scope, solo_activas=False)
        tipos_map = {t.id: t.nombre for t in tipos_situacion if t.id is not None}
        hay_tipos = bool(tipos_map)

        todos_registros = self._repo.listar_registros(
            FiltroConvivenciaDTO(grupo_id=grupo_id, periodo_id=periodo_id, por_pagina=None),
            institucion_id=_scope,
        )
        regs_neg_por_est: dict[int, list] = {}
        conteos_tipo_por_est: dict[int, dict[str, int]] = {}
        _TIPO_A_CONTEO = {
            "fortaleza": "fortalezas", "dificultad": "dificultades",
            "compromiso": "compromisos", "citacion_acudiente": "citaciones",
            "descargo": "descargos",
        }
        for reg in todos_registros:
            if getattr(reg, "es_negativo", False):
                regs_neg_por_est.setdefault(reg.estudiante_id, []).append(reg)
            tipo_v = reg.tipo.value if hasattr(reg.tipo, "value") else str(reg.tipo)
            conteos = conteos_tipo_por_est.setdefault(reg.estudiante_id, {
                "fortalezas": 0, "dificultades": 0, "compromisos": 0,
                "citaciones": 0, "descargos": 0,
            })
            clave = _TIPO_A_CONTEO.get(tipo_v)
            if clave:
                conteos[clave] += 1

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
            nombre = f"{getattr(est, 'apellido', '')} {getattr(est, 'nombre', '')}".strip() or str(
                est_id
            )

            desglose: dict[str, int] | None = None
            if hay_tipos:
                desglose = {nombre: 0 for nombre in tipos_map.values()}
                for reg in regs_neg_por_est.get(est_id, []):
                    ts_id = getattr(reg, "tipo_situacion_id", None)
                    tipo_nombre = tipos_map.get(ts_id, "Sin clasificar") if ts_id is not None else "Sin clasificar"
                    desglose[tipo_nombre] = desglose.get(tipo_nombre, 0) + 1

            ct = conteos_tipo_por_est.get(est_id, {})
            filas.append(
                ReporteConvivenciaFilaDTO(
                    estudiante_id=est_id,
                    nombre=nombre,
                    valor=concepto.valor if concepto else None,
                    nivel_nombre=concepto.nivel_nombre if concepto else None,
                    concepto=concepto.concepto if concepto else None,
                    observaciones=textos_obs,
                    desglose_por_tipo=desglose,
                    fortalezas=ct.get("fortalezas", 0),
                    dificultades=ct.get("dificultades", 0),
                    compromisos=ct.get("compromisos", 0),
                    citaciones=ct.get("citaciones", 0),
                    descargos=ct.get("descargos", 0),
                )
            )
        return filas

    # ------------------------------------------------------------------
    # Exportación del reporte (convivencia_06b)
    # ------------------------------------------------------------------

    # Definición de columnas del reporte de periodo. Fuente única de verdad:
    # (clave, encabezado). El servicio decide qué se exporta y en qué orden;
    # la página no participa en esa decisión.
    _COLUMNAS_REPORTE_PERIODO: tuple[tuple[str, str], ...] = (
        ("estudiante", "Estudiante"),
        ("nota", "Nota comport."),
        ("nivel", "Desempeño"),
        ("fortalezas", "Fortalezas"),
        ("dificultades", "Dificultades"),
        ("compromisos", "Compromisos"),
        ("citaciones", "Citaciones"),
        ("descargos", "Descargos"),
        ("concepto", "Concepto de comportamiento"),
        ("observaciones", "Observaciones"),
    )

    def _fila_a_dict_exportacion(
        self,
        fila: ReporteConvivenciaFilaDTO,
    ) -> dict:
        """Aplana un DTO a un dict con las columnas del reporte."""
        d: dict = {
            "estudiante": fila.nombre,
            "nota": "" if fila.valor is None else fila.valor,
            "nivel": fila.nivel_nombre or "",
            "fortalezas": fila.fortalezas,
            "dificultades": fila.dificultades,
            "compromisos": fila.compromisos,
            "citaciones": fila.citaciones,
            "descargos": fila.descargos,
            "concepto": fila.concepto or "",
            "observaciones": "\n".join(fila.observaciones) if fila.observaciones else "",
        }
        if fila.desglose_por_tipo is not None:
            for tipo_nombre, conteo in fila.desglose_por_tipo.items():
                d[tipo_nombre] = conteo
        return d

    @staticmethod
    def _desglose_cols_de_filas(filas: list[ReporteConvivenciaFilaDTO]) -> list[str]:
        """Recopila los nombres de tipo de desglose en orden de aparición."""
        seen: set[str] = set()
        cols: list[str] = []
        for fila in filas:
            if fila.desglose_por_tipo:
                for nombre in fila.desglose_por_tipo:
                    if nombre not in seen:
                        cols.append(nombre)
                        seen.add(nombre)
        return cols

    def _reporte_periodo_a_html(
        self,
        filas: list[ReporteConvivenciaFilaDTO],
        titulo: str,
    ) -> str:
        """HTML compacto del reporte para el exporter PDF (puerto HTML → PDF)."""
        desglose_cols = self._desglose_cols_de_filas(filas)
        columnas = list(self._COLUMNAS_REPORTE_PERIODO) + [(n, n) for n in desglose_cols]
        heads_html = "".join(f"<th>{h}</th>" for _, h in columnas)
        if not filas:
            cuerpo = "<p>Sin datos.</p>"
        else:
            filas_html: list[str] = []
            for fila in filas:
                d = self._fila_a_dict_exportacion(fila)
                cells = "".join(
                    f"<td>{str(d.get(k, '')).replace(chr(10), '<br/>')}</td>"
                    for k, _ in columnas
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
        **kwargs,
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
                "ConvivenciaService no tiene exporter inyectado; no puede exportar reportes."
            )
        formato_norm = (formato or "").strip().lower()
        if formato_norm not in ("excel", "pdf"):
            raise ValueError(f"Formato no soportado: {formato!r}. Usa 'excel' o 'pdf'.")

        filas = self.reporte_periodo_grupo(grupo_id, periodo_id)
        desglose_cols = self._desglose_cols_de_filas(filas)
        filas_dict = [self._fila_a_dict_exportacion(f) for f in filas]
        for fd, fila in zip(filas_dict, filas):
            fd["num_obs"] = len(fila.observaciones)

        grupo_nombre = kwargs.get("grupo", "")
        periodo_nombre = kwargs.get("periodo", "")

        if formato_norm == "excel":
            from src.infrastructure.exporters.openpyxl_exporter import (
                generar_reporte_convivencia_grupo_excel,
            )

            return generar_reporte_convivencia_grupo_excel(
                filas=filas_dict,
                titulo=titulo,
                grupo=grupo_nombre,
                periodo=periodo_nombre,
                desglose_cols=desglose_cols,
            )

        from src.infrastructure.exporters.boletin_pdf import (
            generar_reporte_convivencia_grupo_pdf,
        )

        return generar_reporte_convivencia_grupo_pdf(
            filas=filas_dict,
            titulo=titulo,
            grupo=grupo_nombre,
            periodo=periodo_nombre,
            desglose_cols=desglose_cols,
        )

    # ------------------------------------------------------------------
    # Catálogo de tipos de situación — Ley 1620 (convivencia_34)
    # ------------------------------------------------------------------

    def listar_tipos_situacion(self, solo_activas: bool = True) -> list[TipoSituacion]:
        """Retorna los tipos de situación activos del tenant activo."""
        from src.services.contexto_tenant import institucion_actual

        return self._repo.listar_tipos_situacion(
            solo_activas=solo_activas, institucion_id=institucion_actual() or "*"
        )

    @requiere_escritura
    def crear_tipo_situacion(
        self,
        dto: NuevoTipoSituacionDTO,
        usuario_rol: str | None = None,
    ) -> TipoSituacion:
        """Crea un tipo de situación. Solo director y coordinador."""
        if usuario_rol not in ("director", "coordinador"):
            raise PermissionError("Solo directores y coordinadores pueden gestionar tipos de situacion.")
        inst_id = self._resolver_institucion(None)
        tipo = TipoSituacion(
            nombre=dto.nombre,
            nivel=dto.nivel,
            descripcion=dto.descripcion,
            protocolo=dto.protocolo,
            institucion_id=inst_id,
        )
        return self._repo.guardar_tipo_situacion(tipo)

    @requiere_escritura
    def actualizar_tipo_situacion(
        self,
        tipo_id: int,
        dto: NuevoTipoSituacionDTO,
        usuario_rol: str | None = None,
    ) -> TipoSituacion:
        """Actualiza nombre/nivel/descripción/protocolo de un tipo existente."""
        if usuario_rol not in ("director", "coordinador"):
            raise PermissionError("Solo directores y coordinadores pueden gestionar tipos de situacion.")
        tipo = self._repo.get_tipo_situacion(tipo_id)
        if tipo is None:
            raise ValueError(f"Tipo de situacion con id {tipo_id} no existe.")
        actualizado = tipo.model_copy(
            update={
                "nombre": dto.nombre,
                "nivel": dto.nivel,
                "descripcion": dto.descripcion,
                "protocolo": dto.protocolo,
            }
        )
        return self._repo.actualizar_tipo_situacion(actualizado)

    @requiere_escritura
    def desactivar_tipo_situacion(
        self,
        tipo_id: int,
        usuario_rol: str | None = None,
    ) -> TipoSituacion:
        """Desactiva un tipo de situación (activa=False) sin eliminarlo."""
        if usuario_rol not in ("director", "coordinador"):
            raise PermissionError("Solo directores y coordinadores pueden gestionar tipos de situacion.")
        tipo = self._repo.get_tipo_situacion(tipo_id)
        if tipo is None:
            raise ValueError(f"Tipo de situacion con id {tipo_id} no existe.")
        desactivado = tipo.model_copy(update={"activa": False})
        return self._repo.actualizar_tipo_situacion(desactivado)

    # ------------------------------------------------------------------
    # Catálogo de medidas pedagógicas (convivencia_36)
    # ------------------------------------------------------------------

    def listar_medidas_pedagogicas(self, solo_activas: bool = True) -> list[MedidaPedagogica]:
        """Retorna las medidas pedagógicas del tenant activo."""
        from src.services.contexto_tenant import institucion_actual

        return self._repo.listar_medidas(
            solo_activas=solo_activas, institucion_id=institucion_actual() or "*"
        )

    @requiere_escritura
    def crear_medida_pedagogica(
        self,
        dto: NuevaMedidaPedagogicaDTO,
        usuario_rol: str | None = None,
    ) -> MedidaPedagogica:
        """Crea una medida pedagógica. Solo director y coordinador."""
        if usuario_rol not in ("director", "coordinador"):
            raise PermissionError("Solo directores y coordinadores pueden gestionar medidas pedagogicas.")
        inst_id = self._resolver_institucion(None)
        medida = MedidaPedagogica(
            nombre=dto.nombre,
            descripcion=dto.descripcion,
            nivel_minimo=dto.nivel_minimo,
            institucion_id=inst_id,
        )
        return self._repo.guardar_medida(medida)

    @requiere_escritura
    def actualizar_medida_pedagogica(
        self,
        medida_id: int,
        dto: NuevaMedidaPedagogicaDTO,
        usuario_rol: str | None = None,
    ) -> MedidaPedagogica:
        """Actualiza nombre/descripcion/nivel_minimo de una medida existente."""
        if usuario_rol not in ("director", "coordinador"):
            raise PermissionError("Solo directores y coordinadores pueden gestionar medidas pedagogicas.")
        medida = self._repo.get_medida(medida_id)
        if medida is None:
            raise ValueError(f"Medida pedagogica con id {medida_id} no existe.")
        actualizada = medida.model_copy(
            update={
                "nombre": dto.nombre,
                "descripcion": dto.descripcion,
                "nivel_minimo": dto.nivel_minimo,
            }
        )
        return self._repo.actualizar_medida(actualizada)

    @requiere_escritura
    def desactivar_medida_pedagogica(
        self,
        medida_id: int,
        usuario_rol: str | None = None,
    ) -> MedidaPedagogica:
        """Desactiva una medida pedagógica (activa=False) sin eliminarla."""
        if usuario_rol not in ("director", "coordinador"):
            raise PermissionError("Solo directores y coordinadores pueden gestionar medidas pedagogicas.")
        medida = self._repo.get_medida(medida_id)
        if medida is None:
            raise ValueError(f"Medida pedagogica con id {medida_id} no existe.")
        desactivada = medida.model_copy(update={"activa": False})
        return self._repo.actualizar_medida(desactivada)

    # ------------------------------------------------------------------
    # Catálogo de categorías de observación (convivencia_09 / _10)
    # ------------------------------------------------------------------

    def listar_categorias(
        self,
        solo_activas: bool = True,
    ) -> list[CategoriaObservacion]:
        """Retorna el catálogo de categorías del tenant activo."""
        from src.services.contexto_tenant import institucion_actual

        return self._repo.listar_categorias(
            solo_activas=solo_activas, institucion_id=institucion_actual() or "*"
        )

    @requiere_escritura
    def crear_categoria(
        self,
        dto: NuevaCategoriaDTO,
    ) -> CategoriaObservacion:
        """Crea una nueva categoría de observación inyectando el tenant."""
        inst_id = self._resolver_institucion(None)
        categoria = CategoriaObservacion(
            nombre=dto.nombre,
            es_comportamental=dto.es_comportamental,
            institucion_id=inst_id,
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
            raise ValueError(f"Categoría con id {categoria_id} no existe.")
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
            raise ValueError(f"Categoría con id {categoria_id} no existe.")
        desactivada = categoria.model_copy(update={"activa": False})
        return self._repo.actualizar_categoria(desactivada)

    def listar_todas_plantillas(
        self, categoria_id: int | None = None
    ) -> list[PlantillaObservacion]:
        """Retorna TODAS las plantillas (activas e inactivas), opcionalmente filtradas por categoría."""
        from src.services.contexto_tenant import institucion_actual

        return self._repo.listar_plantillas(
            categoria_id=categoria_id, solo_activas=False, institucion_id=institucion_actual() or "*"
        )

    @requiere_escritura
    def crear_plantilla(
        self,
        dto: NuevaPlantillaDTO,
        usuario_id: int | None = None,
        usuario_rol: str | None = None,
    ) -> PlantillaObservacion:
        """Crea una nueva plantilla de observación. Director, coordinador y profesor."""
        if usuario_rol not in ("director", "coordinador", "profesor"):
            raise PermissionError(
                "Solo directores, coordinadores y profesores pueden crear plantillas."
            )
        inst_id = self._resolver_institucion(None)
        plantilla = PlantillaObservacion(
            texto=dto.texto, categoria_id=dto.categoria_id, institucion_id=inst_id
        )
        return self._repo.guardar_plantilla(plantilla)

    @requiere_escritura
    def actualizar_plantilla(
        self,
        plantilla_id: int,
        dto: NuevaPlantillaDTO,
        usuario_id: int | None = None,
        usuario_rol: str | None = None,
    ) -> PlantillaObservacion:
        """Actualiza texto y/o categoría de una plantilla. Director, coordinador y profesor."""
        if usuario_rol not in ("director", "coordinador", "profesor"):
            raise PermissionError(
                "Solo directores, coordinadores y profesores pueden actualizar plantillas."
            )
        plantilla = self._repo.get_plantilla(plantilla_id)
        if plantilla is None:
            raise ValueError(f"Plantilla con id {plantilla_id} no existe.")
        actualizada = plantilla.model_copy(
            update={"texto": dto.texto, "categoria_id": dto.categoria_id}
        )
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

    def listar_plantillas(self, categoria_id: int | None = None) -> list[PlantillaObservacion]:
        """Retorna las plantillas activas del tenant activo, filtradas por categoría opcional."""
        from src.services.contexto_tenant import institucion_actual

        return self._repo.listar_plantillas(
            categoria_id=categoria_id, solo_activas=True, institucion_id=institucion_actual() or "*"
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
                raise PermissionError("Solo puedes registrar observaciones de tus asignaciones")

        # Upsert con origen="plantilla"
        existente = self._repo.get_observacion_por_asignacion(
            dto.estudiante_id, dto.asignacion_id, dto.periodo_id
        )
        if existente is not None:
            obs_actualizada = existente.model_copy(
                update={
                    "texto": dto.texto,
                    "es_publica": dto.es_publica,
                    "categoria_id": dto.categoria_id,
                    "origen": "plantilla",
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
        from src.services.contexto_tenant import institucion_actual

        return self._repo.listar_plantillas(
            categoria_id=categoria_id, solo_activas=True, institucion_id=institucion_actual() or "*"
        )[:limite]

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

        obs_actualizada = obs.model_copy(update={"registro_comportamiento_id": registro.id})
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
        _roles_plenos = ("director", "coordinador")
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
                            autorizado = self._catalogo_academico_svc_provider().puede_gestionar_comportamiento_en_grupo(
                                usuario_rol, usuario_id, grupo_id_est
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
                    "Solo director, coordinador o director de grupo pueden ver el seguimiento 360°"
                )

        # ── Nombre del estudiante ────────────────────────────────────────────
        nombre = str(estudiante_id)
        if self._estudiante_svc_provider is not None:
            try:
                est = self._estudiante_svc_provider().get_by_id(estudiante_id)
                nombre = (
                    f"{getattr(est, 'apellido', '')} {getattr(est, 'nombre', '')}".strip() or nombre
                )
            except Exception:
                pass

        # ── Nota de comportamiento y concepto ───────────────────────────────
        nota_comportamiento: float | None = None
        concepto: str | None = None
        nivel_comportamiento: str | None = None
        try:
            concepto_dto = self.get_concepto_periodo(estudiante_id, periodo_id)
            nota_comportamiento = concepto_dto.valor
            concepto = concepto_dto.concepto
            nivel_comportamiento = concepto_dto.nivel_nombre
        except RuntimeError:
            # Providers de niveles no disponibles; extrae la nota directamente.
            try:
                nota = self._repo.get_nota(estudiante_id, periodo_id)
                if nota is not None:
                    nota_comportamiento = nota.valor
                    concepto = nota.observacion
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
                from src.services.contexto_tenant import institucion_actual as _ia

                _scope = _ia() or "*"
                filtro_alertas = FiltroAlertasDTO(
                    institucion_id=_scope,
                    estudiante_id=estudiante_id,
                    solo_pendientes=True,
                )
                alertas = self._alerta_repo.listar_alertas(filtro_alertas)
                alertas_activas = [str(getattr(a, "descripcion", a)) for a in alertas]
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

    # ------------------------------------------------------------------
    # Observador del estudiante (convivencia_37)
    # ------------------------------------------------------------------

    def observador_estudiante(
        self,
        estudiante_id: int,
        anio_id: int,
        periodo_id: int | None = None,
    ) -> dict:
        """Consolida el observador del estudiante como dict estructurado.

        Requiere estudiante_svc_provider y periodo_svc_provider.

        Claves del resultado:
          estudiante  — datos identificatorios del estudiante
          institucion — datos del membrete
          anio        — nombre/id del año lectivo
          periodo     — nombre del periodo filtrado, o None si es anual
          entradas    — lista cronológica ASC (observaciones + registros)
          resumen     — totales (fortalezas, dificultades, compromisos,
                        citaciones, descargos, num_observaciones,
                        notas_por_periodo)
        """
        from datetime import datetime

        if self._estudiante_svc_provider is None or self._periodo_svc_provider is None:
            raise RuntimeError(
                "ConvivenciaService requiere estudiante_svc_provider y "
                "periodo_svc_provider para generar el observador del estudiante."
            )

        # ── Datos del estudiante ────────────────────────────────────────
        _GENERO_DISPLAY = {"M": "Masculino", "F": "Femenino", "OTRO": "Otro"}
        _PARENTESCO_DISPLAY = {
            "padre": "Padre", "madre": "Madre", "abuelo": "Abuelo",
            "abuela": "Abuela", "tio": "Tío", "tia": "Tía",
            "hermano": "Hermano", "hermana": "Hermana",
            "tutor_legal": "Tutor legal", "otro": "Otro",
        }
        try:
            est = self._estudiante_svc_provider().get_by_id(estudiante_id)
            nombre_est = (
                f"{getattr(est, 'apellido', '')} {getattr(est, 'nombre', '')}".strip()
                or str(estudiante_id)
            )
            grupo_id_est = getattr(est, "grupo_id", None)
            grupo_grado = (
                self._repo.resolver_grupo_grado(grupo_id_est) if grupo_id_est else {}
            )
            fecha_nac = getattr(est, "fecha_nacimiento", None)
            genero_raw = getattr(est, "genero", None)
            genero_str = _GENERO_DISPLAY.get(str(genero_raw), "") if genero_raw else ""
            direccion_est = getattr(est, "direccion", None) or ""

            acudiente_data = self._repo.resolver_acudiente_principal(estudiante_id)
            if acudiente_data:
                parentesco_raw = acudiente_data.get("parentesco", "")
                acudiente_data["parentesco_display"] = _PARENTESCO_DISPLAY.get(parentesco_raw, parentesco_raw)

            estudiante_data: dict = {
                "id": estudiante_id,
                "nombre": nombre_est,
                "apellido": getattr(est, "apellido", ""),
                "primer_nombre": getattr(est, "nombre", ""),
                "documento": getattr(est, "documento_display", None) or str(estudiante_id),
                "grupo": grupo_grado.get("grupo_nombre", ""),
                "grado": grupo_grado.get("grado_nombre", ""),
                "fecha_nacimiento": fecha_nac,
                "genero": genero_str,
                "direccion": direccion_est,
                "acudiente": acudiente_data,
            }
        except Exception:
            estudiante_data = {
                "id": estudiante_id,
                "nombre": str(estudiante_id),
                "apellido": "",
                "primer_nombre": "",
                "documento": str(estudiante_id),
                "grupo": "",
                "grado": "",
                "fecha_nacimiento": None,
                "genero": "",
                "direccion": "",
                "acudiente": {},
            }

        # ── Periodos del año ───────────────────────────────────────────
        periodos = self._periodo_svc_provider().listar_por_anio(anio_id)
        periodo_nombre_map: dict[int, str] = {p.id: p.nombre for p in periodos}

        # ── Catálogos (lookup sin N+1) ─────────────────────────────────
        from src.services.contexto_tenant import institucion_actual

        _scope = institucion_actual() or "*"
        tipos_sit_map: dict[int, str] = {
            t.id: t.nombre
            for t in self._repo.listar_tipos_situacion(institucion_id=_scope, solo_activas=False)
            if t.id is not None
        }
        medidas_map: dict[int, str] = {
            m.id: m.nombre
            for m in self._repo.listar_medidas(institucion_id=_scope, solo_activas=False)
            if m.id is not None
        }
        cat_map: dict[int, str] = {
            c.id: c.nombre
            for c in self._repo.listar_categorias(institucion_id=_scope, solo_activas=False)
            if c.id is not None
        }

        # ── Observaciones públicas ─────────────────────────────────────
        obs_list = self._repo.listar_observaciones_por_estudiante(
            estudiante_id, periodo_id, solo_publicas=True
        )
        valid_periodo_ids = set(periodo_nombre_map.keys())
        if periodo_id is None:
            obs_list = [o for o in obs_list if o.periodo_id in valid_periodo_ids]

        # ── Registros de comportamiento ───────────────────────────────
        filtro = FiltroConvivenciaDTO(
            estudiante_id=estudiante_id,
            periodo_id=periodo_id,
            por_pagina=None,
        )
        registros = self._repo.listar_registros(filtro, institucion_id=_scope)
        if periodo_id is None:
            registros = [r for r in registros if r.periodo_id in valid_periodo_ids]

        # ── Entradas de seguimiento por registro (batch) ──────────────
        reg_ids = [reg.id for reg in registros if reg.id is not None]
        seguimiento_map: dict[int, list] = self._repo.listar_entradas_seguimiento_batch(reg_ids)

        # ── Notas de comportamiento ────────────────────────────────────
        notas_est = {
            n.periodo_id: n for n in self._repo.listar_notas_por_estudiante(estudiante_id)
        }

        # ── Resolver nombres de usuario (batch) ──────────────────────
        all_user_ids: set[int] = set()
        for obs in obs_list:
            if obs.usuario_id:
                all_user_ids.add(obs.usuario_id)
        for reg in registros:
            if reg.usuario_registro_id:
                all_user_ids.add(reg.usuario_registro_id)
        for seg_list in seguimiento_map.values():
            for se in seg_list:
                if se.usuario_id:
                    all_user_ids.add(se.usuario_id)
        nombres_usuario = self._repo.resolver_nombres_usuario(list(all_user_ids))

        # ── Resolver nombres de asignatura (batch) ────────────────────
        asig_ids = list({obs.asignacion_id for obs in obs_list if obs.asignacion_id})
        asig_nombre_map = self._repo.resolver_nombres_asignatura(asig_ids)

        def _nombre_usuario(uid: int | None) -> str:
            if not uid:
                return "—"
            return nombres_usuario.get(uid, f"Usuario #{uid}")

        # ── Construir lista unificada ─────────────────────────────────
        entradas: list[dict] = []

        for obs in obs_list:
            cat_nombre = cat_map.get(obs.categoria_id) if obs.categoria_id else None
            asig_nombre = asig_nombre_map.get(obs.asignacion_id)
            entradas.append(
                {
                    "fecha": obs.fecha_registro,
                    "tipo": "observacion",
                    "subtipo": "publica" if obs.es_publica else "privada",
                    "tipo_situacion": None,
                    "descripcion": obs.texto,
                    "medida": None,
                    "responsable": _nombre_usuario(obs.usuario_id),
                    "categoria": cat_nombre,
                    "asignatura": asig_nombre,
                    "seguimiento_entries": [],
                    "periodo": periodo_nombre_map.get(obs.periodo_id, ""),
                }
            )

        for reg in registros:
            seg_entries = seguimiento_map.get(reg.id or 0, [])
            seg_dicts = [
                {
                    "fecha": se.fecha,
                    "texto": se.texto,
                    "responsable": se.usuario_nombre
                    or _nombre_usuario(se.usuario_id),
                }
                for se in seg_entries
            ]
            fecha_reg: datetime = datetime.combine(reg.fecha, datetime.min.time())
            entradas.append(
                {
                    "fecha": fecha_reg,
                    "tipo": "registro",
                    "subtipo": reg.tipo.value,
                    "tipo_situacion": tipos_sit_map.get(reg.tipo_situacion_id)
                    if reg.tipo_situacion_id
                    else None,
                    "descripcion": reg.descripcion,
                    "medida": medidas_map.get(reg.medida_id) if reg.medida_id else None,
                    "responsable": _nombre_usuario(reg.usuario_registro_id),
                    "categoria": None,
                    "asignatura": None,
                    "seguimiento_entries": seg_dicts,
                    "periodo": periodo_nombre_map.get(reg.periodo_id, ""),
                }
            )

        entradas.sort(key=lambda e: e["fecha"] or datetime.min)

        # ── Resumen estadístico ───────────────────────────────────────
        conteos: dict[str, int] = {
            "fortalezas": 0,
            "dificultades": 0,
            "compromisos": 0,
            "citaciones": 0,
            "descargos": 0,
        }
        for reg in registros:
            tipo_v = reg.tipo.value
            if tipo_v == "fortaleza":
                conteos["fortalezas"] += 1
            elif tipo_v == "dificultad":
                conteos["dificultades"] += 1
            elif tipo_v == "compromiso":
                conteos["compromisos"] += 1
            elif tipo_v == "citacion_acudiente":
                conteos["citaciones"] += 1
            elif tipo_v == "descargo":
                conteos["descargos"] += 1

        notas_por_periodo: dict[str, float | None] = {
            p.nombre: (notas_est[p.id].valor if p.id in notas_est else None)
            for p in periodos
        }

        resumen: dict = {
            **conteos,
            "num_observaciones": len(obs_list),
            "notas_por_periodo": notas_por_periodo,
        }

        # ── Datos de la institución ────────────────────────────────────
        institucion_data: dict = {
            "nombre": "Institución Educativa",
            "DANE": "",
            "rector": "",
            "municipio": "",
            "direccion": "",
            "telefono": "",
            "resolucion": "",
        }
        try:
            if self._configuracion_svc_provider is not None:
                cfg = self._configuracion_svc_provider().get_activa()
                if cfg is not None:
                    institucion_data["nombre"] = getattr(cfg, "nombre_institucion", None) or "Institución Educativa"
                    institucion_data["DANE"] = getattr(cfg, "dane_code", None) or ""
                    institucion_data["rector"] = getattr(cfg, "rector", None) or ""
                    institucion_data["municipio"] = getattr(cfg, "municipio", None) or ""
                    institucion_data["direccion"] = getattr(cfg, "direccion", None) or ""
                    institucion_data["telefono"] = getattr(cfg, "telefono_institucion", None) or ""
                    institucion_data["resolucion"] = getattr(cfg, "resolucion_aprobacion", None) or ""
        except Exception:
            pass

        periodo_nombre = periodo_nombre_map.get(periodo_id) if periodo_id else None

        return {
            "estudiante": estudiante_data,
            "institucion": institucion_data,
            "anio": str(anio_id),
            "periodo": periodo_nombre,
            "entradas": entradas,
            "resumen": resumen,
        }

    def exportar_observador(
        self,
        estudiante_id: int,
        anio_id: int,
        formato: str,
        periodo_id: int | None = None,
    ) -> bytes:
        """Genera el observador del estudiante y lo exporta a PDF o Excel.

        Args:
            estudiante_id, anio_id: contexto del observador.
            formato: "pdf" | "excel".
            periodo_id: si se provee, filtra el observador a ese periodo.

        Returns:
            Bytes del archivo listo para descarga.

        Raises:
            RuntimeError: si los providers requeridos no están disponibles.
            ValueError:   si el formato no es soportado.
        """
        formato_norm = (formato or "").strip().lower()
        if formato_norm not in ("pdf", "excel"):
            raise ValueError(f"Formato no soportado: {formato!r}. Usa 'pdf' o 'excel'.")

        datos = self.observador_estudiante(estudiante_id, anio_id, periodo_id)

        if formato_norm == "pdf":
            from src.infrastructure.exporters.observador_pdf import generar_observador_pdf

            return generar_observador_pdf(datos)

        from src.infrastructure.exporters.observador_excel import generar_observador_excel

        return generar_observador_excel(datos)


__all__ = [
    "ConvivenciaService",
    "NuevaAlertaSeguimientoDTO",
    "NuevaCategoriaDTO",
    "NuevaPlantillaDTO",
    "PlantillaObservacion",
    "Seguimiento360DTO",
    "TipoRegistro",
]
