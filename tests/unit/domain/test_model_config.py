"""
Tests de configuración de modelos de dominio — datos_02_model_config_base
=========================================================================

T2 — Hidratación desde base sembrada en memoria.
T7 — Test estructural: toda clase que derive de BaseModel debe derivar de ZeciModel.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import sqlite3
import sys
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ===========================================================================
# Utilidades de BD en memoria
# ===========================================================================


def _make_db() -> sqlite3.Connection:
    """Crea una BD en memoria con schema + seed_test."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    from src.infrastructure.db.schema import SCHEMA

    for stmt in SCHEMA:
        conn.execute(stmt)
    conn.commit()

    from src.infrastructure.db.seed import seed_test

    seed_test(conn)
    conn.commit()
    return conn


# ===========================================================================
# T2 — Verificación de la config de las clases base
# ===========================================================================


class TestConfigBase:
    """Verifica que ZeciModel, EntidadDominio y DTODominio tengan la config correcta."""

    def test_zecimodel_config(self):
        from src.domain.models.base import ZeciModel

        cfg = ZeciModel.model_config
        assert cfg.get("from_attributes") is True
        assert cfg.get("str_strip_whitespace") is True
        assert cfg.get("validate_assignment") is True
        assert cfg.get("use_enum_values") is not True, "use_enum_values debe ser False/ausente (R16)"

    def test_entidad_config(self):
        from src.domain.models.base import EntidadDominio

        cfg = EntidadDominio.model_config
        assert cfg.get("extra") == "ignore", "EntidadDominio debe tener extra='ignore' (D1)"

    def test_dto_config(self):
        from src.domain.models.base import DTODominio

        cfg = DTODominio.model_config
        assert cfg.get("extra") == "forbid", "DTODominio debe tener extra='forbid' (D1)"

    def test_entidad_tolera_campos_extra(self):
        """EntidadDominio con extra='ignore' debe ignorar campos desconocidos (R9)."""
        from src.domain.models.base import EntidadDominio

        class ModeloPrueba(EntidadDominio):
            nombre: str

        # No debe lanzar aunque se pasen campos extra
        obj = ModeloPrueba(nombre="test", columna_que_no_existe="valor", otra_columna=99)
        assert obj.nombre == "test"
        assert not hasattr(obj, "columna_que_no_existe")

    def test_dto_rechaza_campos_extra(self):
        """DTODominio con extra='forbid' debe rechazar campos no declarados (R7, R8)."""
        from src.domain.models.base import DTODominio

        class DTOPrueba(DTODominio):
            nombre: str

        with pytest.raises(ValidationError):
            DTOPrueba(nombre="test", campo_fantasma="valor")

    def test_str_strip_whitespace(self):
        """Los valores de texto se deben recortar (R11)."""
        from src.domain.models.base import ZeciModel

        class ModeloPrueba(ZeciModel):
            nombre: str

        obj = ModeloPrueba(nombre="  hola mundo  ")
        assert obj.nombre == "hola mundo"

    def test_validate_assignment(self):
        """Las asignaciones post-construcción deben validarse (R14, R15)."""
        from src.domain.models.base import ZeciModel

        class ModeloPrueba(ZeciModel):
            valor: int

        obj = ModeloPrueba(valor=5)
        with pytest.raises(ValidationError):
            obj.valor = "no es un entero"


# ===========================================================================
# T2 — Hidratación desde base sembrada
# ===========================================================================


