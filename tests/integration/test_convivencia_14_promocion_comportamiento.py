"""
Tests de integración — Promoción a comportamiento (convivencia_14).

Verifica que promover_a_comportamiento:
  - Persiste el RegistroComportamiento en la BD.
  - Guarda la FK registro_comportamiento_id en observaciones_periodo.
  - La FK ON DELETE SET NULL funciona (integridad referencial).

Usa sqlite3 en memoria + create_schema + seed_base.
"""
from __future__ import annotations

import sqlite3
from datetime import date

import pytest

from src.domain.models.convivencia import (
    CategoriaObservacion,
    ObservacionPeriodo,
)
from src.infrastructure.db.repositories.sqlite_convivencia_repo import (
    SqliteConvivenciaRepository,
)
from src.infrastructure.db.schema import create_schema
from src.infrastructure.db.seed import seed_base, _fast_hasher
from src.services.convivencia_service import ConvivenciaService


class _FakeAsigSvc:
    """Stub mínimo de AsignacionService para resolver grupo_id en los tests."""
    def __init__(self, grupo_id: int):
        self._grupo_id = grupo_id

    def get_by_id(self, asig_id: int):
        class _A:
            pass
        a = _A()
        a.id = asig_id
        a.grupo_id = self._grupo_id
        return a


