# Requisitos: Coherencia de roles en el enrutado (mejora_04_enrutado_roles)

> **Origen:** evaluación del enrutado de `main.py` (alias `/informes`) +
> diagnóstico `specs/audit_menu_rutas/spec.md`.
> **Tipo:** Corrección de consistencia (bajo riesgo). Sin cambio de capacidades.

## Contexto

Se añadieron rutas-alias que redirigen a una página concreta
(`/informes → /informes/estadisticos`, `/evaluacion/cierre → /evaluacion/cierre-periodo`).
El alias `/informes` se registró con `roles=AUTENTICADO`, más laxo que su destino
`/informes/estadisticos` (`_AULA`). Un admin (autenticado, fuera de `_AULA`) pasa
el guard del alias y luego es denegado en el destino: rebote redirección→denegación
en vez de una decisión limpia. No es hueco de seguridad (el destino sigue
protegido), pero es una inconsistencia.

## Requisitos

R1: EL SISTEMA DEBE registrar cada ruta-alias de redirección con el mismo conjunto
    de roles que su ruta de destino, de modo que la autorización se decida una sola
    vez en el alias.

R2: CUANDO un usuario sin el rol requerido navega a una ruta-alias, EL SISTEMA DEBE
    denegar el acceso en el alias (toast + navegación a inicio) sin rebotar a través
    del destino.

R3: EL SISTEMA DEBE mantener la coherencia entre los roles de acceso de cada ruta y
    la visibilidad de su entrada de menú, de acuerdo con los hallazgos del
    diagnóstico de menú/rutas.

R4: EL SISTEMA NO DEBE dejar rutas-alias que apunten a un destino no registrado.

R5: EL SISTEMA DEBE conservar verde `python init.py`, incluidos los tests de
    autorización de rutas.