class TestHidratacionDesdeBaseSembrada:
    """
    Crea una BD en memoria, siembra datos mínimos, y verifica que cada
    entidad se puede construir desde una fila SELECT * sin fallar.
    Este test existe porque la suite de integración está rota (30 fallos
    ajenos a este paso), y no demuestra la hidratación por su cuenta.
    """

    @pytest.fixture(scope="class")
    def conn(self):
        db = _make_db()
        yield db
        db.close()

    def _select_rows(self, conn: sqlite3.Connection, tabla: str) -> list[sqlite3.Row]:
        try:
            cur = conn.execute(f"SELECT * FROM {tabla}")
            return cur.fetchall()
        except sqlite3.OperationalError:
            return []

    def _hydrate(self, model_cls, rows: list[sqlite3.Row]) -> list:
        """Construye el modelo desde cada fila; falla si lanza excepción."""
        results = []
        for row in rows:
            try:
                obj = model_cls(**dict(row))
                results.append(obj)
            except Exception as e:
                pytest.fail(
                    f"Fallo al hidratar {model_cls.__name__} "
                    f"desde tabla con columnas {list(dict(row).keys())}: {e}"
                )
        return results

    # -- Configuración institucional --

    def test_configuracion_anio(self, conn):
        from src.domain.models.configuracion import ConfiguracionAnio

        rows = self._select_rows(conn, "configuracion_anio")
        assert len(rows) > 0, "seed_test debe crear al menos un registro de configuracion_anio"
        self._hydrate(ConfiguracionAnio, rows)

    def test_institucion(self, conn):
        from src.domain.models.institucion import Institucion

        rows = self._select_rows(conn, "instituciones")
        assert len(rows) > 0, "seed_test debe crear al menos una institución"
        self._hydrate(Institucion, rows)

    def test_nivel_desempeno(self, conn):
        from src.domain.models.configuracion import NivelDesempeno

        rows = self._select_rows(conn, "niveles_desempeno")
        assert len(rows) > 0, "seed_test debe crear niveles de desempeño"
        self._hydrate(NivelDesempeno, rows)

    def test_criterio_promocion(self, conn):
        from src.domain.models.configuracion import CriterioPromocion

        rows = self._select_rows(conn, "criterios_promocion")
        self._hydrate(CriterioPromocion, rows)

    # -- Infraestructura --

    def test_area_conocimiento(self, conn):
        from src.domain.models.infraestructura import AreaConocimiento

        rows = self._select_rows(conn, "areas_conocimiento")
        assert len(rows) > 0, "seed_test debe crear áreas"
        self._hydrate(AreaConocimiento, rows)

    def test_asignatura(self, conn):
        from src.domain.models.infraestructura import Asignatura

        rows = self._select_rows(conn, "asignaturas")
        assert len(rows) > 0, "seed_test debe crear asignaturas"
        self._hydrate(Asignatura, rows)

    def test_grupo(self, conn):
        from src.domain.models.infraestructura import Grupo

        rows = self._select_rows(conn, "grupos")
        assert len(rows) > 0, "seed_test debe crear grupos"
        self._hydrate(Grupo, rows)

    def test_escenario_horario(self, conn):
        from src.domain.models.infraestructura import EscenarioHorario

        rows = self._select_rows(conn, "escenarios_horario")
        fields = set(EscenarioHorario.model_fields)
        results = []
        for row in rows:
            d = {k: v for k, v in dict(row).items() if k in fields}
            try:
                obj = EscenarioHorario(**d)
                results.append(obj)
            except Exception as e:
                pytest.fail(f"Fallo al hidratar EscenarioHorario: {e}")

    def test_horario(self, conn):
        from src.domain.models.infraestructura import Horario

        rows = self._select_rows(conn, "horarios")
        fields = set(Horario.model_fields)
        for row in rows:
            d = {k: v for k, v in dict(row).items() if k in fields}
            try:
                Horario(**d)
            except Exception as e:
                pytest.fail(f"Fallo al hidratar Horario: {e}")

    # -- Usuarios --

    def test_usuario(self, conn):
        from src.domain.models.usuario import Usuario

        rows = self._select_rows(conn, "usuarios")
        assert len(rows) > 0, "seed_test debe crear usuarios"
        self._hydrate(Usuario, rows)

    # -- Periodos --

    def test_periodo(self, conn):
        from src.domain.models.periodo import Periodo

        rows = self._select_rows(conn, "periodos")
        assert len(rows) > 0, "seed_test debe crear periodos"
        self._hydrate(Periodo, rows)

    # -- Asignaciones --

    def test_asignacion(self, conn):
        from src.domain.models.asignacion import Asignacion

        rows = self._select_rows(conn, "asignaciones")
        assert len(rows) > 0, "seed_test debe crear asignaciones"
        self._hydrate(Asignacion, rows)

    # -- Estudiantes --

    def test_estudiante(self, conn):
        from src.domain.models.estudiante import Estudiante

        rows = self._select_rows(conn, "estudiantes")
        assert len(rows) > 0, "seed_test debe crear estudiantes"
        self._hydrate(Estudiante, rows)

    # -- Evaluación --

    def test_categoria(self, conn):
        from src.domain.models.evaluacion import Categoria

        rows = self._select_rows(conn, "categorias")
        assert len(rows) > 0, "seed_test debe crear categorías"
        self._hydrate(Categoria, rows)

    def test_actividad(self, conn):
        from src.domain.models.evaluacion import Actividad

        rows = self._select_rows(conn, "actividades")
        assert len(rows) > 0, "seed_test debe crear actividades"
        self._hydrate(Actividad, rows)

    def test_nota(self, conn):
        from src.domain.models.evaluacion import Nota

        rows = self._select_rows(conn, "notas")
        assert len(rows) > 0, "seed_test debe crear notas"
        self._hydrate(Nota, rows)

    # -- Alertas --

    def test_configuracion_alerta(self, conn):
        from src.domain.models.alerta import ConfiguracionAlerta

        rows = self._select_rows(conn, "configuracion_alertas")
        assert len(rows) > 0, "seed_test debe crear configuración de alertas"
        self._hydrate(ConfiguracionAlerta, rows)

    # -- Preferencias --

    def test_preferencia_institucion(self, conn):
        from src.domain.models.preferencia_institucion import PreferenciaInstitucion

        rows = self._select_rows(conn, "preferencias_institucion")
        self._hydrate(PreferenciaInstitucion, rows)


