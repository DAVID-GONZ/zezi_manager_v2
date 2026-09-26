# Requisitos: Tests de esquema (backend_02b_tests_esquema)

> Ámbito: suite de tests que verifica la equivalencia entre el esquema
> declarado en `schema.py` y el esquema realmente aplicado en
> `sqlite_master`. Resuelve D11 de la auditoría (cero tests de esquema)
> y convierte D1 y D2 en fallos rojos reproducibles.

---

## Cobertura del esquema

R1: EL SISTEMA DEBE verificar que toda tabla declarada en `SCHEMA` existe
    en `sqlite_master` con el mismo nombre.

R2: EL SISTEMA DEBE verificar que las columnas de cada tabla coinciden en
    nombre, tipo y nullable entre la declaración y la base.

R3: EL SISTEMA DEBE verificar que las foreign keys declaradas existen
    realmente en la tabla aplicada (no hay FKs fantasma ni FKs faltantes).

R4: EL SISTEMA DEBE verificar que los índices declarados en `INDICES`
    existen en la base.

R5: EL SISTEMA DEBE verificar que los triggers declarados en `TRIGGERS`
    existen en la base.

R6: EL SISTEMA DEBE verificar que el orden de creación declarado en
    `SCHEMA` respeta las dependencias FK: una tabla no debe referenciar
    otra que aparece después en la lista.

---

## Detección de defectos conocidos

R7: EL test de orden de dependencias (R6) DEBE fallar si `grupos`
    referencia `usuarios` antes de que `usuarios` sea creada (D1).

R8: EL test de FKs (R3) DEBE fallar si `grupos.sala_id` no tiene
    `FOREIGN KEY` declarada (D2).

R9: LOS fallos de D1 y D2 DEBEN quedar como tests en `xfail` con
    `reason` explícito que referencie el defecto y el paso que lo
    resuelve (`backend_04`), de modo que el fallo sea esperado y
    documentado pero no bloquee la puerta.

---

## Robustez

R10: LA suite DEBE fallar ante cualquier alteración futura de `schema.py`
     que cambie tablas, columnas, FKs, índices o triggers sin actualizar
     los tests.

R11: LOS tests DEBEN ser independientes del orden en que se ejecuten.

R12: LOS tests NO DEBEN depender de datos sembrados — solo del schema vacío.
