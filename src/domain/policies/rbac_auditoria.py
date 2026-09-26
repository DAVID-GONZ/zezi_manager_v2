"""
Política RBAC de auditoría
===========================

Funciones puras (sin estado, sin dependencias de infraestructura ni interfaz)
que codifican QUIÉN puede leer la huella de auditoría de un registro.

Es la fuente de verdad para el historial de cambios (obs_10) y la futura
bitácora institucional (obs_11). Se usa como defensa en profundidad: tanto el
servicio (enforcement real) como la vista (gating del control) consultan esta
función para no divergir.

Roles auditores: admin, director, coordinador.
  - admin      → opera cross-tenant; acceso total a audit_log.
  - director   → equipo directivo del colegio; lector natural del historial.
  - coordinador → seguimiento disciplinario y académico; requiere historial.
  - profesor, estudiante, apoderado → sin acceso al historial de cambios.

Los roles se manejan como strings (el valor del enum Rol) para que la política
sea utilizable desde cualquier capa sin acoplarse al tipo Enum. Acepta tanto
strings como objetos con atributo `.value` (p.ej. el enum Rol).
"""

from __future__ import annotations

# Conjunto de roles con permiso de leer el historial de cambios de un registro.
_ROLES_AUDITORES: frozenset[str] = frozenset({"admin", "director", "coordinador"})

# Roles del equipo directivo del colegio con acceso a la bitácora institucional.
# El admin NO se incluye porque tiene su propia vista cross-tenant (/admin/auditoria).
_ROLES_BITACORA_INSTITUCIONAL: frozenset[str] = frozenset({"director", "coordinador"})

# obs_12: roles con permiso de exportar la bitácora (R13).
# admin + equipo directivo: quienes leen también pueden exportar (necesitan la evidencia).
_ROLES_EXPORTAR_BITACORA: frozenset[str] = frozenset({"admin", "director", "coordinador"})

# obs_12: solo el admin puede purgar (R13).
# El mismo rol que opera cross-tenant y puede ver todo es el único que puede borrar.
_ROLES_PURGAR_BITACORA: frozenset[str] = frozenset({"admin"})


def _normalizar(rol: object) -> str:
    """Normaliza un rol (string o enum con `.value`) a string en minúsculas."""
    if rol is None:
        return ""
    valor = getattr(rol, "value", rol)
    return str(valor).strip().lower()


def puede_ver_historial(actor_rol: object) -> bool:
    """
    True si el rol puede leer el historial de cambios de un registro.

    Acepta tanto strings como el enum ``Rol`` (o cualquier objeto con
    atributo ``.value``).

    Args:
        actor_rol: Rol del actor (string, Rol enum o None).

    Returns:
        True para admin, director y coordinador; False para el resto.
    """
    return _normalizar(actor_rol) in _ROLES_AUDITORES


def puede_ver_bitacora_institucional(actor_rol: object) -> bool:
    """
    True si el rol puede ver la bitácora institucional (``/institucion/auditoria``).

    Solo el equipo directivo del colegio (director y coordinador). El admin
    tiene su propia vista cross-tenant (``/admin/auditoria``) y no se incluye
    aquí (obs_11, R2).

    Acepta tanto strings como el enum ``Rol`` (o cualquier objeto con
    atributo ``.value``).

    Args:
        actor_rol: Rol del actor (string, Rol enum o None).

    Returns:
        True para director y coordinador; False para admin y el resto.
    """
    return _normalizar(actor_rol) in _ROLES_BITACORA_INSTITUCIONAL


def puede_exportar_bitacora(actor_rol: object) -> bool:
    """
    True si el rol puede exportar la bitácora de auditoría (obs_12, R13).

    admin, director y coordinador pueden exportar. La exportación es el
    mecanismo de salida de evidencia (R1): quienes leen también la necesitan.

    Acepta tanto strings como el enum ``Rol`` (o cualquier objeto con
    atributo ``.value``).

    Args:
        actor_rol: Rol del actor (string, Rol enum o None).

    Returns:
        True para admin, director y coordinador; False para el resto.
    """
    return _normalizar(actor_rol) in _ROLES_EXPORTAR_BITACORA


def puede_purgar_bitacora(actor_rol: object) -> bool:
    """
    True si el rol puede purgar (archivar y eliminar) la bitácora (obs_12, R13).

    Solo el admin puede purgar. La purga es irreversible y solo corresponde
    al rol con visibilidad total del sistema.

    Acepta tanto strings como el enum ``Rol`` (o cualquier objeto con
    atributo ``.value``).

    Args:
        actor_rol: Rol del actor (string, Rol enum o None).

    Returns:
        True únicamente para admin; False para todos los demás.
    """
    return _normalizar(actor_rol) in _ROLES_PURGAR_BITACORA


__all__ = [
    "_ROLES_AUDITORES",
    "_ROLES_BITACORA_INSTITUCIONAL",
    "_ROLES_EXPORTAR_BITACORA",
    "_ROLES_PURGAR_BITACORA",
    "puede_exportar_bitacora",
    "puede_purgar_bitacora",
    "puede_ver_bitacora_institucional",
    "puede_ver_historial",
]
