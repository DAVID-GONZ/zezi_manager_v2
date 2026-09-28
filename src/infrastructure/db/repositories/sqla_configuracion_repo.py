"""Implementación SQLAlchemy Core de IConfiguracionRepository — AVEDRA v2.0."""
from __future__ import annotations

from sqlalchemy import delete, insert, select, update

from src.domain.models.configuracion import (
    ConfiguracionAnio,
    CriterioPromocion,
    NivelDesempeno,
)
from src.domain.models.tenant import TenantScope
from src.domain.ports.configuracion_repo import IConfiguracionRepository
from src.infrastructure.db.repositories.base import RepositorioBase
from src.infrastructure.db.schema import (
    configuracion_anio,
    configuracion_periodos,
    criterios_promocion,
    niveles_desempeno,
)

# Columnas académicas — SELECT explícito, omite campos de identidad
# institucional que viven en la entidad Institucion (datos_06).
_COLS_ACADEMICOS = [
    configuracion_anio.c.id,
    configuracion_anio.c.anio,
    configuracion_anio.c.institucion_id,
    configuracion_anio.c.fecha_inicio_clases,
    configuracion_anio.c.fecha_fin_clases,
    configuracion_anio.c.nota_minima_aprobacion,
    configuracion_anio.c.nota_minima_escala,
    configuracion_anio.c.nota_maxima_escala,
    configuracion_anio.c.activo,
]


