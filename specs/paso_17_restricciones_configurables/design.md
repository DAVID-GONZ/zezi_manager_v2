# Diseño: Restricciones configurables del generador (paso_17_restricciones_configurables)

> Implementación **incremental por fases**; cada fase deja `init.py` verde. El orden
> es: modelo → captura (UI) → duras → blandas → infactibilidad. El default sin
> configurar = comportamiento actual (R16).

## 1. Modelo de dominio (fase A)

Nuevos modelos en `src/domain/models/infraestructura.py` (o un módulo
`restricciones.py` si crece demasiado):

- `Sala(id, nombre, tipo: Literal["aula","laboratorio","computo","ed_fisica","otro"], capacidad: int)`.
- `Asignatura`: añadir `tipo_sala_requerido: str | None`, `bloque_doble: bool = False`,
  `horas_consecutivas: int = 1`.
- `DisponibilidadDocente`: ya existe.
- `LimitesDocente(usuario_id, carga_max, min_horas_dia, max_horas_dia)` — o ampliar
  `usuarios` con `min/max_horas_dia`.
- `VentanaGrupo(grupo_id | grado, franjas_permitidas: list[int])`.
- `BloqueAnclado(escenario_id, asignacion_id, dia, franja_orden)`.
- `FranjaReunion(nombre, docentes: list[int], dia, franja_orden, modo)`.
- `RestriccionConfig` embebido en `ConfigGeneracion`: por cada restricción híbrida,
  `{ "min_max_diario": {"modo": "preferente", "peso": 1.0, "min": 2, "max": 6}, ... }`.
- Ampliar `PesosGeneracion` con: `balance_diario`, `franja_preferida`, `dia_libre`,
  `hueco_comun` (todos `0.0..2.0`, default 0.0 para no alterar el comportamiento).
- `BloqueGeneradoDTO`: `sala` pasa a ser sala real resuelta (sigue admitiendo "Aula").
- `ResultadoGeneracionDTO`: añadir `causas: dict[str,int]` (resumen) y, por incidencia,
  la causa probable; añadir `relajadas: list[str]`.

Persistencia: nuevas tablas `salas`, `ventanas_grupo`, `bloques_anclados`,
`franjas_reunion`; columnas nuevas en `asignaturas` y `usuarios`. **Modo desarrollo:
no hay migración.** Se edita directamente el DDL (`CREATE TABLE` / columnas) en
`src/infrastructure/db/schema.py` y se **recrea la BD con `seed`**; no se requiere
lógica de migración aditiva ni respaldo. Repos en `sqlite_infraestructura_repo.py`;
métodos de servicio en `infraestructura_service.py` y, lo de docente, en
`usuario_service.py`. El `seed` debe poblar datos de ejemplo de las entidades nuevas.

## 2. Captura en la interfaz (fase B)

Páginas/secciones nuevas (a integrar luego en la página única de paso_18):

- **Disponibilidad docente**: rejilla (días × franjas) por docente, toggle por celda;
  usa `bloquear_franjas_docente` / `listar_disponibilidad_docente` /
  `limpiar_disponibilidad_docente` (ya existen en `infraestructura_service`).
- **Límites docente**: inputs carga_max, min/max horas día (en admin/usuarios o en la
  sección Preparar).
- **Salas**: CRUD simple (nombre, tipo, capacidad) + selector "tipo de sala requerido"
  en la edición de asignatura.
- **Restricciones de generación**: en el diálogo de `ConfigGeneracion`, una sección
  con cada restricción híbrida (modo estricta/preferente + peso) y los pesos blandos.

Todo vía `Container.*`, clases CSS del design system, iconos por `ThemeManager`.

## 3. Motor — restricciones duras (fase C)

En `src/services/generador_horario_service.py`:

- **Salas (R5)**: el estado de ocupación pasa de `(grupo,dia,orden)` a incluir
  `ocupado_sala: set[(sala_id, dia, orden)]`. `_puede_colocar` añade el chequeo de
  sala según `tipo_sala_requerido`; al colocar se elige una sala libre del tipo. El
  camino de coloreo solo aplica si no hay restricción de sala (si la hay, se usa
  backtracking). Sin salas configuradas → "Aula" como hoy (R16).
