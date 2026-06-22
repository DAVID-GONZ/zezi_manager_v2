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
    Registra rutas FastAPI auxiliares (health).
    Separadas de las rutas NiceGUI para mantener claridad.

    Nota (paso_38): la antigua página inline `/diagnostico` se movió a una
    página de herramientas de admin (src/interface/pages/admin/diagnostico.py)
    y ahora se registra en `registrar_rutas_ui()` (surgida en el NAV).
    """
    @app.get("/health")
    def health():
        return {"status": "ok", "version": settings.APP_VERSION}


def registrar_rutas_ui() -> None:
    """
    Registra todas las páginas NiceGUI de la aplicación.
    Llamar DESPUÉS de ThemeManager.aplicar() para que el CSS esté disponible.

    Autorización central (paso_35): TODAS las páginas se registran vía
    `registrar_pagina(ruta, page_fn, roles=...)`, que envuelve el `@ui.page`
    con el guard deny-by-default (auth + rol). `roles` es obligatorio; la
    matriz de roles por ruta de abajo es la ÚNICA fuente de verdad y el NAV
    (layout.py) deriva su visibilidad del mismo registro.
    """
    from nicegui import app, ui
    from src.domain.models.usuario import Rol
    from src.interface.auth import AUTENTICADO, PUBLICO, registrar_pagina
    from src.interface.pages.login import login_page

    # Conjuntos de roles reutilizados (matriz del spec paso_35).
    _ADMIN          = {Rol.ADMIN}
    _ADMIN_DIRECTOR = {Rol.ADMIN, Rol.DIRECTOR}
    _DIRECTOR       = {Rol.DIRECTOR}
    _DIR_COORD      = {Rol.DIRECTOR, Rol.COORDINADOR}
    _AULA           = {Rol.DIRECTOR, Rol.COORDINADOR, Rol.PROFESOR}
    _PROFESOR       = {Rol.PROFESOR}

    # ── Públicas (con lógica propia de redirección por sesión) ────────────────
    def raiz():
        if app.storage.user.get("autenticado"):
            ui.navigate.to("/inicio")
        else:
            ui.navigate.to("/login")

    def pagina_login():
        if app.storage.user.get("autenticado"):
            ui.navigate.to("/inicio")
        else:
            login_page()

    def pagina_logout():
        app.storage.user.clear()
        ui.navigate.to("/login")

    registrar_pagina("/", raiz, roles=PUBLICO)
    registrar_pagina("/login", pagina_login, roles=PUBLICO)
    registrar_pagina("/logout", pagina_logout, roles=PUBLICO)

    # ── Inicio / Dashboard (cualquier autenticado) ────────────────────────────
    from src.interface.pages.inicio import inicio_page
    registrar_pagina("/inicio", inicio_page, roles=AUTENTICADO)

    # ── Administración ────────────────────────────────────────────────────────
    from src.interface.pages.admin.usuarios import usuarios_page
    from src.interface.pages.admin.auditoria import auditoria_page
    from src.interface.pages.admin.grupos import grupos_page
    from src.interface.pages.admin.asignaturas import asignaturas_page
    from src.interface.pages.admin.salas import salas_page
    from src.interface.pages.admin.plan_estudios import plan_estudios_page
    from src.interface.pages.admin.disponibilidad_docente import disponibilidad_docente_page
    from src.interface.pages.admin.asignaciones import asignaciones_page
    from src.interface.pages.admin.configuracion_sie import configuracion_sie_page
    from src.interface.pages.admin.configuracion_institucion import configuracion_institucion_page
    from src.interface.pages.admin.diagnostico import diagnostico_page

    registrar_pagina("/admin/usuarios", usuarios_page, roles=_ADMIN_DIRECTOR)
    registrar_pagina("/admin/auditoria", auditoria_page, roles=_ADMIN)
    registrar_pagina("/diagnostico", diagnostico_page, roles=_ADMIN)
    registrar_pagina("/admin/grupos", grupos_page, roles=_DIRECTOR)
    registrar_pagina("/admin/asignaturas", asignaturas_page, roles=_DIRECTOR)
    registrar_pagina("/admin/salas", salas_page, roles=_DIRECTOR)
    registrar_pagina("/admin/configuracion", configuracion_sie_page, roles=_DIRECTOR)
    registrar_pagina(
        "/admin/configuracion-institucion",
        configuracion_institucion_page,
        roles=_DIRECTOR,
    )
    registrar_pagina("/admin/plan-estudios", plan_estudios_page, roles=_DIR_COORD)
    registrar_pagina(
        "/admin/disponibilidad-docente",
        disponibilidad_docente_page,
        roles=_DIR_COORD,
    )
    registrar_pagina("/admin/asignaciones", asignaciones_page, roles=_AULA)

    # ── Académico ─────────────────────────────────────────────────────────────
    from src.interface.pages.academico.estudiantes import estudiantes_page
    from src.interface.pages.academico.horarios_hub import horarios_hub_page
    from src.interface.pages.academico.registro_asistencia import registro_asistencia_page
    from src.interface.pages.academico.tablero_estadisticos import tablero_estadisticos_page

    registrar_pagina("/estudiantes", estudiantes_page, roles=_AULA)
    registrar_pagina("/asistencia", registro_asistencia_page, roles=_AULA)
    registrar_pagina("/academico/tablero", tablero_estadisticos_page, roles=_AULA)

    # Horarios (hub unificado paso_18) — protegido por la ruta (B reconciliado).
    registrar_pagina(
        "/horarios", horarios_hub_page, roles=_AULA, seccion_inicial="visualizar"
    )
    registrar_pagina(
        "/academico/horarios", horarios_hub_page, roles=_AULA,
        seccion_inicial="visualizar",
    )
    registrar_pagina(
        "/academico/generar-horario", horarios_hub_page, roles=_AULA,
        seccion_inicial="generar",
    )

    # ── Evaluación ────────────────────────────────────────────────────────────
    from src.interface.pages.evaluacion.configuracion_evaluacion import configuracion_evaluacion_page
    from src.interface.pages.evaluacion.planilla_notas import planilla_notas_page
    from src.interface.pages.evaluacion.cierre_periodo import cierre_periodo_page
    from src.interface.pages.evaluacion.cierre_anio import cierre_anio_page
    from src.interface.pages.evaluacion.habilitaciones import habilitaciones_page
    from src.interface.pages.evaluacion.planes_mejoramiento import planes_mejoramiento_page

    # C reconciliado: /evaluacion/configuracion = solo profesor (config docente).
    registrar_pagina(
        "/evaluacion/configuracion", configuracion_evaluacion_page, roles=_PROFESOR
    )
    registrar_pagina("/evaluacion/planilla", planilla_notas_page, roles=_AULA)
    registrar_pagina("/evaluacion/habilitaciones", habilitaciones_page, roles=_AULA)
    registrar_pagina("/evaluacion/planes", planes_mejoramiento_page, roles=_AULA)
    registrar_pagina("/evaluacion/cierre-periodo", cierre_periodo_page, roles=_DIR_COORD)
    registrar_pagina("/evaluacion/cierre-anio", cierre_anio_page, roles=_DIR_COORD)

    # ── Convivencia ───────────────────────────────────────────────────────────
    from src.interface.pages.convivencia.observaciones import observaciones_page
    from src.interface.pages.convivencia.comportamiento import comportamiento_page
    from src.interface.pages.convivencia.notas_convivencia import notas_convivencia_page

    registrar_pagina("/convivencia/observaciones", observaciones_page, roles=_AULA)
    registrar_pagina("/convivencia/comportamiento", comportamiento_page, roles=_AULA)
    registrar_pagina("/convivencia/notas", notas_convivencia_page, roles=_AULA)

    # ── Informes ──────────────────────────────────────────────────────────────
    from src.interface.pages.informes.boletin_periodo import boletin_periodo_page
    from src.interface.pages.informes.boletin_anual import boletin_anual_page
    from src.interface.pages.informes.consolidado_notas import consolidado_notas_page
    from src.interface.pages.informes.consolidado_asistencia import consolidado_asistencia_page
    from src.interface.pages.informes.estadisticos import estadisticos_page

    registrar_pagina("/informes/boletin-periodo", boletin_periodo_page, roles=_AULA)
    registrar_pagina("/informes/boletin-anual", boletin_anual_page, roles=_AULA)
    registrar_pagina("/informes/estadisticos", estadisticos_page, roles=_AULA)
    registrar_pagina(
        "/informes/consolidado-notas", consolidado_notas_page, roles=_DIR_COORD
    )
    registrar_pagina(
        "/informes/consolidado-asistencia", consolidado_asistencia_page,
        roles=_DIR_COORD,
    )


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
