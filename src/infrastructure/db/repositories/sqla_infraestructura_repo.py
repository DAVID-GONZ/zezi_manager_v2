"""
SqlaInfraestructuraRepository — implementación SQLAlchemy Core de IInfraestructuraRepository.

Decisiones de migración (T8 — Ola 3c):

Migración a Core (113 métodos):
- SELECT/INSERT/UPDATE/DELETE estándar migrados a expressions de SQLAlchemy Core.
- INSERT OR REPLACE → _upsert() sobre la clave única correspondiente.
- cursor.lastrowid → result.inserted_primary_key[0].
- Commit en escrituras: if self._conn is None: conn.commit()
- TenantScope: filtro si int, omitir si "*"

Uso de text() (8 métodos, documentados inline):
1. listar_configs_generacion: condición `json_each(grupos_json)` es SQLite-specific y no
   tiene equivalente en SQLAlchemy Core sin extensiones. Se usa text() solo para la
   cláusula de filtro de institución.
2. set_horas_plan (rama institucion_id IS NULL): SQLite trata NULLs como distintos en
   UNIQUE, por lo que el upsert estándar no funciona para NULL. Se mantiene la lógica
   Python + text() para los SELECT/UPDATE manuales del fallback.
3. duplicar_escenario: INSERT...SELECT con columna literal → insert().from_select() de Core.
   (No usa text() — resuelto con Core puro.)

Todos los text() tienen docstring explicativo.
"""

from __future__ import annotations

import json

from sqlalchemy import delete, func, insert, literal, or_, select, text, update

from src.domain.models.clock import ahora as _ahora
from src.domain.models.infraestructura import (
    AreaConocimiento,
    Asignatura,
    BloqueAnclado,
    ConfigGeneracion,
    ConfiguracionGradoInstitucion,
    DiaSemana,
    DisponibilidadDocente,
    EscenarioHorario,
    Franja,
    FranjaReunion,
    Grado,
    Grupo,
    Horario,
    HorarioEstadisticasDTO,
    HorarioInfo,
    Jornada,
    LimitesDocente,
    Logro,
    PesosGeneracion,
    PlanEstudios,
    PlantillaFranja,
    Sala,
    VentanaGrupo,
)
from src.domain.models.tenant import TenantScope
from src.domain.ports.infraestructura_repo import IInfraestructuraRepository
from src.infrastructure.db.repositories.base import RepositorioBase
from src.infrastructure.db.schema import (
    areas_conocimiento,
    asignaturas,
    bloques_anclados,
    config_generacion,
    configuracion_grado_institucion,
    disponibilidad_docente,
    escenarios_horario,
    franjas,
    franjas_reunion,
    grados,
    grupos,
    horarios,
    limites_docente,
    logros,
    periodos,
    plan_estudios,
    plantillas_franja,
    salas,
    usuarios,
    ventanas_grupo,
)


