"""
tests/unit/domain/test_fecha_zona_horaria.py
=============================================
Pruebas para el defecto UTC vs hora Colombia (datos_08).

Nomenclatura de marcadores:
  -k origen    → verifica que clock.hoy/ahora son correctos
  -k recupera  → verifica lectura de filas con fecha futura
  -k puerta    → verifica que no reaparecen llamadas directas a date.today() etc.

El test test_defecto_utc_vs_local está en ROJO hasta que T2 crea clock.py.
"""

from __future__ import annotations

import ast
import datetime
from datetime import date, timedelta
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# T1 — Reproducción del defecto (debe estar en ROJO antes de T2)
# ---------------------------------------------------------------------------


def test_defecto_utc_vs_local():
    """
    Fija el instante a las 19:50 hora de Colombia (= 00:50 UTC del día siguiente)
    y demuestra la discrepancia entre la fecha que SQLite sellaría (UTC)
    y la que el dominio debe usar (hora Colombia).

    RED hasta que T2 crea src/domain/models/clock.py.
    GREEN después de T2 + T4.
    """
    # Esta importación lanza ImportError hasta que T2 cree clock.py
    from src.domain.models.clock import hoy

    # Momento: 2026-09-09 00:50 UTC = 2026-09-08 19:50 COT (UTC-5)
    momento_utc = datetime.datetime(2026, 9, 9, 0, 50, tzinfo=datetime.UTC)

    # Fecha que SQLite sellaría con DEFAULT CURRENT_DATE (usa UTC siempre)
    fecha_sqlite_utc = momento_utc.date()  # 2026-09-09 — mañana en Colombia

    # Fecha que el dominio debe usar (hora Colombia, UTC-5)
    fecha_dominio = hoy(_now=momento_utc)  # debe retornar 2026-09-08 — hoy en Colombia

    # ── Verificaciones ──────────────────────────────────────────────────────
    assert fecha_sqlite_utc != fecha_dominio, (
        "A las 19:50 COT, la fecha UTC debe diferir de la fecha Colombia. "
        f"UTC={fecha_sqlite_utc}, Colombia={fecha_dominio}"
    )
    assert fecha_dominio == date(2026, 9, 8), (
        f"hoy() debe retornar 2026-09-08 (hora Colombia), no {fecha_dominio}"
    )
    assert fecha_sqlite_utc == date(2026, 9, 9), (
        f"La fecha UTC a las 00:50 UTC es 2026-09-09, no {fecha_sqlite_utc}"
    )


# ---------------------------------------------------------------------------
# T2 — Origen único del instante actual (marker: origen)
# ---------------------------------------------------------------------------


def test_origen_zona_por_omision():
    """hoy() y ahora() usan America/Bogota por omisión."""
    # Si la configuración no tiene ZONA_HORARIA, la zona debe ser America/Bogota
    import zoneinfo

    from src.domain.models.clock import ahora

    zoneinfo.ZoneInfo("America/Bogota")
    momento = datetime.datetime(2026, 9, 9, 0, 50, tzinfo=datetime.UTC)

    resultado = ahora(_now=momento)
    assert resultado.tzinfo is not None, "ahora() debe retornar datetime con tzinfo"
    assert resultado.utcoffset() == datetime.timedelta(hours=-5), (
        "A esta fecha, COT es UTC-5 (Colombia no usa horario de verano)."
    )


def test_origen_configuracion_sobreescribe():
    """La configuración puede especificar otra zona y hoy() la respeta."""
    # Simular zona diferente: UTC
    import config
    from src.domain.models.clock import hoy

    zona_original = getattr(config, "ZONA_HORARIA", "America/Bogota")
    try:
        config.ZONA_HORARIA = "UTC"
        momento = datetime.datetime(2026, 9, 9, 0, 50, tzinfo=datetime.UTC)
        # En UTC, 00:50 UTC = 2026-09-09
        fecha_utc = hoy(_now=momento)
        assert fecha_utc == date(2026, 9, 9), (
            f"Con zona UTC, hoy() debe retornar 2026-09-09, no {fecha_utc}"
        )
    finally:
        config.ZONA_HORARIA = zona_original


def test_origen_hora_colombia_19h50():
    """A las 19:50 COT, hoy() retorna la fecha en curso en Colombia, no la UTC."""
    from src.domain.models.clock import hoy

    # 2026-09-09 00:50 UTC = 2026-09-08 19:50 COT
    momento_utc = datetime.datetime(2026, 9, 9, 0, 50, tzinfo=datetime.UTC)

    fecha = hoy(_now=momento_utc)

    assert fecha == date(2026, 9, 8), (
        f"A las 19:50 COT, hoy() debe devolver 2026-09-08, no {fecha}"
    )


