"""
Política de contraseñas (dominio puro)
=======================================

Funciones puras (sin estado, sin dependencias de infraestructura ni interfaz)
que codifican los requisitos mínimos que debe cumplir una contraseña elegida
por el usuario (cambiar / resetear-explícito / crear-explícito).

Es la fuente de verdad de la política de contraseñas. El servicio
(`usuario_service`) hace el enforcement real llamando a `validar_password`;
la vista muestra las reglas legibles vía un passthrough del servicio
(`requisitos_password`) para no acoplarse al dominio.

Reglas:
  - longitud >= LONGITUD_MINIMA (8),
  - contiene al menos una letra y al menos un dígito,
  - distinta del `username` (comparación case-insensitive) cuando se provee.

NUNCA se loguea ni se persiste la contraseña aquí: estas funciones solo la
inspeccionan en memoria y devuelven mensajes/errores, nunca el valor.
"""
from __future__ import annotations


# Longitud mínima exigida a una contraseña elegida por el usuario.
LONGITUD_MINIMA = 8


def errores_password(
    password: str, *, username: str | None = None
) -> list[str]:
    """
    Devuelve la lista de mensajes de error de la contraseña dada.

    Lista vacía significa que la contraseña es válida. El orden es estable
    (longitud, composición, igualdad-al-username) para que el primer mensaje
    sea predecible al usarse en `validar_password`.
    """
    pwd = password or ""
    errores: list[str] = []

    if len(pwd) < LONGITUD_MINIMA:
        errores.append(
            f"La contraseña debe tener al menos {LONGITUD_MINIMA} caracteres."
        )

    tiene_letra = any(c.isalpha() for c in pwd)
    tiene_digito = any(c.isdigit() for c in pwd)
    if not (tiene_letra and tiene_digito):
        errores.append(
            "La contraseña debe incluir al menos una letra y al menos un número."
        )

    if username is not None and pwd.strip().lower() == username.strip().lower() \
            and pwd != "":
        errores.append(
            "La contraseña no puede ser igual al nombre de usuario."
        )

    return errores


def validar_password(password: str, *, username: str | None = None) -> None:
    """
    Valida la contraseña; lanza `ValueError` con el primer mensaje si hay errores.

    No retorna nada cuando la contraseña es válida.
    """
    errores = errores_password(password, username=username)
    if errores:
        raise ValueError(errores[0])


def requisitos_password() -> list[str]:
    """
    Textos legibles de las reglas de la política, para mostrar en la UI.

    Devuelve primitivos (strings) para que cualquier capa pueda mostrarlos
    sin acoplarse al dominio.
    """
    return [
        f"Al menos {LONGITUD_MINIMA} caracteres.",
        "Al menos una letra y un número.",
        "Distinta del nombre de usuario.",
    ]


__all__ = [
    "LONGITUD_MINIMA",
    "errores_password",
    "validar_password",
    "requisitos_password",
]