class SqlaConfiguracionRepository(RepositorioBase, IConfiguracionRepository):
    def __init__(self, conn=None):
        super().__init__(conn, configuracion_anio)

    # =========================================================================
    # ConfiguracionAnio
    # =========================================================================

    def _row_to_config(self, row) -> ConfiguracionAnio:
        d = dict(row)
        d["activo"] = bool(d["activo"])
        return ConfiguracionAnio(**d)

    def get_activa(self, institucion_id: TenantScope) -> ConfiguracionAnio | None:
        stmt = select(*_COLS_ACADEMICOS).where(
            configuracion_anio.c.activo == True  # noqa: E712
        ).limit(1)
        if isinstance(institucion_id, int):
            stmt = stmt.where(configuracion_anio.c.institucion_id == institucion_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_config(row) if row else None

    def get_by_id(self, anio_id: int) -> ConfiguracionAnio | None:
        stmt = select(*_COLS_ACADEMICOS).where(configuracion_anio.c.id == anio_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_config(row) if row else None

    def get_by_anio(self, institucion_id: TenantScope, anio: int) -> ConfiguracionAnio | None:
        stmt = select(*_COLS_ACADEMICOS).where(configuracion_anio.c.anio == anio)
        if isinstance(institucion_id, int):
            stmt = stmt.where(configuracion_anio.c.institucion_id == institucion_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_config(row) if row else None

    def listar(self, institucion_id: TenantScope) -> list[ConfiguracionAnio]:
        stmt = select(*_COLS_ACADEMICOS).order_by(configuracion_anio.c.anio.desc())
        if isinstance(institucion_id, int):
            stmt = stmt.where(configuracion_anio.c.institucion_id == institucion_id)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_config(r) for r in rows]

    def guardar(self, config: ConfiguracionAnio) -> ConfiguracionAnio:
        stmt = insert(configuracion_anio).values(
            anio=config.anio,
            institucion_id=config.institucion_id,
            fecha_inicio_clases=config.fecha_inicio_clases,
            fecha_fin_clases=config.fecha_fin_clases,
            nota_minima_aprobacion=float(config.nota_minima_aprobacion),
            nota_minima_escala=float(config.nota_minima_escala),
            nota_maxima_escala=float(config.nota_maxima_escala),
            activo=int(config.activo),
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return config.model_copy(update={"id": pk})

    def actualizar(self, config: ConfiguracionAnio) -> ConfiguracionAnio:
        stmt = (
            update(configuracion_anio)
            .where(configuracion_anio.c.id == config.id)
            .values(
                anio=config.anio,
                institucion_id=config.institucion_id,
                fecha_inicio_clases=config.fecha_inicio_clases,
                fecha_fin_clases=config.fecha_fin_clases,
                nota_minima_aprobacion=float(config.nota_minima_aprobacion),
                nota_minima_escala=float(config.nota_minima_escala),
                nota_maxima_escala=float(config.nota_maxima_escala),
                activo=int(config.activo),
            )
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
        return config

    def activar(self, anio_id: int) -> bool:
        with self._get_conn() as conn:
            # Multi-tenant: desactiva SOLO los años de la misma institución.
            # Se lee el institucion_id del año objetivo para manejar el caso
            # NULL (single-tenant) de forma NULL-safe.
            row = conn.execute(
                select(configuracion_anio.c.institucion_id)
                .where(configuracion_anio.c.id == anio_id)
            ).fetchone()
            inst_id = row[0] if row else None

            deact = update(configuracion_anio).where(
                configuracion_anio.c.activo == True  # noqa: E712
            )
            if inst_id is None:
                deact = deact.where(configuracion_anio.c.institucion_id.is_(None))
            else:
                deact = deact.where(configuracion_anio.c.institucion_id == inst_id)
            conn.execute(deact.values(activo=False))

            result = conn.execute(
                update(configuracion_anio)
                .where(configuracion_anio.c.id == anio_id)
                .values(activo=True)
            )
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    # =========================================================================
    # NivelDesempeno
    # =========================================================================

    def listar_niveles(self, anio_id: int) -> list[NivelDesempeno]:
        stmt = (
            select(niveles_desempeno)
            .where(niveles_desempeno.c.anio_id == anio_id)
            .order_by(niveles_desempeno.c.orden)
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [NivelDesempeno(**dict(r)) for r in rows]

    def get_nivel(self, nivel_id: int) -> NivelDesempeno | None:
        stmt = select(niveles_desempeno).where(niveles_desempeno.c.id == nivel_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return NivelDesempeno(**dict(row)) if row else None

    def guardar_nivel(self, nivel: NivelDesempeno) -> NivelDesempeno:
        stmt = insert(niveles_desempeno).values(
            anio_id=nivel.anio_id,
            nombre=nivel.nombre,
            rango_min=nivel.rango_min,
            rango_max=nivel.rango_max,
            descripcion=nivel.descripcion,
            orden=nivel.orden,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return nivel.model_copy(update={"id": pk})

    def actualizar_nivel(self, nivel: NivelDesempeno) -> NivelDesempeno:
        stmt = (
            update(niveles_desempeno)
            .where(niveles_desempeno.c.id == nivel.id)
            .values(
                nombre=nivel.nombre,
                rango_min=nivel.rango_min,
                rango_max=nivel.rango_max,
                descripcion=nivel.descripcion,
                orden=nivel.orden,
            )
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
        return nivel

    def eliminar_nivel(self, nivel_id: int) -> bool:
        stmt = delete(niveles_desempeno).where(niveles_desempeno.c.id == nivel_id)
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    def reemplazar_niveles(
        self,
        anio_id: int,
        niveles: list[NivelDesempeno],
    ) -> list[NivelDesempeno]:
        # DELETE + INSERT en bloque — la conexión ya abre una transacción implícita
        # en SQLAlchemy Core; el commit final la consolida.
        with self._get_conn() as conn:
            conn.execute(
                delete(niveles_desempeno).where(niveles_desempeno.c.anio_id == anio_id)
            )
            resultado: list[NivelDesempeno] = []
            for nivel in niveles:
                stmt = insert(niveles_desempeno).values(
                    anio_id=anio_id,
                    nombre=nivel.nombre,
                    rango_min=nivel.rango_min,
                    rango_max=nivel.rango_max,
                    descripcion=nivel.descripcion,
                    orden=nivel.orden,
                )
                pk = self._execute_insert(conn, stmt)
                resultado.append(nivel.model_copy(update={"id": pk, "anio_id": anio_id}))
            if self._conn is None:
                conn.commit()
        return resultado

    def clasificar_nota(self, nota: float, anio_id: int) -> NivelDesempeno | None:
        stmt = (
            select(niveles_desempeno)
            .where(
                niveles_desempeno.c.anio_id == anio_id,
                niveles_desempeno.c.rango_min <= nota,
                niveles_desempeno.c.rango_max >= nota,
            )
            .order_by(niveles_desempeno.c.orden)
            .limit(1)
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return NivelDesempeno(**dict(row)) if row else None

    # =========================================================================
    # CriterioPromocion
    # =========================================================================

    def get_criterios(self, anio_id: int) -> CriterioPromocion | None:
        stmt = select(criterios_promocion).where(criterios_promocion.c.anio_id == anio_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            if not row:
                return None
            d = dict(row)
            d["permite_condicionada"] = bool(d["permite_condicionada"])
            return CriterioPromocion(**d)

    def guardar_criterios(self, criterios: CriterioPromocion) -> CriterioPromocion:
        # INSERT OR REPLACE → upsert por clave única (anio_id)
        stmt = self._upsert(
            criterios_promocion,
            values={
                "anio_id": criterios.anio_id,
                "max_asignaturas_perdidas": criterios.max_asignaturas_perdidas,
                "permite_condicionada": int(criterios.permite_condicionada),
                "nota_minima_habilitacion": float(criterios.nota_minima_habilitacion),
                "nota_minima_anual": float(criterios.nota_minima_anual),
            },
            conflict_cols=["anio_id"],
            update_cols=[
                "max_asignaturas_perdidas",
                "permite_condicionada",
                "nota_minima_habilitacion",
                "nota_minima_anual",
            ],
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return criterios.model_copy(update={"id": pk})

    # =========================================================================
    # ConfiguracionPeriodos
    # =========================================================================

    def get_numero_periodos(self, anio_id: int) -> int:
        stmt = select(configuracion_periodos.c.numero_periodos).where(
            configuracion_periodos.c.anio_id == anio_id
        )
        with self._get_conn() as conn:
            result = conn.execute(stmt).scalar()
            return int(result) if result is not None else 4

    def guardar_numero_periodos(
        self,
        anio_id: int,
        numero_periodos: int,
        pesos_iguales: bool = True,
    ) -> None:
        # INSERT OR REPLACE → upsert por clave única (anio_id)
        stmt = self._upsert(
            configuracion_periodos,
            values={
                "anio_id": anio_id,
                "numero_periodos": numero_periodos,
                "pesos_iguales": int(pesos_iguales),
            },
            conflict_cols=["anio_id"],
            update_cols=["numero_periodos", "pesos_iguales"],
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()


__all__ = ["SqlaConfiguracionRepository"]
