"""
SqlaConvivenciaRepository — implementación SQLAlchemy Core de IConvivenciaRepository.

Decisiones de migración (T8 — Ola 3c):
- Todas las queries migradas a SQLAlchemy Core excepto dos casos que usan text():
  * listar_entradas_seguimiento / listar_entradas_seguimiento_batch: LEFT JOIN con
    usuarios en SELECT columnar — Core lo soporta bien; migrado a Core.
  * resolver_acudiente_principal: doble JOIN con condiciones especiales → Core.
- _build_filtro_sql refactorizado a _build_filtro_stmt que retorna un select() de Core.
- guardar_nota: INSERT OR REPLACE → _upsert() sobre (estudiante_id, grupo_id, periodo_id).
- Commit en escrituras: if self._conn is None: conn.commit()
- TenantScope: filtro si int, omitir si "*"
- model_dump() en lugar de .dict() (no hay usos de .dict() en el original).
"""
from __future__ import annotations

from datetime import date as _date

from sqlalchemy import delete, func, insert, select, update

from src.domain.models.convivencia import (
    CategoriaObservacion,
    EntradaSeguimiento,
    FiltroConvivenciaDTO,
    MedidaPedagogica,
    NotaComportamiento,
    ObservacionPeriodo,
    PlantillaObservacion,
    RegistroComportamiento,
    TipoRegistro,
    TipoSituacion,
)
from src.domain.models.tenant import TenantScope
from src.domain.ports.convivencia_repo import IConvivenciaRepository
from src.infrastructure.db.repositories.base import RepositorioBase
from src.infrastructure.db.schema import (
    acudientes,
    asignaciones,
    asignaturas,
    categorias_observacion,
    entradas_seguimiento,
    estudiante_acudiente,
    grados,
    grupos,
    medidas_pedagogicas,
    nota_comportamiento_periodo,
    observaciones_periodo,
    plantillas_observacion,
    registro_comportamiento,
    tipos_situacion,
    usuarios,
)

_TIPOS_NEGATIVOS = ("dificultad", "citacion_acudiente")


