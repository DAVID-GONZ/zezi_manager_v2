# horario_01_validacion_generacion — Validación de datos y preparación interactiva del generador de horarios

> Cierra los defectos detectados en la auditoría del 2026-09-03
> (`progress/review_generador_horario_2026-09-03.md`): las salas bloquean la
> generación pese a ser optativas, una corrida sin asignaciones deja un
> escenario vacío activable sin una sola incidencia, y la checklist de
> preparación mide magnitudes distintas de las que ejecuta el motor.

**Origen:** auditoría del leader sobre `src/services/generador_horario_service.py`
(1337 líneas) y sus páginas asociadas. Dos de los tres bloqueantes están
**reproducidos empíricamente** con los fakes de `tests/unit/services/test_generador_horario.py`
(evidencia en la sección «Evidencia reproducible»).

---

## Principios rectores (invariantes que esta spec establece)

Estos cinco enunciados son el criterio para resolver cualquier duda de diseño
durante la implementación. Si una tarea entra en conflicto con uno de ellos,
gana el principio.

1. **P1 — Las salas nunca bloquean.** Ni la colocación, ni el oráculo, ni la
   persistencia. Una sala faltante o repetida produce una **incidencia**, jamás
   un horario invalidado. El motor ya lo cumple; el oráculo y la UI, no.
2. **P2 — Ninguna corrida termina en silencio.** Si el resultado no es
   persistible, el usuario recibe siempre al menos una incidencia que dice
   *qué* falta y *dónde* corregirlo. Un `incidencias == []` con `valido=False`
   es un bug por definición.
3. **P3 — Un estado `"generado"` implica bloques reales.** No se crea escenario,
   no se transiciona la config y no se ofrece «Activar» si no hay bloques
   persistidos.
4. **P4 — La checklist mide lo que el motor ejecuta.** Cada puerta se evalúa
   sobre la `ConfigGeneracion` concreta (su año, periodo, plantilla y filtro de
   grupos) y sobre las **asignaciones reales**, no sobre el catálogo ni sobre el
   plan de estudios en abstracto. Una puerta `dura` verde debe garantizar que el
   motor no fallará por esa causa.
5. **P5 — La advertencia vive donde se toma la decisión.** El estado de
   preparación se muestra y se recalcula en la sección «Generar», junto al botón
   que dispara la generación, no solo en una pestaña aparte.

---

## Scope

```
src/services/generador_horario_service.py       (mapeo de sala, resultado vacío, rama muerta)
src/services/horario_service.py                 (oráculo: cruce de sala no bloqueante)
src/services/preparacion_horario_service.py     (reescritura de puertas + 4 puertas nuevas)
src/services/restriccion_generacion_service.py  (validar min <= max)
src/services/franja_service.py                  (solape y unicidad de orden)
src/services/sala_service.py                    (requiere_escritura + pertenencia)
src/domain/models/infraestructura.py            (normalizar HH:MM en Franja)
src/interface/presenters/academico/horarios_hub_presenter.py   (estado prep_*)
src/interface/pages/academico/horarios_hub.py   (panel de preparación en Generar)
container.py                                    (wiring de PreparacionHorarioService)
tests/unit/services/test_generador_horario.py   (casos de regresión nuevos)
tests/unit/services/test_preparacion_horario.py (NUEVO — hoy no existe)
tests/unit/services/test_horario_lote.py        (oráculo: sala no bloquea)
```

**Fuera de scope (no tocar en este paso):**
- El algoritmo de colocación (König, backtracking, hill-climbing). Sus
  resultados no cambian; solo cambia cómo se etiqueta y valida la salida.
- Los pesos del optimizador y `PESOS_PRINCIPALES` / `PESOS_AVANZADOS`.
- El rediseño visual de la parrilla.
- Los N+1 de consultas (anotados en T14 como deuda, no se resuelven aquí).

---

## Evidencia reproducible

Ejecutado durante la auditoría con los fakes existentes. Ambos deben pasar a
comportarse distinto al terminar esta spec.

**E1 — Salas faltantes producen filas que el oráculo rechaza.**
3 grupos con una materia `tipo_sala_requerido="laboratorio"` y **1 solo**
laboratorio registrado:

```
colocados = 9   no_colocados = 0   causas = {'sala_pendiente': 6}
Celdas (sala, dia, hora) con MAS DE UN bloque:
   ('Por asignar', 'Lunes', '07:00') -> 2 bloques
   ('Por asignar', 'Lunes', '08:00') -> 2 bloques
   ('Por asignar', 'Lunes', '09:00') -> 2 bloques
```

