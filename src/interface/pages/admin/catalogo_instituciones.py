"""
src/interface/pages/admin/catalogo_instituciones.py
======================================================
Página de catálogo de instituciones (tenants).
Ruta: /admin/instituciones
Acceso: admin

Permite al admin, en un solo flujo, crear una institución nueva con su
usuario director (mejora_09a). El tenant queda aprovisionado (catálogos +
preferencias sembrados) y marcado como pendiente de configuración inicial
— el wizard que consume ese flag se construye en mejora_09b.

La página NO edita identidad completa ni preferencias (eso es del director,
en el wizard/hub de 09b/09c); aquí solo datos básicos + director.
"""
from __future__ import annotations

import logging

from nicegui import ui
from pydantic import ValidationError

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.components import (
    custom_dialog,
    empty_state,
    form_dialog,
    status_badge,
    toast_success,
    toast_warning,
)
from src.interface.design.components.buttons import btn_ghost, btn_primary
from src.interface.design.layout import app_layout
from src.reference.divipola import DEPARTAMENTOS, municipios_de
from src.services.aprovisionamiento_institucion_service import (
    NuevaInstitucionConDirectorDTO,
)

logger = logging.getLogger("ADMIN.CATALOGO_INSTITUCIONES")

_PREFIJO_VALUE_ERROR = "Value error, "


def _formatear_errores_validacion(exc: ValidationError) -> str:
    """
    Convierte un ValidationError de Pydantic en un mensaje legible para el
    usuario. Extrae el texto de cada validador (sin el prefijo técnico
    'Value error, ' ni las URLs de pydantic) y los une deduplicados.
    """
    mensajes: list[str] = []
    for err in exc.errors():
        msg = str(err.get("msg", "")).strip()
        if msg.startswith(_PREFIJO_VALUE_ERROR):
            msg = msg[len(_PREFIJO_VALUE_ERROR):]
        if msg and msg not in mensajes:
            mensajes.append(msg)
    return " ".join(mensajes) or "Revisa los datos del formulario."


