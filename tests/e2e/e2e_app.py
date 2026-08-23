"""Entrypoint de la app para tests e2e headless (nicegui.testing.User).

El fixture `user` ejecuta ESTE archivo con `runpy.run_path(..., "__main__")`, así
que hace las veces de `main.py` pero **sin tocar la BD real**: apunta la conexión
a un archivo temporal sembrado con `seed_dev` (dos instituciones, usuarios con
bcrypt real, password conocido) y registra las rutas. `ui.run()` bajo simulación
solo fija el storage secret y retorna (no arranca servidor).

Credenciales sembradas (seed_dev / _default_hasher):
  admin        / Admin2025*
  director     / Director2025*
  profesores   (rgomez, cmoreno, …) / Pass2025*

La BD se siembra una sola vez por proceso de test (marca en `os.environ`), para
no re-hashear bcrypt en cada test.
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

# ── 1. Apuntar la conexión global a una BD temporal (NUNCA la real) ──────────
_DB = Path(os.environ.setdefault("ZECI_E2E_DB", str(Path(tempfile.gettempdir()) / "zeci_e2e.db")))
os.environ["DB_PATH_OVERRIDE"] = str(_DB)  # respetado por connection._resolve_db_path bajo pytest

import src.infrastructure.db.connection as _conn_mod  # noqa: E402

_conn_mod.DB_PATH = _DB  # get_connection() lee este global en cada llamada


def _sembrar_bd() -> None:
    from src.infrastructure.db.schema import INDICES, SCHEMA, TRIGGERS
    from src.infrastructure.db.seed import seed_dev

    if _DB.exists():
        _DB.unlink()
    con = sqlite3.connect(str(_DB))
    con.execute("PRAGMA foreign_keys = ON")
    con.row_factory = sqlite3.Row
    for sql in SCHEMA:
        con.execute(sql)
    for sql in INDICES:
        con.execute(sql)
    for sql in TRIGGERS:
        con.execute(sql)
    # seed_dev ya siembra una SEGUNDA institución (aislamiento multi-tenant).
    seed_dev(con, anio=2025, total_estudiantes=6, seed_random=42)
    con.commit()
    con.close()


if os.environ.get("ZECI_E2E_SEEDED") != "1":
    _sembrar_bd()
    os.environ["ZECI_E2E_SEEDED"] = "1"

# ── 2. Registrar la app (igual que main(), sin init de BD real ni ui.run real) ─
from container import Container  # noqa: E402

Container.reset()

import main  # noqa: E402
from src.interface.design.theme import ThemeManager  # noqa: E402

ThemeManager.aplicar()

from nicegui import app, ui  # noqa: E402

main.registrar_rutas_internas(app)
main.registrar_rutas_ui()

ui.run(storage_secret="e2e-test-secret")
