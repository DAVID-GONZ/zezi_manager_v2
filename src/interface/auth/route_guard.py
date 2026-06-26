"""
src/interface/auth/route_guard.py
=================================
Guard central de autorización por ruta — DENY BY DEFAULT (paso_35).

La autorización deja de vivir opt-in dentro de cada página: una sola función,
`registrar_pagina`, registra el `@ui.page(ruta)` envolviendo la función de
página con un guard que aplica autenticación + rol ANTES de renderizar.

Fuente única de verdad
----------------------
Cada llamada a `registrar_pagina` puebla un registro interno `{ruta: roles}`.
`roles_de_ruta(ruta)` lo expone para que el NAV (layout.py) derive su
visibilidad del MISMO registro — sin listas de rol duplicadas que puedan
divergir.

Deny by default
---------------
`roles` es OBLIGATORIO (sin valor por defecto): es imposible registrar una
ruta sin declarar quién accede. Para rutas sin restricción de rol existen dos
sentinels explícitos:

  PUBLICO     → sin sesión requerida (`/`, `/login`, `/logout`).
  AUTENTICADO → cualquier usuario con sesión, sin importar el rol (`/inicio`).

Cualquier otro valor debe ser un conjunto de miembros del enum `Rol`.

Decisión del guard (por petición)
---------------------------------
  PUBLICO                              → render directo.
  sin sesión                          → redirige a /login.
  AUTENTICADO con sesión              → render.
  rol permitido                       → render.
  rol NO permitido                    → toast "Acceso no autorizado" + /inicio.

La lógica de decisión vive en `decidir_acceso`, una función pura y testeable
sin servidor NiceGUI; el wrapper solo traduce su veredicto a navegación/render.
"""
from __future__ import annotations

from enum import Enum
from typing import Callable, Iterable

from src.domain.models.usuario import Rol


# ── Sentinels de acceso ───────────────────────────────────────────────────────
class _Sentinel(Enum):
    """Sentinels de acceso para rutas sin restricción de rol."""
    PUBLICO = "publico"
    AUTENTICADO = "autenticado"

    def __repr__(self) -> str:  # pragma: no cover - cosmético
        return f"<{self.value}>"


PUBLICO = _Sentinel.PUBLICO
AUTENTICADO = _Sentinel.AUTENTICADO

# Tipo de roles aceptado por registrar_pagina / almacenado en el registro.
RolesRuta = frozenset[Rol] | _Sentinel

# Veredictos posibles del guard.
ACCESO_OK = "ok"
ACCESO_LOGIN = "login"          # sin sesión → /login
ACCESO_DENEGADO = "denegado"    # con sesión pero rol no permitido → /inicio


# ── Registro único ruta → roles ───────────────────────────────────────────────
_REGISTRO: dict[str, RolesRuta] = {}


def _normalizar_roles(roles: RolesRuta | Iterable[Rol]) -> RolesRuta:
    """
    Normaliza el argumento `roles` a un sentinel o a un frozenset[Rol].

    Acepta los sentinels PUBLICO/AUTENTICADO o un iterable de miembros `Rol`.
    Rechaza strings sueltos y conjuntos vacíos (deny-by-default real: una ruta
    debe declarar acceso de forma inequívoca).
    """
    if isinstance(roles, _Sentinel):
        return roles
    if isinstance(roles, (str, bytes)):
        raise TypeError(
            "roles debe ser un conjunto de miembros de Rol o un sentinel "
            "(PUBLICO/AUTENTICADO), no un string."
        )
    try:
        normalizados = frozenset(roles)
    except TypeError as exc:
        raise TypeError(
            "roles debe ser iterable de Rol o un sentinel (PUBLICO/AUTENTICADO)."
        ) from exc
    if not normalizados:
        raise ValueError(
            "roles vacío: declara al menos un Rol, o usa el sentinel "
            "AUTENTICADO/PUBLICO de forma explícita."
        )
    for r in normalizados:
        if not isinstance(r, Rol):
            raise TypeError(f"roles debe contener miembros de Rol, no {r!r}.")
    return normalizados