El motor colocó todo correctamente, pero `HorarioService.analizar_lote`
(`horario_service.py:690-693`) rechaza esas 6 filas como «Cruce: sala 'Por
asignar' ya ocupada» → `valido=False` → **no se persiste nada**.

**E2 — Corrida sin asignaciones: escenario vacío y cero incidencias.**

```
valido=False  total_req=0  colocados=0  incidencias=[]  escenario_id=100  estado config=generado
```

---

## Tareas

### Bloque A — Las salas dejan de bloquear (Principio P1)

#### T1 — El oráculo deja de invalidar por cruce de sala en el lote del generador  [x]

`src/services/horario_service.py`.

**Problema.** En `analizar_lote` (~línea 690):

```python
if sala != "Aula" and v.get("sala") == sala:
    ok = False
    motivo = f"Cruce: sala '{sala}' ya ocupada en ese horario."
```

`"Por asignar"` no es una sala física, pero pasa el filtro `!= "Aula"` y
provoca un cruce artificial entre dos clases que ni siquiera tienen sala.

**Cambios.**

1. Definir a nivel de módulo el conjunto de centinelas que **no** representan
   una sala física exclusiva:

   ```python
   # Cadenas que NO identifican una sala física: dos bloques que las comparten
   # no están en la misma habitación, así que nunca son un cruce.
   SALAS_NO_EXCLUSIVAS: frozenset[str] = frozenset({"", "Aula", "Por asignar"})
   ```

2. Sustituir la condición por `if sala not in SALAS_NO_EXCLUSIVAS and v.get("sala") == sala:`.

3. Añadir el parámetro `salas_bloquean: bool = True` a `analizar_lote` y a
   `aplicar_lote`. Cuando es `False`, un cruce de sala **no** marca `ok=False`:
   se acumula en una lista aparte y se devuelve como aviso. Los cruces de
   **docente** y de **grupo** siguen siendo duros siempre (son físicamente
   imposibles; una sala repetida solo es un dato que hay que corregir después).

4. Para transportar el aviso sin romper el DTO, añadir a `ReporteLoteDTO` un
   campo `avisos: list[str] = []` (`src/domain/models/infraestructura.py`,
   ~línea 1213) y poblarlo con una línea por cruce de sala detectado cuando
   `salas_bloquean=False`.

**Quién pasa qué:**
- `GeneradorHorarioService.generar` → `salas_bloquean=False` (P1).
- La carga masiva manual del hub (`_seccion_carga_masiva`) → mantiene el
  default `True`: ahí el usuario escribe la sala a mano y sí quiere el error.

**Verificación:** el caso E1 debe salir `valido=True`, con la incidencia de sala
pendiente presente y las 9 filas persistidas.

#### T2 — `_elegir_sala` respeta las aulas base ocupadas  [x]

`src/services/generador_horario_service.py` (~línea 731).

**Problema.** `_elegir_sala` solo consulta `ocupado_sala`, que se alimenta
exclusivamente de las clases con `tipo_sala_req`. Las **aulas base** de los
grupos (`sala_grupo_nombre`, ~línea 1214) nunca entran ahí, así que el motor
puede elegir para un laboratorio una sala que es simultáneamente el salón base
de otro grupo que sí está en clase a esa hora.

**Cambios.**
1. Construir `sala_base_de_grupo: dict[int, int]` (grupo_id → sala_id) junto a
   `sala_grupo_nombre` (~línea 505).
2. En `_colocar`, cuando el grupo tenga aula base y la lección **no** requiera
   tipo de sala, registrar también `ocupado_sala.add((sala_base_id, dia, o))`.
   En `_quitar` y `_desocupar`, hacer el `discard` simétrico.
3. `_elegir_sala` queda igual: al leer un `ocupado_sala` ahora completo, deja de
   elegir salas que en realidad están ocupadas.

**Cuidado:** esto es contabilidad, no una restricción nueva. `_puede_colocar`
**sigue sin mirar salas** (P1): si no queda ninguna sala libre, la clase se
coloca igual con la sala pendiente. No añadir ningún `return False` por sala.

**Verificación:** test nuevo `test_sala_base_no_se_reasigna_a_laboratorio`.

#### T3 — Puerta de preparación: aulas base duplicadas  [x]

`src/services/preparacion_horario_service.py`.

