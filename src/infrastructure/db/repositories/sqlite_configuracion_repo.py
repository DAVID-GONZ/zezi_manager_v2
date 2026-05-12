"""
SqliteConfiguracionRepository
==============================
Implementación SQLite de IConfiguracionRepository.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from src.domain.ports.configuracion_repo import IConfiguracionRepository
from src.domain.models.configuracion import (
    ConfiguracionAnio,
    NivelDesempeno,
    CriterioPromocion,
)


class SqliteConfiguracionRepository(IConfiguracionRepository):

    def __init__(self, conn: sqlite3.Connection | None = None):
        self._conn = conn

    @contextmanager
    def _get_conn(self):
        if self._conn is not None:
            yield self._conn
        else:
            from src.infrastructure.db.connection import get_connection
            with get_connection() as conn:
                yield conn

    # =========================================================================
    # ConfiguracionAnio
    # =========================================================================

    def get_activa(self) -> ConfiguracionAnio | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM configuracion_anio WHERE activo = 1 LIMIT 1"
            ).fetchone()
            return ConfiguracionAnio(**dict(row)) if row else None

    def get_by_id(self, anio_id: int) -> ConfiguracionAnio | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM configuracion_anio WHERE id = ?", (anio_id,)
            ).fetchone()
            return ConfiguracionAnio(**dict(row)) if row else None

    def get_by_anio(self, anio: int) -> ConfiguracionAnio | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM configuracion_anio WHERE anio = ?", (anio,)
            ).fetchone()
            return ConfiguracionAnio(**dict(row)) if row else None

    def listar(self) -> list[ConfiguracionAnio]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM configuracion_anio ORDER BY anio DESC"
            ).fetchall()
            return [ConfiguracionAnio(**dict(r)) for r in rows]

    def guardar(self, config: ConfiguracionAnio) -> ConfiguracionAnio:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO configuracion_anio (
                    anio, fecha_inicio_clases, fecha_fin_clases,
                    nota_minima_aprobacion, nombre_institucion,
                    dane_code, rector, direccion, municipio,
                    telefono_institucion, logo_path, resolucion_aprobacion, activo
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    config.anio,
                    config.fecha_inicio_clases.isoformat() if config.fecha_inicio_clases else None,
                    config.fecha_fin_clases.isoformat() if config.fecha_fin_clases else None,
                    config.nota_minima_aprobacion,
                    config.nombre_institucion,
                    config.dane_code,
                    config.rector,
                    config.direccion,
                    config.municipio,
                    config.telefono_institucion,
                    config.logo_path,
                    config.resolucion_aprobacion,
                    int(config.activo),
                ),
            )
            if self._conn is None:
                conn.commit()
            return config.model_copy(update={"id": cursor.lastrowid})

    def actualizar(self, config: ConfiguracionAnio) -> ConfiguracionAnio:
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE configuracion_anio SET
                    anio = ?, fecha_inicio_clases = ?, fecha_fin_clases = ?,
                    nota_minima_aprobacion = ?, nombre_institucion = ?,
                    dane_code = ?, rector = ?, direccion = ?, municipio = ?,
                    telefono_institucion = ?, logo_path = ?,
                    resolucion_aprobacion = ?, activo = ?
                WHERE id = ?
                """,
                (
                    config.anio,
                    config.fecha_inicio_clases.isoformat() if config.fecha_inicio_clases else None,
                    config.fecha_fin_clases.isoformat() if config.fecha_fin_clases else None,
                    config.nota_minima_aprobacion,
                    config.nombre_institucion,
                    config.dane_code,
                    config.rector,
                    config.direccion,
                    config.municipio,
                    config.telefono_institucion,
                    config.logo_path,
                    config.resolucion_aprobacion,
                    int(config.activo),
                    config.id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return config

    def activar(self, anio_id: int) -> bool:
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE configuracion_anio SET activo = 0 WHERE activo = 1"
            )
            cursor = conn.execute(
                "UPDATE configuracion_anio SET activo = 1 WHERE id = ?",
                (anio_id,),
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0

    # =========================================================================
    # NivelDesempeno
    # =========================================================================

    def listar_niveles(self, anio_id: int) -> list[NivelDesempeno]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM niveles_desempeno WHERE anio_id = ? ORDER BY orden",
                (anio_id,),
            ).fetchall()
            return [NivelDesempeno(**dict(r)) for r in rows]

    def get_nivel(self, nivel_id: int) -> NivelDesempeno | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM niveles_desempeno WHERE id = ?", (nivel_id,)
            ).fetchone()
            return NivelDesempeno(**dict(row)) if row else None

    def guardar_nivel(self, nivel: NivelDesempeno) -> NivelDesempeno:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO niveles_desempeno
                    (anio_id, nombre, rango_min, rango_max, descripcion, orden)
                VALUES (?,?,?,?,?,?)
                """,
                (
                    nivel.anio_id,
                    nivel.nombre,
                    nivel.rango_min,
                    nivel.rango_max,
                    nivel.descripcion,
                    nivel.orden,
                ),
            )
            if self._conn is None:
                conn.commit()
            return nivel.model_copy(update={"id": cursor.lastrowid})

    def actualizar_nivel(self, nivel: NivelDesempeno) -> NivelDesempeno:
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE niveles_desempeno SET
                    nombre = ?, rango_min = ?, rango_max = ?,
                    descripcion = ?, orden = ?
                WHERE id = ?
                """,
                (
                    nivel.nombre,
                    nivel.rango_min,
                    nivel.rango_max,
                    nivel.descripcion,
                    nivel.orden,
                    nivel.id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return nivel

    def eliminar_nivel(self, nivel_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM niveles_desempeno WHERE id = ?", (nivel_id,)
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0

    def reemplazar_niveles(
        self,
        anio_id: int,
        niveles: list[NivelDesempeno],
    ) -> list[NivelDesempeno]:
        with self._get_conn() as conn:
            conn.execute(
                "DELETE FROM niveles_desempeno WHERE anio_id = ?", (anio_id,)
            )
            resultado: list[NivelDesempeno] = []
            for nivel in niveles:
                cursor = conn.execute(
                    """
                    INSERT INTO niveles_desempeno
                        (anio_id, nombre, rango_min, rango_max, descripcion, orden)
                    VALUES (?,?,?,?,?,?)
                    """,
                    (
                        anio_id,
                        nivel.nombre,
                        nivel.rango_min,
                        nivel.rango_max,
                        nivel.descripcion,
                        nivel.orden,
                    ),
                )
                resultado.append(
                    nivel.model_copy(update={"id": cursor.lastrowid, "anio_id": anio_id})
                )
            if self._conn is None:
                conn.commit()
            return resultado

    def clasificar_nota(self, nota: float, anio_id: int) -> NivelDesempeno | None:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT * FROM niveles_desempeno
                WHERE anio_id = ? AND rango_min <= ? AND rango_max >= ?
                ORDER BY orden LIMIT 1
                """,
                (anio_id, nota, nota),
            ).fetchone()
            return NivelDesempeno(**dict(row)) if row else None

    # =========================================================================
    # CriterioPromocion
    # =========================================================================

    def get_criterios(self, anio_id: int) -> CriterioPromocion | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM criterios_promocion WHERE anio_id = ?", (anio_id,)
            ).fetchone()
            return CriterioPromocion(**dict(row)) if row else None

    def guardar_criterios(self, criterios: CriterioPromocion) -> CriterioPromocion:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT OR REPLACE INTO criterios_promocion (
                    anio_id, max_asignaturas_perdidas, permite_condicionada,
                    nota_minima_habilitacion, nota_minima_anual
                ) VALUES (?,?,?,?,?)
                """,
                (
                    criterios.anio_id,
                    criterios.max_asignaturas_perdidas,
                    int(criterios.permite_condicionada),
                    criterios.nota_minima_habilitacion,
                    criterios.nota_minima_anual,
                ),
            )
            if self._conn is None:
                conn.commit()
            return criterios.model_copy(update={"id": cursor.lastrowid})

    # =========================================================================
    # ConfiguracionPeriodos
    # =========================================================================

    def get_numero_periodos(self, anio_id: int) -> int:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT numero_periodos FROM configuracion_periodos WHERE anio_id = ?",
                (anio_id,),
            ).fetchone()
            return int(row["numero_periodos"]) if row else 4

    def guardar_numero_periodos(
        self,
        anio_id: int,
        numero_periodos: int,
        pesos_iguales: bool = True,
    ) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO configuracion_periodos
                    (anio_id, numero_periodos, pesos_iguales)
                VALUES (?,?,?)
                """,
                (anio_id, numero_periodos, int(pesos_iguales)),
            )
            if self._conn is None:
                conn.commit()


__all__ = ["SqliteConfiguracionRepository"]
