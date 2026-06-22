"""
Tests de integración — paso_34 (ajustado en paso_37): 2ª institución en seed_dev.

Cubre que el dataset de desarrollo permite probar el multi-tenant a mano:
  - seed_dev crea DOS instituciones (la #1 por defecto + "Institución de Prueba").
  - Identificadores compuestos compartidos entre tenants conviven gracias a los
    uniques compuestos: mismo codigo de grupo (`601`), mismo numero_documento.
  - El director de la #2 usa un username DISTINTO y global-único
    (`director.prueba`): paso_37 revirtió la unicidad del username a GLOBAL, así
    que ya NO comparte el `director` de la #1 ni hay login ambiguo.
  - Aislamiento: el director de la #2, con su institución fijada en el
    contextvar, solo ve los grupos/estudiantes de la #2 (no los de la #1);
    el admin (sin scope) ve todo.
  - Login simple: el director de la #2 entra por su username distinto, sin
    selector de institución.

Usa el fixture `db_dev` (seed_dev completo, hasher rápido) de conftest.
"""
from __future__ import annotations

from src.domain.models.estudiante import FiltroEstudiantesDTO
from src.infrastructure.auth.bcrypt_auth_service import BcryptAuthService
from src.infrastructure.db.repositories.sqlite_estudiante_repo import (
    SqliteEstudianteRepository,
)
from src.infrastructure.db.repositories.sqlite_infraestructura_repo import (
    SqliteInfraestructuraRepository,
)
from src.infrastructure.db.repositories.sqlite_usuario_repo import (
    SqliteUsuarioRepository,
)
from src.infrastructure.db.seed import _fast_hasher
from src.services.contexto_tenant import usar_institucion
from src.services.estudiante_service import EstudianteService
from src.services.infraestructura_service import InfraestructuraService


def _ids_dos_instituciones(conn) -> tuple[int, int]:
    filas = conn.execute(
        "SELECT id FROM instituciones ORDER BY id"
    ).fetchall()
    assert len(filas) == 2, "seed_dev debe crear exactamente 2 instituciones"
    return int(filas[0][0]), int(filas[1][0])


# =============================================================================
# seed_dev crea 2 instituciones con identificadores compartidos
# =============================================================================

class TestSeedDevDosInstituciones:

    def test_crea_dos_instituciones(self, db_dev):
        conn, _ = db_dev
        nombres = [
            r[0] for r in conn.execute(
                "SELECT nombre FROM instituciones ORDER BY id"
            ).fetchall()
        ]
        assert len(nombres) == 2
        assert "Institución de Prueba" in nombres

    def test_director_inst2_username_distinto_y_global_unico(self, db_dev):
        """paso_37: el director de la #2 usa `director.prueba`, no `director`."""
        conn, _ = db_dev
        inst1, inst2 = _ids_dos_instituciones(conn)
        # El `director` plano pertenece SOLO a la #1.
        rows_director = conn.execute(
            "SELECT institucion_id FROM usuarios WHERE usuario='director'"
        ).fetchall()
        assert {r[0] for r in rows_director} == {inst1}
        # El director de la #2 tiene un username distinto.
        rows_prueba = conn.execute(
            "SELECT institucion_id FROM usuarios WHERE usuario='director.prueba'"
        ).fetchall()
        assert {r[0] for r in rows_prueba} == {inst2}
        # Unicidad global: ningún username se repite.
        dups = conn.execute(
            "SELECT usuario, COUNT(*) c FROM usuarios GROUP BY usuario HAVING c > 1"
        ).fetchall()
        assert not dups

    def test_codigo_grupo_601_compartido(self, db_dev):
        conn, _ = db_dev
        inst1, inst2 = _ids_dos_instituciones(conn)
        rows = conn.execute(
            "SELECT institucion_id FROM grupos WHERE codigo='601'"
        ).fetchall()
        assert {r[0] for r in rows} == {inst1, inst2}

    def test_numero_documento_compartido(self, db_dev):
        conn, _ = db_dev
        duplicados = conn.execute(
            "SELECT numero_documento, COUNT(DISTINCT institucion_id) c "
            "FROM estudiantes GROUP BY numero_documento HAVING c > 1"
        ).fetchall()
        assert duplicados, (
            "algún numero_documento debe existir en ambas instituciones "
            "(unicidad compuesta)"
        )

    def test_segunda_institucion_tiene_anio_activo_y_asignatura(self, db_dev):
        conn, _ = db_dev
        _, inst2 = _ids_dos_instituciones(conn)
        anio = conn.execute(
            "SELECT activo FROM configuracion_anio WHERE institucion_id=?",
            (inst2,),
        ).fetchone()
        assert anio is not None and anio[0] == 1
        asig = conn.execute(
            "SELECT codigo FROM asignaturas WHERE institucion_id=?", (inst2,)
        ).fetchall()
        assert any(r[0] == "PRB" for r in asig)