Nada impide hoy asignar la misma sala como aula base a dos grupos
(`salas.py:214`; no hay `UNIQUE` en `grupos.sala_id`, `schema.py:219`). Con T1
eso ya no invalida el horario, pero sigue siendo un dato erróneo que produce dos
grupos «en la misma habitación».

Añadir la puerta `aulas_base_unicas`, **severidad `advertencia`**,
`fix_ruta="/admin/salas"`. Detalle: lista los grupos que comparten aula, hasta 3
ejemplos más «y N más».

---

### Bloque B — Ninguna corrida termina en silencio (Principios P2 y P3)

#### T4 — Incidencia explícita cuando no hay nada que generar  [x]

`src/services/generador_horario_service.py`, método `generar`.

**Problema.** Tras cargar y filtrar asignaciones (~línea 566), si la lista queda
vacía el método sigue adelante: König «resuelve» un problema vacío, `bloques`
queda en `[]`, la rama `else: resultado.valido = False` (~línea 1310) **no añade
mensaje**, y aun así se crea escenario y se transiciona la config.

**Cambios.** Inmediatamente después del filtro `config.grupos`, distinguir dos
casos y añadir la incidencia correspondiente antes de continuar:

- `asignaciones` vacía y `config.grupos` vacío →
  `"No hay asignaciones activas en el periodo N. Crea las asignaciones docente–grupo–asignatura antes de generar."`
- `asignaciones` vacía y `config.grupos` no vacío →
  `"Los N grupo(s) seleccionados en esta configuración no tienen asignaciones activas en el periodo."`
- `asignaciones` no vacía pero `total_requeridos == 0` (todas las asignaturas
  resolvieron a 0 horas) →
  `"Las N asignaciones del periodo suman 0 horas semanales: revisa el plan de estudios del grado."`

Y en la rama final `else` (~línea 1310), cuando `filas` está vacío pero ninguna
de las anteriores disparó, añadir un genérico
`"El motor no colocó ningún bloque; revisa las incidencias anteriores."`

**Invariante a testear:** `not resultado.valido` ⇒ `len(resultado.incidencias) > 0`.
Nunca puede darse un resultado inválido y mudo.

#### T5 — No crear escenario ni transicionar a `"generado"` sin bloques  [x]

`src/services/generador_horario_service.py` (~líneas 1252-1270 y 1345-1350).

**Problema.** `crear_escenario=True` crea el escenario **antes** de saber si hay
algo que persistir, y `cambiar_estado_config(config_id, "generado")` se ejecuta
siempre, aunque no se haya escrito ni un bloque.

**Cambios.**
1. Mover la creación del escenario a **después** de comprobar que
   `bloques` no está vacío. Si `bloques == []`, devolver el resultado con las
   incidencias de T4, `escenario_id=None`, sin tocar la config y **sin** borrar
   el `escenario_destino_id` anterior (una corrida fallida no debe destruir el
   escenario de la corrida buena previa — hoy `eliminar_escenario` se llama
   incondicionalmente en la línea 1255).
2. `cambiar_estado_config(config_id, "generado")` solo si
   `resultado.valido and resultado.colocados > 0`.
3. `actualizar_config_generacion` con el nuevo `escenario_destino_id` solo si se
   creó escenario.

**Verificación:** el caso E2 debe salir con
`escenario_id=None`, `estado config=None` (sin transición) e `incidencias` con
un mensaje explicativo.

#### T6 — «Activar este escenario» exige un escenario con bloques  [x]

`src/interface/pages/academico/horarios_hub.py`, `_gen_render_detalle` (~1718-1731).

**Problema.**

```python
puede_activar_config = bool(escenario_destino) and estado == "generado"
```

No comprueba validez. Tras una corrida fallida el botón aparece y activar el
escenario vacío **desactiva el horario real del año** (`activar_escenario`
desactiva todos los demás del año lectivo).

**Cambios.**
1. Añadir a `EscenarioHorarioService` un método
   `tiene_bloques(escenario_id: int) -> bool` (cuenta sobre
   `listar_horario_escenario`, o mejor un `contar_bloques_escenario` en el repo
   si ya existe una consulta equivalente).
2. `puede_activar_config = bool(escenario_destino) and estado == "generado" and svc.tiene_bloques(escenario_destino)`.
3. Cuando `escenario_destino` existe pero está vacío, en lugar del botón
   mostrar un aviso ámbar: *«El escenario de la última generación está vacío;
   vuelve a generar antes de activarlo.»*
4. La confirmación de `_gen_activar_escenario` debe indicar cuántos bloques se
   van a activar.

#### T7 — El resultado en pantalla distingue «no hay datos» de «no cupo»  [x]

