"""
Política RBAC de gestión de usuarios
=====================================

Funciones puras (sin estado, sin dependencias de infraestructura ni interfaz)
que codifican QUIÉN puede asignar QUÉ rol y QUIÉN puede gestionar a QUIÉN.

Es la fuente de verdad de la matriz de roles. Se usa como defensa en
profundidad: tanto el servicio (enforcement real) como la vista (gating de
controles) consultan estas funciones para no divergir.

Matriz de asignación de roles (quién puede crear / promover a qué rol):
  admin    → {admin, director}
  director → {coordinador, profesor}
  otros    → {}  (no gestionan usuarios)

Gestión (reactivar / desactivar / resetear password / cambiar rol) del actor
sobre un usuario destino, según el rol actual del destino:
  admin    → puede gestionar a cualquier rol.
  director → puede gestionar solo a coordinador / profesor.
  otros    → no gestionan a nadie.

Los roles se manejan como strings (el valor del enum Rol) para que la política
sea utilizable desde cualquier capa sin acoplarse al tipo Enum. Acepta tanto
strings como objetos con atributo `.value` (p.ej. el enum Rol).
"""
from __future__ import annotations


# Matriz de asignación: actor_rol -> conjunto de roles que puede asignar/crear.
_ASIGNABLES: dict[str, frozenset[str]] = {
    "admin":    frozenset({"admin", "director"}),
    "director": frozenset({"coordinador", "profesor"}),
}

# Gestión: actor_rol -> conjunto de roles destino que puede gestionar.
_GESTIONABLES: dict[str, frozenset[str]] = {
    "admin":    frozenset({"admin", "director", "coordinador", "profesor",
                           "estudiante", "apoderado"}),
    "director": frozenset({"coordinador", "profesor"}),
}


def _normalizar(rol: object) -> str:
    """Normaliza un rol (string o enum con `.value`) a string en minúsculas."""
    if rol is None:
        return ""
    valor = getattr(rol, "value", rol)
    return str(valor).strip().lower()


def roles_asignables(actor_rol: object) -> set[str]:
    """
    Conjunto de roles (strings) que `actor_rol` puede asignar o crear.

    Retorna un conjunto vacío si el actor no gestiona usuarios.
    """
    return set(_ASIGNABLES.get(_normalizar(actor_rol), frozenset()))


def puede_asignar_rol(actor_rol: object, target_rol: object) -> bool:
    """True si `actor_rol` puede asignar/crear el rol `target_rol`."""
    return _normalizar(target_rol) in _ASIGNABLES.get(
        _normalizar(actor_rol), frozenset()
    )


def puede_gestionar(actor_rol: object, target_rol: object) -> bool:
    """
    True si `actor_rol` puede gestionar (reactivar / desactivar / resetear
    password / cambiar rol) a un usuario cuyo rol actual es `target_rol`.
    """
    return _normalizar(target_rol) in _GESTIONABLES.get(
        _normalizar(actor_rol), frozenset()
    )


__all__ = [
    "roles_asignables",
    "puede_asignar_rol",
    "puede_gestionar",
]