# =============================================================================
# Aislamiento por institución (vía contextvar usar_institucion)
# =============================================================================

class TestAislamientoSegundaInstitucion:

    def test_director_inst2_solo_ve_sus_grupos(self, db_dev):
        conn, _ = db_dev
        _, inst2 = _ids_dos_instituciones(conn)
        svc = InfraestructuraService(SqliteInfraestructuraRepository(conn=conn))

        with usar_institucion(inst2):
            grupos_inst2 = svc.listar_grupos()

        ids_inst2 = {
            r[0] for r in conn.execute(
                "SELECT id FROM grupos WHERE institucion_id=?", (inst2,)
            ).fetchall()
        }
        vistos = {g.id for g in grupos_inst2}
        assert vistos == ids_inst2
        # No se cuela ningún grupo de la #1.
        ids_inst1 = {
            r[0] for r in conn.execute(
                "SELECT id FROM grupos WHERE institucion_id=1"
            ).fetchall()
        }
        assert vistos.isdisjoint(ids_inst1)

    def test_director_inst2_solo_ve_sus_estudiantes(self, db_dev):
        conn, _ = db_dev
        _, inst2 = _ids_dos_instituciones(conn)
        svc = EstudianteService(SqliteEstudianteRepository(conn=conn))

        with usar_institucion(inst2):
            vistos = svc.listar_filtrado(FiltroEstudiantesDTO())
        ids_vistos = {e.id for e in vistos}

        ids_inst2 = {
            r[0] for r in conn.execute(
                "SELECT id FROM estudiantes WHERE institucion_id=?", (inst2,)
            ).fetchall()
        }
        assert ids_vistos == ids_inst2
        ids_inst1 = {
            r[0] for r in conn.execute(
                "SELECT id FROM estudiantes WHERE institucion_id=1"
            ).fetchall()
        }
        assert ids_vistos.isdisjoint(ids_inst1)


# =============================================================================
# Login simple con el director de la 2ª institución
# =============================================================================

class TestLoginSimpleSegundaInstitucion:

    def test_login_director_inst2_por_username_distinto(self, db_dev):
        conn, _ = db_dev
        _, inst2 = _ids_dos_instituciones(conn)
        # El director de la #2 fue sembrado con _fast_hasher y password Prueba2025*.
        repo = SqliteUsuarioRepository(conn=conn)
        auth = BcryptAuthService(repo=repo)
        # Verifica que el hash sembrado corresponde a la contraseña conocida.
        usuario_inst2 = conn.execute(
            "SELECT password_hash FROM usuarios "
            "WHERE usuario='director.prueba' AND institucion_id=?",
            (inst2,),
        ).fetchone()
        assert usuario_inst2[0] == _fast_hasher("Prueba2025*")

        # Login simple: sin selector de institución; la institución viaja en la
        # entidad retornada (un username = una institución).
        user = auth.autenticar_usuario("director.prueba", "Prueba2025*")
        assert user.institucion_id == inst2