`horarios_hub.py`, `_gen_render_resultado` (~1582-1640).

Hoy las incidencias son texto plano sin severidad. Cambios:

1. Agrupar por **causa** usando `resultado.causas` (el motor ya lo devuelve:
   `sin_slots`, `docente_ocupado`, `sin_disponibilidad`, `tope_carga`,
   `max_dia`, `grupo_saturado`, `sala_pendiente`, `min_dia_docente`…) y mostrar
   un bloque por causa con su conteo, no una lista plana de N líneas repetidas.
2. Mapa `CAUSA → (etiqueta legible, fix_ruta)` en el **servicio** (no en la
   página; ver `regla-logica-negocio-al-backend`), por ejemplo en
   `GeneradorHorarioService` junto a `catalogo_pesos()`. `sala_pendiente` se
   pinta como **informativo** (azul), nunca como error (P1).
3. Sustituir los IDs crudos de las incidencias del motor
   (`"PRE-VUELO: docente 7 requiere…"`, `"No colocado: G3/Materia 5…"`) por
   nombres. El motor ya tiene `a.grupo_codigo`, `a.asignatura_nombre` y
   `a.docente_nombre` en `AsignacionInfo`: usarlos al construir el texto en
   lugar del `usuario_id` / `grupo_id` numérico.
4. Mostrar `relajadas` como una línea propia («Se relajaron: tope diario
   estricto»), y `presupuesto_agotado` con su badge ya existente.

---

### Bloque C — La checklist mide lo que el motor ejecuta (Principio P4)

#### T8 — `validar()` recibe la configuración concreta  [x]

`src/services/preparacion_horario_service.py` + `container.py` + `horarios_hub.py`.

**Problema (B3 de la auditoría).** La checklist evalúa un año, un periodo y una
plantilla que pueden no ser los de la config que el usuario va a generar:

- Preparar usa `_s["anio_id"] / _s["periodo_id"]` (hub:1774-1775), derivados de
  `configuracion_service().get_activa()` + primer periodo no cerrado.
- Generar usa `_s["gen_anio_id"] = ctx.anio_id or …` y
  `periodo_service().get_activo(...)` (hub:203-218) — otra resolución.
- La plantilla evaluada (hub:1778-1793) es `gen_plantilla_sel`, o la de la config
  seleccionada, o la primera activa — no necesariamente la de la config generada.

**Cambios.**

1. Nueva firma primaria:

   ```python
   def validar_config(self, config_id: int) -> ReportePreparacionDTO:
       """Evalúa las puertas contra la ConfigGeneracion real: su anio_id,
       periodo_id, plantilla_id y filtro de grupos."""
   ```

   Lee la config vía el repo de infraestructura y deriva de ella los cuatro
   parámetros. `config is None` → una única puerta `dura` en rojo.

2. Mantener `validar(anio_id, periodo_id, plantilla_id)` como envoltorio
   (`grupos_filtro=None`) para no romper llamadas existentes ni tests.

3. Todas las puertas reciben además `grupos_filtro: set[int] | None`. Cuando no
   es `None`, `grupos`, `asignaciones` y la cobertura del plan se restringen a
   esos grupos — exactamente como hace el motor en `generar` (~línea 568).

4. Inyectar el repo de infraestructura ya presente (`self._infra`) — no hace
   falta wiring nuevo en `container.py` salvo que se decida inyectar
   `restriccion_generacion_service` para leer la config; en ese caso, añadirlo
   al `lambda` de `Container.preparacion_horario_service` (container.py:597-609).

#### T9 — Reescribir P2 y P3 sobre los datos reales  [x]

**P2 `asignaturas_con_horas` es una puerta muerta.**
`Asignatura.horas_semanales` es `Field(default=1, ge=1)` (models:105) y el schema
tiene `CHECK(horas_semanales > 0)` (schema:199): `horas_semanales < 1` es
**estructuralmente imposible**. La puerta siempre sale verde y da falsa
seguridad; y por ser `dura`, si alguna vez fuese roja bloquearía por una
asignatura del catálogo que ninguna asignación usa.

Reemplazarla por `horas_plan_asignaciones` (`dura`, `fix_ruta="/admin/plan-estudios"`):
para cada asignación activa del periodo, resolver sus horas con **la misma
función que el motor** (`plan.horas_de(grado_del_grupo, asignatura_id)`, con
fallback a las horas globales) y reportar las que resuelvan a `0`. Ese es el
caso real que hace que una asignación se genere sin ninguna hora, en silencio.