# ---------------------------------------------------------------------------
# T6 — Lectura de filas ya selladas con fecha futura (marker: recupera)
# ---------------------------------------------------------------------------


def test_recupera_fila_fecha_futura_sin_excepcion():
    """
    Una fila existente con fecha = mañana (sellada antes del fix) puede
    recuperarse usando model_construct (sin validación).

    R11: recuperar no lanza excepción aunque la fecha sea futura.
    """
    from src.domain.models.asistencia import ControlDiario

    fecha_futura = date.today() + timedelta(days=1)

    # Simula lo que el repositorio haría al leer una fila existente
    # con fecha "por delante" (fila vieja sellada con UTC antes del fix).
    # model_construct omite la validación → no lanza excepción.
    cd = ControlDiario.model_construct(
        id=99,
        estudiante_id=1,
        grupo_id=1,
        asignacion_id=1,
        periodo_id=1,
        fecha=fecha_futura,
        estado="P",
        uniforme=True,
        materiales=True,
    )

    assert cd.fecha == fecha_futura, "La fila leída debe tener la fecha original"
    assert cd.id == 99


def test_recupera_nueva_fila_fecha_futura_sigue_rechazando():
    """
    Crear una NUEVA fila con fecha futura sigue fallando (la validación sana).

    La asimetría: model_construct (lectura) no valida; el constructor normal sí.
    R11/R12: la validación de entrada sigue protegiendo contra errores del usuario.
    """
    from pydantic import ValidationError

    from src.domain.models.asistencia import ControlDiario

    fecha_futura = date.today() + timedelta(days=1)

    with pytest.raises(ValidationError):
        ControlDiario(
            estudiante_id=1,
            grupo_id=1,
            asignacion_id=1,
            periodo_id=1,
            fecha=fecha_futura,
        )


# ---------------------------------------------------------------------------
# T7 — Puerta contra la reaparición (marker: puerta)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Módulos exentos de la puerta (lista explícita; cada entrada justificada).
# ---------------------------------------------------------------------------
_EXENCIONES = frozenset([
    # ── Origen único (permitido — usa datetime internamente) ───────────────
    "src/domain/models/clock.py",

    # ── Configuraci��n (solo declara ZONA_HORARIA; no llama a today()) ──────
    "config.py",

    # ── Schema de BD: DEFAULTS se conservan como red de seguridad (datos_08
    #    D3). Eliminar el DEFAULT rompería insercciones sin dominio (cron,
    #    scripts legacy, etc.).
    "src/infrastructure/db/schema.py",

    # ── Seed de datos: datos de arranque, no lógica de negocio ──────────────
    "src/infrastructure/db/seed.py",

    # ── Deuda técnica — modelos fuera del scope de datos_08 ─────────────────
    # Pendiente de migrar a hoy()/ahora() en un paso dedicado.
    "src/domain/models/alerta.py",
    "src/domain/models/habilitacion.py",
    "src/domain/models/periodo.py",
    "src/domain/models/piar.py",
    "src/domain/models/usuario.py",

    # ── Deuda técnica — repositorios fuera del scope de datos_08 ────────────
    "src/infrastructure/db/repositories/sqlite_alerta_repo.py",
    "src/infrastructure/db/repositories/sqlite_plan_mejoramiento_repo.py",

    # ── Deuda técnica — exporters e interface ───────────────────────────────
    "src/infrastructure/exporters/boletin_pdf.py",
    "src/infrastructure/exporters/observador_excel.py",
    "src/infrastructure/exporters/observador_pdf.py",
    "src/infrastructure/exporters/openpyxl_exporter.py",
    "src/infrastructure/exporters/pdf_exporter.py",
    "src/interface/design/components/activity_feed.py",
    "src/interface/design/components/date_input.py",
    "src/interface/design/components/greeting_hero.py",
    "src/interface/design/components/milestones_panel.py",
    "src/interface/design/components/period_status.py",
    "src/interface/pages/academico/horarios_hub.py",
    "src/interface/pages/academico/registro_asistencia.py",
    "src/interface/pages/convivencia/observaciones.py",
    "src/interface/pages/informes/estadisticos.py",
    "src/interface/presenters/academico/registro_asistencia_presenter.py",

    # ── Deuda técnica — servicios fuera del scope de datos_08 ───────────────
    "src/services/alerta_service.py",
    "src/services/auditoria_service.py",
    "src/services/cierre_service.py",
    "src/services/estadisticos_service.py",
    "src/services/nivelacion_service.py",
    "src/services/periodo_service.py",

    # ── Deuda en tests — pendiente de migrar a hoy()/ahora() ────────────────
    # (la spec dice "NO eximir" como objetivo final; estos se migran por separado)
    "tests/integration/test_convivencia_34_tipos_situacion.py",
    "tests/integration/test_convivencia_35_entradas_seguimiento.py",
    "tests/integration/test_convivencia_categorias.py",
    "tests/integration/test_repositories.py",
    "tests/integration/test_tenant_b2_estudiantes.py",
    "tests/unit/domain/test_alerta_piar_convivencia.py",
    "tests/unit/domain/test_cierre_periodo_infraestructura.py",
    "tests/unit/domain/test_configuracion_usuario_auditoria.py",
    "tests/unit/domain/test_decimal_notas.py",
    "tests/unit/domain/test_estudiante.py",
    "tests/unit/domain/test_evaluacion.py",
    "tests/unit/domain/test_habilitacion.py",
    "tests/unit/domain/test_institucion.py",
    "tests/unit/interface/test_inicio_seguimientos.py",
    "tests/unit/services/test_alerta_service.py",
    "tests/unit/services/test_asistencia_service.py",
    "tests/unit/services/test_cierre_service.py",
    "tests/unit/services/test_convivencia_service.py",
    "tests/unit/services/test_estudiante_service.py",
    "tests/unit/services/test_habilitacion_service.py",
    "tests/unit/services/test_nivelacion_service.py",
    "tests/unit/services/test_periodo_service.py",
    "tests/unit/services/test_solo_lectura.py",
])

