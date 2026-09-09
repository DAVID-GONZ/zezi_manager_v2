# Requisitos: Puerta de huella (obs_02_puerta_huella)

> **Contexto:** `docs/auditoria_observabilidad_2026-09-08.md` §1.
> **Depende de:** `obs_01_huella_actor` (define el helper que la puerta busca).
> **Habilita:** los tramos `obs_04a/b/c`, que se miden contra esta puerta.

R1: EL SISTEMA DEBE disponer de una verificación automática que identifique todo método
    de servicio que persista datos sin registrar la operación en la bitácora de cambios.

R2: EL SISTEMA DEBE fallar la puerta de calidad cuando exista un método que persista
    datos sin registro y que no esté declarado como deuda conocida.

R3: EL SISTEMA DEBE mantener la lista de deuda conocida de forma que solo pueda
    reducirse, y DEBE fallar tanto si la lista crece como si contiene una entrada que ya
    dejó de ser deuda.

R4: EL SISTEMA DEBE reportar el inventario completo de métodos que persisten datos,
    indicando para cada uno si deja huella, y el total pendiente.

R5: EL SISTEMA DEBE reconocer el registro de la operación aunque la llamada esté
    repartida en varias líneas.

R6: EL SISTEMA DEBE verificar, ejecutando contra una base de datos real, que una
    escritura representativa de cada servicio cubierto produce un registro de bitácora
    con usuario e institución identificados.

R7: EL SISTEMA DEBE emitir su salida sin fallar en consolas que no usen UTF-8.

## Criterio de done

- Introducir a mano un método de servicio que escriba sin registrar hace fallar la puerta.
- Retirar de la deuda un servicio que sigue sin huella hace fallar la puerta.
- Dejar en la deuda un servicio que ya tiene huella hace fallar la puerta.
- `python scripts/init.py` ejecuta la puerta y respeta su código de salida.