**P3 `horas_grupo_vs_slots` mide el plan, el motor mide las asignaciones.**
Hoy `_p3_horas_grupo_vs_slots(grupos, plantilla, franjas)` ni siquiera recibe las
asignaciones: usa `plan.horas_por_grado(g.grado)`. Si el plan está vacío o corto
pero el grupo tiene 40 h asignadas, la puerta sale verde y el fallo aparece
recién en el pre-vuelo del motor (gen:686-690).

Reescribirla para que calcule la **demanda real por grupo** sumando las horas de
las asignaciones activas (misma resolución que T9) y la compare contra los cupos
`franjas_lectivas × días_activos`. Debe cubrir también los grupos con
`grado is None`, que hoy se saltan (`continue`, prep:239) y cuyas horas el motor
sí calcula por fallback (`_horas_de`, gen:513-519).

Conservar en el detalle el desglose `N franjas × M días` que ya tiene, y añadir
el nombre del grupo y sus horas.

#### T10 — P4 sube a `dura` (el tope de carga sí bloquea)  [x]

`_p4_capacidad_docente` es hoy `severidad="advertencia"`, pero en el motor
`carga_horaria_max` es una restricción **dura**:

- `_puede_colocar` la rechaza (gen:751-753),
- `_coloreo_activable` desactiva König si algún docente la excede (gen:967-970),
- la escalera de relajación (gen:1058-1077) relaja `max_horas_dia` y
  `franjas_reunion` pero **nunca** el tope de carga,
- y el oráculo la vuelve a aplicar (horario:706-719).

Resultado: excederla garantiza un horario parcial que no se persiste. Cambiar la
severidad a `"dura"` y ajustar el detalle para que diga explícitamente que
bloquea la generación.

#### T11 — Cuatro puertas nuevas para lo que hoy solo se detecta al generar  [x]

Todas en `preparacion_horario_service.py`, siguiendo el patrón `PuertaDTO`:

1. **`asignaciones_activas`** — `dura`, `fix_ruta="/admin/asignaciones"`.
   Cero asignaciones activas en el periodo (o en los grupos del filtro) es la
   causa raíz de E2. Debe ser lo primero que vea el usuario.

2. **`capacidad_docente_slots`** — `dura`, `fix_ruta="/admin/disponibilidad-docente"`.
   Adelanta a la preparación el pre-vuelo que el motor ya hace (gen:681-705):
   demanda de horas del docente vs. slots donde está disponible, y vs. su carga
   máxima. Reusar la misma aritmética para que checklist y motor no se
   contradigan.

3. **`disponibilidad_coherente`** — `advertencia`, `fix_ruta="/admin/disponibilidad-docente"`.
   La página de disponibilidad graba contra `plantilla_activa("UNICA")`
   (`disponibilidad_docente.py:57`), que puede no ser la plantilla de la config.
   El motor ya detecta las filas huérfanas (`_disp_huerfanas`, gen:466-471) pero
   **solo después** de generar. Contar aquí las filas cuyo `dia_semana` o
   `franja_orden` no existen en la plantilla de la config.

4. **`grupos_con_grado`** — `advertencia`, `fix_ruta="/admin/grupos"`.
   Grupos sin `grado`: el plan de estudios no aplica y el motor cae al fallback
   de horas globales sin avisar.

Más la puerta `aulas_base_unicas` de T3. Orden final del reporte (el orden en
que se renderiza importa: primero lo que impide arrancar):

```
1. anio_periodo              (dura)
2. asignaciones_activas      (dura)   ← NUEVA
3. plantilla_suficiente      (dura)
4. horas_plan_asignaciones   (dura)   ← reemplaza asignaturas_con_horas
5. horas_grupo_vs_slots      (dura)   ← reescrita
6. capacidad_docente         (dura)   ← sube de advertencia
7. capacidad_docente_slots   (dura)   ← NUEVA
8. cobertura_asignaciones    (advertencia)
9. disponibilidad_coherente  (advertencia)   ← NUEVA
10. grupos_con_grado         (advertencia)   ← NUEVA
11. aulas_base_unicas        (advertencia)   ← NUEVA
12. salas_suficientes        (advertencia)   ← se mantiene tal cual (P1)
```

**No tocar P7 `salas_suficientes`:** ya es `advertencia` y su rama «sin salas
registradas» devuelve `ok=True`. Es el comportamiento correcto según P1.

#### T12 — `fix_ruta` según el rol y `TenantScope` correcto  [x]

