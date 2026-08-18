"""
Política RBAC de convivencia (dirección de grupo)
=================================================

Función pura (sin estado, sin dependencias de infraestructura ni interfaz) que
codifica QUIÉN puede gestionar el comportamiento / la convivencia de un grupo.

A diferencia de `rbac_usuarios.py` (autoridad global por rol), la autoridad del
director de grupo es **por objeto**: no basta el rol, hay que saber si el actor
es director del grupo concreto en cuestión. Esta política separa las dos
mitades de esa decisión:

  - La resolución de datos ("¿es director de ESTE grupo?") vive en el servicio
    (`CatalogoAcademicoService.es_director_de_grupo`), que sí tiene acceso al
    repositorio de grupos.
  - La regla pura ("dado el rol y ese hecho booleano, ¿puede gestionar?") vive
    aquí, como fuente única de verdad consultable desde servicio y vista
    (defensa en profundidad, igual que rbac_usuarios).

Matriz de autorización de gestión de comportamiento
(`puede_gestionar_comportamiento(usuario_rol, es_director_de_grupo)`):

  rol           | es_director_de_grupo = True | es_director_de_grupo = False
  --------------|-----------------------------|-----------------------------
  admin         | False                       | False  (auditor técnico, NO edita)
  director      | True                        | True   (directivo, autoridad global)
  coordinador   | True                        | True   (directivo, autoridad global)
  profesor      | True                        | False  (solo su grupo dirigido)
  otros/None    | False                       | False

Decisión de diseño (admin): admin es un **auditor técnico**. Puede impersonar
("ver como") cualquier rol de un usuario de su tenant, pero **nunca edita datos
directamente** en nombre propio. Por eso NO figura entre los directivos con
autoridad de gestión aquí: cuando un admin gestiona convivencia, lo hace vía
impersonación, momento en el que su rol efectivo pasa a ser el del usuario
objetivo (director / coordinador / profesor) y esta política se evalúa con ese
rol, no con "admin".

Los roles se manejan como strings (el valor del enum Rol) para que la política
sea utilizable desde cualquier capa sin acoplarse al tipo Enum. Acepta tanto
strings como objetos con atributo `.value` (p.ej. el enum Rol).
"""

from __future__ import annotations

# Roles con autoridad global sobre convivencia (no dependen del objeto grupo).
# admin NO está aquí: es auditor técnico y nunca edita datos en nombre propio
# (gestiona solo mediante impersonación "ver como", con el rol del objetivo).
_DIRECTIVOS: frozenset[str] = frozenset({"director", "coordinador"})


def _normalizar(rol: object) -> str:
    """Normaliza un rol (string o enum con `.value`) a string en minúsculas."""
    if rol is None:
        return ""
    valor = getattr(rol, "value", rol)
    return str(valor).strip().lower()


def puede_gestionar_comportamiento(usuario_rol: object, es_director_de_grupo: bool) -> bool:
    """
    True si un usuario con rol `usuario_rol` puede gestionar el comportamiento /
    la convivencia de un grupo, dado el hecho `es_director_de_grupo` (si el
    usuario es director de ese grupo concreto).

    Regla:
      - directivos (director / coordinador) → True siempre.
      - profesor → True solo si `es_director_de_grupo` es True.
      - admin y cualquier otro rol (o None) → False. admin es auditor técnico:
        gestiona solo vía impersonación, con el rol efectivo del objetivo.

    Es una función pura: la resolución de `es_director_de_grupo` corresponde al
    servicio, que tiene acceso al repositorio de grupos.
    """
    if _normalizar(usuario_rol) in _DIRECTIVOS:
        return True
    if _normalizar(usuario_rol) == "profesor":
        return bool(es_director_de_grupo)
    return False


__all__ = [
    "puede_gestionar_comportamiento",
]
