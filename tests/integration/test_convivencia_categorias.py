"""
Tests de integración — Categorías de observación (convivencia_09).

Usa sqlite3 en memoria + create_schema + seed_base para garantizar
aislamiento total. El repo recibe la conexión explícitamente.
"""
from __future__ import annotations

import sqlite3

import pytest

from src.domain.models.convivencia import CategoriaObservacion
from src.infrastructure.db.repositories.sqlite_convivencia_repo import (
    SqliteConvivenciaRepository,
)
from src.infrastructure.db.schema import create_schema
from src.infrastructure.db.seed import _fast_hasher, seed_base

# ---------------------------------------------------------------------------
# Fixture local — BD en memoria con schema + seed_base
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_cat():
    """Conexión en memoria con schema y seed_base aplicados."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    create_schema(conn)
    seed_base(conn, anio=2025, hasher=_fast_hasher)
    conn.commit()
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_listar_categorias_activas_incluye_seed(db_cat):
    """Después del seed_base deben existir al menos 7 categorías activas."""
    repo = SqliteConvivenciaRepository(conn=db_cat)
    cats = repo.listar_categorias(solo_activas=True)
    assert len(cats) >= 7, f"Se esperaban >=7 categorías, hay {len(cats)}"
    nombres = {c.nombre for c in cats}
    assert "Académico" in nombres
    assert "Convivencia y normas" in nombres
    assert "Comportamiento positivo" in nombres


def test_guardar_y_leer_categoria(db_cat):
    """Crear una categoría nueva y recuperarla por id."""
    repo = SqliteConvivenciaRepository(conn=db_cat)
    nueva = CategoriaObservacion(nombre="Prueba nueva", es_comportamental=False)
    guardada = repo.guardar_categoria(nueva)

    assert guardada.id is not None
    leida = repo.get_categoria(guardada.id)
    assert leida is not None
    assert leida.nombre == "Prueba nueva"
    assert leida.es_comportamental is False
    assert leida.activa is True


def test_actualizar_categoria_desactivar(db_cat):
    """Desactivar una categoría; listar(solo_activas=True) ya no la incluye."""
    repo = SqliteConvivenciaRepository(conn=db_cat)

    # Crear una categoría activa
    cat = repo.guardar_categoria(
        CategoriaObservacion(nombre="Para desactivar", es_comportamental=True)
    )
    db_cat.commit()

    # Verificar que aparece en el listado activo
    nombres_antes = {c.nombre for c in repo.listar_categorias(solo_activas=True)}
    assert "Para desactivar" in nombres_antes

    # Desactivar
    desactivada = cat.model_copy(update={"activa": False})
    repo.actualizar_categoria(desactivada)
    db_cat.commit()

    # Ya no debe aparecer en el listado activo
    nombres_despues = {c.nombre for c in repo.listar_categorias(solo_activas=True)}
    assert "Para desactivar" not in nombres_despues

    # Pero sí aparece si pedimos todas
    todas = {c.nombre for c in repo.listar_categorias(solo_activas=False)}
    assert "Para desactivar" in todas


def test_get_categoria_inexistente(db_cat):
    """get_categoria con id inexistente retorna None."""
    repo = SqliteConvivenciaRepository(conn=db_cat)
    resultado = repo.get_categoria(99999)
    assert resultado is None


def test_listar_plantillas_por_categoria(db_cat):
    """Filtrar plantillas por categoria_id retorna solo las de esa categoría."""
    repo = SqliteConvivenciaRepository(conn=db_cat)

    # Obtener IDs de dos categorías sembradas
    cats = repo.listar_categorias(solo_activas=True)
    assert len(cats) >= 2, "Se necesitan al menos 2 categorías del seed"
    cat_a = cats[0]
    cat_b = cats[1]

    # Verificar que el seed insertó plantillas (convivencia_12)
    todas = repo.listar_plantillas(solo_activas=True)
    assert len(todas) >= 1, "seed_base debe haber insertado plantillas"

    # Filtrar por cat_a: solo deben aparecer plantillas de esa categoría
    de_cat_a = repo.listar_plantillas(categoria_id=cat_a.id, solo_activas=True)
    for p in de_cat_a:
        assert p.categoria_id == cat_a.id

    # Filtrar por cat_b: solo deben aparecer plantillas de esa categoría
    de_cat_b = repo.listar_plantillas(categoria_id=cat_b.id, solo_activas=True)
    for p in de_cat_b:
        assert p.categoria_id == cat_b.id

    # Los conjuntos no deben solaparse (si ambas tienen plantillas)
    ids_a = {p.id for p in de_cat_a}
    ids_b = {p.id for p in de_cat_b}
    assert ids_a.isdisjoint(ids_b), "Plantillas de distintas categorías no deben solaparse"


def test_registrar_observacion_desde_plantilla_incrementa_uso(db_cat):
    """Usar una plantilla debe incrementar su uso_count en 1."""
    from src.domain.models.convivencia import NuevaObservacionDTO
    from src.services.convivencia_service import ConvivenciaService

    repo = SqliteConvivenciaRepository(conn=db_cat)

    # Obtener la primera plantilla activa del seed
    plantillas = repo.listar_plantillas(solo_activas=True)
    assert len(plantillas) >= 1, "seed_base debe haber insertado plantillas"
    plantilla = plantillas[0]
    uso_inicial = plantilla.uso_count

    # Crear los registros mínimos necesarios (grupo, asignatura, estudiante, periodo, asignacion)
    anio_id = db_cat.execute("SELECT id FROM configuracion_anio LIMIT 1").fetchone()["id"]
    grupo_id = db_cat.execute(
        "INSERT INTO grupos (codigo, institucion_id) VALUES ('TPLT-01', 1)"
    ).lastrowid
    asig_sub_id = db_cat.execute(
        "INSERT INTO asignaturas (nombre, horas_semanales, institucion_id) VALUES ('Prueba PLT', 1, 1)"
    ).lastrowid
    est_id = db_cat.execute(
        "INSERT INTO estudiantes (tipo_documento, numero_documento, nombre, apellido, "
        "grupo_id, fecha_ingreso, institucion_id) "
        "VALUES ('TI', '99999999', 'Est', 'Plantilla', ?, CURRENT_DATE, 1)",
        (grupo_id,),
    ).lastrowid
    periodo_id = db_cat.execute(
        "INSERT INTO periodos (anio_id, nombre, numero, peso_porcentual) "
        "VALUES (?, 'Periodo PLT', 1, 25.0)",
        (anio_id,),
    ).lastrowid
    from src.infrastructure.db.seed import _fast_hasher
    pwd = _fast_hasher("test")
    usuario_id = db_cat.execute(
        "INSERT INTO usuarios (usuario, password_hash, nombre_completo, rol, institucion_id) "
        "VALUES ('docente_plt', ?, 'Docente PLT', 'profesor', 1)",
        (pwd,),
    ).lastrowid
    asignacion_id = db_cat.execute(
        "INSERT INTO asignaciones (grupo_id, asignatura_id, usuario_id, periodo_id) "
        "VALUES (?, ?, ?, ?)",
        (grupo_id, asig_sub_id, usuario_id, periodo_id),
    ).lastrowid
    db_cat.commit()

    # Usar la plantilla via el servicio
    svc = ConvivenciaService(repo=repo)
    dto = NuevaObservacionDTO(
        estudiante_id=est_id,
        asignacion_id=asignacion_id,
        periodo_id=periodo_id,
        texto=plantilla.texto,
        categoria_id=plantilla.categoria_id or repo.listar_categorias()[0].id,
        es_publica=True,
    )
    obs = svc.registrar_observacion_desde_plantilla(dto, plantilla.id)
    db_cat.commit()

    # Verificar que la observación se guardó con origen="plantilla"
    assert obs.id is not None
    assert obs.origen == "plantilla"

    # Verificar que uso_count se incrementó
    plantilla_actualizada = repo.get_plantilla(plantilla.id)
    assert plantilla_actualizada is not None
    assert plantilla_actualizada.uso_count == uso_inicial + 1


def test_guardar_observacion_con_categoria(db_cat):
    """Crear una observación con categoria_id y verificar que se guarda y recupera."""
    from src.domain.models.convivencia import ObservacionPeriodo

    repo = SqliteConvivenciaRepository(conn=db_cat)

    # Usar la primera categoría activa sembrada
    cats = repo.listar_categorias(solo_activas=True)
    assert len(cats) > 0, "Se esperaban categorías en el seed"
    categoria_id = cats[0].id

    # seed_base no crea grupos/estudiantes/asignaciones: los creamos en línea
    # para no depender de seed_dev. Usamos IDs ficticios sin FK real (las FK a
    # estudiantes / asignaciones / periodos son ON DELETE CASCADE, no NOT NULL
    # con CHECK; SQLite en modo WAL no los valida si la tabla padre está vacía).
    # En su lugar, creamos registros mínimos en cadena.
    anio_id = db_cat.execute("SELECT id FROM configuracion_anio LIMIT 1").fetchone()["id"]

    # Grupo mínimo (sin sala, sin director)
    grupo_id = db_cat.execute(
        "INSERT INTO grupos (codigo, institucion_id) VALUES ('TEST-01', 1)"
    ).lastrowid

    # Asignatura mínima
    asig_id_sub = db_cat.execute(
        "INSERT INTO asignaturas (nombre, horas_semanales, institucion_id) VALUES ('Prueba', 1, 1)"
    ).lastrowid

    # Estudiante mínimo
    est_id = db_cat.execute(
        "INSERT INTO estudiantes (tipo_documento, numero_documento, nombre, apellido, "
        "grupo_id, fecha_ingreso, institucion_id) "
        "VALUES ('TI', '12345678', 'Test', 'Estudiante', ?, CURRENT_DATE, 1)",
        (grupo_id,),
    ).lastrowid

    # Crear un periodo de prueba (seed_base no crea periodos en la tabla `periodos`)
    periodo_id = db_cat.execute(
        "INSERT INTO periodos (anio_id, nombre, numero, peso_porcentual) "
        "VALUES (?, 'Periodo 1 Test', 1, 25.0)",
        (anio_id,),
    ).lastrowid

    # Usuario docente mínimo
    from src.infrastructure.db.seed import _fast_hasher
    pwd = _fast_hasher("test123")
    usuario_id = db_cat.execute(
        "INSERT INTO usuarios (usuario, password_hash, nombre_completo, rol, institucion_id) "
        "VALUES ('docente_test', ?, 'Docente Test', 'profesor', 1)",
        (pwd,),
    ).lastrowid

    # Asignación
    asignacion_id = db_cat.execute(
        "INSERT INTO asignaciones (grupo_id, asignatura_id, usuario_id, periodo_id) "
        "VALUES (?, ?, ?, ?)",
        (grupo_id, asig_id_sub, usuario_id, periodo_id),
    ).lastrowid

    db_cat.commit()

    obs = ObservacionPeriodo(
        estudiante_id=est_id,
        asignacion_id=asignacion_id,
        periodo_id=periodo_id,
        texto="Observación de prueba con categoría",
        categoria_id=categoria_id,
        origen="libre",
    )
    guardada = repo.guardar_observacion(obs)
    db_cat.commit()

    assert guardada.id is not None
    assert guardada.categoria_id == categoria_id
    assert guardada.origen == "libre"

    # Recuperar por id y verificar todos los campos nuevos
    recuperada = repo.get_observacion(guardada.id)
    assert recuperada is not None
    assert recuperada.categoria_id == categoria_id
    assert recuperada.origen == "libre"
    assert recuperada.texto == "Observación de prueba con categoría"