1. **Rutas inaccesibles.** Los `fix_ruta` apuntan a `/admin/configuracion`,
   `/admin/asignaturas`, `/admin/salas` y `/admin/grupos`, registradas con
   `roles=_DIRECTOR` o `_DIR_COORD` (`main.py:197-206`). Un **coordinador** —que
   sí entra al hub y a Preparar (`_ROLES_ESCRITURA`, hub:79)— recibe botones
   «Corregir» que le rebotan. La página debe ocultar el botón cuando el rol no
   puede abrir la ruta (la comprobación de roles vive en `registrar_pagina`;
   exponer un helper consultable o mapear rol→rutas permitidas en el presenter).

2. **`TenantScope`.** `validar` pasa `institucion_id=inst_id`, que es `None` para
   admin (prep:77-82). El contrato es `int | Literal["*"]` (`tenant.py:11`) y el
   resto del código usa `institucion_actual() or "*"`. Hoy el repo SQLite trata
   `None` como `"*"` por el `isinstance(institucion_id, int)`, así que no falla,
   pero es una violación latente justo en el frente `tenant_02/03`. Cambiar a
   `institucion_actual() or "*"` en las cinco llamadas (prep:80-90).

---

### Bloque D — La preparación es interactiva y vive junto al botón (Principio P5)

#### T13 — Panel de preparación embebido en la sección «Generar»  [x]

`horarios_hub.py` + `horarios_hub_presenter.py`.

**Lo que ya funciona y no hay que romper:** `_cambiar_seccion` →
`hub_refreshable.refresh()` → `_render_preparar()` re-ejecuta `svc.validar(...)`,
así que cada vuelta a «Preparar» recalcula; hay botón «Actualizar»; los colores
distinguen dura (rojo) de advertencia (ámbar) y hay «Corregir» por puerta.

**Lo que falta (D de la auditoría):**

1. **Extraer el render de puertas a un helper reutilizable**
   `_render_puertas(reporte, *, compacto: bool)` — usado tanto por
   `_render_preparar` (completo) como por el panel embebido (compacto: solo las
   puertas en rojo/ámbar, con un resumen «5 de 12 puertas OK»).

2. **Nuevo `@ui.refreshable preparacion_refreshable()`** declarado al nivel de
   los demás refreshables (respetar el comentario de hub:2063: *ALL defined at
   TOP LEVEL of page function*). Renderiza el panel compacto para
   `_s["gen_config_sel"]`.

3. **Colocarlo en `_gen_render_detalle`**, encima del botón «Generar horario»,
   y en la tabla de configuraciones mostrar por fila un badge con el número de
   puertas duras en rojo.

4. **Gating real del botón.** `disabled` deja de depender solo de
   `plantilla_generable` y pasa a `_s["gen_generando"] or not generable or not puede_gen`.
   Cuando está deshabilitado, mostrar **el motivo concreto** (la primera puerta
   dura roja con su `fix_ruta`), no un texto genérico.

5. **`_gen_generar_config` revalida antes de lanzar** (hub:1315). Si aparece una
   puerta dura roja entre el render y el clic (otra pestaña, otro usuario),
   abortar con `toast_warning` nombrando la puerta, sin llamar al motor.

6. **Recálculo en tiempo real.** Añadir `preparacion_refreshable.refresh()` a
   los puntos que hoy solo refrescan `gen_refreshable`: `_gen_guardar_franjas`
   (hub:969), `_gen_activar_plantilla` (hub:953), `_gen_eliminar_franja`,
   `_gen_seleccionar_config` (hub:1067), `_guardar` del diálogo de config
   (hub:1240-1250) y el retorno de `_gen_generar_config`.

7. **Estado en el presenter.** `prep_reporte: list`, `prep_error: str | None`,
   `prep_config_id: int | None` en `HorariosHubPresenter.estado`, con un
   `set_prep_reporte(...)`. El presenter **solo guarda el view-model**: el
   cómputo y el mapa causa→etiqueta viven en los servicios
   (memoria `regla-logica-negocio-al-backend`).

---

### Bloque E — Validaciones de datos de entrada

#### T14 — `min <= max` en las restricciones diarias  [x]

`restriccion_generacion_service.py:88-106`. `construir_restricciones` acepta
`min_horas=10, max_horas=1` sin chistar, mientras que `LimitesDocente`
(models:863-871) **sí** valida el rango. Con `modo="estricta"` eso produce un
horario imposible más un aviso de mínimo incumplido en cada día.