def decidir_acceso(roles: RolesRuta, *, autenticado: bool, rol: str | None) -> str:
    """
    Decisión pura del guard (sin NiceGUI). Retorna uno de:
    ACCESO_OK, ACCESO_LOGIN, ACCESO_DENEGADO.

    - PUBLICO            → siempre OK.
    - sin sesión         → LOGIN.
    - AUTENTICADO        → OK (cualquier rol con sesión).
    - rol en `roles`     → OK.
    - rol fuera de roles → DENEGADO.
    """
    if roles is PUBLICO:
        return ACCESO_OK
    if not autenticado:
        return ACCESO_LOGIN
    if roles is AUTENTICADO:
        return ACCESO_OK
    # roles es frozenset[Rol]; comparar por el valor string del rol de sesión.
    valores = {r.value for r in roles}  # type: ignore[union-attr]
    if rol in valores:
        return ACCESO_OK
    return ACCESO_DENEGADO


def registrar_pagina(
    ruta: str,
    page_fn: Callable[..., None],
    *,
    roles: RolesRuta | Iterable[Rol],
    **page_fn_kwargs,
) -> None:
    """
    Registra `page_fn` en la ruta `ruta` envolviéndola con el guard central.

    `roles` es OBLIGATORIO (deny-by-default): pasa el sentinel PUBLICO /
    AUTENTICADO o un conjunto de miembros de `Rol`. Los `page_fn_kwargs`
    extra se reenvían a `page_fn` en cada render (p.ej. `seccion_inicial`).

    El veredicto del guard se calcula con `decidir_acceso` y se traduce a:
      - OK       → page_fn(**kwargs)
      - LOGIN    → ui.navigate.to("/login")
      - DENEGADO → toast_error("Acceso no autorizado") + ui.navigate.to("/inicio")
    """
    roles_norm = _normalizar_roles(roles)
    _REGISTRO[ruta] = roles_norm

    from nicegui import app, ui

    @ui.page(ruta)
    def _pagina_protegida() -> None:
        autenticado = bool(app.storage.user.get("autenticado"))
        rol = app.storage.user.get("usuario_rol")
        veredicto = decidir_acceso(roles_norm, autenticado=autenticado, rol=rol)

        if veredicto == ACCESO_LOGIN:
            ui.navigate.to("/login")
            return
        if veredicto == ACCESO_DENEGADO:
            from src.interface.design.components import toast_error
            toast_error("Acceso no autorizado")
            ui.navigate.to("/inicio")
            return
        # A2 (seguridad_01) — cambio forzado de contraseña: deny-by-default real.
        # Si la sesión está marcada y la ruta no es /cambiar-password ni /logout,
        # se fuerza el cambio antes de servir cualquier otra página.
        if (
            autenticado
            and app.storage.user.get("debe_cambiar_password")
            and ruta not in ("/cambiar-password", "/logout")
        ):
            ui.navigate.to("/cambiar-password")
            return
        # B1 (seguridad_04) — sync central del contexto antes de renderizar.
        # Centraliza la reconstrucción de los ContextVar de servicios
        # (solo_lectura + scope de institución) en el guard, de modo que TODA
        # petición protegida los sincronice independientemente de lo que recuerde
        # la página. Defensa en profundidad: una página de mutación futura que
        # olvide llamar a desde_storage() ya no correría con el flag heredado.
        # Import perezoso: este módulo de dominio/auth no debe arrastrar NiceGUI
        # en import-time, y desde_storage() requiere el contexto de petición.
        from src.interface.context.session_context import SessionContext
        SessionContext.desde_storage()
        page_fn(**page_fn_kwargs)


def roles_de_ruta(ruta: str) -> RolesRuta | None:
    """
    Roles declarados para `ruta` (sentinel o frozenset[Rol]); None si la ruta
    no está registrada. Consumido por el NAV para derivar su visibilidad.
    """
    return _REGISTRO.get(ruta)


def rutas_registradas() -> dict[str, RolesRuta]:
    """Copia del registro completo `ruta → roles` (para tests/diagnóstico)."""
    return dict(_REGISTRO)


__all__ = [
    "PUBLICO",
    "AUTENTICADO",
    "registrar_pagina",
    "roles_de_ruta",
    "rutas_registradas",
    "decidir_acceso",
    "ACCESO_OK",
    "ACCESO_LOGIN",
    "ACCESO_DENEGADO",
]
