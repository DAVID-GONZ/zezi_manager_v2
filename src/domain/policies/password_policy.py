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
  - longitud >= LONGITUD_MINIMA (10),
  - longitud <= LONGITUD_MAXIMA (128),
  - al menos una letra mayúscula,
  - al menos una letra minúscula,
  - al menos un dígito,
  - al menos un carácter especial,
  - distinta del `username` (comparación case-insensitive) cuando se provee,
  - no pertenece a la lista de contraseñas comunes prohibidas.

NUNCA se loguea ni se persiste la contraseña aquí: estas funciones solo la
inspeccionan en memoria y devuelven mensajes/errores, nunca el valor.
"""
from __future__ import annotations

LONGITUD_MINIMA = 10
LONGITUD_MAXIMA = 128

# Contraseñas triviales que cumplen las reglas de composición pero son
# predecibles. Comparación case-insensitive.
_PASSWORDS_PROHIBIDAS: frozenset[str] = frozenset(
    p.lower()
    for p in (
        "Password1!",
        "Password123!",
        "Passw0rd!",
        "Qwerty12345!",
        "Abc12345678!",
        "Admin12345!",
        "Welcome123!",
        "Letmein123!",
        "Changeme123!",
        "Iloveyou123!",
        "P@ssw0rd123",
        "Superman123!",
        "Master12345!",
        "Trustno1234!",
        "Dragon12345!",
        "Shadow12345!",
        "Michael1234!",
        "Football123!",
        "Baseball123!",
        "Monkey12345!",
        "Qwerty1234!",
        "Abcdef12345!",
        "Zxcvbnm1234!",
        "Asdfghjkl12!",
        "1234567890Aa!",
    )
)


def errores_password(
    password: str, *, username: str | None = None
) -> list[str]:
    """
    Devuelve la lista de mensajes de error de la contraseña dada.

    Lista vacía significa que la contraseña es válida. El orden es estable
    para que el primer mensaje sea predecible al usarse en `validar_password`.
    """
    pwd = password or ""
    errores: list[str] = []

    if len(pwd) < LONGITUD_MINIMA:
        errores.append(
            f"La contraseña debe tener al menos {LONGITUD_MINIMA} caracteres."
        )

    if len(pwd) > LONGITUD_MAXIMA:
        errores.append(
            f"La contraseña no debe exceder {LONGITUD_MAXIMA} caracteres."
        )

    if not any(c.isupper() for c in pwd):
        errores.append(
            "La contraseña debe incluir al menos una letra mayúscula."
        )

    if not any(c.islower() for c in pwd):
        errores.append(
            "La contraseña debe incluir al menos una letra minúscula."
        )

    if not any(c.isdigit() for c in pwd):
        errores.append(
            "La contraseña debe incluir al menos un número."
        )

    if not any(not c.isalnum() for c in pwd):
        errores.append(
            "La contraseña debe incluir al menos un carácter especial."
        )

    if username is not None and pwd.strip().lower() == username.strip().lower() \
            and pwd != "":
        errores.append(
            "La contraseña no puede ser igual al nombre de usuario."
        )

    if pwd.lower() in _PASSWORDS_PROHIBIDAS:
        errores.append(
            "Esa contraseña es demasiado común. Elige una más original."
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
        f"Máximo {LONGITUD_MAXIMA} caracteres.",
        "Al menos una letra mayúscula.",
        "Al menos una letra minúscula.",
        "Al menos un número.",
        "Al menos un carácter especial.",
    ]


__all__ = [
    "LONGITUD_MAXIMA",
    "LONGITUD_MINIMA",
    "errores_password",
    "requisitos_password",
    "validar_password",
]