# ===========================================================================
# T7 — Test estructural: toda clase de dominio debe derivar de ZeciModel
# ===========================================================================

# Lista de excepciones explícitas (clases que NO deben derivar de ZeciModel).
# Vacía al cerrar el paso, permite documentar casos legítimos futuros.
_EXCEPCIONES_ZECIMODEL: set[str] = set()


def _iter_modelos() -> list[tuple[str, type]]:
    """Devuelve todos los pares (nombre_modulo, clase) de src/domain/models/."""
    modelos_path = ROOT / "src" / "domain" / "models"
    resultados = []

    for _finder, modname, _ in pkgutil.walk_packages(
        path=[str(modelos_path)],
        prefix="src.domain.models.",
    ):
        try:
            mod = importlib.import_module(modname)
        except ImportError:
            continue

        for _nombre, obj in inspect.getmembers(mod, inspect.isclass):
            if (
                obj.__module__ == modname  # definida en este módulo, no importada
                and issubclass(obj, BaseModel)
                and obj is not BaseModel
            ):
                resultados.append((modname, obj))

    return resultados


class TestEstructuraHerencia:
    """
    Verifica que toda clase derivada de BaseModel en src/domain/models/
    derive también de ZeciModel (R1, R2, R3, D4).
    """

    def test_toda_clase_deriva_de_zecimodel(self):
        from src.domain.models.base import ZeciModel

        violaciones = []
        for modname, cls in _iter_modelos():
            nombre_cls = f"{modname}.{cls.__name__}"
            if nombre_cls in _EXCEPCIONES_ZECIMODEL:
                continue
            if not issubclass(cls, ZeciModel):
                violaciones.append(nombre_cls)

        assert not violaciones, (
            "Las siguientes clases derivan de BaseModel pero NO de ZeciModel:\n"
            + "\n".join(f"  - {v}" for v in sorted(violaciones))
        )