1. Lanzar `ValueError` con el mismo texto que usa `LimitesDocente`
   («min_horas_dia (N) no puede ser mayor que max_horas_dia (M).»).
2. En el diálogo de config (hub:1190-1207), comparar los dos `field_number`
   antes de llamar al servicio y mostrar `toast_warning` con el mensaje, igual
   que se hace ya con nombre y plantilla vacíos.
3. **Efecto lateral a corregir:** si `min == 0` y `max == 8`, `restricciones`
   sale `{}` y el modo `"estricta"` que el usuario eligió **se descarta en
   silencio**. Incluir `min_max_diario` también cuando `modo == "estricta"`,
   aunque el rango sea el default.

#### T15 — Franjas: normalizar `HH:MM`, prohibir solapes y `orden` duplicado  [x]

1. **Normalización.** `Franja` (models:501-535) compara
   `hora_inicio >= hora_fin` **lexicográficamente sin normalizar**: un `"7:00"`
   que no pase por `_validar_intervalo` compararía mal frente a `"12:00"`.
   Aplicar en el validador `normalizar_hora` la misma lógica que
   `_normalizar_hora` de `horario_service.py:51-59` (`'8:00' → '08:00'`), y
   rechazar lo que no parsee como `HH:MM` en rango.
   *Evitar duplicar la función:* moverla a un único sitio compartido o
   reexportarla, no copiarla.

2. **Solapes y unicidad.** `FranjaService.guardar_franjas` (franja_service:107-125)
   construye los DTOs y llama a `reemplazar_franjas` sin comprobar el conjunto.
   Añadir antes del guardado: `orden` único, y ningún par de franjas del mismo
   set con intervalos solapados. Es de lo que depende `orden_siguiente`
   (gen:407-411) para que un bloque doble ocupe horas realmente contiguas.
   `ValueError` con mensaje legible — la página ya lo convierte en
   `toast_warning` vía `_texto_error` (hub:977-979).

3. **Página.** `_gen_agregar_franja` / `_gen_editar_franja` (hub:993, 1017) solo
   comprueban «no vacío». Dejar que el `ValueError` del servicio suba (ya está
   manejado) y añadir la comprobación local de inicio < fin para dar respuesta
   inmediata sin round-trip.

#### T16 — Limpieza: rama muerta y protecciones faltantes  [x]

1. **`_diagnosticar_no_colocado`** (gen:882-891): la rama `sin_sala` es
   **inalcanzable**. Su conjunto de checks es idéntico al de `_puede_colocar`,
   que no mira salas: si la ejecución llega a esa línea, `_puede_colocar` ya
   había devuelto `True` y la lección se habría colocado. Eliminar la rama y
   `"sin_sala"` del vocabulario de causas — hoy es una etiqueta que solo puede
   confundir («la generación falló por salas» cuando las salas no bloquean).
   Conservar `sala_pendiente`, que sí se emite y sí es real.

2. **`sala_service.asignar_sala_a_grupo`** (sala_service:105) no tiene
   `@requiere_escritura` ni verificación de pertenencia al tenant. Añadir ambas,
   siguiendo el patrón de `FranjaService._verificar_pertenencia_obj`
   (franja_service:52-62).

3. **Documentar el acoplamiento de `aplicar_max_dia_estricto`** (gen:597):
   `bool(limites_por_docente) or (...)` significa que basta **un** docente con
   `LimitesDocente` para que el tope diario pase a duro para todos los que
   tengan fila, aunque la config diga `"preferente"`. Está en el docstring del
   módulo, pero no se comunica en la UI: añadir la nota en el diálogo de config,
   junto al selector de modo.

---

### Bloque F — Tests

#### T17 — Regresión del generador  [x]

`tests/unit/services/test_generador_horario.py` — añadir, reutilizando los fakes
existentes (`_build`, `_config`, `_plantilla`, `_asig_info`, `DIAS_3`, `FRANJAS_3`):

- `test_sala_faltante_no_invalida_el_horario` — el caso E1 completo:
  3 grupos / 1 laboratorio → `valido=True`, `causas["sala_pendiente"] == 6`,
  9 bloques persistidos. **Este test es el que cierra P1.**
  Requiere que `FakeHorarioService.analizar_lote` incorpore la regla de sala del
  oráculo real (hoy la ignora, por eso el fake no detectaba el bug).
- `test_sin_asignaciones_no_crea_escenario` — el caso E2:
  `escenario_id is None`, config **sin** transicionar, `incidencias` no vacía.
- `test_resultado_invalido_siempre_tiene_incidencias` — parametrizado sobre los
  escenarios de fallo conocidos; asserta el invariante de T4.
