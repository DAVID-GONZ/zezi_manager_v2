"""Implementación SQLAlchemy Core de ISIEERepository — AVEDRA v2.0."""
from __future__ import annotations

from sqlalchemy import delete, func, insert, select, update

from src.domain.models.evaluacion import Categoria, ConfiguracionSIEE, ModoSIEE
from src.domain.ports.siee_repo import ISIEERepository
from src.infrastructure.db.repositories.base import RepositorioBase
from src.infrastructure.db.schema import categorias, configuracion_siee


class SqlaSIEERepository(RepositorioBase, ISIEERepository):
    def __init__(self, conn=None):
        super().__init__(conn, configuracion_siee)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _row_to_siee(self, row) -> ConfiguracionSIEE:
        d = dict(row._mapping)
        d["modo"] = ModoSIEE(d["modo"])
        return ConfiguracionSIEE(**d)

    def _row_to_categoria(self, row) -> Categoria:
        d = dict(row._mapping)
        # Integer columns in schema: need explicit bool() conversion
        d["es_institucional"] = bool(d.get("es_institucional", 0))
        d["permite_subcategorias"] = bool(d.get("permite_subcategorias", 0))
        return Categoria(**d)

    # ------------------------------------------------------------------
    # Configuración SIEE
    # ------------------------------------------------------------------

    def get_configuracion(self, anio_id: int) -> ConfiguracionSIEE | None:
        with self._get_conn() as conn:
            stmt = self._select().where(configuracion_siee.c.anio_id == anio_id)
            row = conn.execute(stmt).fetchone()
            return self._row_to_siee(row) if row else None

    def guardar_configuracion(self, cfg: ConfiguracionSIEE) -> ConfiguracionSIEE:
        with self._get_conn() as conn:
            existing = conn.execute(
                select(configuracion_siee.c.id).where(
                    configuracion_siee.c.anio_id == cfg.anio_id
                )
            ).fetchone()

            if existing:
                stmt = (
                    update(configuracion_siee)
                    .where(configuracion_siee.c.anio_id == cfg.anio_id)
                    .values(
                        modo=cfg.modo.value,
                        porcentaje_autonomia_docente=cfg.porcentaje_autonomia_docente,
                    )
                )
                conn.execute(stmt)
                siee_id = existing[0]
            else:
                stmt = insert(configuracion_siee).values(
                    anio_id=cfg.anio_id,
                    modo=cfg.modo.value,
                    porcentaje_autonomia_docente=cfg.porcentaje_autonomia_docente,
                )
                siee_id = self._execute_insert(conn, stmt)

            if self._conn is None:
                conn.commit()

        return cfg.model_copy(update={"id": siee_id})

    # ------------------------------------------------------------------
    # Categorías institucionales
    # ------------------------------------------------------------------

    def listar_categorias_institucionales(self, anio_id: int) -> list[Categoria]:
        with self._get_conn() as conn:
            stmt = (
                select(categorias)
                .where(
                    categorias.c.es_institucional == 1,
                    categorias.c.anio_id == anio_id,
                )
                .order_by(categorias.c.nombre)
            )
            rows = conn.execute(stmt).fetchall()
            return [self._row_to_categoria(r) for r in rows]

    def get_categoria_institucional(self, cat_id: int) -> Categoria | None:
        with self._get_conn() as conn:
            stmt = select(categorias).where(
                categorias.c.id == cat_id,
                categorias.c.es_institucional == 1,
            )
            row = conn.execute(stmt).fetchone()
            return self._row_to_categoria(row) if row else None

    def guardar_categoria_institucional(self, cat: Categoria) -> Categoria:
        stmt = insert(categorias).values(
            nombre=cat.nombre,
            peso=cat.peso,
            anio_id=cat.anio_id,
            es_institucional=1,
            permite_subcategorias=int(cat.permite_subcategorias),
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return cat.model_copy(update={"id": pk})

    def actualizar_categoria_institucional(self, cat: Categoria) -> Categoria:
        stmt = (
            update(categorias)
            .where(
                categorias.c.id == cat.id,
                categorias.c.es_institucional == 1,
            )
            .values(
                nombre=cat.nombre,
                peso=cat.peso,
                permite_subcategorias=int(cat.permite_subcategorias),
            )
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
        return cat

    def eliminar_categoria_institucional(self, cat_id: int) -> None:
        stmt = delete(categorias).where(
            categorias.c.id == cat_id,
            categorias.c.es_institucional == 1,
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()

    def suma_pesos_institucionales(self, anio_id: int) -> float:
        with self._get_conn() as conn:
            stmt = select(
                func.coalesce(func.sum(categorias.c.peso), 0.0)
            ).where(
                categorias.c.es_institucional == 1,
                categorias.c.anio_id == anio_id,
            )
            row = conn.execute(stmt).fetchone()
            return float(row[0])


__all__ = ["SqlaSIEERepository"]
