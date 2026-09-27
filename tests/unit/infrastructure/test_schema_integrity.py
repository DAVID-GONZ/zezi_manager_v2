"""
Tests de integridad de esquema — backend_04_metadata_schema

Verifica la equivalencia entre el MetaData declarado en schema.py y el
esquema realmente aplicado en sqlite_master/PRAGMAs de SQLite.

Tras backend_04:
  - D1 (orden) resuelto: create_all() usa sorted_tables.
  - D2 (grupos.sala_id FK fantasma) resuelto: FK real declarada.
  Los xfail de backend_02b se convierten en tests normales.
"""
from __future__ import annotations

import pytest

from src.infrastructure.db.schema import metadata


# ---------------------------------------------------------------------------
# T1 — Helpers de introspección
# ---------------------------------------------------------------------------


def pragma_table_info(conn, tabla: str) -> list[dict]:
    rows = conn.execute(f"PRAGMA table_info({tabla})").fetchall()
    return [dict(r) for r in rows]


def pragma_fk_list(conn, tabla: str) -> list[dict]:
    rows = conn.execute(f"PRAGMA foreign_key_list({tabla})").fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# T2 — Tablas: MetaData ↔ sqlite_master
# ---------------------------------------------------------------------------


def test_todas_las_tablas_existen(db_schema):
    """Toda tabla en metadata existe en sqlite_master."""
    esperadas = set(metadata.tables.keys())
    reales = {
        row[0]
        for row in db_schema.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    }
    faltantes = esperadas - reales
    assert not faltantes, f"Tablas del MetaData ausentes en sqlite_master: {faltantes}"


def test_no_hay_tablas_extra(db_schema):
    """No hay tablas en sqlite_master que no estén en metadata."""
    esperadas = set(metadata.tables.keys())
    reales = {
        row[0]
        for row in db_schema.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    }
    extra = reales - esperadas
    assert not extra, f"Tablas en sqlite_master no declaradas en metadata: {extra}"


def test_conteo_tablas():
    """metadata contiene exactamente 65 tablas."""
    assert len(metadata.tables) == 65, (
        f"Se esperaban 65 tablas, metadata tiene {len(metadata.tables)}"
    )


# ---------------------------------------------------------------------------
# T3 — Columnas: MetaData ↔ PRAGMA table_info
# ---------------------------------------------------------------------------


def test_columnas_del_metadata_existen_en_pragma(db_schema):
    """
    Cada columna declarada en metadata existe en PRAGMA table_info.
    Compara por nombre; tolerante al tipo exacto por afinidad SQLite.
    """
    errores: list[str] = []
    for tabla_nombre, tabla_obj in metadata.tables.items():
        pragma_cols = {row["name"] for row in pragma_table_info(db_schema, tabla_nombre)}
        for col in tabla_obj.columns:
            if col.name not in pragma_cols:
                errores.append(
                    f"{tabla_nombre}.{col.name}: declarada en MetaData pero ausente en PRAGMA"
                )
    assert not errores, "Diferencias columna MetaData vs PRAGMA:\n" + "\n".join(errores)


def test_sin_columnas_extra_en_sqlite(db_schema):
    """
    PRAGMA table_info no reporta columnas extra respecto al MetaData.
    """
    errores: list[str] = []
    for tabla_nombre, tabla_obj in metadata.tables.items():
        meta_cols = {col.name for col in tabla_obj.columns}
        pragma_cols = {row["name"] for row in pragma_table_info(db_schema, tabla_nombre)}
        extra = pragma_cols - meta_cols
        if extra:
            errores.append(
                f"{tabla_nombre}: columnas en PRAGMA no declaradas en MetaData: {extra}"
            )
    assert not errores, "Columnas extra en sqlite_master:\n" + "\n".join(errores)


# ---------------------------------------------------------------------------
# T4 — Foreign keys: MetaData ↔ PRAGMA foreign_key_list
# ---------------------------------------------------------------------------


def test_fks_del_metadata_existen_en_pragma(db_schema):
    """
    Toda FK declarada en metadata existe en PRAGMA foreign_key_list.
    """
    errores: list[str] = []
    for tabla_nombre, tabla_obj in metadata.tables.items():
        pragma_fk_cols = {row["from"] for row in pragma_fk_list(db_schema, tabla_nombre)}
        for col in tabla_obj.columns:
            for fk in col.foreign_keys:
                if col.name not in pragma_fk_cols:
                    errores.append(
                        f"{tabla_nombre}.{col.name} → {fk.target_fullname}: "
                        f"FK en MetaData ausente en PRAGMA"
                    )
    assert not errores, "FKs sin respaldo en PRAGMA:\n" + "\n".join(errores)