- `test_sala_base_no_se_reasigna_a_laboratorio` — T2.

#### T18 — Suite nueva de preparación  [x]

`tests/unit/services/test_preparacion_horario.py` — **hoy no existe ningún test
de este servicio**, lo que explica que P2 llevara tiempo siendo una puerta
muerta sin que nadie lo notara.

Fakes mínimos de los cinco repos + `PlanEstudiosService`. Un test por puerta,
cubriendo verde y rojo, y en particular:

- `test_p_horas_plan_detecta_asignacion_con_cero_horas` (T9).
- `test_p_horas_grupo_usa_asignaciones_no_plan` — grupo con 40 h asignadas y
  plan vacío ⇒ puerta **roja** (hoy sale verde).
- `test_p_capacidad_docente_es_dura` (T10).
- `test_p_asignaciones_activas_roja_sin_asignaciones` (T11).
- `test_validar_config_respeta_filtro_de_grupos` (T8).
- `test_puede_generar_falso_con_cualquier_dura_roja`.

#### T19 — Oráculo  [x]

`tests/unit/services/test_horario_lote.py`:

- `test_cruce_sala_no_bloquea_cuando_salas_bloquean_false` (T1).
- `test_por_asignar_nunca_es_cruce` — dos filas solapadas con `"Por asignar"`
  son válidas incluso con `salas_bloquean=True`.
- `test_cruce_sala_real_sigue_bloqueando_en_carga_masiva` — el default `True` no
  cambia de comportamiento.
- `test_cruce_docente_y_grupo_siguen_siendo_duros` — la relajación de salas no
  se contagia.

---

## Criterio de done

- [ ] E1 reproducido como test: 3 grupos / 1 laboratorio ⇒ `valido=True` y 9 bloques persistidos.
- [ ] E2 reproducido como test: sin asignaciones ⇒ sin escenario, sin transición de estado, con incidencia.
- [ ] Invariante `not valido ⇒ incidencias != []` cubierto por test.
- [ ] Ninguna ruta de código puede invalidar un horario por causa de sala.
- [ ] «Activar este escenario» no aparece si el escenario no tiene bloques.
- [ ] La checklist se evalúa contra la `ConfigGeneracion` seleccionada (año, periodo, plantilla y filtro de grupos).
- [ ] Las 12 puertas del orden de T11 existen, con la severidad indicada.
- [ ] El panel de preparación aparece en «Generar», se recalcula al guardar franjas / cambiar config / activar plantilla, y bloquea el botón con el motivo concreto.
- [ ] `construir_restricciones` rechaza `min > max`; el diálogo lo avisa antes de llamar.
- [ ] `guardar_franjas` rechaza solapes y `orden` duplicado; `Franja` normaliza `HH:MM`.
- [ ] `tests/unit/services/test_preparacion_horario.py` existe y cubre las 12 puertas.
- [ ] `python init.py` **completamente verde** (design system `--all`, tokens, `audit_design --strict` y la puerta de ruff).
- [ ] `python -m pytest tests/unit/services -q` verde.
- [ ] Sin `.dict()`, sin `import src.db` fuera de `src/infrastructure/`, sin instanciar repos fuera de `container.py`.

---

## Riesgos y decisiones abiertas

1. **Cambiar P4 a `dura` puede bloquear a instituciones que hoy generan.**
   Si un colegio tiene docentes sobrecargados, la generación ya le sale parcial y
   no se persiste — la puerta solo hace visible antes lo que ya fallaba después.
   Aun así, el detalle debe nombrar a los docentes y enlazar a
   `/admin/asignaciones` para que la corrección sea de un clic.

2. **`salas_bloquean=False` es un flag de comportamiento en un servicio de
   dominio.** La alternativa es una severidad por fila en `FilaReporteDTO`.
   Se elige el flag por ser el cambio mínimo y porque solo hay dos llamadores con
   políticas claramente distintas (generador vs. carga masiva manual). Si en el
   futuro aparece un tercero, migrar a severidades.

3. **Orden de ejecución sugerido:** T1 → T4 → T5 → T6 desbloquean el uso real
   (son los que hoy impiden persistir un horario correcto) y pueden ir a un
   commit propio. T8-T12 son el grueso de la checklist. T13 depende de T8.
   T14-T16 son independientes y pueden paralelizarse.

4. **No mezclar con un reformateo.** Regla dura del harness: nada de
   `ruff format` ni `ruff check --fix` masivos dentro de este paso.
