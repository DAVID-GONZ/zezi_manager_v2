"""
src/interface/pages/admin/grupos.py
====================================
Página de administración de grupos escolares.
Ruta: /admin/grupos
Acceso: admin, director

Permite listar, crear, editar y eliminar grupos, y administrar el catálogo
global de grados (numero → nombre, min/max estudiantes, horas) que los grupos
referencian.

Regla de capas:
  Esta página NO importa ningún símbolo de src.domain.models.*. El campo `grado`
  se maneja como primitivo (int); el modelo Grupo lo valida en el servicio.

Refreshables:
  tabla()        — re-renderiza la lista de grupos
  grados_tabla() — re-renderiza el catálogo de grados
"""
from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.tokens import Icons
from src.interface.design.components.buttons import btn_primary, btn_icon
from src.interface.design.components import (
    confirm_dialog,
    empty_state,
    form_dialog,
    toast_error,
    toast_success,
    toast_warning,
)
from src.services.infraestructura_service import Grupo

logger = logging.getLogger("ADMIN.GRUPOS")

# Opciones de jornada para selectores
_JORNADAS = {
    "Mañana (AM)": "AM",
    "Tarde (PM)":  "PM",
    "Única":       "UNICA",
}
_JORNADA_LABELS = {v: k for k, v in _JORNADAS.items()}


