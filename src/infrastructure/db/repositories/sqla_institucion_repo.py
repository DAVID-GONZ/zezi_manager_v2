"""Implementación SQLAlchemy Core de IInstitucionRepository — ZECI Manager v2.0."""
from __future__ import annotations

from sqlalchemy import func, insert, select, update

from src.domain.models.institucion import Institucion
from src.domain.ports.institucion_repo import IInstitucionRepository
from src.infrastructure.db.repositories.base import RepositorioBase
from src.infrastructure.db.schema import instituciones


class SqlaInstitucionRepository(RepositorioBase, IInstitucionRepository):
    def __init__(self, conn=None):
        super().__init__(conn, instituciones)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _row_to_institucion(self, row) -> Institucion:
        from src.domain.models.institucion import (
            Calendario,
            JornadaPrincipal,
            TipoInstitucion,
        )

        d = dict(row._mapping)
        # Boolean columns: ensure Python bool type
        d["activa"] = bool(d["activa"])
        d["configuracion_inicial_completa"] = bool(d.get("configuracion_inicial_completa", False))
        for field, enum_cls in [
            ("jornada_principal", JornadaPrincipal),
            ("tipo_institucion", TipoInstitucion),
            ("calendario", Calendario),
        ]:
            if d.get(field):
                try:
                    d[field] = enum_cls(d[field])
                except ValueError:
                    d[field] = None
        return Institucion(**d)

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------

    def get_by_id(self, institucion_id: int) -> Institucion | None:
        with self._get_conn() as conn:
            stmt = self._select().where(instituciones.c.id == institucion_id)
            row = conn.execute(stmt).fetchone()
            return self._row_to_institucion(row) if row else None

    def listar(self, solo_activas: bool = False) -> list[Institucion]:
        stmt = self._select().order_by(instituciones.c.id)
        if solo_activas:
            stmt = stmt.where(instituciones.c.activa == True)  # noqa: E712
        with self._get_conn() as conn:
            rows = conn.execute(stmt).fetchall()
            return [self._row_to_institucion(r) for r in rows]

    def existe_nombre(self, nombre: str) -> bool:
        stmt = select(instituciones.c.id).where(
            func.lower(instituciones.c.nombre) == func.lower(nombre.strip())
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).fetchone()
            return row is not None

    def get_por_defecto(self) -> Institucion | None:
        stmt = self._select().order_by(instituciones.c.id).limit(1)
        with self._get_conn() as conn:
            row = conn.execute(stmt).fetchone()
            return self._row_to_institucion(row) if row else None

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------

    def guardar(self, institucion: Institucion) -> Institucion:
        stmt = insert(instituciones).values(
            nombre=institucion.nombre,
            nit=institucion.nit,
            codigo=institucion.codigo,
            activa=institucion.activa,
            fecha_creacion=institucion.fecha_creacion,
            codigo_dane=institucion.codigo_dane,
            pais=institucion.pais,
            departamento=institucion.departamento,
            municipio=institucion.municipio,
            configuracion_inicial_completa=institucion.configuracion_inicial_completa,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return institucion.model_copy(update={"id": pk})

    def actualizar(self, institucion: Institucion) -> Institucion:
        if not institucion.id:
            raise ValueError("La institución debe tener id para actualizar.")
        stmt = (
            update(instituciones)
            .where(instituciones.c.id == institucion.id)
            .values(
                nombre=institucion.nombre,
                nit=institucion.nit,
                codigo=institucion.codigo,
                activa=institucion.activa,
                nombre_oficial=institucion.nombre_oficial,
                codigo_dane=institucion.codigo_dane,
                rector=institucion.rector,
                direccion=institucion.direccion,
                pais=institucion.pais,
                departamento=institucion.departamento,
                municipio=institucion.municipio,
                telefono=institucion.telefono,
                logo_path=institucion.logo_path,
                logo_url=institucion.logo_url,
                resolucion_aprobacion=institucion.resolucion_aprobacion,
                lema=institucion.lema,
                email_institucional=institucion.email_institucional,
                jornada_principal=(
                    institucion.jornada_principal.value
                    if institucion.jornada_principal
                    else None
                ),
                tipo_institucion=(
                    institucion.tipo_institucion.value
                    if institucion.tipo_institucion
                    else None
                ),
                calendario=(
                    institucion.calendario.value if institucion.calendario else None
                ),
                configuracion_inicial_completa=institucion.configuracion_inicial_completa,
            )
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
        return institucion

    def sembrar_defaults_tenant(self, institucion_id: int) -> None:
        """
        Siembra catálogos estándar + preferencias por defecto para un tenant nuevo.
        Implementado directamente con SQLAlchemy Core (no depende de sqlite3.Connection).
        """
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        from src.domain.models.catalogos_estandar import (
            AREAS_ESTANDAR_CO,
            CATEGORIAS_BASE_CO,
            PREF_DEFAULTS,
        )
        from src.infrastructure.db.schema import (
            areas_conocimiento,
            categorias_observacion,
            preferencias_institucion,
        )

        with self._get_conn() as conn:
            # Seed áreas de conocimiento estándar CO
            for nombre, codigo in AREAS_ESTANDAR_CO:
                stmt = (
                    sqlite_insert(areas_conocimiento)
                    .values(nombre=nombre, codigo=codigo, institucion_id=institucion_id)
                    .on_conflict_do_nothing()
                )
                conn.execute(stmt)

            # Seed categorías de observación base CO
            for nombre, es_comportamental in CATEGORIAS_BASE_CO:
                stmt = (
                    sqlite_insert(categorias_observacion)
                    .values(
                        nombre=nombre,
                        es_comportamental=int(es_comportamental),
                        institucion_id=institucion_id,
                    )
                    .on_conflict_do_nothing()
                )
                conn.execute(stmt)

            # Seed preferencias por defecto
            for categoria, clave, valor, tipo in PREF_DEFAULTS:
                stmt = (
                    sqlite_insert(preferencias_institucion)
                    .values(
                        institucion_id=institucion_id,
                        categoria=categoria,
                        clave=clave,
                        valor=valor,
                        tipo_valor=tipo,
                    )
                    .on_conflict_do_nothing()
                )
                conn.execute(stmt)

            if self._conn is None:
                conn.commit()


__all__ = ["SqlaInstitucionRepository"]