# page-delegate: ruta y guard de rol registrados en main.py
def catalogo_instituciones_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    logger.info("Catálogo instituciones: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    # ── Estado mutable ────────────────────────────────────────────────────────
    _s: dict = {"instituciones": []}

    # ── Carga de datos ────────────────────────────────────────────────────────
    def _cargar_estado() -> None:
        try:
            _s["instituciones"] = Container.institucion_service().listar_entidades()
        except Exception as exc:
            logger.error("Error al cargar instituciones: %s", exc)
            _s["instituciones"] = []

    _cargar_estado()

    # ── Acciones ──────────────────────────────────────────────────────────────
    def _mostrar_credenciales(nombre_institucion: str, usuario: str, password: str | None) -> None:
        with custom_dialog(max_width="sm") as dlg:
            ui.label("Institución creada").classes("font-h3 form-dialog-title")
            ui.label(
                f"'{nombre_institucion}' quedó aprovisionada. Comunica estas "
                "credenciales al director — la contraseña temporal solo se "
                "muestra una vez."
            ).classes("text-sm text-muted mb-4")

            with ui.element("div").classes("panel-card"):
                ui.label("Usuario").classes("eyebrow-label")
                ui.label(usuario).classes("cell-mono-bold u-mb-sm")
                if password:
                    ui.label("Contraseña temporal").classes("eyebrow-label")
                    ui.label(password).classes("cell-mono-bold")

            with ui.row().classes("form-dialog-actions"):
                if password:
                    btn_ghost(
                        "Copiar",
                        on_click=lambda: (
                            ui.run_javascript(
                                f"navigator.clipboard.writeText({password!r})"
                            ),
                            toast_success("Contraseña copiada"),
                        ),
                        icon="content_copy",
                    )
                btn_primary("Entendido", on_click=dlg.close)
        dlg.open()

    def _abrir_crear_institucion() -> None:
        def _crear(datos: dict) -> bool | None:
            try:
                dto = NuevaInstitucionConDirectorDTO(
                    nombre=datos.get("nombre", ""),
                    codigo_dane=datos.get("codigo_dane", ""),
                    pais=datos.get("pais", "Colombia"),
                    departamento=datos.get("departamento", ""),
                    municipio=datos.get("municipio", ""),
                    director_usuario=datos.get("director_usuario", ""),
                    director_nombre_completo=datos.get("director_nombre_completo", ""),
                    director_email=datos.get("director_email", ""),
                )
            except ValidationError as exc:
                # ValidationError hereda de ValueError en pydantic v2: hay que
                # capturarlo aparte para no mostrar el volcado técnico crudo.
                toast_warning(_formatear_errores_validacion(exc))
                return False

            try:
                resultado = Container.aprovisionamiento_service().crear_institucion_con_director(
                    dto, actor_rol=ctx.usuario_rol,
                )
                toast_success(f"Institución '{resultado.institucion.nombre}' creada")
                _cargar_estado()
                lista_instituciones.refresh()
                _mostrar_credenciales(
                    resultado.institucion.nombre,
                    resultado.director_usuario,
                    resultado.password_temporal,
                )
            except ValueError as exc:
                toast_warning(str(exc))
                return False
            except Exception as exc:
                logger.error("Error al crear institución con director: %s", exc)
                toast_warning("Error al crear la institución")
                return False

        form_dialog(
            titulo    = "Crear institución",
            subtitulo = "Registra la institución y su usuario director",
            campos    = [
                {"tipo": "section", "label": "Institución", "icono": "apartment"},
                {"key": "nombre", "label": "Nombre de la institución", "tipo": "text",
                 "requerido": True, "minlength": 3, "maxlength": 200,
                 "normalizar": "titulo"},
                {"key": "codigo_dane", "label": "Código DANE", "tipo": "text",
                 "requerido": True, "minlength": 12, "maxlength": 12,
                 "hint": "12 dígitos numéricos"},
                {"tipo": "section", "label": "Ubicación", "icono": "location_on"},
                {"key": "pais", "label": "País", "tipo": "select",
                 "requerido": True, "opciones": ["Colombia"],
                 "valor": "Colombia"},
                {"key": "departamento", "label": "Departamento", "tipo": "select",
                 "requerido": True, "opciones": DEPARTAMENTOS},
                {"key": "municipio", "label": "Municipio", "tipo": "select",
                 "requerido": True,
                 "opciones_desde": "departamento", "opciones_fn": municipios_de},
                {"tipo": "section", "label": "Director", "icono": "person"},
                {"key": "director_nombre_completo", "label": "Nombre completo", "tipo": "text",
                 "requerido": True, "minlength": 3,
                 "normalizar": "titulo"},
                {"key": "director_usuario", "label": "Nombre de usuario", "tipo": "text",
                 "requerido": True, "minlength": 3,
                 "normalizar": "minusculas", "hint": "Sin espacios"},
                {"key": "director_email", "label": "Correo electrónico", "tipo": "email",
                 "requerido": True, "normalizar": "minusculas"},
            ],
            on_submit    = _crear,
            texto_submit = "Crear institución",
            max_width    = "max-w-lg",
            columnas     = 2,
            icono        = "apartment",
        )

    # ── Sección refreshable ───────────────────────────────────────────────────
    @ui.refreshable
    def lista_instituciones() -> None:
        instituciones = _s["instituciones"]
        if not instituciones:
            empty_state(
                icono="apartment",
                titulo="Aún no hay instituciones registradas",
                descripcion="Crea la primera institución para gestionar la plataforma.",
            )
            return

        with ui.element("div").classes("w-full"):
            with ui.element("div").classes(
                "flex items-center gap-4 p-2 font-semibold text-sm border-b"
            ):
                ui.label("Institución").classes("flex-1")
                ui.label("Ubicación").classes("w-48")
                ui.label("Estado").classes("w-48")

            for inst in instituciones:
                ubicacion = ", ".join(
                    p for p in [inst.municipio, inst.departamento] if p
                ) or "—"
                with ui.element("div").classes("divider-row"):
                    ui.label(inst.nombre).classes("flex-1")
                    ui.label(ubicacion).classes("w-48 name-w48-ellipsis")
                    with ui.element("div").classes("w-48"):
                        if inst.configuracion_inicial_completa:
                            status_badge("Configurada", "success")
                        else:
                            status_badge("Pendiente de configuración", "warning")

    # ── Contenido principal ───────────────────────────────────────────────────
    def contenido() -> None:
        with ui.element("div").classes("page-stack"):
            with ui.element("div").classes("panel-card"):
                with ui.row().classes(
                    "gap-4 items-center justify-between flex-wrap mb-4"
                ):
                    ui.label("Instituciones registradas").classes("text-base font-semibold")
                    btn_primary(
                        "Crear institución",
                        on_click=_abrir_crear_institucion,
                        icon="add_business",
                        size="sm",
                    )
                lista_instituciones()

    app_layout(
        ctx,
        contenido,
        page_titulo    = "Instituciones",
        page_subtitulo = "Catálogo de instituciones (tenants) de la plataforma",
        page_icono     = "apartment",
    )


__all__ = ["catalogo_instituciones_page"]