class SqlaConvivenciaRepository(RepositorioBase, IConvivenciaRepository):
    def __init__(self, conn=None):
        super().__init__(conn, observaciones_periodo)

    # ------------------------------------------------------------------
    # Row mappers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_observacion(row) -> ObservacionPeriodo:
        d = dict(row)
        d["es_publica"] = bool(d["es_publica"])
        return ObservacionPeriodo(**d)

    @staticmethod
    def _row_to_registro(row) -> RegistroComportamiento:
        d = dict(row)
        d["tipo"] = TipoRegistro(d["tipo"])
        d["requiere_firma"] = bool(d["requiere_firma"])
        d["acudiente_notificado"] = bool(d["acudiente_notificado"])
        d.setdefault("tipo_situacion_id", None)
        d.setdefault("medida_id", None)
        if isinstance(d.get("fecha"), str):
            d["fecha"] = _date.fromisoformat(d["fecha"])
        return RegistroComportamiento.model_construct(**d)

    @staticmethod
    def _row_to_nota(row) -> NotaComportamiento:
        return NotaComportamiento(**dict(row))

    @staticmethod
    def _row_to_categoria(row) -> CategoriaObservacion:
        d = dict(row)
        d["es_comportamental"] = bool(d["es_comportamental"])
        d["activa"] = bool(d["activa"])
        return CategoriaObservacion(**d)

    @staticmethod
    def _row_to_plantilla(row) -> PlantillaObservacion:
        d = dict(row)
        d["activa"] = bool(d["activa"])
        return PlantillaObservacion(**d)

    @staticmethod
    def _row_to_tipo_situacion(row) -> TipoSituacion:
        d = dict(row)
        d["activa"] = bool(d["activa"])
        return TipoSituacion(**d)

    @staticmethod
    def _row_to_entrada_seguimiento(row) -> EntradaSeguimiento:
        d = dict(row)
        return EntradaSeguimiento(
            id=d["id"],
            registro_id=d["registro_id"],
            fecha=d["fecha"],
            texto=d["texto"],
            usuario_id=d.get("usuario_id"),
            usuario_nombre=d.get("usuario_nombre"),
        )

    @staticmethod
    def _row_to_medida(row) -> MedidaPedagogica:
        d = dict(row)
        d["activa"] = bool(d["activa"])
        return MedidaPedagogica(**d)

    # ------------------------------------------------------------------
    # Observaciones de Periodo
    # ------------------------------------------------------------------

    def get_observacion(self, observacion_id: int) -> ObservacionPeriodo | None:
        stmt = select(observaciones_periodo).where(observaciones_periodo.c.id == observacion_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_observacion(row) if row else None

    def get_observacion_por_asignacion(
        self, estudiante_id: int, asignacion_id: int, periodo_id: int
    ) -> ObservacionPeriodo | None:
        stmt = (
            select(observaciones_periodo)
            .where(
                observaciones_periodo.c.estudiante_id == estudiante_id,
                observaciones_periodo.c.asignacion_id == asignacion_id,
                observaciones_periodo.c.periodo_id == periodo_id,
            )
            .limit(1)
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_observacion(row) if row else None

    def listar_observaciones_por_estudiante(
        self, estudiante_id: int, periodo_id: int | None = None, solo_publicas: bool = False
    ) -> list[ObservacionPeriodo]:
        stmt = select(observaciones_periodo).where(
            observaciones_periodo.c.estudiante_id == estudiante_id
        )
        if periodo_id is not None:
            stmt = stmt.where(observaciones_periodo.c.periodo_id == periodo_id)
        if solo_publicas:
            stmt = stmt.where(observaciones_periodo.c.es_publica == True)  # noqa: E712
        stmt = stmt.order_by(observaciones_periodo.c.periodo_id, observaciones_periodo.c.asignacion_id)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_observacion(r) for r in rows]

    def listar_observaciones_por_grupo(
        self, grupo_id: int, periodo_id: int | None = None, solo_publicas: bool = False
    ) -> list[ObservacionPeriodo]:
        stmt = (
            select(observaciones_periodo)
            .join(asignaciones, asignaciones.c.id == observaciones_periodo.c.asignacion_id)
            .where(asignaciones.c.grupo_id == grupo_id)
        )
        if periodo_id is not None:
            stmt = stmt.where(observaciones_periodo.c.periodo_id == periodo_id)
        if solo_publicas:
            stmt = stmt.where(observaciones_periodo.c.es_publica == True)  # noqa: E712
        stmt = stmt.order_by(
            observaciones_periodo.c.estudiante_id,
            observaciones_periodo.c.periodo_id,
            observaciones_periodo.c.asignacion_id,
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_observacion(r) for r in rows]

    def guardar_observacion(self, observacion: ObservacionPeriodo) -> ObservacionPeriodo:
        stmt = insert(observaciones_periodo).values(
            estudiante_id=observacion.estudiante_id,
            asignacion_id=observacion.asignacion_id,
            periodo_id=observacion.periodo_id,
            texto=observacion.texto,
            es_publica=int(observacion.es_publica),
            fecha_registro=observacion.fecha_registro,
            usuario_id=observacion.usuario_id,
            categoria_id=observacion.categoria_id,
            origen=observacion.origen,
            registro_comportamiento_id=observacion.registro_comportamiento_id,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return observacion.model_copy(update={"id": pk})

    def actualizar_observacion(self, observacion: ObservacionPeriodo) -> ObservacionPeriodo:
        stmt = (
            update(observaciones_periodo)
            .where(observaciones_periodo.c.id == observacion.id)
            .values(
                texto=observacion.texto,
                es_publica=int(observacion.es_publica),
                categoria_id=observacion.categoria_id,
                origen=observacion.origen,
                registro_comportamiento_id=observacion.registro_comportamiento_id,
            )
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
        return observacion

    def eliminar_observacion(self, observacion_id: int) -> bool:
        stmt = delete(observaciones_periodo).where(observaciones_periodo.c.id == observacion_id)
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    # ------------------------------------------------------------------
    # Registros de Comportamiento
    # ------------------------------------------------------------------

    def get_registro(self, registro_id: int) -> RegistroComportamiento | None:
        stmt = select(registro_comportamiento).where(registro_comportamiento.c.id == registro_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_registro(row) if row else None

    def _build_filtro_stmt(
        self,
        filtro: FiltroConvivenciaDTO,
        institucion_id: TenantScope,
    ):
        """Construye un SELECT * de registro_comportamiento con JOIN opcional para multi-tenant."""
        stmt = select(registro_comportamiento)
        if isinstance(institucion_id, int):
            stmt = stmt.join(grupos, grupos.c.id == registro_comportamiento.c.grupo_id)
            stmt = stmt.where(grupos.c.institucion_id == institucion_id)
        if filtro.estudiante_id is not None:
            stmt = stmt.where(registro_comportamiento.c.estudiante_id == filtro.estudiante_id)
        if filtro.grupo_id is not None:
            stmt = stmt.where(registro_comportamiento.c.grupo_id == filtro.grupo_id)
        if filtro.periodo_id is not None:
            stmt = stmt.where(registro_comportamiento.c.periodo_id == filtro.periodo_id)
        if filtro.tipo is not None:
            stmt = stmt.where(registro_comportamiento.c.tipo == filtro.tipo.value)
        if filtro.solo_negativos:
            stmt = stmt.where(registro_comportamiento.c.tipo.in_(_TIPOS_NEGATIVOS))
        return stmt

    def listar_registros(
        self,
        filtro: FiltroConvivenciaDTO,
        institucion_id: TenantScope,
    ) -> list[RegistroComportamiento]:
        stmt = self._build_filtro_stmt(filtro, institucion_id)
        stmt = stmt.order_by(registro_comportamiento.c.fecha.desc(), registro_comportamiento.c.id.desc())
        if filtro.por_pagina is not None:
            offset = (filtro.pagina - 1) * filtro.por_pagina
            stmt = stmt.limit(filtro.por_pagina).offset(offset)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_registro(r) for r in rows]

    def contar_registros(
        self,
        filtro: FiltroConvivenciaDTO,
        institucion_id: TenantScope,
    ) -> int:
        base = self._build_filtro_stmt(filtro, institucion_id)
        stmt = select(func.count()).select_from(base.subquery())
        with self._get_conn() as conn:
            return int(conn.execute(stmt).scalar() or 0)

    def guardar_registro(self, registro: RegistroComportamiento) -> RegistroComportamiento:
        stmt = insert(registro_comportamiento).values(
            estudiante_id=registro.estudiante_id,
            grupo_id=registro.grupo_id,
            periodo_id=registro.periodo_id,
            fecha=registro.fecha,
            tipo=registro.tipo.value,
            descripcion=registro.descripcion,
            seguimiento=registro.seguimiento,
            requiere_firma=int(registro.requiere_firma),
            acudiente_notificado=int(registro.acudiente_notificado),
            usuario_registro_id=registro.usuario_registro_id,
            tipo_situacion_id=registro.tipo_situacion_id,
            medida_id=registro.medida_id,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return registro.model_copy(update={"id": pk})

    def actualizar_registro(self, registro: RegistroComportamiento) -> RegistroComportamiento:
        stmt = (
            update(registro_comportamiento)
            .where(registro_comportamiento.c.id == registro.id)
            .values(
                seguimiento=registro.seguimiento,
                requiere_firma=int(registro.requiere_firma),
                acudiente_notificado=int(registro.acudiente_notificado),
                tipo_situacion_id=registro.tipo_situacion_id,
                medida_id=registro.medida_id,
            )
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
        return registro

    def eliminar_registro(self, registro_id: int) -> bool:
        stmt = delete(registro_comportamiento).where(registro_comportamiento.c.id == registro_id)
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    # ------------------------------------------------------------------
    # Notas de Comportamiento
    # ------------------------------------------------------------------

    def get_nota(self, estudiante_id: int, periodo_id: int) -> NotaComportamiento | None:
        stmt = select(nota_comportamiento_periodo).where(
            nota_comportamiento_periodo.c.estudiante_id == estudiante_id,
            nota_comportamiento_periodo.c.periodo_id == periodo_id,
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_nota(row) if row else None

    def listar_notas_por_estudiante(self, estudiante_id: int) -> list[NotaComportamiento]:
        stmt = (
            select(nota_comportamiento_periodo)
            .where(nota_comportamiento_periodo.c.estudiante_id == estudiante_id)
            .order_by(nota_comportamiento_periodo.c.periodo_id.desc())
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_nota(r) for r in rows]

    def listar_notas_por_grupo(self, grupo_id: int, periodo_id: int) -> list[NotaComportamiento]:
        stmt = (
            select(nota_comportamiento_periodo)
            .where(
                nota_comportamiento_periodo.c.grupo_id == grupo_id,
                nota_comportamiento_periodo.c.periodo_id == periodo_id,
            )
            .order_by(nota_comportamiento_periodo.c.estudiante_id)
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_nota(r) for r in rows]

    def guardar_nota(self, nota: NotaComportamiento) -> NotaComportamiento:
        """INSERT OR REPLACE → upsert sobre (estudiante_id, grupo_id, periodo_id)."""
        stmt = self._upsert(
            nota_comportamiento_periodo,
            {
                "estudiante_id": nota.estudiante_id,
                "grupo_id": nota.grupo_id,
                "periodo_id": nota.periodo_id,
                "valor": float(nota.valor),
                "desempeno_id": nota.desempeno_id,
                "observacion": nota.observacion,
                "usuario_id": nota.usuario_id,
            },
            conflict_cols=["estudiante_id", "grupo_id", "periodo_id"],
            update_cols=["valor", "desempeno_id", "observacion", "usuario_id"],
        )
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            pk = result.inserted_primary_key[0] if result.inserted_primary_key else nota.id
        return nota.model_copy(update={"id": pk})

    # ------------------------------------------------------------------
    # Categorías de Observación
    # ------------------------------------------------------------------

    def listar_categorias(
        self, institucion_id: TenantScope, solo_activas: bool = True
    ) -> list[CategoriaObservacion]:
        stmt = select(categorias_observacion)
        if solo_activas:
            stmt = stmt.where(categorias_observacion.c.activa == True)  # noqa: E712
        if isinstance(institucion_id, int):
            stmt = stmt.where(categorias_observacion.c.institucion_id == institucion_id)
        stmt = stmt.order_by(categorias_observacion.c.nombre)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_categoria(r) for r in rows]

    def get_categoria(self, categoria_id: int) -> CategoriaObservacion | None:
        stmt = select(categorias_observacion).where(categorias_observacion.c.id == categoria_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_categoria(row) if row else None

    def guardar_categoria(self, categoria: CategoriaObservacion) -> CategoriaObservacion:
        stmt = insert(categorias_observacion).values(
            nombre=categoria.nombre,
            es_comportamental=int(categoria.es_comportamental),
            activa=int(categoria.activa),
            institucion_id=categoria.institucion_id,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return categoria.model_copy(update={"id": pk})

    def actualizar_categoria(self, categoria: CategoriaObservacion) -> CategoriaObservacion:
        stmt = (
            update(categorias_observacion)
            .where(categorias_observacion.c.id == categoria.id)
            .values(
                nombre=categoria.nombre,
                es_comportamental=int(categoria.es_comportamental),
                activa=int(categoria.activa),
            )
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
        return categoria

    # ------------------------------------------------------------------
    # Plantillas de observación
    # ------------------------------------------------------------------

    def listar_plantillas(
        self,
        institucion_id: TenantScope,
        categoria_id: int | None = None,
        solo_activas: bool = True,
    ) -> list[PlantillaObservacion]:
        stmt = select(plantillas_observacion)
        if solo_activas:
            stmt = stmt.where(plantillas_observacion.c.activa == True)  # noqa: E712
        if categoria_id is not None:
            stmt = stmt.where(plantillas_observacion.c.categoria_id == categoria_id)
        if isinstance(institucion_id, int):
            stmt = stmt.where(plantillas_observacion.c.institucion_id == institucion_id)
        stmt = stmt.order_by(plantillas_observacion.c.uso_count.desc())
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_plantilla(r) for r in rows]

    def get_plantilla(self, plantilla_id: int) -> PlantillaObservacion | None:
        stmt = select(plantillas_observacion).where(plantillas_observacion.c.id == plantilla_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_plantilla(row) if row else None

    def guardar_plantilla(self, plantilla: PlantillaObservacion) -> PlantillaObservacion:
        stmt = insert(plantillas_observacion).values(
            texto=plantilla.texto,
            categoria_id=plantilla.categoria_id,
            uso_count=plantilla.uso_count,
            activa=int(plantilla.activa),
            institucion_id=plantilla.institucion_id,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return plantilla.model_copy(update={"id": pk})

    def actualizar_plantilla(self, plantilla: PlantillaObservacion) -> PlantillaObservacion:
        stmt = (
            update(plantillas_observacion)
            .where(plantillas_observacion.c.id == plantilla.id)
            .values(
                texto=plantilla.texto,
                categoria_id=plantilla.categoria_id,
                activa=int(plantilla.activa),
            )
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
        return plantilla

    def incrementar_uso_plantilla(self, plantilla_id: int) -> None:
        stmt = (
            update(plantillas_observacion)
            .where(plantillas_observacion.c.id == plantilla_id)
            .values(uso_count=plantillas_observacion.c.uso_count + 1)
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()

    # ------------------------------------------------------------------
    # Tipos de situación
    # ------------------------------------------------------------------

    def listar_tipos_situacion(
        self, institucion_id: TenantScope, solo_activas: bool = True
    ) -> list[TipoSituacion]:
        stmt = select(tipos_situacion)
        if solo_activas:
            stmt = stmt.where(tipos_situacion.c.activa == True)  # noqa: E712
        if isinstance(institucion_id, int):
            stmt = stmt.where(tipos_situacion.c.institucion_id == institucion_id)
        stmt = stmt.order_by(tipos_situacion.c.nivel, tipos_situacion.c.nombre)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_tipo_situacion(r) for r in rows]

    def get_tipo_situacion(self, tipo_situacion_id: int) -> TipoSituacion | None:
        stmt = select(tipos_situacion).where(tipos_situacion.c.id == tipo_situacion_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_tipo_situacion(row) if row else None

    def guardar_tipo_situacion(self, tipo_situacion: TipoSituacion) -> TipoSituacion:
        stmt = insert(tipos_situacion).values(
            nombre=tipo_situacion.nombre,
            nivel=tipo_situacion.nivel,
            descripcion=tipo_situacion.descripcion,
            protocolo=tipo_situacion.protocolo,
            activa=int(tipo_situacion.activa),
            institucion_id=tipo_situacion.institucion_id,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return tipo_situacion.model_copy(update={"id": pk})

    def actualizar_tipo_situacion(self, tipo_situacion: TipoSituacion) -> TipoSituacion:
        stmt = (
            update(tipos_situacion)
            .where(tipos_situacion.c.id == tipo_situacion.id)
            .values(
                nombre=tipo_situacion.nombre,
                nivel=tipo_situacion.nivel,
                descripcion=tipo_situacion.descripcion,
                protocolo=tipo_situacion.protocolo,
                activa=int(tipo_situacion.activa),
            )
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
        return tipo_situacion

    # ------------------------------------------------------------------
    # Entradas de seguimiento
    # ------------------------------------------------------------------

    def listar_entradas_seguimiento(self, registro_id: int) -> list[EntradaSeguimiento]:
        stmt = (
            select(
                entradas_seguimiento.c.id,
                entradas_seguimiento.c.registro_id,
                entradas_seguimiento.c.fecha,
                entradas_seguimiento.c.texto,
                entradas_seguimiento.c.usuario_id,
                usuarios.c.nombre_completo.label("usuario_nombre"),
            )
            .outerjoin(usuarios, usuarios.c.id == entradas_seguimiento.c.usuario_id)
            .where(entradas_seguimiento.c.registro_id == registro_id)
            .order_by(entradas_seguimiento.c.fecha.asc())
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_entrada_seguimiento(r) for r in rows]

    def listar_entradas_seguimiento_batch(
        self, registro_ids: list[int],
    ) -> dict[int, list[EntradaSeguimiento]]:
        if not registro_ids:
            return {}
        stmt = (
            select(
                entradas_seguimiento.c.id,
                entradas_seguimiento.c.registro_id,
                entradas_seguimiento.c.fecha,
                entradas_seguimiento.c.texto,
                entradas_seguimiento.c.usuario_id,
                usuarios.c.nombre_completo.label("usuario_nombre"),
            )
            .outerjoin(usuarios, usuarios.c.id == entradas_seguimiento.c.usuario_id)
            .where(entradas_seguimiento.c.registro_id.in_(registro_ids))
            .order_by(entradas_seguimiento.c.fecha.asc())
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
        result: dict[int, list[EntradaSeguimiento]] = {}
        for r in rows:
            entry = self._row_to_entrada_seguimiento(r)
            result.setdefault(entry.registro_id, []).append(entry)
        return result

    def guardar_entrada_seguimiento(self, entrada: EntradaSeguimiento) -> EntradaSeguimiento:
        stmt = insert(entradas_seguimiento).values(
            registro_id=entrada.registro_id,
            fecha=entrada.fecha,
            texto=entrada.texto,
            usuario_id=entrada.usuario_id,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return entrada.model_copy(update={"id": pk})

    # ------------------------------------------------------------------
    # Medidas pedagógicas
    # ------------------------------------------------------------------

    def listar_medidas(
        self, institucion_id: TenantScope, solo_activas: bool = True
    ) -> list[MedidaPedagogica]:
        stmt = select(medidas_pedagogicas)
        if solo_activas:
            stmt = stmt.where(medidas_pedagogicas.c.activa == True)  # noqa: E712
        if isinstance(institucion_id, int):
            stmt = stmt.where(medidas_pedagogicas.c.institucion_id == institucion_id)
        stmt = stmt.order_by(medidas_pedagogicas.c.nivel_minimo, medidas_pedagogicas.c.nombre)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_medida(r) for r in rows]

    def get_medida(self, medida_id: int) -> MedidaPedagogica | None:
        stmt = select(medidas_pedagogicas).where(medidas_pedagogicas.c.id == medida_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_medida(row) if row else None

    def guardar_medida(self, medida: MedidaPedagogica) -> MedidaPedagogica:
        stmt = insert(medidas_pedagogicas).values(
            nombre=medida.nombre,
            descripcion=medida.descripcion,
            nivel_minimo=medida.nivel_minimo,
            activa=int(medida.activa),
            institucion_id=medida.institucion_id,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return medida.model_copy(update={"id": pk})

    def actualizar_medida(self, medida: MedidaPedagogica) -> MedidaPedagogica:
        stmt = (
            update(medidas_pedagogicas)
            .where(medidas_pedagogicas.c.id == medida.id)
            .values(
                nombre=medida.nombre,
                descripcion=medida.descripcion,
                nivel_minimo=medida.nivel_minimo,
                activa=int(medida.activa),
            )
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
        return medida

    # ------------------------------------------------------------------
    # Lookups auxiliares
    # ------------------------------------------------------------------

    def resolver_nombres_usuario(self, usuario_ids: list[int]) -> dict[int, str]:
        if not usuario_ids:
            return {}
        stmt = select(usuarios.c.id, usuarios.c.nombre_completo).where(
            usuarios.c.id.in_(usuario_ids)
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).fetchall()
        return {row[0]: row[1] for row in rows}

    def resolver_nombres_asignatura(self, asignacion_ids: list[int]) -> dict[int, str]:
        if not asignacion_ids:
            return {}
        stmt = (
            select(asignaciones.c.id, asignaturas.c.nombre)
            .join(asignaturas, asignaturas.c.id == asignaciones.c.asignatura_id)
            .where(asignaciones.c.id.in_(asignacion_ids))
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).fetchall()
        return {row[0]: row[1] for row in rows}

    def resolver_grupo_grado(self, grupo_id: int) -> dict:
        stmt = (
            select(
                grupos.c.codigo,
                grupos.c.nombre,
                grupos.c.grado,
                grados.c.nombre.label("grado_nombre"),
            )
            .outerjoin(grados, grados.c.numero == grupos.c.grado)
            .where(grupos.c.id == grupo_id)
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
        if not row:
            return {"grupo_codigo": "", "grupo_nombre": "", "grado_nombre": ""}
        return {
            "grupo_codigo": row["codigo"] or "",
            "grupo_nombre": row["nombre"] or row["codigo"] or "",
            "grado_nombre": row["grado_nombre"] or (f"Grado {row['grado']}" if row["grado"] else ""),
        }

    def resolver_acudiente_principal(self, estudiante_id: int) -> dict:
        stmt = (
            select(
                acudientes.c.nombre_completo,
                acudientes.c.parentesco,
                acudientes.c.celular,
                acudientes.c.email,
                acudientes.c.direccion,
                acudientes.c.numero_documento,
            )
            .join(estudiante_acudiente, estudiante_acudiente.c.acudiente_id == acudientes.c.id)
            .where(
                estudiante_acudiente.c.estudiante_id == estudiante_id,
                estudiante_acudiente.c.es_principal == True,  # noqa: E712
                acudientes.c.activo == True,  # noqa: E712
            )
            .limit(1)
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
        if not row:
            return {}
        return {
            "nombre": row["nombre_completo"] or "",
            "parentesco": row["parentesco"] or "",
            "celular": row["celular"] or "",
            "email": row["email"] or "",
            "direccion": row["direccion"] or "",
            "documento": row["numero_documento"] or "",
        }


__all__ = ["SqlaConvivenciaRepository"]