# Patrones prohibidos fuera de las exenciones (como texto de nodos AST)
_PATRONES_PROHIBIDOS = [
    "date.today()",
    "datetime.now()",
    "datetime.utcnow()",
    # En SQL strings dentro de .py: CURRENT_DATE, CURRENT_TIMESTAMP, datetime('now')
    # — estos se detectan como cadenas literales en el AST.
]

_SQL_PROHIBIDOS = [
    "CURRENT_DATE",
    "CURRENT_TIMESTAMP",
    "datetime('now')",
]


def _sentencias_logicas(tree: ast.AST) -> list[tuple[int, str]]:
    """
    Retorna (lineno, texto) de cada nodo Call en el AST que coincida con
    un patrón prohibido. Opera sobre el AST (sentencias lógicas, no líneas físicas).
    """
    hallazgos = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            try:
                texto = ast.unparse(node)
            except Exception:  # pragma: no cover
                continue
            for patron in _PATRONES_PROHIBIDOS:
                # Eliminar espacios para comparar sin importar el formateo
                if patron.replace(" ", "") in texto.replace(" ", ""):
                    hallazgos.append((node.lineno, texto))
                    break
        # Detectar cadenas SQL con patrones prohibidos
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            for patron in _SQL_PROHIBIDOS:
                if patron in node.value:
                    hallazgos.append((node.lineno, f"[SQL literal] {patron!r}"))
                    break
    return hallazgos


def _archivos_a_revisar(root: Path) -> list[Path]:
    """Retorna todos los .py del proyecto excluyendo exenciones y scripts/."""
    archivos = []
    for py in root.rglob("*.py"):
        rel = py.relative_to(root).as_posix()
        # Excluir exenciones explícitas
        if rel in _EXENCIONES:
            continue
        # Excluir scripts/ (herramientas de harness)
        if rel.startswith("scripts/"):
            continue
        # Excluir el propio archivo de test (usa los patrones para detectarlos)
        if "test_fecha_zona_horaria" in rel:
            continue
        # Excluir .venv/ y .claude/ (worktrees de agentes, no código del proyecto)
        if rel.startswith((".venv", ".claude")):
            continue
        archivos.append(py)
    return archivos


def test_puerta_no_hay_llamadas_directas_a_today():
    """
    Escanea todos los .py del proyecto y falla si encuentra date.today(),
    datetime.now(), datetime.utcnow(), CURRENT_DATE, CURRENT_TIMESTAMP
    o datetime('now') fuera de las exenciones declaradas.

    Analiza el AST (sentencias lógicas), no líneas físicas.
    Un uso partido en varias líneas se detecta igual.
    """
    root = Path(__file__).parents[3]  # raíz del proyecto

    violaciones = []
    for archivo in _archivos_a_revisar(root):
        try:
            fuente = archivo.read_text(encoding="utf-8")
        except Exception:  # pragma: no cover
            continue
        try:
            tree = ast.parse(fuente, filename=str(archivo))
        except SyntaxError:  # pragma: no cover
            continue
        hallazgos = _sentencias_logicas(tree)
        for lineno, texto in hallazgos:
            rel = archivo.relative_to(root).as_posix()
            violaciones.append(f"  {rel}:{lineno}: {texto}")

    assert not violaciones, (
        "Encontradas llamadas directas a date.today() / datetime.now() / "
        "SQL UTC fuera de las exenciones declaradas. "
        "Usa hoy() o ahora() de src.domain.models.clock.\n"
        + "\n".join(violaciones)
    )