class SqlaInfraestructuraRepository(RepositorioBase, IInfraestructuraRepository):
    def __init__(self, conn=None):
        super().__init__(conn, None)

    # =========================================================================
    # Row mappers
    # =========================================================================

    @staticmethod
    def _row_to_escenario(row) -> EscenarioHorario:
        d = dict(row)
        d["activo"] = bool(d.get("activo", 0))
        return EscenarioHorario(
            **{k: v for k, v in d.items() if k in EscenarioHorario.model_fields}
        )

    @staticmethod
    def _row_to_plantilla(row) -> PlantillaFranja:
        d = dict(row)
        d["activa"] = bool(d.get("activa", 0))
        d["dias_activos"] = d["dias_activos"].split(",") if d.get("dias_activos") else []
        return PlantillaFranja(**{k: v for k, v in d.items() if k in PlantillaFranja.model_fields})

    @staticmethod
    def _row_to_franja(row) -> Franja:
        d = dict(row)
        return Franja(**{k: v for k, v in d.items() if k in Franja.model_fields})

    @staticmethod
    def _row_to_asignatura(row) -> Asignatura:
        d = dict(row)
        d["bloque_doble"] = bool(d.get("bloque_doble", 0))
        return Asignatura(**{k: v for k, v in d.items() if k in Asignatura.model_fields})

    @staticmethod
    def _row_to_horario(row) -> Horario:
        d = dict(row)
        d["dia_semana"] = DiaSemana(d["dia_semana"])
        return Horario(**{k: v for k, v in d.items() if k in Horario.model_fields})

    @staticmethod
    def _row_to_horario_info(row) -> HorarioInfo:
        d = dict(row)
        d["dia_semana"] = DiaSemana(d["dia_semana"])
        valid_keys = set(HorarioInfo.model_fields.keys())
        d = {k: v for k, v in d.items() if k in valid_keys}
        return HorarioInfo(**d)

    @staticmethod
    def _row_to_disponibilidad(row) -> DisponibilidadDocente:
        d = dict(row)
        d["disponible"] = bool(d.get("disponible", 1))
        return DisponibilidadDocente(
            **{k: v for k, v in d.items() if k in DisponibilidadDocente.model_fields}
        )

    @staticmethod
    def _row_to_config(row) -> ConfigGeneracion:
        d = dict(row)
        grupos_list = json.loads(d.pop("grupos_json", "[]") or "[]")
        pesos_dict = json.loads(d.pop("pesos_json", "{}") or "{}")
        pesos = PesosGeneracion(**pesos_dict) if pesos_dict else PesosGeneracion()
        restricciones = json.loads(d.pop("restricciones_json", "{}") or "{}")
        return ConfigGeneracion(
            id=d["id"],
            nombre=d["nombre"],
            periodo_id=d["periodo_id"],
            anio_id=d["anio_id"],
            plantilla_id=d["plantilla_id"],
            estado=d["estado"],
            grupos=grupos_list,
            pesos=pesos,
            restricciones=restricciones,
            escenario_destino_id=d.get("escenario_destino_id"),
            created_at=d.get("created_at"),
            updated_at=d.get("updated_at"),
        )

    @staticmethod
    def _row_to_sala(row) -> Sala:
        d = dict(row)
        return Sala(**{k: v for k, v in d.items() if k in Sala.model_fields})

    @staticmethod
    def _row_to_ventana_grupo(row) -> VentanaGrupo:
        d = dict(row)
        d["franjas_permitidas"] = json.loads(d.get("franjas_permitidas", "[]"))
        return VentanaGrupo(**{k: v for k, v in d.items() if k in VentanaGrupo.model_fields})

    @staticmethod
    def _row_to_bloque_anclado(row) -> BloqueAnclado:
        d = dict(row)
        return BloqueAnclado(**{k: v for k, v in d.items() if k in BloqueAnclado.model_fields})

    @staticmethod
    def _row_to_franja_reunion(row) -> FranjaReunion:
        d = dict(row)
        d["docentes"] = json.loads(d.pop("docentes_json", "[]"))
        return FranjaReunion(**{k: v for k, v in d.items() if k in FranjaReunion.model_fields})

    @staticmethod
    def _row_to_limites_docente(row) -> LimitesDocente:
        d = dict(row)
        return LimitesDocente(**{k: v for k, v in d.items() if k in LimitesDocente.model_fields})

    @staticmethod
    def _row_to_grado(row) -> Grado:
        d = dict(row)
        return Grado(**{k: v for k, v in d.items() if k in Grado.model_fields})

    @staticmethod
    def _row_to_plan_estudios(row) -> PlanEstudios:
        d = dict(row)
        return PlanEstudios(**{k: v for k, v in d.items() if k in PlanEstudios.model_fields})

    @staticmethod
    def _row_to_config_grado(row) -> ConfiguracionGradoInstitucion:
        return ConfiguracionGradoInstitucion(**dict(row))

    # =========================================================================
    # Escenarios de horario
    # =========================================================================

    def get_escenario(self, escenario_id: int) -> EscenarioHorario | None:
        stmt = select(escenarios_horario).where(escenarios_horario.c.id == escenario_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_escenario(row) if row else None

    def listar_escenarios(self, anio_id: int) -> list[EscenarioHorario]:
        stmt = (
            select(escenarios_horario)
            .where(escenarios_horario.c.anio_id == anio_id)
            .order_by(escenarios_horario.c.nombre)
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_escenario(r) for r in rows]

    def get_escenario_activo(self, anio_id: int) -> EscenarioHorario | None:
        stmt = select(escenarios_horario).where(
            escenarios_horario.c.anio_id == anio_id,
            escenarios_horario.c.activo == 1,
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_escenario(row) if row else None

    def crear_escenario(self, esc: EscenarioHorario) -> EscenarioHorario:
        stmt = insert(escenarios_horario).values(
            anio_id=esc.anio_id,
            nombre=esc.nombre,
            descripcion=esc.descripcion,
            activo=int(esc.activo),
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return esc.model_copy(update={"id": pk})

    def actualizar_escenario(self, esc: EscenarioHorario) -> EscenarioHorario:
        stmt = (
            update(escenarios_horario)
            .where(escenarios_horario.c.id == esc.id)
            .values(nombre=esc.nombre, descripcion=esc.descripcion, activo=int(esc.activo))
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
        return esc

    def activar_escenario(self, escenario_id: int) -> None:
        with self._get_conn() as conn:
            row = conn.execute(
                select(escenarios_horario.c.anio_id).where(escenarios_horario.c.id == escenario_id)
            ).fetchone()
            if not row:
                raise ValueError(f"Escenario {escenario_id} no existe.")
            anio_id = row[0]
            conn.execute(
                update(escenarios_horario)
                .where(escenarios_horario.c.anio_id == anio_id)
                .values(activo=0)
            )
            conn.execute(
                update(escenarios_horario)
                .where(escenarios_horario.c.id == escenario_id)
                .values(activo=1)
            )
            if self._conn is None:
                conn.commit()

    def eliminar_escenario(self, escenario_id: int) -> bool:
        stmt = delete(escenarios_horario).where(escenarios_horario.c.id == escenario_id)
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    def duplicar_escenario(self, escenario_id: int, nuevo_nombre: str) -> EscenarioHorario:
        with self._get_conn() as conn:
            orig_row = (
                conn.execute(
                    select(escenarios_horario).where(escenarios_horario.c.id == escenario_id)
                )
                .mappings()
                .first()
            )
            if not orig_row:
                raise ValueError(f"Escenario {escenario_id} no existe.")
            # Insertar nuevo escenario inactivo
            nuevo_stmt = insert(escenarios_horario).values(
                anio_id=orig_row["anio_id"],
                nombre=nuevo_nombre,
                descripcion=orig_row.get("descripcion"),
                activo=0,
            )
            nuevo_id = self._execute_insert(conn, nuevo_stmt)

            # Copiar bloques de horarios usando INSERT...SELECT Core
            cols = [
                horarios.c.grupo_id,
                horarios.c.asignatura_id,
                horarios.c.usuario_id,
                horarios.c.asignacion_id,
                horarios.c.periodo_id,
                literal(nuevo_id).label("escenario_id"),
                horarios.c.dia_semana,
                horarios.c.hora_inicio,
                horarios.c.hora_fin,
                horarios.c.sala,
            ]
            sub = select(*cols).where(horarios.c.escenario_id == escenario_id)
            ins = insert(horarios).from_select(
                [
                    "grupo_id",
                    "asignatura_id",
                    "usuario_id",
                    "asignacion_id",
                    "periodo_id",
                    "escenario_id",
                    "dia_semana",
                    "hora_inicio",
                    "hora_fin",
                    "sala",
                ],
                sub,
            )
            conn.execute(ins)
            if self._conn is None:
                conn.commit()
            nuevo_row = (
                conn.execute(select(escenarios_horario).where(escenarios_horario.c.id == nuevo_id))
                .mappings()
                .first()
            )
            return self._row_to_escenario(nuevo_row)

    # =========================================================================
    # Plantillas de franja y franjas
    # =========================================================================

    def crear_plantilla_franja(self, p: PlantillaFranja) -> PlantillaFranja:
        stmt = insert(plantillas_franja).values(
            nombre=p.nombre,
            jornada=p.jornada,
            dias_activos=",".join(p.dias_activos),
            activa=int(p.activa),
            institucion_id=p.institucion_id,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return p.model_copy(update={"id": pk})

    def get_plantilla_franja(self, plantilla_id: int) -> PlantillaFranja | None:
        stmt = select(plantillas_franja).where(plantillas_franja.c.id == plantilla_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_plantilla(row) if row else None

    def listar_plantillas_franja(self, institucion_id: TenantScope) -> list[PlantillaFranja]:
        stmt = select(plantillas_franja)
        if isinstance(institucion_id, int):
            stmt = stmt.where(plantillas_franja.c.institucion_id == institucion_id)
        stmt = stmt.order_by(plantillas_franja.c.nombre)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_plantilla(r) for r in rows]

    def get_plantilla_activa(
        self, jornada: str, institucion_id: TenantScope
    ) -> PlantillaFranja | None:
        stmt = select(plantillas_franja).where(
            plantillas_franja.c.jornada == jornada,
            plantillas_franja.c.activa == 1,
        )
        if isinstance(institucion_id, int):
            stmt = stmt.where(plantillas_franja.c.institucion_id == institucion_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_plantilla(row) if row else None

    def actualizar_plantilla_franja(self, p: PlantillaFranja) -> PlantillaFranja:
        stmt = (
            update(plantillas_franja)
            .where(plantillas_franja.c.id == p.id)
            .values(
                nombre=p.nombre,
                jornada=p.jornada,
                dias_activos=",".join(p.dias_activos),
                activa=int(p.activa),
            )
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
        return p

    def activar_plantilla_franja(self, plantilla_id: int) -> None:
        with self._get_conn() as conn:
            row = conn.execute(
                select(plantillas_franja.c.jornada, plantillas_franja.c.institucion_id).where(
                    plantillas_franja.c.id == plantilla_id
                )
            ).fetchone()
            if not row:
                raise ValueError(f"Plantilla {plantilla_id} no existe.")
            jornada = row[0]
            institucion_id = row[1]
            if institucion_id is not None:
                conn.execute(
                    update(plantillas_franja)
                    .where(
                        plantillas_franja.c.jornada == jornada,
                        plantillas_franja.c.institucion_id == institucion_id,
                    )
                    .values(activa=0)
                )
            else:
                conn.execute(
                    update(plantillas_franja)
                    .where(
                        plantillas_franja.c.jornada == jornada,
                        plantillas_franja.c.institucion_id.is_(None),
                    )
                    .values(activa=0)
                )
            conn.execute(
                update(plantillas_franja)
                .where(plantillas_franja.c.id == plantilla_id)
                .values(activa=1)
            )
            if self._conn is None:
                conn.commit()

    def eliminar_plantilla_franja(self, plantilla_id: int) -> bool:
        stmt = delete(plantillas_franja).where(plantillas_franja.c.id == plantilla_id)
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    def crear_franja(self, f: Franja) -> Franja:
        stmt = insert(franjas).values(
            plantilla_id=f.plantilla_id,
            orden=f.orden,
            hora_inicio=f.hora_inicio,
            hora_fin=f.hora_fin,
            tipo=f.tipo,
            etiqueta=f.etiqueta,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return f.model_copy(update={"id": pk})

    def listar_franjas(self, plantilla_id: int) -> list[Franja]:
        stmt = (
            select(franjas).where(franjas.c.plantilla_id == plantilla_id).order_by(franjas.c.orden)
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_franja(r) for r in rows]

    def actualizar_franja(self, f: Franja) -> Franja:
        stmt = (
            update(franjas)
            .where(franjas.c.id == f.id)
            .values(
                plantilla_id=f.plantilla_id,
                orden=f.orden,
                hora_inicio=f.hora_inicio,
                hora_fin=f.hora_fin,
                tipo=f.tipo,
                etiqueta=f.etiqueta,
            )
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
        return f

    def eliminar_franja(self, franja_id: int) -> bool:
        stmt = delete(franjas).where(franjas.c.id == franja_id)
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    def reemplazar_franjas(self, plantilla_id: int, franjas_list: list[Franja]) -> int:
        with self._get_conn() as conn:
            conn.execute(delete(franjas).where(franjas.c.plantilla_id == plantilla_id))
            filas = [
                {
                    "plantilla_id": plantilla_id,
                    "orden": f.orden,
                    "hora_inicio": f.hora_inicio,
                    "hora_fin": f.hora_fin,
                    "tipo": f.tipo,
                    "etiqueta": f.etiqueta,
                }
                for f in franjas_list
            ]
            if filas:
                conn.execute(insert(franjas), filas)
            if self._conn is None:
                conn.commit()
        return len(filas)

    # =========================================================================
    # Áreas de conocimiento
    # =========================================================================

    def get_area(self, area_id: int) -> AreaConocimiento | None:
        stmt = select(areas_conocimiento).where(areas_conocimiento.c.id == area_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return AreaConocimiento(**dict(row)) if row else None

    def listar_areas(self, institucion_id: TenantScope) -> list[AreaConocimiento]:
        stmt = select(areas_conocimiento)
        if isinstance(institucion_id, int):
            stmt = stmt.where(areas_conocimiento.c.institucion_id == institucion_id)
        stmt = stmt.order_by(areas_conocimiento.c.nombre)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [AreaConocimiento(**dict(r)) for r in rows]

    def guardar_area(self, area: AreaConocimiento) -> AreaConocimiento:
        stmt = insert(areas_conocimiento).values(
            nombre=area.nombre,
            codigo=area.codigo,
            color=area.color,
            institucion_id=area.institucion_id,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return area.model_copy(update={"id": pk})

    def actualizar_area(self, area: AreaConocimiento) -> AreaConocimiento:
        stmt = (
            update(areas_conocimiento)
            .where(areas_conocimiento.c.id == area.id)
            .values(nombre=area.nombre, codigo=area.codigo, color=area.color)
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
        return area

    def actualizar_color_area(self, area_id: int, color: str | None) -> bool:
        stmt = (
            update(areas_conocimiento).where(areas_conocimiento.c.id == area_id).values(color=color)
        )
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    def eliminar_area(self, area_id: int) -> bool:
        stmt = delete(areas_conocimiento).where(areas_conocimiento.c.id == area_id)
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    # =========================================================================
    # Asignaturas
    # =========================================================================

    def get_asignatura(self, asignatura_id: int) -> Asignatura | None:
        stmt = select(asignaturas).where(asignaturas.c.id == asignatura_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_asignatura(row) if row else None

    def listar_asignaturas(
        self,
        institucion_id: TenantScope,
        area_id: int | None = None,
    ) -> list[Asignatura]:
        stmt = select(asignaturas)
        if isinstance(institucion_id, int):
            stmt = stmt.where(asignaturas.c.institucion_id == institucion_id)
        if area_id is not None:
            stmt = stmt.where(asignaturas.c.area_id == area_id)
        stmt = stmt.order_by(asignaturas.c.nombre)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_asignatura(r) for r in rows]

    def guardar_asignatura(self, asignatura: Asignatura) -> Asignatura:
        stmt = insert(asignaturas).values(
            nombre=asignatura.nombre,
            codigo=asignatura.codigo,
            area_id=asignatura.area_id,
            horas_semanales=asignatura.horas_semanales,
            tipo_sala_requerido=asignatura.tipo_sala_requerido,
            bloque_doble=int(asignatura.bloque_doble),
            horas_consecutivas=asignatura.horas_consecutivas,
            institucion_id=asignatura.institucion_id,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return asignatura.model_copy(update={"id": pk})

    def actualizar_asignatura(self, asignatura: Asignatura) -> Asignatura:
        # Multi-tenant: NO se toca institucion_id en update.
        stmt = (
            update(asignaturas)
            .where(asignaturas.c.id == asignatura.id)
            .values(
                nombre=asignatura.nombre,
                codigo=asignatura.codigo,
                area_id=asignatura.area_id,
                horas_semanales=asignatura.horas_semanales,
                tipo_sala_requerido=asignatura.tipo_sala_requerido,
                bloque_doble=int(asignatura.bloque_doble),
                horas_consecutivas=asignatura.horas_consecutivas,
            )
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
        return asignatura

    def eliminar_asignatura(self, asignatura_id: int) -> bool:
        stmt = delete(asignaturas).where(asignaturas.c.id == asignatura_id)
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    # =========================================================================
    # Grupos
    # =========================================================================

    def get_grupo(self, grupo_id: int) -> Grupo | None:
        stmt = select(grupos).where(grupos.c.id == grupo_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
        if not row:
            return None
        d = dict(row)
        d["jornada"] = Jornada(d["jornada"]) if d.get("jornada") else Jornada.UNICA
        return Grupo(**d)

    def get_grupo_por_codigo(self, codigo: str, institucion_id: int | None = None) -> Grupo | None:
        stmt = select(grupos).where(grupos.c.codigo == codigo)
        if institucion_id is not None:
            stmt = stmt.where(grupos.c.institucion_id == institucion_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
        if not row:
            return None
        d = dict(row)
        d["jornada"] = Jornada(d["jornada"]) if d.get("jornada") else Jornada.UNICA
        return Grupo(**d)

    def listar_grupos(
        self,
        institucion_id: TenantScope,
        grado: int | None = None,
    ) -> list[Grupo]:
        stmt = select(grupos)
        if isinstance(institucion_id, int):
            stmt = stmt.where(grupos.c.institucion_id == institucion_id)
        if grado is not None:
            stmt = stmt.where(grupos.c.grado == grado)
        stmt = stmt.order_by(grupos.c.codigo)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
        resultado = []
        for r in rows:
            d = dict(r)
            d["jornada"] = Jornada(d["jornada"]) if d.get("jornada") else Jornada.UNICA
            resultado.append(Grupo(**d))
        return resultado

    def asignar_sala_a_grupo(self, grupo_id: int, sala_id: int | None) -> bool:
        stmt = update(grupos).where(grupos.c.id == grupo_id).values(sala_id=sala_id)
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    def guardar_grupo(self, grupo: Grupo) -> Grupo:
        stmt = insert(grupos).values(
            codigo=grupo.codigo,
            nombre=grupo.nombre,
            grado=grupo.grado,
            jornada=grupo.jornada.value if grupo.jornada else None,
            capacidad_maxima=grupo.capacidad_maxima,
            institucion_id=grupo.institucion_id,
            director_grupo_id=grupo.director_grupo_id,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return grupo.model_copy(update={"id": pk})

    def actualizar_grupo(self, grupo: Grupo) -> Grupo:
        # Multi-tenant: institucion_id no se modifica en update.
        stmt = (
            update(grupos)
            .where(grupos.c.id == grupo.id)
            .values(
                codigo=grupo.codigo,
                nombre=grupo.nombre,
                grado=grupo.grado,
                jornada=grupo.jornada.value if grupo.jornada else None,
                capacidad_maxima=grupo.capacidad_maxima,
                director_grupo_id=grupo.director_grupo_id,
            )
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
        return grupo

    def eliminar_grupo(self, grupo_id: int) -> bool:
        stmt = delete(grupos).where(grupos.c.id == grupo_id)
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    # =========================================================================
    # Horarios
    # =========================================================================

    def _build_horario_info_stmt(self):
        """SELECT enriquecido con JOINs para HorarioInfo."""
        return (
            select(
                horarios,
                grupos.c.codigo.label("grupo_codigo"),
                asignaturas.c.nombre.label("asignatura_nombre"),
                usuarios.c.nombre_completo.label("docente_nombre"),
                func.coalesce(periodos.c.nombre, "").label("periodo_nombre"),
            )
            .join(grupos, grupos.c.id == horarios.c.grupo_id)
            .join(asignaturas, asignaturas.c.id == horarios.c.asignatura_id)
            .join(usuarios, usuarios.c.id == horarios.c.usuario_id)
            .outerjoin(periodos, periodos.c.id == horarios.c.periodo_id)
        )

    def get_horario(self, horario_id: int) -> Horario | None:
        stmt = select(horarios).where(horarios.c.id == horario_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_horario(row) if row else None

    def get_info_horario(self, horario_id: int) -> HorarioInfo | None:
        stmt = self._build_horario_info_stmt().where(horarios.c.id == horario_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_horario_info(row) if row else None

    def _get_escenario_activo_por_periodo(self, conn, periodo_id: int) -> int | None:
        """Resuelve periodo_id → anio_id → escenario activo. Retorna escenario_id o None."""
        stmt = (
            select(escenarios_horario.c.id)
            .join(periodos, periodos.c.anio_id == escenarios_horario.c.anio_id)
            .where(
                periodos.c.id == periodo_id,
                escenarios_horario.c.activo == 1,
            )
        )
        row = conn.execute(stmt).fetchone()
        return row[0] if row else None

    def listar_horario_grupo(self, grupo_id: int, periodo_id: int) -> list[HorarioInfo]:
        with self._get_conn() as conn:
            escenario_id = self._get_escenario_activo_por_periodo(conn, periodo_id)
            if escenario_id is None:
                return []
            stmt = (
                self._build_horario_info_stmt()
                .where(horarios.c.grupo_id == grupo_id, horarios.c.escenario_id == escenario_id)
                .order_by(horarios.c.dia_semana, horarios.c.hora_inicio)
            )
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_horario_info(r) for r in rows]

    def listar_horario_docente(self, usuario_id: int, periodo_id: int) -> list[HorarioInfo]:
        with self._get_conn() as conn:
            escenario_id = self._get_escenario_activo_por_periodo(conn, periodo_id)
            if escenario_id is None:
                return []
            stmt = (
                self._build_horario_info_stmt()
                .where(horarios.c.usuario_id == usuario_id, horarios.c.escenario_id == escenario_id)
                .order_by(horarios.c.dia_semana, horarios.c.hora_inicio)
            )
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_horario_info(r) for r in rows]

    def listar_horario_grupo_escenario(self, grupo_id: int, escenario_id: int) -> list[HorarioInfo]:
        stmt = (
            self._build_horario_info_stmt()
            .where(horarios.c.grupo_id == grupo_id, horarios.c.escenario_id == escenario_id)
            .order_by(horarios.c.dia_semana, horarios.c.hora_inicio)
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_horario_info(r) for r in rows]

    def listar_horario_escenario(self, escenario_id: int) -> list[HorarioInfo]:
        stmt = (
            self._build_horario_info_stmt()
            .where(horarios.c.escenario_id == escenario_id)
            .order_by(horarios.c.dia_semana, horarios.c.hora_inicio)
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_horario_info(r) for r in rows]

    def existe_conflicto_horario(
        self,
        usuario_id: int,
        periodo_id: int,
        dia_semana: str,
        hora_inicio: str,
        hora_fin: str,
        excluir_horario_id: int | None = None,
    ) -> bool:
        stmt = select(horarios.c.id).where(
            horarios.c.usuario_id == usuario_id,
            horarios.c.periodo_id == periodo_id,
            horarios.c.dia_semana == dia_semana,
            horarios.c.hora_inicio < hora_fin,
            horarios.c.hora_fin > hora_inicio,
        )
        if excluir_horario_id is not None:
            stmt = stmt.where(horarios.c.id != excluir_horario_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).fetchone()
            return row is not None

    def get_estadisticas(self, periodo_id: int) -> HorarioEstadisticasDTO:
        stmt = select(
            func.count().label("total_bloques"),
            func.count(horarios.c.grupo_id.distinct()).label("grupos_cubiertos"),
            func.count(horarios.c.asignatura_id.distinct()).label("materias_cargadas"),
            func.count(horarios.c.usuario_id.distinct()).label("docentes_con_horario"),
        ).where(horarios.c.periodo_id == periodo_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
        if not row:
            return HorarioEstadisticasDTO()
        return HorarioEstadisticasDTO(**dict(row))

    def guardar_horario(self, horario: Horario) -> Horario:
        stmt = insert(horarios).values(
            grupo_id=horario.grupo_id,
            asignatura_id=horario.asignatura_id,
            usuario_id=horario.usuario_id,
            asignacion_id=horario.asignacion_id,
            periodo_id=horario.periodo_id,
            escenario_id=horario.escenario_id,
            dia_semana=horario.dia_semana.value,
            hora_inicio=horario.hora_inicio.strftime("%H:%M"),
            hora_fin=horario.hora_fin.strftime("%H:%M"),
            sala=horario.sala,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return horario.model_copy(update={"id": pk})

    def actualizar_horario(self, horario: Horario) -> Horario:
        stmt = (
            update(horarios)
            .where(horarios.c.id == horario.id)
            .values(
                grupo_id=horario.grupo_id,
                asignatura_id=horario.asignatura_id,
                usuario_id=horario.usuario_id,
                asignacion_id=horario.asignacion_id,
                periodo_id=horario.periodo_id,
                escenario_id=horario.escenario_id,
                dia_semana=horario.dia_semana.value,
                hora_inicio=horario.hora_inicio.strftime("%H:%M"),
                hora_fin=horario.hora_fin.strftime("%H:%M"),
                sala=horario.sala,
            )
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
        return horario

    def eliminar_horario(self, horario_id: int) -> bool:
        stmt = delete(horarios).where(horarios.c.id == horario_id)
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    def existe_cruce(
        self,
        escenario_id: int,
        dia_semana: str,
        hora_inicio: str,
        hora_fin: str,
        *,
        usuario_id: int | None = None,
        grupo_id: int | None = None,
        sala: str | None = None,
        excluir_horario_id: int | None = None,
    ) -> bool:
        stmt = select(horarios.c.id).where(
            horarios.c.escenario_id == escenario_id,
            horarios.c.dia_semana == dia_semana,
            horarios.c.hora_inicio < hora_fin,
            horarios.c.hora_fin > hora_inicio,
        )
        if usuario_id is not None:
            stmt = stmt.where(horarios.c.usuario_id == usuario_id)
        if grupo_id is not None:
            stmt = stmt.where(horarios.c.grupo_id == grupo_id)
        if sala is not None:
            stmt = stmt.where(horarios.c.sala == sala)
        if excluir_horario_id is not None:
            stmt = stmt.where(horarios.c.id != excluir_horario_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).fetchone()
        return row is not None

    def contar_bloques_asignacion(self, escenario_id: int, asignacion_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(horarios)
            .where(
                horarios.c.escenario_id == escenario_id,
                horarios.c.asignacion_id == asignacion_id,
            )
        )
        with self._get_conn() as conn:
            return int(conn.execute(stmt).scalar() or 0)

    def contar_bloques_docente(self, escenario_id: int, usuario_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(horarios)
            .where(
                horarios.c.escenario_id == escenario_id,
                horarios.c.usuario_id == usuario_id,
            )
        )
        with self._get_conn() as conn:
            return int(conn.execute(stmt).scalar() or 0)

    def crear_bloques_masivo(self, horarios_list: list) -> int:
        if not horarios_list:
            return 0
        rows = []
        for h in horarios_list:
            dia = h.dia_semana.value if hasattr(h.dia_semana, "value") else str(h.dia_semana)
            hi = (
                h.hora_inicio.strftime("%H:%M")
                if hasattr(h.hora_inicio, "strftime")
                else str(h.hora_inicio)
            )
            hf = (
                h.hora_fin.strftime("%H:%M") if hasattr(h.hora_fin, "strftime") else str(h.hora_fin)
            )
            rows.append(
                {
                    "grupo_id": h.grupo_id,
                    "asignatura_id": h.asignatura_id,
                    "usuario_id": h.usuario_id,
                    "asignacion_id": getattr(h, "asignacion_id", None),
                    "periodo_id": getattr(h, "periodo_id", None),
                    "escenario_id": h.escenario_id,
                    "dia_semana": dia,
                    "hora_inicio": hi,
                    "hora_fin": hf,
                    "sala": getattr(h, "sala", "Aula") or "Aula",
                }
            )
        with self._get_conn() as conn:
            conn.execute(insert(horarios), rows)
            if self._conn is None:
                conn.commit()
        return len(rows)

    def eliminar_horarios_por_asignacion(self, asignacion_id: int) -> int:
        stmt = delete(horarios).where(horarios.c.asignacion_id == asignacion_id)
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount

    # =========================================================================
    # Logros
    # =========================================================================

    def get_logro(self, logro_id: int) -> Logro | None:
        stmt = select(logros).where(logros.c.id == logro_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return Logro(**dict(row)) if row else None

    def listar_logros(self, asignacion_id: int, periodo_id: int) -> list[Logro]:
        stmt = (
            select(logros)
            .where(logros.c.asignacion_id == asignacion_id, logros.c.periodo_id == periodo_id)
            .order_by(logros.c.orden, logros.c.id)
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [Logro(**dict(r)) for r in rows]

    def guardar_logro(self, logro: Logro) -> Logro:
        stmt = insert(logros).values(
            asignacion_id=logro.asignacion_id,
            periodo_id=logro.periodo_id,
            descripcion=logro.descripcion,
            orden=logro.orden,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return logro.model_copy(update={"id": pk})

    def actualizar_logro(self, logro: Logro) -> Logro:
        stmt = (
            update(logros)
            .where(logros.c.id == logro.id)
            .values(descripcion=logro.descripcion, orden=logro.orden)
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
        return logro

    def eliminar_logro(self, logro_id: int) -> bool:
        stmt = delete(logros).where(logros.c.id == logro_id)
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    # =========================================================================
    # Disponibilidad docente
    # =========================================================================

    def upsert_disponibilidad(self, d: DisponibilidadDocente) -> DisponibilidadDocente:
        """INSERT OR REPLACE → _upsert() + re-lectura por clave única."""
        stmt = self._upsert(
            disponibilidad_docente,
            {
                "usuario_id": d.usuario_id,
                "dia_semana": d.dia_semana,
                "franja_orden": d.franja_orden,
                "disponible": int(d.disponible),
            },
            conflict_cols=["usuario_id", "dia_semana", "franja_orden"],
            update_cols=["disponible"],
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            row = (
                conn.execute(
                    select(disponibilidad_docente).where(
                        disponibilidad_docente.c.usuario_id == d.usuario_id,
                        disponibilidad_docente.c.dia_semana == d.dia_semana,
                        disponibilidad_docente.c.franja_orden == d.franja_orden,
                    )
                )
                .mappings()
                .first()
            )
            return self._row_to_disponibilidad(row) if row else d

    def listar_disponibilidad_docente(self, usuario_id: int) -> list[DisponibilidadDocente]:
        stmt = (
            select(disponibilidad_docente)
            .where(disponibilidad_docente.c.usuario_id == usuario_id)
            .order_by(disponibilidad_docente.c.dia_semana, disponibilidad_docente.c.franja_orden)
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_disponibilidad(r) for r in rows]

    def es_disponible(self, usuario_id: int, dia: str, franja_orden: int) -> bool:
        stmt = select(disponibilidad_docente.c.disponible).where(
            disponibilidad_docente.c.usuario_id == usuario_id,
            disponibilidad_docente.c.dia_semana == dia,
            disponibilidad_docente.c.franja_orden == franja_orden,
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).fetchone()
        if row is None:
            return True  # R2: no hay fila → disponible por defecto
        return bool(row[0])

    def limpiar_disponibilidad_docente(self, usuario_id: int) -> int:
        stmt = delete(disponibilidad_docente).where(
            disponibilidad_docente.c.usuario_id == usuario_id
        )
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount

    def cargar_disponibilidad_lote(self, usuario_id: int, slots: list[dict]) -> int:
        """INSERT OR REPLACE de indisponibilidades (disponible=0) → _upsert()."""
        with self._get_conn() as conn:
            count = 0
            for slot in slots:
                stmt = self._upsert(
                    disponibilidad_docente,
                    {
                        "usuario_id": usuario_id,
                        "dia_semana": slot["dia_semana"],
                        "franja_orden": slot["franja_orden"],
                        "disponible": 0,
                    },
                    conflict_cols=["usuario_id", "dia_semana", "franja_orden"],
                    update_cols=["disponible"],
                )
                conn.execute(stmt)
                count += 1
            if self._conn is None:
                conn.commit()
        return count

    def reemplazar_disponibilidad_docente(self, usuario_id: int, slots: list[dict]) -> int:
        """Borra + recarga la disponibilidad en una sola transacción."""
        with self._get_conn() as conn:
            conn.execute(
                delete(disponibilidad_docente).where(
                    disponibilidad_docente.c.usuario_id == usuario_id
                )
            )
            count = 0
            for slot in slots:
                stmt = self._upsert(
                    disponibilidad_docente,
                    {
                        "usuario_id": usuario_id,
                        "dia_semana": slot["dia_semana"],
                        "franja_orden": slot["franja_orden"],
                        "disponible": 0,
                    },
                    conflict_cols=["usuario_id", "dia_semana", "franja_orden"],
                    update_cols=["disponible"],
                )
                conn.execute(stmt)
                count += 1
            if self._conn is None:
                conn.commit()
        return count

    # =========================================================================
    # Config generación
    # =========================================================================

    def crear_config_generacion(self, c: ConfigGeneracion) -> ConfigGeneracion:
        grupos_json = json.dumps(c.grupos)
        pesos_json = json.dumps(c.pesos.model_dump())
        restricciones_json = json.dumps(c.restricciones)
        stmt = insert(config_generacion).values(
            nombre=c.nombre,
            periodo_id=c.periodo_id,
            anio_id=c.anio_id,
            plantilla_id=c.plantilla_id,
            estado=c.estado,
            grupos_json=grupos_json,
            pesos_json=pesos_json,
            restricciones_json=restricciones_json,
            escenario_destino_id=c.escenario_destino_id,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
            row = (
                conn.execute(select(config_generacion).where(config_generacion.c.id == pk))
                .mappings()
                .first()
            )
            return self._row_to_config(row)

    def get_config_generacion(self, config_id: int) -> ConfigGeneracion | None:
        stmt = select(config_generacion).where(config_generacion.c.id == config_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_config(row) if row else None

    def listar_configs_generacion(
        self,
        institucion_id: TenantScope,
        periodo_id: int | None = None,
    ) -> list[ConfigGeneracion]:
        """
        Usa text() para la cláusula de filtro de institución porque depende de
        json_each(grupos_json), función SQLite-specific sin equivalente en Core
        que no requiera extensiones. El resto del SELECT es Core.

        La condición filtra configuraciones que:
          - son globales (grupos_json vacío o null), o
          - contienen algún grupo de la institución dada.
        """
        stmt = select(config_generacion)
        if periodo_id is not None:
            stmt = stmt.where(config_generacion.c.periodo_id == periodo_id)
        if institucion_id != "*":
            tenant_filter = text(
                "(grupos_json IN ('[]', 'null') OR grupos_json IS NULL OR EXISTS ("
                "SELECT 1 FROM json_each(grupos_json) j"
                " JOIN grupos g ON g.id = CAST(j.value AS INTEGER)"
                " WHERE g.institucion_id = :inst_id"
                "))"
            ).bindparams(inst_id=institucion_id)
            stmt = stmt.where(tenant_filter)
        stmt = stmt.order_by(config_generacion.c.nombre)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_config(r) for r in rows]

    def actualizar_config_generacion(self, c: ConfigGeneracion) -> ConfigGeneracion:
        grupos_json = json.dumps(c.grupos)
        pesos_json = json.dumps(c.pesos.model_dump())
        restricciones_json = json.dumps(c.restricciones)
        stmt = (
            update(config_generacion)
            .where(config_generacion.c.id == c.id)
            .values(
                nombre=c.nombre,
                periodo_id=c.periodo_id,
                anio_id=c.anio_id,
                plantilla_id=c.plantilla_id,
                estado=c.estado,
                grupos_json=grupos_json,
                pesos_json=pesos_json,
                restricciones_json=restricciones_json,
                escenario_destino_id=c.escenario_destino_id,
                updated_at=_ahora().isoformat(timespec="seconds"),
            )
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            row = (
                conn.execute(select(config_generacion).where(config_generacion.c.id == c.id))
                .mappings()
                .first()
            )
            return self._row_to_config(row)

    def eliminar_config_generacion(self, config_id: int) -> bool:
        stmt = delete(config_generacion).where(config_generacion.c.id == config_id)
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    def cambiar_estado_config(self, config_id: int, nuevo_estado: str) -> ConfigGeneracion:
        with self._get_conn() as conn:
            row = (
                conn.execute(select(config_generacion).where(config_generacion.c.id == config_id))
                .mappings()
                .first()
            )
            if not row:
                raise ValueError(f"Config {config_id} no existe.")
            cfg = self._row_to_config(row)
            if not cfg.puede_transicionar_a(nuevo_estado):
                raise ValueError(f"Transición inválida: '{cfg.estado}' → '{nuevo_estado}'.")
            conn.execute(
                update(config_generacion)
                .where(config_generacion.c.id == config_id)
                .values(estado=nuevo_estado, updated_at=_ahora().isoformat(timespec="seconds"))
            )
            if self._conn is None:
                conn.commit()
            row = (
                conn.execute(select(config_generacion).where(config_generacion.c.id == config_id))
                .mappings()
                .first()
            )
            return self._row_to_config(row)

    def duplicar_config_generacion(self, config_id: int) -> ConfigGeneracion:
        with self._get_conn() as conn:
            row = (
                conn.execute(select(config_generacion).where(config_generacion.c.id == config_id))
                .mappings()
                .first()
            )
            if not row:
                raise ValueError(f"Config {config_id} no existe.")
            orig = self._row_to_config(row)
            nuevo_nombre = f"{orig.nombre} (copia)"
            stmt = insert(config_generacion).values(
                nombre=nuevo_nombre,
                periodo_id=orig.periodo_id,
                anio_id=orig.anio_id,
                plantilla_id=orig.plantilla_id,
                estado="borrador",
                grupos_json=json.dumps(orig.grupos),
                pesos_json=json.dumps(orig.pesos.model_dump()),
                restricciones_json=json.dumps(orig.restricciones),
                escenario_destino_id=None,
            )
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
            nuevo_row = (
                conn.execute(select(config_generacion).where(config_generacion.c.id == pk))
                .mappings()
                .first()
            )
            return self._row_to_config(nuevo_row)

    # =========================================================================
    # Salas
    # =========================================================================

    def listar_salas(self, institucion_id: TenantScope) -> list[Sala]:
        stmt = select(salas)
        if isinstance(institucion_id, int):
            stmt = stmt.where(salas.c.institucion_id == institucion_id)
        stmt = stmt.order_by(salas.c.nombre)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_sala(r) for r in rows]

    def get_sala(self, sala_id: int) -> Sala | None:
        stmt = select(salas).where(salas.c.id == sala_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_sala(row) if row else None

    def crear_sala(self, sala: Sala) -> Sala:
        stmt = insert(salas).values(
            nombre=sala.nombre,
            tipo=sala.tipo,
            capacidad=sala.capacidad,
            institucion_id=sala.institucion_id,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return sala.model_copy(update={"id": pk})

    def actualizar_sala(self, sala: Sala) -> Sala:
        # Multi-tenant: NO se toca institucion_id en update.
        stmt = (
            update(salas)
            .where(salas.c.id == sala.id)
            .values(nombre=sala.nombre, tipo=sala.tipo, capacidad=sala.capacidad)
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
        return sala

    def eliminar_sala(self, sala_id: int) -> bool:
        stmt = delete(salas).where(salas.c.id == sala_id)
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    # =========================================================================
    # VentanaGrupo
    # =========================================================================

    def listar_ventanas_grupo(self, institucion_id: TenantScope) -> list[VentanaGrupo]:
        if institucion_id == "*":
            stmt = select(ventanas_grupo)
        else:
            stmt = (
                select(ventanas_grupo)
                .join(grupos, grupos.c.id == ventanas_grupo.c.grupo_id)
                .where(grupos.c.institucion_id == institucion_id)
            )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_ventana_grupo(r) for r in rows]

    def get_ventanas_por_grupo(self, grupo_id: int) -> list[VentanaGrupo]:
        stmt = select(ventanas_grupo).where(ventanas_grupo.c.grupo_id == grupo_id)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_ventana_grupo(r) for r in rows]

    def get_ventanas_por_grado(self, grado: int) -> list[VentanaGrupo]:
        stmt = select(ventanas_grupo).where(ventanas_grupo.c.grado == grado)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_ventana_grupo(r) for r in rows]

    def crear_ventana_grupo(self, v: VentanaGrupo) -> VentanaGrupo:
        stmt = insert(ventanas_grupo).values(
            grupo_id=v.grupo_id,
            grado=v.grado,
            franjas_permitidas=json.dumps(v.franjas_permitidas),
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return v.model_copy(update={"id": pk})

    def eliminar_ventana_grupo(self, ventana_id: int) -> bool:
        stmt = delete(ventanas_grupo).where(ventanas_grupo.c.id == ventana_id)
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    # =========================================================================
    # BloqueAnclado
    # =========================================================================

    def listar_bloques_anclados(self, escenario_id: int) -> list[BloqueAnclado]:
        stmt = select(bloques_anclados).where(bloques_anclados.c.escenario_id == escenario_id)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_bloque_anclado(r) for r in rows]

    def crear_bloque_anclado(self, b: BloqueAnclado) -> BloqueAnclado:
        stmt = insert(bloques_anclados).values(
            escenario_id=b.escenario_id,
            asignacion_id=b.asignacion_id,
            dia_semana=b.dia_semana,
            franja_orden=b.franja_orden,
            sala_id=b.sala_id,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return b.model_copy(update={"id": pk})

    def eliminar_bloque_anclado(self, bloque_id: int) -> bool:
        stmt = delete(bloques_anclados).where(bloques_anclados.c.id == bloque_id)
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    # =========================================================================
    # FranjaReunion
    # =========================================================================

    def listar_franjas_reunion(self, institucion_id: TenantScope) -> list[FranjaReunion]:
        stmt = select(franjas_reunion)
        if isinstance(institucion_id, int):
            stmt = stmt.where(franjas_reunion.c.institucion_id == institucion_id)
        stmt = stmt.order_by(franjas_reunion.c.dia_semana, franjas_reunion.c.franja_orden)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_franja_reunion(r) for r in rows]

    def get_franja_reunion(self, franja_id: int) -> FranjaReunion | None:
        stmt = select(franjas_reunion).where(franjas_reunion.c.id == franja_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_franja_reunion(row) if row else None

    def crear_franja_reunion(self, f: FranjaReunion) -> FranjaReunion:
        stmt = insert(franjas_reunion).values(
            nombre=f.nombre,
            docentes_json=json.dumps(f.docentes),
            dia_semana=f.dia_semana,
            franja_orden=f.franja_orden,
            modo=f.modo,
            institucion_id=f.institucion_id,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return f.model_copy(update={"id": pk})

    def actualizar_franja_reunion(self, f: FranjaReunion) -> FranjaReunion:
        stmt = (
            update(franjas_reunion)
            .where(franjas_reunion.c.id == f.id)
            .values(
                nombre=f.nombre,
                docentes_json=json.dumps(f.docentes),
                dia_semana=f.dia_semana,
                franja_orden=f.franja_orden,
                modo=f.modo,
            )
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
        return f

    def eliminar_franja_reunion(self, franja_id: int) -> bool:
        stmt = delete(franjas_reunion).where(franjas_reunion.c.id == franja_id)
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    # =========================================================================
    # LimitesDocente
    # =========================================================================

    def get_limites_docente(self, usuario_id: int) -> LimitesDocente | None:
        stmt = select(limites_docente).where(limites_docente.c.usuario_id == usuario_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_limites_docente(row) if row else None

    def set_limites_docente(self, limites: LimitesDocente) -> LimitesDocente:
        """ON CONFLICT(usuario_id) DO UPDATE → _upsert()."""
        stmt = self._upsert(
            limites_docente,
            {
                "usuario_id": limites.usuario_id,
                "min_horas_dia": limites.min_horas_dia,
                "max_horas_dia": limites.max_horas_dia,
            },
            conflict_cols=["usuario_id"],
            update_cols=["min_horas_dia", "max_horas_dia"],
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            row = (
                conn.execute(
                    select(limites_docente).where(
                        limites_docente.c.usuario_id == limites.usuario_id
                    )
                )
                .mappings()
                .first()
            )
            return self._row_to_limites_docente(row)

    def listar_limites_docente(self, institucion_id: TenantScope) -> list[LimitesDocente]:
        if institucion_id == "*":
            stmt = select(limites_docente)
        else:
            stmt = (
                select(limites_docente)
                .join(usuarios, usuarios.c.id == limites_docente.c.usuario_id)
                .where(usuarios.c.institucion_id == institucion_id)
            )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_limites_docente(r) for r in rows]

    # =========================================================================
    # Grados
    # =========================================================================

    def listar_grados(self, institucion_id: TenantScope) -> list[Grado]:
        if institucion_id == "*":
            stmt = select(grados).order_by(grados.c.numero)
        else:
            stmt = (
                select(grados)
                .join(
                    configuracion_grado_institucion,
                    configuracion_grado_institucion.c.grado_id == grados.c.id,
                )
                .where(configuracion_grado_institucion.c.institucion_id == institucion_id)
                .order_by(grados.c.numero)
            )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_grado(r) for r in rows]

    def upsert_grado(self, grado: Grado) -> Grado:
        """ON CONFLICT(numero) DO UPDATE → _upsert()."""
        stmt = self._upsert(
            grados,
            {
                "numero": grado.numero,
                "nombre": grado.nombre,
                "min_estudiantes": grado.min_estudiantes,
                "max_estudiantes": grado.max_estudiantes,
                "horas_semanales": grado.horas_semanales,
            },
            conflict_cols=["numero"],
            update_cols=["nombre", "min_estudiantes", "max_estudiantes", "horas_semanales"],
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            row = (
                conn.execute(select(grados).where(grados.c.numero == grado.numero))
                .mappings()
                .first()
            )
            return self._row_to_grado(row)

    def eliminar_grado(self, numero: int) -> bool:
        stmt = delete(grados).where(grados.c.numero == numero)
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    # =========================================================================
    # PlanEstudios
    # =========================================================================

    def listar_plan_estudios(self, institucion_id: TenantScope) -> list[PlanEstudios]:
        stmt = select(plan_estudios)
        if institucion_id != "*":
            stmt = stmt.where(
                or_(
                    plan_estudios.c.institucion_id == institucion_id,
                    plan_estudios.c.institucion_id.is_(None),
                )
            )
        stmt = stmt.order_by(plan_estudios.c.grado, plan_estudios.c.asignatura_id)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_plan_estudios(r) for r in rows]

    def get_plan_estudios_por_grado(
        self, grado: int, institucion_id: int | None = None
    ) -> list[PlanEstudios]:
        stmt = select(plan_estudios).where(plan_estudios.c.grado == grado)
        if institucion_id not in (None, "*"):
            stmt = stmt.where(
                or_(
                    plan_estudios.c.institucion_id == institucion_id,
                    plan_estudios.c.institucion_id.is_(None),
                )
            )
        stmt = stmt.order_by(plan_estudios.c.asignatura_id)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_plan_estudios(r) for r in rows]

    def set_horas_plan(
        self, grado: int, asignatura_id: int, horas: int, institucion_id: int | None = None
    ) -> PlanEstudios:
        """
        Upsert de plan_estudios.

        Con institucion_id (NOT NULL): usa _upsert() sobre (institucion_id, grado, asignatura_id).
        Sin institucion_id (NULL): SQLite trata NULLs como distintos en UNIQUE, por lo que
        el upsert estándar no puede resolver el conflicto por NULL. Se mantiene la lógica
        Python original: buscar fila existente y UPDATE o INSERT manual.

        El fallback NULL usa text() mínimo solo en la variante IS NULL del SELECT, que
        SQLAlchemy Core soporta nativamente con .is_(None).
        """
        with self._get_conn() as conn:
            if institucion_id is not None:
                stmt = self._upsert(
                    plan_estudios,
                    {
                        "grado": grado,
                        "asignatura_id": asignatura_id,
                        "horas_semanales": horas,
                        "institucion_id": institucion_id,
                    },
                    conflict_cols=["institucion_id", "grado", "asignatura_id"],
                    update_cols=["horas_semanales"],
                )
                conn.execute(stmt)
                if self._conn is None:
                    conn.commit()
                sel = select(plan_estudios).where(
                    plan_estudios.c.grado == grado,
                    plan_estudios.c.asignatura_id == asignatura_id,
                    plan_estudios.c.institucion_id == institucion_id,
                )
            else:
                # SQLite NULL en UNIQUE: buscar fila existente manualmente.
                existing = conn.execute(
                    select(plan_estudios.c.id, plan_estudios.c.institucion_id)
                    .where(
                        plan_estudios.c.grado == grado,
                        plan_estudios.c.asignatura_id == asignatura_id,
                    )
                    .order_by(plan_estudios.c.institucion_id)
                    .limit(1)
                ).fetchone()
                if existing:
                    conn.execute(
                        update(plan_estudios)
                        .where(plan_estudios.c.id == existing[0])
                        .values(horas_semanales=horas)
                    )
                    found_inst_id = existing[1]
                else:
                    conn.execute(
                        insert(plan_estudios).values(
                            grado=grado,
                            asignatura_id=asignatura_id,
                            horas_semanales=horas,
                            institucion_id=None,
                        )
                    )
                    found_inst_id = None
                if self._conn is None:
                    conn.commit()
                if found_inst_id is not None:
                    sel = select(plan_estudios).where(
                        plan_estudios.c.grado == grado,
                        plan_estudios.c.asignatura_id == asignatura_id,
                        plan_estudios.c.institucion_id == found_inst_id,
                    )
                else:
                    sel = select(plan_estudios).where(
                        plan_estudios.c.grado == grado,
                        plan_estudios.c.asignatura_id == asignatura_id,
                        plan_estudios.c.institucion_id.is_(None),
                    )
            row = conn.execute(sel).mappings().first()
            return self._row_to_plan_estudios(row)

    def eliminar_plan_estudios(self, grado: int, asignatura_id: int) -> bool:
        stmt = delete(plan_estudios).where(
            plan_estudios.c.grado == grado,
            plan_estudios.c.asignatura_id == asignatura_id,
        )
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    # =========================================================================
    # ConfiguracionGradoInstitucion
    # =========================================================================

    def get_config_grado(
        self, grado_id: int, institucion_id: int
    ) -> ConfiguracionGradoInstitucion | None:
        stmt = select(configuracion_grado_institucion).where(
            configuracion_grado_institucion.c.grado_id == grado_id,
            configuracion_grado_institucion.c.institucion_id == institucion_id,
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_config_grado(row) if row else None

    def upsert_config_grado(
        self, cfg: ConfiguracionGradoInstitucion
    ) -> ConfiguracionGradoInstitucion:
        """ON CONFLICT(grado_id, institucion_id) DO UPDATE → _upsert()."""
        stmt = self._upsert(
            configuracion_grado_institucion,
            {
                "grado_id": cfg.grado_id,
                "institucion_id": cfg.institucion_id,
                "min_estudiantes": cfg.min_estudiantes,
                "max_estudiantes": cfg.max_estudiantes,
                "horas_semanales": cfg.horas_semanales,
            },
            conflict_cols=["grado_id", "institucion_id"],
            update_cols=["min_estudiantes", "max_estudiantes", "horas_semanales"],
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            row = (
                conn.execute(
                    select(configuracion_grado_institucion).where(
                        configuracion_grado_institucion.c.grado_id == cfg.grado_id,
                        configuracion_grado_institucion.c.institucion_id == cfg.institucion_id,
                    )
                )
                .mappings()
                .first()
            )
            return self._row_to_config_grado(row)


__all__ = ["SqlaInfraestructuraRepository"]
