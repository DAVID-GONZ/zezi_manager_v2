"""
main.py — Punto de entrada de ZECI Manager v2.0
=================================================
Orden de arranque:
  1. Configurar logging
  2. Inicializar base de datos (schema + seed_dev en dev / seed_base en prod)
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
    Crea el schema si no existe y ejecuta el seed correspondiente al entorno:

      - development: seed_dev() si no hay grupos (primera instalación o BD vacía).
        seed_dev() incluye seed_base() internamente — no se llaman por separado.
      - production/test:  seed_base() solo si la BD es nueva.
    """
    from src.infrastructure.db.schema import init_db
    from src.infrastructure.db.connection import DB_PATH, get_connection

    es_nueva = not DB_PATH.exists()
    ok = init_db()
    if not ok:
        logging.critical("Falló la inicialización del schema. Abortando.")
        return False

    if settings.is_development:
        # Verificar si ya existen datos de desarrollo (grupos creados)
        with get_connection() as conn:
            tiene_grupos = conn.execute(
                "SELECT COUNT(*) FROM grupos"
            ).fetchone()[0] > 0

        if not tiene_grupos:
            logging.info(
                "Entorno desarrollo — datos no detectados, ejecutando seed_dev"
            )
            from src.infrastructure.db.seed import seed_dev
            with get_connection() as conn:
                seed_dev(conn)
                conn.commit()
            logging.info("Seed dev completado")
        else:
            logging.info("Entorno desarrollo — datos ya presentes, seed omitido")

    elif es_nueva:
        logging.info("Base de datos nueva detectada — ejecutando seed base")
        from src.infrastructure.db.seed import seed_base
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

    # Ruta interna — health/diagnóstico del sistema; no aparece en NAV_ITEMS intencionalmente.
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
    
    # ──tablero estadístico──
    from src.interface.pages.academico.tablero_estadisticos import tablero_estadisticos_page
    
    # ──registro de asistencia──
    from src.interface.pages.academico.registro_asistencia  import registro_asistencia_page

    # ── Inicio / Dashboard ───────────────────────────────────────────────────
    from src.interface.pages.inicio import inicio_page

    @ui.page("/inicio")
    def pagina_inicio():
        if not app.storage.user.get("autenticado"):
            ui.navigate.to("/login")
            return
        inicio_page()

    # ── Admin: Grupos ────────────────────────────────────────────────────────
    from src.interface.pages.admin.grupos import grupos_page

    @ui.page("/admin/grupos")
    def pagina_admin_grupos():
        if not app.storage.user.get("autenticado"):
            ui.navigate.to("/login")
            return
        grupos_page()

    # ── Admin: Asignaturas ───────────────────────────────────────────────────
    from src.interface.pages.admin.asignaturas import asignaturas_page

    @ui.page("/admin/asignaturas")
    def pagina_admin_asignaturas():
        if not app.storage.user.get("autenticado"):
            ui.navigate.to("/login")
            return
        asignaturas_page()

    # ── Admin: Usuarios ──────────────────────────────────────────────────────
    from src.interface.pages.admin.usuarios import usuarios_page

    @ui.page("/admin/usuarios")
    def pagina_admin_usuarios():
        if not app.storage.user.get("autenticado"):
            ui.navigate.to("/login")
            return
        usuarios_page()

    # ── Admin: Asignaciones ──────────────────────────────────────────────────
    from src.interface.pages.admin.asignaciones import asignaciones_page

    @ui.page("/admin/asignaciones")
    def pagina_admin_asignaciones():
        if not app.storage.user.get("autenticado"):
            ui.navigate.to("/login")
            return
        asignaciones_page()

    # ── Admin: Configuración SIE ─────────────────────────────────────────────
    from src.interface.pages.admin.configuracion_sie import configuracion_sie_page

    @ui.page("/admin/configuracion")
    def pagina_admin_configuracion():
        if not app.storage.user.get("autenticado"):
            ui.navigate.to("/login")
            return
        configuracion_sie_page()

    # ── Admin: Información Institucional ─────────────────────────────────────
    from src.interface.pages.admin.configuracion_institucion import configuracion_institucion_page

    @ui.page("/admin/configuracion-institucion")
    def pagina_admin_configuracion_institucion():
        if not app.storage.user.get("autenticado"):
            ui.navigate.to("/login")
            return
        configuracion_institucion_page()

    # ── Académico: Estudiantes y PIAR ─────────────────────────────────────────
    from src.interface.pages.academico.estudiantes import estudiantes_page

    @ui.page("/estudiantes")
    def pagina_estudiantes():
        if not app.storage.user.get("autenticado"):
            ui.navigate.to("/login")
            return
        estudiantes_page()

    # ── Académico: Horarios ───────────────────────────────────────────────────
    from src.interface.pages.academico.horarios import horarios_page
    from src.interface.pages.academico.horario_generar import horario_generar_page

    @ui.page("/horarios")
    def pagina_horarios():
        if not app.storage.user.get("autenticado"):
            ui.navigate.to("/login")
            return
        horarios_page()

    @ui.page("/academico/generar-horario")
    def pagina_generar_horario():
        if not app.storage.user.get("autenticado"):
            ui.navigate.to("/login")
            return
        horario_generar_page()

    # ── Evaluación: Configuración de categorías ───────────────────────────────
    from src.interface.pages.evaluacion.configuracion_evaluacion import configuracion_evaluacion_page

    @ui.page("/evaluacion/configuracion")
    def pagina_evaluacion_configuracion():
        if not app.storage.user.get("autenticado"):
            ui.navigate.to("/login")
            return
        configuracion_evaluacion_page()

    # ── Evaluación: Planilla de notas ─────────────────────────────────────────
    from src.interface.pages.evaluacion.planilla_notas import planilla_notas_page

    @ui.page("/evaluacion/planilla")
    def pagina_planilla_notas():
        if not app.storage.user.get("autenticado"):
            ui.navigate.to("/login")
            return
        planilla_notas_page()

    # ── Evaluación: Cierre de periodo ─────────────────────────────────────────
    from src.interface.pages.evaluacion.cierre_periodo import cierre_periodo_page

    @ui.page("/evaluacion/cierre-periodo")
    def pagina_cierre_periodo():
        if not app.storage.user.get("autenticado"):
            ui.navigate.to("/login")
            return
        cierre_periodo_page()

    # ── Evaluación: Cierre de año ─────────────────────────────────────────────
    from src.interface.pages.evaluacion.cierre_anio import cierre_anio_page

    @ui.page("/evaluacion/cierre-anio")
    def pagina_cierre_anio():
        if not app.storage.user.get("autenticado"):
            ui.navigate.to("/login")
            return
        cierre_anio_page()

    # ── Evaluación: Habilitaciones ────────────────────────────────────────────
    from src.interface.pages.evaluacion.habilitaciones import habilitaciones_page

    @ui.page("/evaluacion/habilitaciones")
    def pagina_habilitaciones():
        if not app.storage.user.get("autenticado"):
            ui.navigate.to("/login")
            return
        habilitaciones_page()

    # ── Evaluación: Planes de mejoramiento ────────────────────────────────────
    from src.interface.pages.evaluacion.planes_mejoramiento import planes_mejoramiento_page

    @ui.page("/evaluacion/planes")
    def pagina_planes_mejoramiento():
        if not app.storage.user.get("autenticado"):
            ui.navigate.to("/login")
            return
        planes_mejoramiento_page()

    # ── Convivencia: Observaciones ────────────────────────────────────────────
    from src.interface.pages.convivencia.observaciones import observaciones_page

    @ui.page("/convivencia/observaciones")
    def pagina_observaciones():
        if not app.storage.user.get("autenticado"):
            ui.navigate.to("/login")
            return
        observaciones_page()

    # ── Convivencia: Comportamiento ───────────────────────────────────────────
    from src.interface.pages.convivencia.comportamiento import comportamiento_page

    @ui.page("/convivencia/comportamiento")
    def pagina_comportamiento():
        if not app.storage.user.get("autenticado"):
            ui.navigate.to("/login")
            return
        comportamiento_page()

    # ── Convivencia: Notas ────────────────────────────────────────────────────
    from src.interface.pages.convivencia.notas_convivencia import notas_convivencia_page

    @ui.page("/convivencia/notas")
    def pagina_notas_convivencia():
        if not app.storage.user.get("autenticado"):
            ui.navigate.to("/login")
            return
        notas_convivencia_page()

    # ── Informes: Boletín Periodo ─────────────────────────────────────────────
    from src.interface.pages.informes.boletin_periodo import boletin_periodo_page

    @ui.page("/informes/boletin-periodo")
    def pagina_boletin_periodo():
        if not app.storage.user.get("autenticado"):
            ui.navigate.to("/login")
            return
        boletin_periodo_page()

    # ── Informes: Boletín Anual ───────────────────────────────────────────────
    from src.interface.pages.informes.boletin_anual import boletin_anual_page

    @ui.page("/informes/boletin-anual")
    def pagina_boletin_anual():
        if not app.storage.user.get("autenticado"):
            ui.navigate.to("/login")
            return
        boletin_anual_page()

    # ── Informes: Consolidado de Notas ────────────────────────────────────────
    from src.interface.pages.informes.consolidado_notas import consolidado_notas_page

    @ui.page("/informes/consolidado-notas")
    def pagina_consolidado_notas():
        if not app.storage.user.get("autenticado"):
            ui.navigate.to("/login")
            return
        consolidado_notas_page()

    # ── Informes: Consolidado de Asistencia ───────────────────────────────────
    from src.interface.pages.informes.consolidado_asistencia import consolidado_asistencia_page

    @ui.page("/informes/consolidado-asistencia")
    def pagina_consolidado_asistencia():
        if not app.storage.user.get("autenticado"):
            ui.navigate.to("/login")
            return
        consolidado_asistencia_page()

    # ── Informes: Estadísticos ────────────────────────────────────────────────
    from src.interface.pages.informes.estadisticos import estadisticos_page

    @ui.page("/informes/estadisticos")
    def pagina_estadisticos():
        if not app.storage.user.get("autenticado"):
            ui.navigate.to("/login")
            return
        estadisticos_page()


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