# page-delegate: ruta y guard de rol registrados en main.py (paso_35)
def grupos_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    logger.info("Grupos admin: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    # ── Estado mutable ────────────────────────────────────────────────────────
    _s: dict = {
        "grupos":         [],
        "grados":         [],
        "cargando":       False,
        # formulario crear
        "form_codigo":    "",
        "form_grado":     1,
        "form_jornada":   "UNICA",
        "form_capacidad": 40,
        # edición
        "edit_id":        None,
        "edit_codigo":    "",
        "edit_grado":     1,
        "edit_jornada":   "UNICA",
        "edit_capacidad": 40,
    }

    # ── Carga de datos ────────────────────────────────────────────────────────
    def _cargar_estado() -> None:
        try:
            _s["grupos"] = Container.infraestructura_service().listar_grupos()
        except Exception as exc:
            logger.error("Error al cargar grupos: %s", exc)
            _s["grupos"] = []

    def _cargar_grados() -> None:
        try:
            _s["grados"] = Container.plan_estudios_service().listar_grados()
        except Exception as exc:
            logger.error("Error al cargar grados: %s", exc)
            _s["grados"] = []

    _cargar_estado()
    _cargar_grados()

    # ── Helpers de catálogo ───────────────────────────────────────────────────
    def _opciones_grado() -> dict:
        """Mapa {numero: 'numero — nombre'} para los selects de grado.

        Fallback: si el catálogo está vacío, ofrece 1-13 sin nombre para no
        bloquear la creación de grupos (la validación 1-13 la hace el modelo).
        """
        grados = sorted(_s["grados"], key=lambda g: g.numero)
        if not grados:
            return {n: str(n) for n in range(1, 14)}
        return {
            g.numero: (f"{g.numero} — {g.nombre}" if g.nombre else str(g.numero))
            for g in grados
        }

    def _grado_valido(numero: int | None) -> int:
        """Valor inicial seguro para el select de grado en formularios."""
        opciones = _opciones_grado()
        if numero in opciones:
            return numero
        return next(iter(opciones))

    def _contar_grupos_por_grado(numero: int) -> int:
        return sum(1 for g in _s["grupos"] if (g.grado or 0) == numero)

    # ── Acciones CRUD: grupos ─────────────────────────────────────────────────
    def _crear_grupo() -> None:
        # Sanitización y validación (strip/upper, grado 1-13, capacidad>=1,
        # jornada) las realiza la entidad Grupo en sus field_validator.
        try:
            grupo = Grupo(
                id=None,
                codigo=_s["form_codigo"],
                grado=_s["form_grado"],
                jornada=_s["form_jornada"],
                capacidad_maxima=_s["form_capacidad"],
            )
            Container.infraestructura_service().guardar_grupo(grupo)
            toast_success(f"Grupo {grupo.codigo} creado")
            _s["form_codigo"] = ""
            _s["form_grado"]  = _grado_valido(None)
            _s["form_jornada"] = "UNICA"
            _s["form_capacidad"] = 40
            _cargar_estado()
            tabla.refresh()
        except ValueError as exc:
            toast_warning(str(exc))
        except Exception as exc:
            logger.error("Error al crear grupo: %s", exc)
            toast_error("Error al crear el grupo")

    def _confirmar_eliminar_grupo(grupo_id: int, codigo: str) -> None:
        try:
            Container.infraestructura_service().eliminar_grupo(grupo_id)
            toast_success(f"Grupo {codigo} eliminado")
            _cargar_estado()
            tabla.refresh()
        except ValueError as exc:
            toast_warning(str(exc))
        except Exception as exc:
            logger.error("Error al eliminar grupo %s: %s", grupo_id, exc)
            toast_error("Error al eliminar el grupo")

    def _eliminar_grupo(grupo_id: int, codigo: str) -> None:
        confirm_dialog(
            titulo          = "Eliminar grupo",
            mensaje         = f"¿Eliminar el grupo {codigo}? Esta acción es irreversible.",
            on_confirm      = lambda: _confirmar_eliminar_grupo(grupo_id, codigo),
            variante        = "danger",
            texto_confirmar = "Eliminar",
        )

    def _abrir_editar(grupo: Grupo) -> None:
        jornada_val = grupo.jornada.value if hasattr(grupo.jornada, "value") else str(grupo.jornada)

        def _guardar(datos: dict) -> "bool | None":
            # La entidad Grupo valida y normaliza; la vista solo mapea el
            # formulario y conserva los valores actuales si vienen vacíos.
            grado = datos.get("grado")
            capacidad = datos.get("capacidad")
            try:
                grupo_act = Grupo(
                    id=grupo.id,
                    codigo=datos.get("codigo", ""),
                    grado=grado if grado is not None else grupo.grado,
                    jornada=datos.get("jornada", grupo.jornada),
                    capacidad_maxima=capacidad if capacidad is not None else grupo.capacidad_maxima,
                )
                Container.infraestructura_service().actualizar_grupo(grupo_act)
                toast_success(f"Grupo {grupo_act.codigo} actualizado")
                _cargar_estado()
                tabla.refresh()
            except ValueError as exc:
                toast_warning(str(exc))
                return False
            except Exception as exc:
                logger.error("Error al actualizar grupo: %s", exc)
                toast_error("Error al actualizar el grupo")
                return False

        form_dialog(
            titulo    = "Editar grupo",
            campos    = [
                {"key": "codigo",    "label": "Código *",  "tipo": "text",
                 "valor": grupo.codigo,           "requerido": True},
                {"key": "grado",     "label": "Grado",     "tipo": "select",
                 "valor": _grado_valido(grupo.grado),
                 "opciones": _opciones_grado()},
                {"key": "jornada",   "label": "Jornada",   "tipo": "select",
                 "valor": jornada_val,
                 "opciones": {v: k for k, v in _JORNADAS.items()}},
                {"key": "capacidad", "label": "Capacidad", "tipo": "number",
                 "valor": grupo.capacidad_maxima, "min": 1},
            ],
            on_submit    = _guardar,
            texto_submit = "Guardar",
            max_width    = "max-w-md",
            columnas     = 2,
        )

    # ── Acciones CRUD: grados ─────────────────────────────────────────────────
    def _guardar_grado(datos: dict) -> "bool | None":
        try:
            Container.plan_estudios_service().guardar_grado(
                numero          = int(datos.get("numero")),
                nombre          = (datos.get("nombre") or "").strip() or None,
                min_estudiantes = int(datos.get("min_estudiantes") or 0),
                max_estudiantes = int(datos.get("max_estudiantes") or 1),
                horas_semanales = int(datos.get("horas_semanales") or 0),
            )
            toast_success("Grado guardado")
            _cargar_grados()
            grados_tabla.refresh()
        except (ValueError, TypeError) as exc:
            toast_warning(str(exc))
            return False
        except Exception as exc:
            logger.error("Error al guardar grado: %s", exc)
            toast_error("Error al guardar el grado")
            return False

    def _abrir_crear_grado() -> None:
        form_dialog(
            titulo    = "Nuevo grado",
            campos    = [
                {"key": "numero",          "label": "Número *",      "tipo": "number",
                 "valor": None, "min": 1, "max": 13, "requerido": True},
                {"key": "nombre",          "label": "Nombre",        "tipo": "text",
                 "valor": "", "placeholder": "Sexto, Décimo…"},
                {"key": "min_estudiantes", "label": "Mín. estud.",   "tipo": "number",
                 "valor": 0,  "min": 0},
                {"key": "max_estudiantes", "label": "Máx. estud.",   "tipo": "number",
                 "valor": 40, "min": 1},
                {"key": "horas_semanales", "label": "Horas/semana",  "tipo": "number",
                 "valor": 0,  "min": 0},
            ],
            on_submit    = _guardar_grado,
            texto_submit = "Crear",
            max_width    = "max-w-md",
            columnas     = 2,
        )

    def _abrir_editar_grado(grado) -> None:
        form_dialog(
            titulo    = f"Editar grado {grado.numero}",
            campos    = [
                {"key": "numero",          "label": "Número *",      "tipo": "number",
                 "valor": grado.numero, "min": 1, "max": 13, "requerido": True},
                {"key": "nombre",          "label": "Nombre",        "tipo": "text",
                 "valor": grado.nombre or "", "placeholder": "Sexto, Décimo…"},
                {"key": "min_estudiantes", "label": "Mín. estud.",   "tipo": "number",
                 "valor": grado.min_estudiantes, "min": 0},
                {"key": "max_estudiantes", "label": "Máx. estud.",   "tipo": "number",
                 "valor": grado.max_estudiantes, "min": 1},
                {"key": "horas_semanales", "label": "Horas/semana",  "tipo": "number",
                 "valor": grado.horas_semanales, "min": 0},
            ],
            on_submit    = _guardar_grado,
            texto_submit = "Guardar",
            max_width    = "max-w-md",
            columnas     = 2,
        )

    def _confirmar_eliminar_grado(numero: int) -> None:
        try:
            ok = Container.plan_estudios_service().eliminar_grado(numero)
            if ok:
                toast_success(f"Grado {numero} eliminado")
            else:
                toast_warning(f"No existe el grado {numero}")
            _cargar_grados()
            grados_tabla.refresh()
        except ValueError as exc:
            toast_warning(str(exc))
        except Exception as exc:
            logger.error("Error al eliminar grado %s: %s", numero, exc)
            toast_error("Error al eliminar el grado")

    def _eliminar_grado(numero: int) -> None:
        en_uso = _contar_grupos_por_grado(numero)
        if en_uso:
            mensaje = (
                f"El grado {numero} está asignado a {en_uso} "
                f"grupo(s). Esos grupos quedarán con un grado inexistente. "
                f"¿Eliminar de todas formas?"
            )
        else:
            mensaje = f"¿Eliminar el grado {numero}? Esta acción es irreversible."
        confirm_dialog(
            titulo          = "Eliminar grado",
            mensaje         = mensaje,
            on_confirm      = lambda: _confirmar_eliminar_grado(numero),
            variante        = "danger",
            texto_confirmar = "Eliminar",
        )

    # ── Secciones refreshables ────────────────────────────────────────────────
    @ui.refreshable
    def grados_tabla() -> None:
        grados = sorted(_s["grados"], key=lambda g: g.numero)
        if not grados:
            empty_state(
                titulo="No hay grados definidos",
                descripcion="Crea los grados (Sexto, Décimo…) para darles significado real.",
            )
            return

        with ui.element("div").classes("w-full"):
            for g in grados:
                en_uso = _contar_grupos_por_grado(g.numero)
                with ui.element("div").classes("flex items-center gap-4 p-2 border-b"):
                    ui.label(str(g.numero)).classes("font-mono font-bold w-12")
                    ui.label(g.nombre or "—").classes("w-32 font-medium")
                    ui.label(f"{g.min_estudiantes}–{g.max_estudiantes} estud.").classes("w-32")
                    ui.label(f"{g.horas_semanales} h/sem").classes("w-24")
                    if en_uso:
                        ui.badge(f"{en_uso} grupo(s)").classes("badge-primary")
                    with ui.row().classes("gap-2 ml-auto"):
                        btn_icon("edit", on_click=lambda g=g: _abrir_editar_grado(g), tooltip="Editar")
                        btn_icon("delete", on_click=lambda n=g.numero: _eliminar_grado(n), tooltip="Eliminar", variante="danger")

    @ui.refreshable
    def tabla() -> None:
        grupos = _s["grupos"]
        if not grupos:
            empty_state(
                titulo="No hay grupos registrados",
                descripcion="Crea el primer grupo con el formulario de arriba.",
            )
            return

        filas = []
        for g in grupos:
            jornada_val = g.jornada.value if hasattr(g.jornada, "value") else str(g.jornada)
            filas.append({
                "id":           g.id,
                "codigo":       g.codigo,
                "grado":        g.grado or "—",
                "jornada_label": _JORNADA_LABELS.get(jornada_val, jornada_val),
                "capacidad":    g.capacidad_maxima,
            })

        with ui.element("div").classes("w-full"):
            for fila in filas:
                g_obj = next((x for x in grupos if x.id == fila["id"]), None)
                with ui.element("div").classes("flex items-center gap-4 p-2 border-b"):
                    ui.label(fila["codigo"]).classes("font-mono font-bold w-24")
                    ui.label(f"Grado {fila['grado']}").classes("w-20")
                    ui.label(fila["jornada_label"]).classes("w-28")
                    ui.label(f"{fila['capacidad']} estudiantes").classes("w-32")
                    with ui.row().classes("gap-2 ml-auto"):
                        btn_icon("edit", on_click=lambda g=g_obj: _abrir_editar(g), tooltip="Editar")
                        btn_icon("delete", on_click=lambda gid=fila["id"], cod=fila["codigo"]: _eliminar_grupo(gid, cod), tooltip="Eliminar", variante="danger")

    # ── Contenido principal ───────────────────────────────────────────────────
    def contenido() -> None:
        with ui.element("div").classes("page-stack"):

            # Panel: catálogo de grados
            with ui.element("div").classes("panel-card"):
                with ui.row().classes("items-center gap-2 mb-3"):
                    ui.label("Grados").classes("text-base font-semibold")
                    ui.badge(str(len(_s["grados"]))).classes("badge-primary")
                    btn_icon("add", on_click=_abrir_crear_grado, tooltip="Nuevo grado")
                    btn_icon("refresh", on_click=lambda: (_cargar_grados(), grados_tabla.refresh()), tooltip="Recargar")
                grados_tabla()

            # Panel de gestión de grupos
            with ui.element("div").classes("panel-card mt-4"):

                # Formulario de creación
                ui.label("Crear nuevo grupo").classes("text-base font-semibold mb-2")
                with ui.row().classes("gap-3 flex-wrap items-end"):
                    cod = ui.input("Código *", placeholder="601").classes("w-28").bind_value(
                        _s, "form_codigo"
                    )
                    # Asegura un valor inicial dentro del catálogo
                    _s["form_grado"] = _grado_valido(_s["form_grado"])
                    grd = ui.select(
                        _opciones_grado(),
                        label="Grado",
                    ).classes("w-40").bind_value(_s, "form_grado")
                    jor = ui.select(
                        {v: k for k, v in _JORNADAS.items()},
                        value="UNICA",
                        label="Jornada",
                    ).classes("w-36").bind_value(_s, "form_jornada")
                    cap = ui.number("Capacidad", value=40, min=1).classes("w-28").bind_value(
                        _s, "form_capacidad"
                    )
                    btn_primary("Crear grupo", on_click=_crear_grupo, icon="add").classes("mt-1")

            # Tabla de grupos
            with ui.element("div").classes("panel-card mt-4"):
                with ui.row().classes("items-center gap-2 mb-3"):
                    ui.label("Grupos registrados").classes("text-base font-semibold")
                    ui.badge(str(len(_s["grupos"]))).classes("badge-primary")
                    btn_icon("refresh", on_click=lambda: (_cargar_estado(), tabla.refresh()), tooltip="Recargar")
                tabla()

    app_layout(
        ctx,
        contenido,
        page_titulo    = "Gestión de Grupos",
        page_subtitulo = "Crea y administra los grupos académicos de la institución",
        page_icono     = Icons.GROUPS,
        mostrar_contexto = False,
    )


__all__ = ["grupos_page"]
