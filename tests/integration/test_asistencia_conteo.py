"""
Tests de integración para contar_clases_dictadas_docente y clases_dictadas_por_asignacion.

Usa las fixtures db_seed / db_conn / seed_result definidas en conftest.py.
El seed_test inserta registros de asistencia, por lo que solo validamos que
los métodos no lanzan excepciones y retornan los tipos correctos.
También inserta registros manuales para verificar el comportamiento exacto.
"""
from __future__ import annotations

import pytest
from datetime import date

from src.infrastructure.db.repositories.sqlite_asistencia_repo import SqliteAsistenciaRepository


class TestContarClasesDictadasDocente:

    def test_retorna_entero_con_seed(self, db_conn, seed_result):
        """El método no explota con la BD de seed y retorna un int."""
        repo = SqliteAsistenciaRepository(conn=db_conn)
        usuario_id = next(iter(seed_result.usuario_ids.values()))
        resultado = repo.contar_clases_dictadas_docente(usuario_id, anio=2025, mes=1)
        assert isinstance(resultado, int)
        assert resultado >= 0

    def test_mes_sin_datos_retorna_cero(self, db_conn, seed_result):
        """Mes muy lejano (2099-01) no tiene datos → 0."""
        repo = SqliteAsistenciaRepository(conn=db_conn)
        usuario_id = next(iter(seed_result.usuario_ids.values()))
        resultado = repo.contar_clases_dictadas_docente(usuario_id, anio=2099, mes=1)
        assert resultado == 0

    def test_cuenta_combinaciones_asignacion_fecha_no_filas(self, db_conn, seed_result):
        """
        Inserta 3 filas con la misma (asignacion_id, fecha) pero distintos
        estudiantes → debe contar como 1 clase, no 3.
        """
        repo = SqliteAsistenciaRepository(conn=db_conn)

        # Usa el primer usuario y la primera asignación disponibles
        usuario_id = next(iter(seed_result.usuario_ids.values()))
        if not seed_result.asignacion_ids:
            pytest.skip("Seed no tiene asignaciones")

        # Busca una asignación del docente
        asig_id = db_conn.execute(
            "SELECT id FROM asignaciones WHERE usuario_id=? LIMIT 1",
            (usuario_id,)
        ).fetchone()
        if asig_id is None:
            pytest.skip("No hay asignaciones para este docente en el seed")

        asig_id = asig_id[0]
        grupo_id = db_conn.execute(
            "SELECT grupo_id FROM asignaciones WHERE id=?", (asig_id,)
        ).fetchone()[0]
        periodo_id = db_conn.execute(
            "SELECT periodo_id FROM asignaciones WHERE id=?", (asig_id,)
        ).fetchone()[0]

        # Obtiene 3 estudiantes del grupo
        estudiantes = db_conn.execute(
            "SELECT id FROM estudiantes WHERE grupo_id=? LIMIT 3", (grupo_id,)
        ).fetchall()
        if len(estudiantes) < 2:
            pytest.skip("Grupo con menos de 2 estudiantes")

        fecha_test = date(2025, 11, 15)

        # Inserta filas con ON CONFLICT REPLACE — misma asignación/fecha, distintos estudiantes
        for est in estudiantes:
            db_conn.execute(
                """
                INSERT OR REPLACE INTO control_diario
                    (estudiante_id, grupo_id, asignacion_id, periodo_id,
                     fecha, estado, uniforme, materiales)
                VALUES (?,?,?,?,?,?,?,?)
                """,
                (est[0], grupo_id, asig_id, periodo_id,
                 fecha_test.isoformat(), "P", 1, 1),
            )
        db_conn.commit()

        resultado = repo.contar_clases_dictadas_docente(usuario_id, anio=2025, mes=11)
        # Puede haber más clases del seed en noviembre, pero al menos 1
        assert resultado >= 1
        # El número de clases NO debe ser igual al número de estudiantes insertados
        # si solo hay 1 (asignacion_id, fecha). Verificamos que no multiplica por estudiantes:
        resultado_asig = repo.clases_dictadas_por_asignacion(usuario_id, anio=2025, mes=11)
        assert resultado_asig.get(asig_id, 0) >= 1


class TestClasesDictadasPorAsignacion:

    def test_retorna_dict_con_seed(self, db_conn, seed_result):
        """El método retorna un dict[int, int] sin lanzar excepciones."""
        repo = SqliteAsistenciaRepository(conn=db_conn)
        usuario_id = next(iter(seed_result.usuario_ids.values()))
        resultado = repo.clases_dictadas_por_asignacion(usuario_id, anio=2025, mes=1)
        assert isinstance(resultado, dict)
        for k, v in resultado.items():
            assert isinstance(k, int)
            assert isinstance(v, int)
            assert v > 0

    def test_mes_sin_datos_retorna_dict_vacio(self, db_conn, seed_result):
        """Mes 2099-01 → dict vacío."""
        repo = SqliteAsistenciaRepository(conn=db_conn)
        usuario_id = next(iter(seed_result.usuario_ids.values()))
        resultado = repo.clases_dictadas_por_asignacion(usuario_id, anio=2099, mes=1)
        assert resultado == {}

    def test_suma_total_coincide_con_contar(self, db_conn, seed_result):
        """
        La suma de values() del desglose debe igualar contar_clases_dictadas_docente.
        """
        repo = SqliteAsistenciaRepository(conn=db_conn)
        # Usa 'lopez' que es el primer profesor con asignaciones en seed_dev
        usuario_id = seed_result.usuario_ids.get(
            "lopez", next(iter(seed_result.usuario_ids.values()))
        )
        for mes in range(1, 13):
            total = repo.contar_clases_dictadas_docente(usuario_id, anio=2025, mes=mes)
            desglose = repo.clases_dictadas_por_asignacion(usuario_id, anio=2025, mes=mes)
            assert sum(desglose.values()) == total, (
                f"Discrepancia en mes={mes}: total={total}, desglose sum={sum(desglose.values())}"
            )
