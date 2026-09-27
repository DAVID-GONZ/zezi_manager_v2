"""
SqlaEvaluacionRepository — implementación SQLAlchemy Core de IEvaluacionRepository.

Decisiones de migración:
- ON CONFLICT ... DO UPDATE: guardar_nota y guardar_puntos_extra usan _upsert().
- guardar_notas_masivas: sqlite_insert + on_conflict_do_update ejecutado con lista de dicts.
- suma_pesos_otras: filtro condicional explícito, más legible que COALESCE(?, 0).
- fecha NULLS LAST: actividades.c.fecha.nullslast().
- Notas son Float (schema.py, no Decimal).
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from src.domain.models.evaluacion import (
    Actividad,
    Categoria,
    EstadoActividad,
    Nota,
    PuntosExtra,
    ResultadoEstudianteDTO,
    TipoPuntosExtra,
)
from src.domain.ports.evaluacion_repo import IEvaluacionRepository
from src.infrastructure.db.repositories.base import RepositorioBase
from src.infrastructure.db.schema import (
    actividades,
    categorias,
    estudiantes,
    notas,
    puntos_extra,
)


class SqlaEvaluacionRepository(RepositorioBase, IEvaluacionRepository):
    def __init__(self, conn=None):
        super().__init__(conn, None)

    # ------------------------------------------------------------------
    # Row mappers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_categoria(row) -> Categoria:
        return Categoria(**dict(row))

    @staticmethod
    def _row_to_actividad(row) -> Actividad:
        d = dict(row)
        d["estado"] = EstadoActividad(d["estado"])
        return Actividad(**d)

    @staticmethod
    def _row_to_nota(row) -> Nota:
        return Nota(**dict(row))

    @staticmethod
    def _row_to_puntos_extra(row) -> PuntosExtra:
        d = dict(row)
        d["tipo"] = TipoPuntosExtra(d["tipo"])
        return PuntosExtra(**d)

    # ------------------------------------------------------------------
    # Categorías
    # ------------------------------------------------------------------

    def listar_categorias(self, asignacion_id: int, periodo_id: int) -> list[Categoria]:
        stmt = (
            select(categorias)
            .where(
                categorias.c.asignacion_id == asignacion_id,
                categorias.c.periodo_id == periodo_id,
            )
            .order_by(categorias.c.nombre)
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_categoria(r) for r in rows]

    def get_categoria(self, cat_id: int) -> Categoria | None:
        stmt = select(categorias).where(categorias.c.id == cat_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_categoria(row) if row else None

    def guardar_categoria(self, categoria: Categoria) -> Categoria:
        stmt = categorias.insert().values(
            nombre=categoria.nombre,
            peso=float(categoria.peso),
            asignacion_id=categoria.asignacion_id,
            periodo_id=categoria.periodo_id,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
            return categoria.model_copy(update={"id": pk})

    def actualizar_categoria(self, categoria: Categoria) -> Categoria:
        stmt = (
            categorias.update()
            .where(categorias.c.id == categoria.id)
            .values(nombre=categoria.nombre, peso=float(categoria.peso))
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return categoria

    def eliminar_categoria(self, cat_id: int) -> None:
        stmt = categorias.delete().where(categorias.c.id == cat_id)
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()

    def suma_pesos_otras(
        self,
        asignacion_id: int,
        periodo_id: int,
        excluir_cat_id: int | None = None,
    ) -> float:
        stmt = select(func.coalesce(func.sum(categorias.c.peso), 0.0)).where(
            categorias.c.asignacion_id == asignacion_id,
            categorias.c.periodo_id == periodo_id,
        )
        if excluir_cat_id is not None:
            stmt = stmt.where(categorias.c.id != excluir_cat_id)
        with self._get_conn() as conn:
            return float(conn.execute(stmt).scalar() or 0.0)

    # ------------------------------------------------------------------
    # Actividades
    # ------------------------------------------------------------------

    def listar_actividades(self, asignacion_id: int, periodo_id: int) -> list[Actividad]:
        stmt = (
            select(actividades)
            .join(categorias, categorias.c.id == actividades.c.categoria_id)
            .where(
                categorias.c.asignacion_id == asignacion_id,
                categorias.c.periodo_id == periodo_id,
            )
            .order_by(actividades.c.fecha.nullslast(), actividades.c.nombre)
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_actividad(r) for r in rows]

    def listar_actividades_por_categoria(self, cat_id: int) -> list[Actividad]:
        stmt = (
            select(actividades)
            .where(actividades.c.categoria_id == cat_id)
            .order_by(actividades.c.fecha.nullslast(), actividades.c.nombre)
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_actividad(r) for r in rows]

    def listar_actividades_publicadas(
        self,
        asignacion_id: int,
        periodo_id: int,
        hasta_fecha: date | None = None,
    ) -> list[Actividad]:
        stmt = (
            select(actividades)
            .join(categorias, categorias.c.id == actividades.c.categoria_id)
            .where(
                categorias.c.asignacion_id == asignacion_id,
                categorias.c.periodo_id == periodo_id,
                actividades.c.estado.in_(["publicada", "cerrada"]),
            )
        )
        if hasta_fecha is not None:
            stmt = stmt.where(
                or_(
                    actividades.c.fecha.is_(None),
                    actividades.c.fecha <= hasta_fecha.isoformat(),
                )
            )
        stmt = stmt.order_by(actividades.c.fecha.nullslast(), actividades.c.nombre)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_actividad(r) for r in rows]

    def get_actividad(self, act_id: int) -> Actividad | None:
        stmt = select(actividades).where(actividades.c.id == act_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_actividad(row) if row else None

    def guardar_actividad(self, actividad: Actividad) -> Actividad:
        stmt = actividades.insert().values(
            nombre=actividad.nombre,
            descripcion=actividad.descripcion,
            fecha=actividad.fecha,
            valor_maximo=float(actividad.valor_maximo),
            estado=actividad.estado.value,
            categoria_id=actividad.categoria_id,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
            return actividad.model_copy(update={"id": pk})

    def actualizar_actividad(self, actividad: Actividad) -> Actividad:
        stmt = (
            actividades.update()
            .where(actividades.c.id == actividad.id)
            .values(
                nombre=actividad.nombre,
                descripcion=actividad.descripcion,
                fecha=actividad.fecha,
                valor_maximo=float(actividad.valor_maximo),
                estado=actividad.estado.value,
            )
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return actividad

    def actualizar_estado_actividad(self, act_id: int, estado: EstadoActividad) -> bool:
        stmt = (
            actividades.update()
            .where(actividades.c.id == act_id)
            .values(estado=estado.value)
        )
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    def eliminar_actividad(self, act_id: int) -> None:
        stmt = actividades.delete().where(actividades.c.id == act_id)
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()

    # ------------------------------------------------------------------
    # Notas
    # ------------------------------------------------------------------

    def listar_notas_por_estudiante(
        self,
        estudiante_id: int,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[Nota]:
        stmt = (
            select(notas)
            .join(actividades, actividades.c.id == notas.c.actividad_id)
            .join(categorias, categorias.c.id == actividades.c.categoria_id)
            .where(
                notas.c.estudiante_id == estudiante_id,
                categorias.c.asignacion_id == asignacion_id,
                categorias.c.periodo_id == periodo_id,
            )
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_nota(r) for r in rows]

    def listar_notas_por_actividad(self, actividad_id: int) -> list[Nota]:
        stmt = select(notas).where(notas.c.actividad_id == actividad_id)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_nota(r) for r in rows]

    def get_nota(self, estudiante_id: int, actividad_id: int) -> Nota | None:
        stmt = select(notas).where(
            notas.c.estudiante_id == estudiante_id,
            notas.c.actividad_id == actividad_id,
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_nota(row) if row else None

    def guardar_nota(self, nota: Nota) -> Nota:
        values = {
            "estudiante_id": nota.estudiante_id,
            "actividad_id": nota.actividad_id,
            "valor": float(nota.valor),
            "usuario_registro_id": nota.usuario_registro_id,
            "fecha_registro": nota.fecha_registro,
        }
        stmt = self._upsert(
            notas,
            values,
            ["estudiante_id", "actividad_id"],
            ["valor", "usuario_registro_id", "fecha_registro"],
        )
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return nota.model_copy(update={"id": result.inserted_primary_key[0]})

    def guardar_notas_masivas(self, items: list[Nota]) -> int:
        if not items:
            return 0
        ins = sqlite_insert(notas)
        stmt = ins.on_conflict_do_update(
            index_elements=["estudiante_id", "actividad_id"],
            set_={
                "valor": ins.excluded.valor,
                "usuario_registro_id": ins.excluded.usuario_registro_id,
                "fecha_registro": ins.excluded.fecha_registro,
            },
        )
        params = [
            {
                "estudiante_id": n.estudiante_id,
                "actividad_id": n.actividad_id,
                "valor": float(n.valor),
                "usuario_registro_id": n.usuario_registro_id,
                "fecha_registro": n.fecha_registro,
            }
            for n in items
        ]
        with self._get_conn() as conn:
            conn.execute(stmt, params)
            if self._conn is None:
                conn.commit()
            return len(items)

    def eliminar_nota(self, estudiante_id: int, actividad_id: int) -> bool:
        stmt = notas.delete().where(
            notas.c.estudiante_id == estudiante_id,
            notas.c.actividad_id == actividad_id,
        )
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    # ------------------------------------------------------------------
    # Puntos extra
    # ------------------------------------------------------------------

    def get_puntos_extra(
        self,
        estudiante_id: int,
        asignacion_id: int,
        periodo_id: int,
        tipo: TipoPuntosExtra | None = None,
    ) -> PuntosExtra | None:
        stmt = select(puntos_extra).where(
            puntos_extra.c.estudiante_id == estudiante_id,
            puntos_extra.c.asignacion_id == asignacion_id,
            puntos_extra.c.periodo_id == periodo_id,
        )
        if tipo is not None:
            stmt = stmt.where(puntos_extra.c.tipo == tipo.value)
        stmt = stmt.limit(1)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_puntos_extra(row) if row else None

    def listar_puntos_extra(self, asignacion_id: int, periodo_id: int) -> list[PuntosExtra]:
        stmt = (
            select(puntos_extra)
            .where(
                puntos_extra.c.asignacion_id == asignacion_id,
                puntos_extra.c.periodo_id == periodo_id,
            )
            .order_by(puntos_extra.c.estudiante_id, puntos_extra.c.tipo)
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_puntos_extra(r) for r in rows]

    def guardar_puntos_extra(self, pe: PuntosExtra) -> PuntosExtra:
        values = {
            "estudiante_id": pe.estudiante_id,
            "asignacion_id": pe.asignacion_id,
            "periodo_id": pe.periodo_id,
            "tipo": pe.tipo.value,
            "positivos": pe.positivos,
            "negativos": pe.negativos,
            "observacion": pe.observacion,
            "fecha_actualizacion": pe.fecha_actualizacion,
        }
        stmt = self._upsert(
            puntos_extra,
            values,
            ["estudiante_id", "asignacion_id", "periodo_id", "tipo"],
            ["positivos", "negativos", "observacion", "fecha_actualizacion"],
        )
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return pe.model_copy(update={"id": result.inserted_primary_key[0]})

    # ------------------------------------------------------------------
    # Read models — resultados consolidados
    # ------------------------------------------------------------------

    def listar_resultados_grupo(
        self,
        grupo_id: int,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[ResultadoEstudianteDTO]:
        nombre_col = (estudiantes.c.nombre + " " + estudiantes.c.apellido).label(
            "nombre_completo"
        )
        stmt_est = (
            select(estudiantes.c.id, nombre_col, estudiantes.c.posee_piar)
            .where(
                estudiantes.c.grupo_id == grupo_id,
                estudiantes.c.estado_matricula == "activo",
            )
            .order_by(estudiantes.c.apellido, estudiantes.c.nombre)
        )
        stmt_notas = (
            select(notas.c.estudiante_id, notas.c.actividad_id, notas.c.valor)
            .join(actividades, actividades.c.id == notas.c.actividad_id)
            .join(categorias, categorias.c.id == actividades.c.categoria_id)
            .where(
                categorias.c.asignacion_id == asignacion_id,
                categorias.c.periodo_id == periodo_id,
            )
        )
        with self._get_conn() as conn:
            est_rows = conn.execute(stmt_est).mappings().all()
            notas_rows = conn.execute(stmt_notas).mappings().all()

        notas_por_est: dict[int, dict[int, float]] = {}
        for r in notas_rows:
            notas_por_est.setdefault(r["estudiante_id"], {})[r["actividad_id"]] = r["valor"]

        return [
            ResultadoEstudianteDTO(
                estudiante_id=r["id"],
                nombre_completo=r["nombre_completo"],
                notas=notas_por_est.get(r["id"], {}),
                posee_piar=bool(r["posee_piar"]),
            )
            for r in est_rows
        ]


__all__ = ["SqlaEvaluacionRepository"]
