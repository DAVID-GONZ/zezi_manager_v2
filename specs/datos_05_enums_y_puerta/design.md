# Diseño: datos_05_enums_y_puerta

## Estado medido

Parseo de `schema.py` e introspección de `src/domain/models/`:

| Medida | Valor |
|---|---|
| Restricciones `CHECK(col IN (...))` | 35 |
| `StrEnum` en el dominio | 31 |
| **Pares alineados exactamente** | **30** |
| `CHECK` sin enumeración | 5 |
| Enumeraciones sin `CHECK` | 7 |

Los 30 pares alineados son un activo del proyecto: `usuarios.rol ↔ usuario.Rol`,
`estudiantes.estado_matricula ↔ estudiante.EstadoMatricula`,
`control_diario.estado ↔ asistencia.EstadoAsistencia`, y 27 más, con conjuntos de valores
**idénticos**. Hoy **nada impide que diverjan**: no hay test ni puerta que lo compruebe.
Ese es el verdadero objeto de este paso.

### Las 5 restricciones sin enumeración

El modelo las tipa como `str` libre con un valor por omisión; la única defensa es la base.

| Columna | Valores | Campo del modelo hoy |
|---|---|---|
| `franjas.tipo` | `lectiva`, `descanso`, `almuerzo` | `Franja.tipo: str = 'lectiva'` |
| `salas.tipo` | `aula`, `computo`, `ed_fisica`, `laboratorio`, `otro` | `Sala.tipo: str = 'aula'` |
| `franjas_reunion.modo` | `estricta`, `preferente` | `FranjaReunion.modo: str = 'preferente'` |
| `config_generacion.estado` | `borrador`, `generado`, `aplicado` | `ConfigGeneracion.estado: str = 'borrador'` |
| `observaciones_periodo.origen` | `libre`, `plantilla` | `ObservacionPeriodo.origen: str = 'libre'` |

### Las 7 enumeraciones sin restricción

Se separan en dos casos distintos, y confundirlos sería el error:

**Persisten en una columna `TEXT` sin `CHECK` — agujero real (5):**

| Enumeración | Columna |
|---|---|
| `institucion.Calendario` (`A`, `B`) | `instituciones.calendario TEXT` |
| `institucion.JornadaPrincipal` (`AM`, `PM`, `UNICA`) | `instituciones.jornada_principal TEXT` |
| `institucion.TipoInstitucion` (`publica`, `privada`) | `instituciones.tipo_institucion TEXT` |
| `auditoria.AccionCambio` (`CREATE`, `READ`, `UPDATE`, `DELETE`) | `audit_log.accion TEXT NOT NULL` |
| `preferencia_institucion.CategoriaPreferencia` | `preferencias_institucion.categoria TEXT NOT NULL` |

El modelo valida, pero cualquier escritura que no pase por el modelo corrompe el dato.

**No persisten — legítimamente sin `CHECK` (2):**

| Enumeración | Por qué |
|---|---|
| `busqueda.TipoResultadoBusqueda` | Clasifica resultados de búsqueda en memoria |
| `dtos.FormatoInforme` (`pdf`, `excel`) | Selecciona el formato de exportación |

Estas dos van a la lista de excepciones documentadas de R7, no a la de deuda.

## Decisiones

### D1 — Este paso NO toca `schema.py`

`schema.py` no está en el `destino_v2` del paso, y `CLAUDE.md` exige puerta de aprobación
de David para cambiar el esquema.

**Recomendación:** no añadir aquí los 5 `CHECK` que faltan. Motivos:

1. `backend_04_metadata_schema` redefine el esquema completo como `MetaData` de
   SQLAlchemy. Añadir ahora `CHECK` en cadenas DDL es trabajo que se reescribe entero.
2. En SQLite un `CHECK` no se puede añadir a una tabla existente con `ALTER TABLE`:
   exigiría recrear la tabla y copiar los datos. Coste alto para un retorno que
   `backend_04` da gratis.
3. El riesgo queda cubierto mientras tanto: los cinco campos ya se validan en el dominio,
   y la puerta de este paso los deja **registrados como deuda conocida y visible**, no
   como omisión silenciosa (R8).

La puerta distingue por tanto tres estados, no dos: alineado, exención documentada, y
**deuda registrada con destino** (`backend_04`).

### D2 — Las 5 enumeraciones nuevas

Se declaran en el módulo donde vive su modelo, junto a las demás enumeraciones de ese
módulo: `TipoFranja` y `TipoSala` y `ModoFranjaReunion` y `EstadoConfigGeneracion` en
`infraestructura.py`, `OrigenObservacion` en `convivencia.py`.

El valor por omisión de cada campo pasa a ser el miembro correspondiente, conservando
exactamente el mismo valor textual (R4, R15).

`StrEnum` y no `Enum`: un `StrEnum` es subclase de `str`, así que `sqlite3` lo acepta como
parámetro y lo almacena con su valor textual sin conversión explícita. Es lo que ya hacen
las 31 enumeraciones existentes, y lo que garantiza R15 y R16 sin tocar los repositorios.

### D3 — Diseño de la puerta

`scripts/check_enums.py`:

- **Emparejamiento (R6):** por igualdad exacta del conjunto de valores, que es como se
  verificó el inventario. No por nombre de columna: `alertas.tipo_alerta` y
  `configuracion_alertas.tipo_alerta` comparten `alerta.TipoAlerta`, y
  `boletines_emitidos.tipo` se corresponde con `habilitacion.TipoHabilitacion`, cuyos
  nombres no guardan relación.
- **Informe (R10):** ante una divergencia, indica la columna, la enumeración candidata más
  próxima, y los valores que sobran y faltan en cada lado. Un mensaje que solo diga
  «divergencia» no sirve para arreglar nada.
- **Exenciones (R7, R14):** dos listas explícitas en el propio script —restricciones sin
  enumeración y enumeraciones sin restricción—, cada una con su motivo. Lo que no esté en
  ellas y no empareje, falla. Así una enumeración nueva sin contraparte se señala sola,
  sin tocar el script.
- **Salida (R13):** copia el bloque «Consola UTF-8» de un script existente de `scripts/`,
  según la regla del harness de `CLAUDE.md`.
- **Código de salida (R11):** distinto de cero ante cualquier divergencia.

### D4 — Integración en `scripts/init.py`

La comprobación es parseo de un fichero más introspección de 24 módulos ya importados:
coste despreciable frente a los ~18 s de la suite (R12). Se encadena junto a las demás
puertas, antes de los tests, para que un fallo barato aparezca pronto.

## Alternativa descartada

**Generar los `CHECK` del esquema a partir de las enumeraciones del dominio, en lugar de
comprobar que coinciden.**

Elimina por construcción toda posibilidad de divergencia y es la solución de fondo. Se
descarta aquí porque exige que el esquema deje de ser cadenas DDL literales y pase a
construirse en Python — que es exactamente `backend_04_metadata_schema`. Adelantarlo
significaría reescribir `schema.py` dentro de un paso de dominio, sin la puerta de
aprobación de esquema y duplicando trabajo ya planificado. La comprobación de este paso
es la red que protege los 30 pares alineados **hasta** que esa generación exista, y sigue
siendo útil después como verificación independiente.