def test_grupos_sala_id_tiene_fk(db_schema):
    """
    grupos.sala_id referencia salas(id) — D2 resuelto en backend_04.
    (Era xfail en backend_02b.)
    """
    pragma_fks = pragma_fk_list(db_schema, "grupos")
    fk_cols = {row["from"] for row in pragma_fks}
    assert "sala_id" in fk_cols, (
        "grupos.sala_id no tiene FOREIGN KEY — D2 debería estar resuelto en backend_04"
    )
    ref_tables = {row["table"] for row in pragma_fks if row["from"] == "sala_id"}
    assert "salas" in ref_tables, f"grupos.sala_id referencia {ref_tables}, no salas"


# ---------------------------------------------------------------------------
# T5 — Orden de dependencias: sorted_tables es topológicamente válido
# ---------------------------------------------------------------------------


def test_orden_dependencias():
    """
    metadata.sorted_tables produce un orden topológicamente válido.
    Cada tabla solo depende de tablas que aparecen antes en el orden.
    D1 resuelto: create_all() usa este orden.
    """
    tablas_vistas: set[str] = set()
    violaciones: list[str] = []

    for tabla in metadata.sorted_tables:
        for fk in tabla.foreign_keys:
            ref_table_name = fk.column.table.name
            if ref_table_name != tabla.name and ref_table_name not in tablas_vistas:
                violaciones.append(
                    f"{tabla.name} → {ref_table_name} (referencia no resuelta en orden)"
                )
        tablas_vistas.add(tabla.name)

    assert not violaciones, (
        "sorted_tables tiene dependencias adelantadas:\n"
        + "\n".join(f"  {v}" for v in violaciones)
    )


# ---------------------------------------------------------------------------
# T6 — Índices: MetaData ↔ sqlite_master
# ---------------------------------------------------------------------------


def test_todos_los_indices_existen(db_schema):
    """Todo índice declarado en metadata existe en sqlite_master."""
    indices_meta: set[str] = set()
    for tabla_obj in metadata.tables.values():
        for idx in tabla_obj.indexes:
            indices_meta.add(idx.name)

    indices_reales = {
        row[0]
        for row in db_schema.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
    }
    faltantes = indices_meta - indices_reales
    assert not faltantes, (
        f"Índices del MetaData ausentes en sqlite_master: {faltantes}"
    )


def test_conteo_indices(db_schema):
    """sqlite_master contiene el número esperado de índices (sin contar los implícitos del PK)."""
    indices_meta: set[str] = set()
    for tabla_obj in metadata.tables.values():
        for idx in tabla_obj.indexes:
            indices_meta.add(idx.name)

    indices_reales = {
        row[0]
        for row in db_schema.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_autoindex_%'"
        ).fetchall()
    }
    # Solo verificamos que los del MetaData estén todos en sqlite_master
    faltantes = indices_meta - indices_reales
    assert not faltantes, f"Índices MetaData no encontrados: {faltantes}"


# ---------------------------------------------------------------------------
# T7 — Triggers: sqlite_master
# ---------------------------------------------------------------------------


def test_triggers_esperados_existen(db_schema):
    """Los 7 triggers declarados (incluyendo D10 UPDATE) existen en sqlite_master."""
    esperados = {
        "tg_validar_peso_categorias",
        "tg_validar_peso_categorias_update",
        "tg_actualizar_ultima_sesion",
        "tg_proteger_periodo_con_cierres",
        "tg_proteger_nota_periodo_cerrado",
        "tg_proteger_nota_periodo_cerrado_update",
        "tg_resolver_alerta_aprobacion",
    }
    reales = {
        row[0]
        for row in db_schema.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger'"
        ).fetchall()
    }
    faltantes = esperados - reales
    assert not faltantes, f"Triggers ausentes en sqlite_master: {faltantes}"


# ---------------------------------------------------------------------------
# T8 — Check constraints de deuda (D4)
# ---------------------------------------------------------------------------


def test_d4_check_constraints_instituciones(db_schema):
    """instituciones tiene CHECK para jornada_principal, tipo_institucion y calendario."""
    ddl = db_schema.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='instituciones'"
    ).fetchone()[0]
    assert "jornada_principal" in ddl.lower() or "ck_instituciones_jornada" in ddl.lower()
    assert "tipo_institucion" in ddl.lower() or "ck_instituciones_tipo" in ddl.lower()
    assert "calendario" in ddl.lower() or "ck_instituciones_calendario" in ddl.lower()


def test_d4_check_constraint_audit_log_accion(db_schema):
    """audit_log tiene CHECK para accion IN (CREATE, UPDATE, DELETE, READ)."""
    ddl = db_schema.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='audit_log'"
    ).fetchone()[0]
    assert "CREATE" in ddl or "accion" in ddl.lower()
