# Diseño: Docstrings de modelos de dominio (mejora_03_docstrings_dominio)

## 1. Fuente de la lista de trabajo

`tools/gen_api_reference.py` ya marca cada método sin docstring como
`⚠️ sin docstring` en `docs/api_reference/dominio_modelos.md`, con una tabla de
cobertura por archivo. Esa es la lista de trabajo autoritativa; se regenera para
medir el progreso (R3).

## 2. Regla del cambio (idéntica a mejora ya aplicada en servicios)

- **Solo insertar docstrings** como primera sentencia del cuerpo. Cero cambios de
  firma, lógica, orden o imports (R4).
- Leer el cuerpo del método para describir con precisión; no inventar comportamiento.
- Triviales aceptables en una línea; validadores con regla no trivial explican la
  invariante (p. ej. "La suma de pesos de categorías de un periodo no puede exceder
  1.0").
- Español, 1–3 líneas, estilo coherente con el módulo (R6).

## 3. Criterio de "no trivial"

No es obligatorio documentar getters/propiedades de una línea evidentes (p. ej.
`nombre_display`). Sí es obligatorio: métodos de transición de estado, factories
(`para_creacion`, `desde_*`), cálculos, y validadores con lógica de negocio. El
umbral del 85% (R3) da margen para omitir lo verdaderamente trivial.

## 4. Alternativa descartada

Se consideró **generar docstrings automáticamente** desde los nombres. Se descartó:
produce texto redundante ("Valida el documento") sin explicar la invariante; el
valor está en describir la **regla de negocio**, que requiere leer el método.

## 5. Verificación

`tools/gen_api_reference.py` recalcula la cobertura; `python init.py` garantiza que
los docstrings no rompieron el parseo ni introdujeron regresiones.

## Nota de implementación

Trabajar módulo por módulo (empezar por los de mayor densidad de lógica:
`evaluacion.py`, `cierre.py`, `configuracion.py`, `infraestructura.py`,
`habilitacion.py`), regenerando la referencia al cerrar cada uno para ver avanzar
el porcentaje.
