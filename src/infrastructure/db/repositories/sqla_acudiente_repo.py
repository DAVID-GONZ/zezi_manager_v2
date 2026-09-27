"""Implementación SQLAlchemy Core de IAcudienteRepository — ZECI Manager v2.0."""
from __future__ import annotations

from sqlalchemy import delete, insert, select, update

from src.domain.models.acudiente import (
    Acudiente,
    EstudianteAcudiente,
    Parentesco,
    TipoDocumentoAcudiente,
)
from src.domain.models.tenant import TenantScope
from src.domain.ports.acudiente_repo import IAcudienteRepository
from src.infrastructure.db.repositories.base import RepositorioBase
from src.infrastructure.db.schema import acudientes, estudiante_acudiente


class SqlaAcudienteRepository(RepositorioBase, IAcudienteRepository):
    def __init__(self, conn=None):
        super().__init__(conn, acudientes)

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _row_to_acudiente(self, row) -> Acudiente:
        d = dict(row)
        d["tipo_documento"] = TipoDocumentoAcudiente(d["tipo_documento"])
        d["parentesco"] = Parentesco(d["parentesco"])
        d["activo"] = bool(d["activo"])
        return Acudiente(**d)

    # ------------------------------------------------------------------
    # Lectura — acudiente
    # ------------------------------------------------------------------

    def listar(
        self, institucion_id: TenantScope, activos_solo: bool = False
    ) -> list[Acudiente]:
        stmt = self._select()
        if activos_solo:
            stmt = stmt.where(acudientes.c.activo == True)  # noqa: E712
        if isinstance(institucion_id, int):
            stmt = stmt.where(acudientes.c.institucion_id == institucion_id)
        stmt = stmt.order_by(acudientes.c.nombre_completo)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_acudiente(r) for r in rows]

    def buscar_por_documento(
        self, numero: str, institucion_id: TenantScope
    ) -> Acudiente | None:
        stmt = select(acudientes).where(
            acudientes.c.numero_documento == numero.upper()
        )
        if isinstance(institucion_id, int):
            stmt = stmt.where(acudientes.c.institucion_id == institucion_id)
        stmt = stmt.limit(1)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_acudiente(row) if row else None

    def get_by_id(self, acudiente_id: int) -> Acudiente | None:
        stmt = self._select().where(acudientes.c.id == acudiente_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_acudiente(row) if row else None

    def get_by_documento(self, numero_documento: str) -> Acudiente | None:
        stmt = select(acudientes).where(
            acudientes.c.numero_documento == numero_documento.upper()
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_acudiente(row) if row else None

    def existe_documento(self, numero_documento: str) -> bool:
        stmt = select(acudientes.c.id).where(
            acudientes.c.numero_documento == numero_documento.upper()
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).fetchone()
            return row is not None

    def listar_por_estudiante(
        self,
        estudiante_id: int,
        solo_activos: bool = True,
    ) -> list[Acudiente]:
        stmt = (
            select(acudientes)
            .join(estudiante_acudiente, estudiante_acudiente.c.acudiente_id == acudientes.c.id)
            .where(estudiante_acudiente.c.estudiante_id == estudiante_id)
        )
        if solo_activos:
            stmt = stmt.where(acudientes.c.activo == True)  # noqa: E712
        stmt = stmt.order_by(
            estudiante_acudiente.c.es_principal.desc(),
            acudientes.c.nombre_completo,
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_acudiente(r) for r in rows]

    def get_principal(self, estudiante_id: int) -> Acudiente | None:
        stmt = (
            select(acudientes)
            .join(estudiante_acudiente, estudiante_acudiente.c.acudiente_id == acudientes.c.id)
            .where(
                estudiante_acudiente.c.estudiante_id == estudiante_id,
                estudiante_acudiente.c.es_principal == True,  # noqa: E712
            )
            .limit(1)
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_acudiente(row) if row else None

    def listar_estudiantes_de_acudiente(self, acudiente_id: int) -> list[int]:
        stmt = select(estudiante_acudiente.c.estudiante_id).where(
            estudiante_acudiente.c.acudiente_id == acudiente_id
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).fetchall()
            return [r[0] for r in rows]

    # ------------------------------------------------------------------
    # Escritura — acudiente
    # ------------------------------------------------------------------

    def guardar(self, acudiente: Acudiente) -> Acudiente:
        stmt = insert(acudientes).values(
            tipo_documento=acudiente.tipo_documento.value,
            numero_documento=acudiente.numero_documento,
            nombre_completo=acudiente.nombre_completo,
            parentesco=acudiente.parentesco.value,
            celular=acudiente.celular,
            email=acudiente.email,
            direccion=acudiente.direccion,
            activo=int(acudiente.activo),
            usuario_id=acudiente.usuario_id,
            institucion_id=acudiente.institucion_id,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return acudiente.model_copy(update={"id": pk})

    def actualizar(self, acudiente: Acudiente) -> Acudiente:
        stmt = (
            update(acudientes)
            .where(acudientes.c.id == acudiente.id)
            .values(
                nombre_completo=acudiente.nombre_completo,
                parentesco=acudiente.parentesco.value,
                celular=acudiente.celular,
                email=acudiente.email,
                direccion=acudiente.direccion,
            )
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
        return acudiente

    def desactivar(self, acudiente_id: int) -> bool:
        stmt = (
            update(acudientes)
            .where(acudientes.c.id == acudiente_id)
            .values(activo=False)
        )
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    # ------------------------------------------------------------------
    # Gestión de vínculos
    # ------------------------------------------------------------------

    def vincular(self, vinculo: EstudianteAcudiente) -> None:
        stmt = self._upsert(
            estudiante_acudiente,
            values={
                "estudiante_id": vinculo.estudiante_id,
                "acudiente_id": vinculo.acudiente_id,
                "es_principal": int(vinculo.es_principal),
            },
            conflict_cols=["estudiante_id", "acudiente_id"],
            update_cols=["es_principal"],
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()

    def desvincular(self, estudiante_id: int, acudiente_id: int) -> bool:
        stmt = delete(estudiante_acudiente).where(
            estudiante_acudiente.c.estudiante_id == estudiante_id,
            estudiante_acudiente.c.acudiente_id == acudiente_id,
        )
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    def establecer_principal(self, estudiante_id: int, acudiente_id: int) -> None:
        stmt_clear = (
            update(estudiante_acudiente)
            .where(estudiante_acudiente.c.estudiante_id == estudiante_id)
            .values(es_principal=False)
        )
        stmt_set = (
            update(estudiante_acudiente)
            .where(
                estudiante_acudiente.c.estudiante_id == estudiante_id,
                estudiante_acudiente.c.acudiente_id == acudiente_id,
            )
            .values(es_principal=True)
        )
        with self._get_conn() as conn:
            conn.execute(stmt_clear)
            conn.execute(stmt_set)
            if self._conn is None:
                conn.commit()

    def get_vinculo(self, estudiante_id: int, acudiente_id: int) -> EstudianteAcudiente | None:
        stmt = select(estudiante_acudiente).where(
            estudiante_acudiente.c.estudiante_id == estudiante_id,
            estudiante_acudiente.c.acudiente_id == acudiente_id,
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            if not row:
                return None
            d = dict(row)
            d["es_principal"] = bool(d["es_principal"])
            return EstudianteAcudiente(**d)


__all__ = ["SqlaAcudienteRepository"]
