# Diseño: Coherencia de roles en el enrutado (mejora_04_enrutado_roles)

## 1. Cambio principal (R1/R2)

En `main.py::registrar_rutas_ui()`, el alias `/informes` pasa de `AUTENTICADO` a
`_AULA` (espeja a su destino `/informes/estadisticos`):

```python
registrar_pagina(
    "/informes",
    redirigir_a("/informes/estadisticos"),
    roles=_AULA,          # antes: AUTENTICADO
)
```

`/evaluacion/cierre` ya usa `_DIR_COORD` == roles de su destino
`/evaluacion/cierre-periodo`: correcto, no se toca.

## 2. Regla general para futuros alias

Un alias de redirección **hereda los roles de su destino**. Se documenta como
convención junto al helper `redirigir_a` (comentario en `main.py`) para que no
vuelva a divergir.

## 3. Barrido de consistencia (R3/R4)

Con `src/interface/auth/rutas_registradas()` y `roles_de_ruta()` (registro central),
verificar en un test o script:
- Todo alias de redirección apunta a una ruta **registrada** (R4).
- Los roles del alias == roles del destino (R1).
- La visibilidad de menú (`layout._rol_permitido_en_ruta`) no expone rutas a roles
  que el guard denegaría (cerrar hallazgos de `audit_menu_rutas`).

## 4. Alternativa descartada

Se consideró **dejar `/informes` en `AUTENTICADO` y no redirigir a una página
`_AULA`** (p. ej. una landing propia de informes accesible a todos). Se descartó
porque no hay tal landing y crearla es alcance nuevo; espejar roles es el cambio
mínimo y correcto.

## 5. Manejo de errores

Sin cambios: el guard central ya traduce la denegación a toast + `/inicio`.

## Nota de implementación

Cambio de baja superficie (una línea + posible test guardarraíl). El valor está en
el **test** que fija la invariante "roles(alias) == roles(destino)" para impedir
regresiones futuras.
