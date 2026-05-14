"""
main.py — Punto de entrada de ZECI Manager v2.0
=================================================
Orden de arranque:
  1. Configurar logging
  2. Inicializar base de datos (schema + seed_base si es primera vez)
  3. Aplicar design system (ThemeManager.aplicar — inyecta CSS global)
  4. Verificar el Container (detecta configuraciones rotas antes de servir)
  5. Registrar todas las rutas NiceGUI
  6. Arrancar NiceGUI
"""
from __future__ import annotations

import logging

from config import settings
from container import Container


def inicializar_base_de_datos() -> bool:
    """
    Crea el schema si no existe y ejecuta seed_base si es
    la primera vez que corre la aplicación.
    """
    from src.infrastructure.db.schema import init_db
    from src.infrastructure.db.connection import DB_PATH

    es_nueva = not DB_PATH.exists()
    ok = init_db()
    if not ok:
        logging.critical("Falló la inicialización del schema. Abortando.")
        return False

    if es_nueva:
        logging.info("Base de datos nueva detectada — ejecutando seed base")
        from src.infrastructure.db.seed import seed_base
        from src.infrastructure.db.connection import get_connection
        with get_connection() as conn:
            seed_base(conn)
            conn.commit()
        logging.info("Seed base completado")

    return True


def configurar_logging() -> None:
    settings.configure_logging()


def registrar_rutas_internas(app) -> None:
    """
    Registra rutas FastAPI auxiliares (health, diagnóstico).
    Separadas de las rutas NiceGUI para mantener claridad.
    """
    from nicegui import ui

    @app.get("/health")
    def health():
        return {"status": "ok", "version": settings.APP_VERSION}

    @ui.page("/diagnostico")
    def pagina_diagnostico():
        resultado = Container.diagnostico()
        with ui.card().classes("m-4 p-4"):
            ui.label("Diagnóstico del Container").classes("text-xl font-bold")
            for nombre, estado in resultado.items():
                color = "text-green-600" if estado == "OK" else "text-red-600"
                ui.label(f"{nombre}: {estado}").classes(color)


def registrar_rutas_ui() -> None:
    """
    Registra todas las páginas NiceGUI de la aplicación.
    Llamar DESPUÉS de ThemeManager.aplicar() para que el CSS esté disponible.
    """
    from nicegui import app, ui
    from src.interface.pages.login import login_page

    # ── Raíz: redirige según estado de sesión ────────────────────────────────
    @ui.page("/")
    def raiz():
        if app.storage.user.get("autenticado"):
            ui.navigate.to("/inicio")
        else:
            ui.navigate.to("/login")

    # ── Login ────────────────────────────────────────────────────────────────
    @ui.page("/login")
    def pagina_login():
        if app.storage.user.get("autenticado"):
            ui.navigate.to("/inicio")
        else:
            login_page()

    # ── Logout ───────────────────────────────────────────────────────────────
    @ui.page("/logout")
    def pagina_logout():
        app.storage.user.clear()
        ui.navigate.to("/login")

    # ── Inicio / Dashboard ───────────────────────────────────────────────────
    @ui.page("/inicio")
    def pagina_inicio():
        if not app.storage.user.get("autenticado"):
            ui.navigate.to("/login")
            return
        # Placeholder hasta tener la página de dashboard completa
        ui.label("Dashboard próximamente").classes("text-xl p-8")


def main() -> None:
    configurar_logging()
    log = logging.getLogger("MAIN")

    log.info("Iniciando %s v%s", settings.APP_NAME, settings.APP_VERSION)
    log.info("Entorno: %s", settings.APP_ENV)
    log.info("Base de datos: %s", settings.DATABASE_PATH)

    # 1. Inicializar BD
    if not inicializar_base_de_datos():
        raise SystemExit(1)

    # 2. Aplicar design system (CSS global — debe llamarse antes de registrar páginas)
    from src.interface.design.theme import ThemeManager
    ThemeManager.aplicar()

    # 3. Verificar container en desarrollo (detecta errores de config antes de servir)
    if settings.is_development:
        Container.diagnostico()

    # 4. Registrar rutas
    from nicegui import app, ui
    registrar_rutas_internas(app)
    registrar_rutas_ui()

    # 5. Arrancar NiceGUI
    ui.run(
        host=settings.HOST,
        port=settings.PORT,
        title=settings.APP_NAME,
        reload=settings.RELOAD,
        show=False,
        storage_secret=settings.JWT_SECRET,
    )


if __name__ == "__main__":
    main()
