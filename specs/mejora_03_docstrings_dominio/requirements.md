# Requisitos: Docstrings de modelos de dominio (mejora_03_docstrings_dominio)

> **Origen:** `docs/analisis_arquitectura.md` §6 (hallazgo #8).
> **Tipo:** Calidad/documentación. Solo añade docstrings; cero cambios de lógica.

## Contexto

La cobertura de docstrings de `src/domain/models/` es del **28%** (135/484
métodos), según `docs/api_reference/dominio_modelos.md`. Muchos son validators o
propiedades triviales, pero los métodos de dominio, factories y validadores con
reglas no triviales carecen de descripción, lo que dificulta entender las
invariantes del negocio.

## Requisitos

R1: EL SISTEMA DEBE documentar con docstring cada método de dominio, factory y
    propiedad de `src/domain/models/` cuya intención no sea evidente por su firma.

R2: EL SISTEMA DEBE documentar cada `field_validator`/`model_validator` cuya regla
    de validación no sea trivial (más allá de "no vacío"), explicando qué invariante
    protege.

R3: EL SISTEMA DEBE alcanzar una cobertura de docstrings de modelos de al menos
    **85%** medida por `tools/gen_api_reference.py`.

R4: EL SISTEMA NO DEBE alterar firmas, lógica, nombres ni comportamiento de ningún
    método al añadir su docstring.

R5: EL SISTEMA DEBE mantener verde `python init.py` tras el backfill.

R6: Los docstrings DEBEN estar en español y ser concisos (1–3 líneas), coherentes
    con el estilo existente en esos módulos.