- **Bloques dobles (R6)**: una lección doble se modela como una **macro-lección** que
  ocupa franjas `orden, orden+1, …`; `_puede_colocar` exige contigüidad y todas libres.
- **Ventanas de grupo (R7)**: filtra `slots` por grupo antes de colocar.
- **Anclados (R8)**: se siembran en los grids de ocupación antes del backtracking y se
  excluyen de `lecciones_ordenadas`.
- **Híbridas estrictas (R9)**: min/máx diario docente y máx/día materia se chequean en
  `_puede_colocar` (contadores por `(docente,dia)` y `(asignacion,dia)`); el mínimo
  diario se valida como cota al cierre (un día abierto no puede quedar por debajo del
  mínimo si ya tiene ≥1 bloque) y se reporta si no se cumple.

> Cota de complejidad: con salas/dobles activos el coloreo se desactiva y crece el
> backtracking. Mitigación: pre-vuelo (fase E) recorta instancias imposibles y el
> presupuesto de iteraciones evita cuelgues; las nuevas duras se aplican solo si están
> configuradas.

## 4. Motor — coste blando (fase D)

Ampliar `_costo(...)`:
- **balance_diario (R10)**: varianza/rango de horas por día del docente →
  `pesos.balance_diario * Σ(max_dia - min_dia)` por docente.
- **hueco_comun (R11)**: para cada `FranjaReunion` preferente, penaliza cada docente
  del conjunto que tenga clase en esa franja.
- **franja_preferida / dia_libre (R12)**: penaliza bloques fuera de la franja preferida
  de la materia y bloques en el día preferido-libre del docente.

`_mejorar_local` (hill-climbing) ya recorre estos costes sin cambios estructurales:
al añadir términos a `_costo`, la mejora local los optimiza automáticamente.

## 5. Infactibilidad (fase E)

Función nueva `_prevuelo(...) -> list[str]` antes del backtracking:
- Por grupo: `Σ horas plan ≤ len(slots ∩ ventana)`.
- Por docente: `Σ horas ≤ min(carga_max, slots disponibles)`.
- Por tipo de sala: `Σ horas tipo T ≤ (#salas tipo T) × len(slots)`.
- Por bloques dobles: pares de franjas contiguas suficientes.
Cada violación → incidencia accionable (R13). Si hay violaciones de cota, se omite la
búsqueda y se devuelve resultado con `valido=False` y las incidencias.

Relajación ordenada (R14): si tras el presupuesto no hay solución completa, se
re-resuelve ignorando términos `preferente`/blandos en orden configurable
(`orden_relajacion: list[str]` en la config), registrando en `resultado.relajadas`.

Diagnóstico (R15): el greedy de relleno etiqueta cada no-colocado con la primera
causa de fallo (`_puede_colocar` devuelve el motivo) y se agrega en `resultado.causas`.

## 6. Archivos afectados

- `src/domain/models/infraestructura.py` (+ posible `restricciones.py`).
- `src/domain/models/asignacion.py` (sin cambios; horas siguen en asignatura).
- `src/infrastructure/db/schema.py`, `sqlite_infraestructura_repo.py`,
  `sqlite_usuario_repo.py`.
- `src/services/infraestructura_service.py`, `usuario_service.py`,
  `generador_horario_service.py`.
- `src/interface/pages/...` (captura; se reubica en paso_18).
- **No se toca** `parrilla_widget.py` (R17).

## 7. Manejo de errores
- Validaciones de modelo (pydantic) en todos los nuevos DTO.
- El motor nunca lanza por infactibilidad: devuelve `ResultadoGeneracionDTO` con
  `valido=False` + incidencias.
- El GATE oráculo `analizar_lote` se mantiene como verificación final antes de persistir.

## 8. Decisiones y preguntas abiertas

**Aprobado:** Desdobles / grupos partidos / co-docencia (catálogo #16) **NO entran en
este paso**; se difieren a un **paso_17g** posterior. El resto del catálogo (salas,
dobles, mín/máx diario, huecos, hueco común, ventanas, anclados, preferencias) sí.

Pendientes de detalle (no bloquean el arranque):
1. ¿`min/max_horas_dia` viven en `usuarios` (global por docente) o por `(docente, año)`?
2. ¿Las salas son por año lectivo o globales de la institución?
3. "Hueco común de reunión": ¿franja fija elegida por David, o el motor busca la mejor
   franja común?