# ---------------------------------------------------------------------------
# Fixture — BD en memoria con schema + seed_base + fixtures de convivencia
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_conv14():
    """Conexión en memoria con schema, seed y datos mínimos de convivencia."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    create_schema(conn)
    seed_base(conn, anio=2025, hasher=_fast_hasher)

    # Institución ya sembrada por seed_base (_seed_institucion)
    # Grupo mínimo (para FK de RegistroComportamiento.grupo_id)
    conn.execute(
        "INSERT INTO grupos (codigo, nombre, grado, jornada, institucion_id) "
        "VALUES ('10A', 'Décimo A', 10, 'UNICA', 1)"
    )
    grupo_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Estudiante mínimo
    conn.execute(
        "INSERT INTO estudiantes "
        "(tipo_documento, numero_documento, nombre, apellido, grupo_id, institucion_id) "
        "VALUES ('TI', '123456', 'Juan', 'Pérez', ?, 1)",
        (grupo_id,),
    )
    est_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Asignatura y asignación mínimas (para FK de observaciones_periodo.asignacion_id)
    conn.execute("INSERT INTO asignaturas (nombre, horas_semanales, institucion_id) VALUES ('Ciencias', 4, 1)")
    asig_id_asignatura = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Periodo manual (seed_base no crea periodos)
    anio_row = conn.execute("SELECT id FROM configuracion_anio LIMIT 1").fetchone()
    assert anio_row is not None, "seed_base debe sembrar configuracion_anio"
    anio_id = anio_row[0]
    conn.execute(
        "INSERT INTO periodos (anio_id, nombre, numero, peso_porcentual, activo) "
        "VALUES (?, 'Periodo 1', 1, 25.0, 1)",
        (anio_id,),
    )
    periodo_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Usuario (director) — ya sembrado por seed_base; lo buscamos
    user_row = conn.execute("SELECT id FROM usuarios WHERE rol = 'director' LIMIT 1").fetchone()
    usuario_id = user_row[0] if user_row else None

    conn.execute(
        "INSERT INTO asignaciones (grupo_id, asignatura_id, usuario_id, periodo_id) "
        "VALUES (?, ?, ?, ?)",
        (grupo_id, asig_id_asignatura, usuario_id or 1, periodo_id),
    )
    asignacion_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    conn.commit()

    yield conn, {
        "grupo_id":      grupo_id,
        "est_id":        est_id,
        "asignacion_id": asignacion_id,
        "periodo_id":    periodo_id,
        "usuario_id":    usuario_id,
    }
    conn.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_promover_a_comportamiento_guarda_fk(db_conv14):
    """
    Después de promover, observaciones_periodo.registro_comportamiento_id
    debe referenciar el registro creado en registro_comportamiento.
    """
    conn, ids = db_conv14

    repo = SqliteConvivenciaRepository(conn=conn)
    # Proveemos un asignacion_svc_provider que resuelve el grupo_id del fixture
    svc = ConvivenciaService(
        repo=repo,
        asignacion_svc_provider=lambda: _FakeAsigSvc(ids["grupo_id"]),
    )

    # Usar una categoría comportamental existente del seed
    cats = repo.listar_categorias(solo_activas=True)
    cat_comp = next((c for c in cats if c.es_comportamental), None)
    assert cat_comp is not None, "seed_base debe sembrar al menos una categoría comportamental"

    # Crear observación con esa categoría
    obs = repo.guardar_observacion(
        ObservacionPeriodo(
            estudiante_id=ids["est_id"],
            asignacion_id=ids["asignacion_id"],
            periodo_id=ids["periodo_id"],
            texto="Agredió verbalmente a un compañero",
            es_publica=True,
            categoria_id=cat_comp.id,
        )
    )
    conn.commit()

    # Aún no promovida
    assert obs.registro_comportamiento_id is None

    # Promover
    registro = svc.promover_a_comportamiento(
        obs.id,
        usuario_id=ids["usuario_id"],
        usuario_rol="director",
    )
    conn.commit()

    # El registro debe existir en BD
    assert registro.id is not None
    row_reg = conn.execute(
        "SELECT id FROM registro_comportamiento WHERE id = ?", (registro.id,)
    ).fetchone()
    assert row_reg is not None, "El registro_comportamiento debe existir en BD"

    # La FK en observaciones_periodo debe apuntar al registro
    row_obs = conn.execute(
        "SELECT registro_comportamiento_id FROM observaciones_periodo WHERE id = ?",
        (obs.id,),
    ).fetchone()
    assert row_obs is not None
    assert row_obs["registro_comportamiento_id"] == registro.id, (
        f"FK esperada={registro.id}, encontrada={row_obs['registro_comportamiento_id']}"
    )

    # Verificar mediante el repo también
    obs_leida = repo.get_observacion(obs.id)
    assert obs_leida.registro_comportamiento_id == registro.id


def test_promover_a_comportamiento_fk_on_delete_set_null(db_conv14):
    """
    Al eliminar el registro_comportamiento, la FK en observaciones_periodo
    debe quedar en NULL (ON DELETE SET NULL).
    """
    conn, ids = db_conv14

    repo = SqliteConvivenciaRepository(conn=conn)
    svc = ConvivenciaService(
        repo=repo,
        asignacion_svc_provider=lambda: _FakeAsigSvc(ids["grupo_id"]),
    )

    # Usar categoría comportamental del seed
    cats = repo.listar_categorias(solo_activas=True)
    cat_comp = next((c for c in cats if c.es_comportamental), None)
    assert cat_comp is not None

    obs = repo.guardar_observacion(
        ObservacionPeriodo(
            estudiante_id=ids["est_id"],
            asignacion_id=ids["asignacion_id"],
            periodo_id=ids["periodo_id"],
            texto="No respetó las normas del aula",
            es_publica=True,
            categoria_id=cat_comp.id,
        )
    )
    conn.commit()

    registro = svc.promover_a_comportamiento(
        obs.id,
        usuario_id=ids["usuario_id"],
        usuario_rol="director",
    )
    conn.commit()

    # Eliminar el registro de comportamiento
    conn.execute(
        "DELETE FROM registro_comportamiento WHERE id = ?", (registro.id,)
    )
    conn.commit()

    # La FK en observaciones_periodo debe haber quedado en NULL
    row = conn.execute(
        "SELECT registro_comportamiento_id FROM observaciones_periodo WHERE id = ?",
        (obs.id,),
    ).fetchone()
    assert row is not None
    assert row["registro_comportamiento_id"] is None, (
        "ON DELETE SET NULL debe haber puesto la FK en NULL"
    )


def test_columna_registro_comportamiento_id_existe_en_schema(db_conv14):
    """Verifica que la columna existe en la tabla observaciones_periodo."""
    conn, _ = db_conv14
    cols = [
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(observaciones_periodo)"
        ).fetchall()
    ]
    assert "registro_comportamiento_id" in cols, (
        f"La columna no existe. Columnas encontradas: {cols}"
    )
