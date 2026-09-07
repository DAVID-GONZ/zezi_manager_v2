# Diseño: harness_01_integracion_en_puerta

## El agujero

`scripts/init.py` es la puerta que decide si el proyecto está en verde. Llama a
`run_tests.py` en modo `rapido`, y ese modo es:

```python
# scripts/run_tests.py:42-45
if modo == "rapido":
    return _pytest("-q", "-m", "not slow and not integration and not e2e and not browser", *extra)
```

**Cuatro familias completas de pruebas quedan fuera de la única puerta que se ejecuta.**
La infraestructura para correrlas ya existe —`run_tests.py` tiene modos `integration`,
`e2e`, `browser` y `completo`—, pero nada obliga a usarlos, así que nadie los usa.

Resultado medido el 2026-09-06:

```
scripts/init.py                      ->  TODO VERDE   (1868 passed)
pytest -m "integration or slow"      ->  30 failed, 246 passed
```

**El proyecto lleva en «verde» con 30 pruebas rotas.** Y llevan rotas desde `tenant_02` /
`tenant_03`, es decir, desde que se introdujo el `institucion_id` obligatorio.

## Por qué importa más de lo que parece

Las pruebas de integración son las únicas que ejercitan la ruta
`SELECT * → Modelo(**dict(row))`, presente en **25 puntos de los repositorios**. Ninguna
prueba unitaria la cubre, porque las unitarias usan `FakeRepository`.

Es decir: **la hidratación de entidades desde la base no la verifica nadie**, justo cuando
`datos_02_model_config_base` y `backend_07_repos_migracion` dependen de que sea correcta.
El diseño de `datos_02` tuvo que rodear este hueco midiendo la hidratación por su cuenta
(su T2), precisamente porque no podía apoyarse en esta suite.

## Composición de los 30 fallos

### 25 fallos — firmas desactualizadas (este paso)

Llamadas a repositorios sin el `institucion_id` que las interfaces vigentes exigen. Los 14
métodos afectados declaran hoy `institucion_id: TenantScope`, obligatorio y sin valor por
omisión.

| Repositorio | Métodos | Fallos |
|---|---|---|
| `SqliteConvivenciaRepository` | `listar_categorias` (6), `listar_registros`, `listar_plantillas` | 8 |
| `SqliteInfraestructuraRepository` | `get_plantilla_activa` (4), `listar_configs_generacion` (3), `listar_asignaturas`, `listar_areas` | 9 |
| `SqliteEstudianteRepository` | `listar_por_grupo`, `get_by_documento`, `existe_documento`, `contar_por_grupo` | 4 |
| `SqliteAsignacionRepository` | `listar_por_grupo`, `listar_por_docente` | 2 |
| `SqliteAlertaRepository` | `contar_pendientes` | 1 |
| `SqliteConfiguracionRepository` | `get_activa` | 1 |

Repartidos en 6 ficheros: `test_repositories.py` (11), `test_convivencia_categorias.py` (5),
`test_convivencia_35_entradas_seguimiento.py` (5), `test_franjas_repo.py` (4),
`test_disponibilidad_config_repo.py` (3),
`test_convivencia_14_promocion_comportamiento.py` (2).

**Son fallos de la prueba, no del código.** El código es correcto; las llamadas se
quedaron atrás.

### 5 fallos — desfase de zona horaria (NO es este paso)

```
ValidationError: 1 validation error for RegistroComportamiento
  fecha: Value error, La fecha del registro (2026-09-07) no puede ser futura.
```

**Son fallos del código, no de la prueba.** Los cubre
`datos_08_fecha_zona_horaria`, del que este paso **depende**: mientras exista ese defecto,
la puerta no puede quedar verde con integración encadenada.

## Decisiones

### D1 — El scope pasa el tenant explícito, nunca lo evita

Al actualizar las 25 llamadas hay dos formas de hacerlas compilar: pasar el
`institucion_id` de la institución sembrada, o pasar `"*"` (cross-tenant, admin).

**Se pasa el identificador concreto** (R2). `"*"` haría pasar la prueba sin verificar el
aislamiento, que es justo lo que `tenant_02`–`tenant_04` construyeron. Solo se usa `"*"`
donde la prueba verifique deliberadamente el comportamiento de administrador, y en ese
caso el nombre de la prueba debe decirlo.

Esto es R15 en concreto: **no se debilita una comprobación para que pase**.

### D2 — La puerta gana una familia, el modo rápido no la pierde

`scripts/init.py` pasa a ejecutar **dos** familias: `rapido` e `integration`, como bloques
separados con su propio encabezado y resultado (R10).

`run_tests.py rapido` se queda **exactamente como está** (R9): es el atajo del día a día y
debe seguir siendo veloz. Lo que cambia es la puerta, no la herramienta.

Coste medido: ~18 s la rápida, ~27 s la de integración. **Total ~45 s** (R11). Asumible
para una puerta que hoy tarda 18 s y no ve un tercio de lo que debería.

`e2e` y `browser` se quedan fuera por ahora: `e2e` requiere el entrypoint dedicado
`tests/e2e/e2e_app.py` y `browser` requiere `playwright install`. Incorporarlas es trabajo
propio; este paso cierra el agujero mayor y **deja constancia explícita** de los dos que
siguen abiertos (R13), en lugar de dejarlos en silencio como estaban.

### D3 — Cobertura de hidratación para los repositorios sin prueba

Arreglar las 25 llamadas devuelve la suite al estado que debió tener, pero no cubre R5:
hay repositorios sin ninguna prueba de integración.

El inventario de cuáles carecen de cobertura se levanta en T1 y se cierra en T5. El
criterio (R4, R6) es modesto y verificable: por cada repositorio, al menos una prueba que
recupere una fila real y construya su entidad.

### D4 — Que no vuelva a ocurrir (R12, R13)

Dos medidas, porque la causa fue doble —las pruebas se quedaron atrás **y** nadie lo vio—:

1. La puerta ejecuta integración (D2): una firma que cambie rompe la puerta el mismo día.
2. Una comprobación que falle si `init.py` deja de ejecutar alguna familia declarada,
   de modo que excluir una vuelva a ser una decisión visible y no un olvido.

## Dependencia

**Este paso no puede cerrarse antes que `datos_08_fecha_zona_horaria`.** Orden:

```
datos_08  ->  30 fallos bajan a 25   (arregla el defecto de zona horaria)
harness_01 ->  25 bajan a 0          (actualiza las firmas)
           ->  se encadena la puerta
```

Invertir el orden dejaría la puerta encadenada y en rojo, bloqueando todo lo demás.

## Alternativa descartada

**Cambiar el modo `rapido` para que incluya `integration`, en vez de añadir un bloque a la
puerta.**

Es un cambio de una línea y garantiza que cualquiera que corra la suite vea los fallos. Se
descarta porque destruye la utilidad del modo rápido: `run_tests.py rapido` existe para
ejecutarse muchas veces durante el desarrollo, y pasar de 18 s a 45 s en el ciclo corto
lleva a que se ejecute menos, no más. La distinción entre «lo que corro mientras trabajo»
y «lo que decide si el proyecto está verde» es correcta; el defecto no era esa distinción,
sino que la puerta se conformara con la primera.
