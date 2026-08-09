from __future__ import annotations

import logging

from nicegui import app, ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.components.buttons import btn_icon, btn_primary, btn_secondary
from src.interface.design.components.toast import toast_success
from src.interface.design.layout import app_layout
from src.interface.design.theme import ThemeManager

logger = logging.getLogger(__name__)


# page-delegate
def mi_cuenta_password_page() -> None:
    ctx = SessionContext.desde_storage()

    def contenido() -> None:
        with ui.element("div").classes("pwd-page-center"):
            with ui.element("div").classes("andes-login-card"):
                # Header
                with ui.element("div").classes("andes-login-logo"):
                    with ui.element("div").classes("andes-login-icon-wrap"):
                        ThemeManager.icono("key", size=40, color="var(--color-primary)")
                    ui.label("Cambiar contraseña").classes("andes-login-logo-title")
                    ui.label("Elige una nueva contraseña segura para tu cuenta").classes(
                        "andes-login-logo-subtitle"
                    )

                # Campos
                with ui.column().classes("w-full gap-4"):
                    actual_input = (
                        ui.input(label="Contraseña actual", password=True, password_toggle_button=True)
                        .classes("w-full andes-input")
                        .props("outlined")
                    )

                    ui.element("div").classes("pwd-separator")

                    nueva_input = (
                        ui.input(label="Nueva contraseña", password=True, password_toggle_button=True)
                        .classes("w-full andes-input")
                        .props("outlined")
                    )

                    # Medidor de fortaleza
                    with ui.element("div").classes("pwd-strength"):
                        with ui.element("div").classes("pwd-strength-track"):
                            seg1 = ui.element("div").classes("pwd-strength-seg")
                            seg2 = ui.element("div").classes("pwd-strength-seg")
                            seg3 = ui.element("div").classes("pwd-strength-seg")
                        strength_label = ui.label("").classes("pwd-strength-label")

                    # Checklist dinámico de requisitos
                    requisitos = Container.usuario_service().requisitos_password()
                    req_items: dict[str, object] = {}
                    with ui.element("div").classes("pwd-reqs"):
                        ui.label("Requisitos").classes("pwd-reqs-title")
                        for req in requisitos:
                            with ui.row().classes("pwd-req-item") as row:
                                ThemeManager.icono("check_circle", size=16)
                                ui.label(req)
                            req_items[req] = row

                    confirmar_input = (
                        ui.input(
                            label="Confirmar nueva contraseña",
                            password=True,
                            password_toggle_button=True,
                        )
                        .classes("w-full andes-input")
                        .props("outlined")
                    )

                # Banner de error
                with ui.row().classes("alert alert--error hidden") as error_container:
                    ThemeManager.icono("error", size=18)
                    error_label = ui.label("").classes("flex-1")

                # Banner de éxito
                with ui.row().classes("alert alert--success hidden") as success_container:
                    ThemeManager.icono("check_circle", size=18)
                    success_label = ui.label("").classes("flex-1")

                # Acciones
                with ui.element("div").classes("pwd-actions"):
                    btn_secondary("Cancelar", on_click=lambda: ui.navigate.to("/inicio"))
                    cambiar_btn = btn_primary("Cambiar contraseña", on_click=lambda: intentar_cambio())

        # --- Handlers ---

        def _limpiar_banners() -> None:
            error_container.classes(add="hidden")
            success_container.classes(add="hidden")

        def _show_error(msg: str) -> None:
            error_label.set_text(msg)
            error_container.classes(remove="hidden")

        def _set_loading(loading: bool) -> None:
            if loading:
                cambiar_btn.disable()
                cambiar_btn.props("loading")
                actual_input.disable()
                nueva_input.disable()
                confirmar_input.disable()
            else:
                cambiar_btn.enable()
                cambiar_btn.props(remove="loading")
                actual_input.enable()
                nueva_input.enable()
                confirmar_input.enable()

        def _on_nueva_change(e) -> None:
            val = (e.args if isinstance(e.args, str) else nueva_input.value) or ""
            if not val:
                for s in (seg1, seg2, seg3):
                    s.classes(remove="s-weak s-fair s-strong")
                strength_label.classes(remove="l-weak l-fair l-strong")
                strength_label.set_text("")
                for row in req_items.values():
                    row.classes(remove="met")
                return

            has_min_len = len(val) >= 10
            has_max_len = len(val) <= 128
            has_upper = any(c.isupper() for c in val)
            has_lower = any(c.islower() for c in val)
            has_digit = any(c.isdigit() for c in val)
            has_special = any(not c.isalnum() for c in val)

            checks = {
                "10": has_min_len,
                "128": has_max_len,
                "mayúscula": has_upper,
                "minúscula": has_lower,
                "número": has_digit,
                "especial": has_special,
            }

            for req, row in req_items.items():
                req_lower = req.lower()
                met = False
                for keyword, passed in checks.items():
                    if keyword in req_lower:
                        met = passed
                        break
                if met:
                    row.classes(add="met")
                else:
                    row.classes(remove="met")

            score = sum([
                has_min_len,
                has_upper and has_lower,
                has_digit,
                has_special,
                len(val) >= 14,
            ])

            if score <= 2:
                nivel, label_txt = "weak", "Débil"
            elif score <= 3:
                nivel, label_txt = "fair", "Aceptable"
            else:
                nivel, label_txt = "strong", "Fuerte"

            for s in (seg1, seg2, seg3):
                s.classes(remove="s-weak s-fair s-strong")
            for s in (seg1, seg2, seg3) if nivel == "strong" else (seg1, seg2) if nivel == "fair" else (seg1,):
                s.classes(add=f"s-{nivel}")

            strength_label.classes(remove="l-weak l-fair l-strong")
            strength_label.classes(add=f"l-{nivel}")
            strength_label.set_text(label_txt)

        nueva_input.on("update:model-value", _on_nueva_change)

        def intentar_cambio() -> None:
            _limpiar_banners()
            actual_input.props(remove="error")
            nueva_input.props(remove="error")
            confirmar_input.props(remove="error")

            actual = actual_input.value or ""
            nueva = nueva_input.value or ""
            confirmar = confirmar_input.value or ""

            if not actual or not nueva or not confirmar:
                _show_error("Completa todos los campos.")
                if not actual:
                    actual_input.props("error")
                if not nueva:
                    nueva_input.props("error")
                if not confirmar:
                    confirmar_input.props("error")
                return

            if nueva != confirmar:
                _show_error("La nueva contraseña y su confirmación no coinciden.")
                nueva_input.props("error")
                confirmar_input.props("error")
                return

            if nueva == actual:
                _show_error("La nueva contraseña debe ser distinta de la actual.")
                nueva_input.props("error")
                return

            uid = app.storage.user.get("usuario_id")
            if not uid:
                ui.navigate.to("/login")
                return

            _set_loading(True)

            try:
                Container.usuario_service().cambiar_password(uid, actual, nueva)
                success_label.set_text("Contraseña actualizada correctamente.")
                success_container.classes(remove="hidden")
                toast_success("Contraseña actualizada correctamente")
                ui.timer(1.5, lambda: ui.navigate.to("/inicio"), once=True)
            except PermissionError:
                _show_error("No disponible en modo solo lectura (impersonación activa).")
                _set_loading(False)
            except ValueError as exc:
                _show_error(str(exc).strip() or "No se pudo cambiar la contraseña.")
                _set_loading(False)
            except Exception:
                logger.exception("Error inesperado al cambiar contraseña")
                _show_error("Error del sistema. Intenta de nuevo.")
                _set_loading(False)

        confirmar_input.on("keydown.enter", lambda _: intentar_cambio())
        actual_input.on("keydown", lambda _: actual_input.props(remove="error"))
        nueva_input.on("keydown", lambda _: nueva_input.props(remove="error"))
        confirmar_input.on("keydown", lambda _: confirmar_input.props(remove="error"))

    app_layout(
        ctx,
        contenido,
        page_titulo="Cambiar contraseña",
        page_subtitulo="Actualiza tu contraseña de acceso",
        page_icono="lock",
    )


__all__ = ["mi_cuenta_password_page"]
