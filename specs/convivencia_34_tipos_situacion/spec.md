# convivencia_34_tipos_situacion — Spec

## Contexto

La Ley 1620 de 2013 y el Decreto 1965 (Art. 40) exigen que toda situacion
que afecte la convivencia escolar se clasifique en tres tipos:

- **Tipo I** — conflictos manejados inadecuadamente, esporadicos, sin dano
  al cuerpo o la salud fisica o mental.
- **Tipo II** — agresion escolar, acoso, ciberacoso (no constitutivo de
  delito).
- **Tipo III** — situaciones constitutivas de presuntos delitos.

El sistema actual solo tiene `TipoRegistro` (fortaleza/dificultad/compromiso/
citacion/descargo), que clasifica la ACCION registrada pero no la GRAVEDAD
de la situacion. Un "dificultad" puede ser Tipo I o Tipo III — el modelo
no los distingue. Esto impide activar protocolos diferenciados y genera
riesgo legal para la institucion.

Esta spec agrega un catalogo configurable `tipos_situacion` por institucion,
un FK en `registro_comportamiento`, y una preferencia que permite a cada
colegio decidir si la clasificacion es obligatoria al crear registros.

Scope:
- `src/infrastructure/db/schema.py` (NUEVA tabla + ALTER)
- `src/infrastructure/db/seed.py` (migracion + seed)
- `src/domain/models/catalogos_estandar.py` (EXTENDER)
- `src/domain/models/convivencia.py` (EXTENDER — nuevo modelo + campo)
- `src/domain/models/preferencia_institucion.py` (EXTENDER)
- `src/domain/ports/convivencia_repo.py` (EXTENDER)
- `src/infrastructure/db/repositories/sqlite_convivencia_repo.py` (EXTENDER)
- `src/services/convivencia_service.py` (EXTENDER)
- `src/services/preferencias_institucion_service.py` (EXTENDER — nueva clave)
- `src/interface/pages/convivencia/configuracion_convivencia.py` (EXTENDER)
- `src/interface/presenters/convivencia/configuracion_convivencia_presenter.py` (EXTENDER)
- `src/interface/pages/convivencia/seguimiento.py` (MODIFICAR — form de registro)
- `tests/` (EXTENDER)

## Requisitos (EARS)

- **R1** — DEBE existir una tabla `tipos_situacion` con `institucion_id` FK,
  `nombre` (UNIQUE por institucion), `nivel` (1-3), `descripcion`, `protocolo`,
  y `activa`.
- **R2** — `registro_comportamiento` DEBE tener una columna nullable
  `tipo_situacion_id` (FK a `tipos_situacion`, ON DELETE SET NULL).
- **R3** — Al aprovisionar una institucion, DEBEN insertarse tres tipos
  default (Tipo I, II, III) con descripciones alineadas al Decreto 1965.
- **R4** — Director y coordinador DEBEN poder crear, editar nombre/nivel/
  descripcion/protocolo, y desactivar tipos de situacion desde la pagina
  de configuracion de convivencia.
- **R5** — Profesor, admin y otros roles NO DEBEN poder crear/editar/
  desactivar tipos de situacion.
- **R6** — Desactivar un tipo (`activa=False`) DEBE ocultarlo del selector
  de creacion pero NO DEBE eliminar la referencia en registros historicos.
- **R7** — `PreferenciasDTO` DEBE incluir un campo
  `tipo_situacion_obligatorio: bool = False`. Si es `True`, el formulario
  de creacion de registros DEBE exigir `tipo_situacion_id` (no permitir
  guardado sin seleccion). Si es `False`, el campo es opcional.
- **R8** — La clave `tipo_situacion_obligatorio` DEBE estar registrada en
  `CLAVES_CONOCIDAS` con categoria `CONVIVENCIA` y tipo `BOOL`.
- **R9** — Registros existentes (sin `tipo_situacion_id`) DEBEN seguir
  siendo validos y legibles — no se altera el comportamiento de consultas,
  boletines ni reportes existentes.
- **R10** — `ConvivenciaService.registrar_comportamiento` DEBE validar que,
  si la preferencia `tipo_situacion_obligatorio` esta activa y el DTO trae
  `tipo_situacion_id=None`, lance `ValueError`.

### Bug fix incluido

- **R11** — `NotaComportamiento.aprobado` (`convivencia.py:349`) es un
  `@property` con parametro `nota_minima` que Python ignora. DEBE
  convertirse a un metodo regular `def esta_aprobado(self, nota_minima)`
  o eliminar el parametro y usar 60.0. El servicio ya lo maneja bien
  en `get_concepto_periodo`; solo corregir la property.

## Diseno

### T1 — Schema y migracion

En `schema.py`, nueva tabla en seccion 8:
```sql
CREATE TABLE IF NOT EXISTS tipos_situacion (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre         TEXT    NOT NULL,
    nivel          INTEGER NOT NULL DEFAULT 1 CHECK(nivel BETWEEN 1 AND 3),
    descripcion    TEXT,
    protocolo      TEXT,
    activa         BOOLEAN NOT NULL DEFAULT 1,
    institucion_id INTEGER REFERENCES instituciones(id),
    UNIQUE(institucion_id, nombre)
)
```

En `seed.py`, nueva funcion `_migrate_tipo_situacion(conn)`:
- ALTER TABLE registro_comportamiento ADD COLUMN tipo_situacion_id INTEGER
  REFERENCES tipos_situacion(id) ON DELETE SET NULL
  (idempotente via PRAGMA table_info check, patron existente).
- INSERT OR IGNORE de defaults por cada institucion.
- Llamar desde `seed_base()`.

Nuevo indice: `idx_comp_tipo_situacion ON registro_comportamiento(tipo_situacion_id)`.

### T2 — Catalogos estandar

En `catalogos_estandar.py`:
```python
TIPOS_SITUACION_CO: list[tuple[str, int, str]] = [
    (
        "Tipo I - Conflictos manejados inadecuadamente",
        1,
        "Situaciones esporadicas que inciden negativamente en el clima escolar "
        "y que en ningun caso generan danos al cuerpo o a la salud fisica o "
        "mental de los involucrados.",
    ),
    (
        "Tipo II - Agresion escolar o acoso",
        2,
        "Situaciones de agresion escolar, acoso escolar (bullying) y "
        "ciberacoso que no revistan las caracteristicas de la comision de "
        "un delito y que cumplan con cualquiera de las siguientes "
        "caracteristicas: a) que se presenten de manera repetida o "
        "sistematica; b) que causen danos al cuerpo o a la salud (fisica "
        "o mental) sin generar incapacidad alguna.",
    ),
    (
        "Tipo III - Presuntos delitos",
        3,
        "Situaciones de agresion escolar que sean constitutivas de presuntos "
        "delitos contra la libertad, integridad y formacion sexual, u otro "
        "delito establecido en la ley penal colombiana vigente.",
    ),
]
```

### T3 — Modelo de dominio

En `convivencia.py`:
```python
class TipoSituacion(BaseModel):
    id: int | None = None
    nombre: str
    nivel: int = 1
    descripcion: str | None = None
    protocolo: str | None = None
    activa: bool = True
    institucion_id: int | None = None

class NuevoTipoSituacionDTO(BaseModel):
    nombre: str
    nivel: int = 1
    descripcion: str | None = None
    protocolo: str | None = None

    @field_validator("nivel")
    @classmethod
    def validar_nivel(cls, v: int) -> int:
        if not (1 <= v <= 3):
            raise ValueError("El nivel debe ser 1, 2 o 3.")
        return v
```

Agregar campo en `RegistroComportamiento`:
```python
tipo_situacion_id: int | None = None
```

Agregar campo en `NuevoRegistroComportamientoDTO`:
```python
tipo_situacion_id: int | None = None
```

Fix de `NotaComportamiento.aprobado`: eliminar el parametro `nota_minima`
del `@property` (dejar como `return self.valor >= 60.0`) o convertir a
metodo. El servicio ya maneja el umbral configurable en `get_concepto_periodo`.

### T4 — Preferencia de obligatoriedad

En `preferencia_institucion.py`, agregar a `PreferenciasDTO`:
```python
tipo_situacion_obligatorio: bool = False
```

En `preferencias_institucion_service.py`, agregar a `CLAVES_CONOCIDAS`:
```python
"tipo_situacion_obligatorio",
```

### T5 — Port y repositorio

En `convivencia_repo.py`, agregar metodos abstractos:
- `listar_tipos_situacion(solo_activas, institucion_id) -> list[TipoSituacion]`
- `get_tipo_situacion(tipo_situacion_id) -> TipoSituacion | None`
- `guardar_tipo_situacion(tipo_situacion) -> TipoSituacion`
- `actualizar_tipo_situacion(tipo_situacion) -> TipoSituacion`

En `sqlite_convivencia_repo.py`, implementar los 4 metodos siguiendo el
patron exacto de `categorias_observacion` (INSERT, UPDATE, SELECT con
WHERE institucion_id).

Actualizar `guardar_registro` para incluir `tipo_situacion_id` en el INSERT.
Actualizar `_row_to_registro` (o su equivalente) para leer `tipo_situacion_id`.
Actualizar `actualizar_registro` para incluir `tipo_situacion_id` en el UPDATE.

### T6 — Servicio

En `convivencia_service.py`, agregar metodos:
- `listar_tipos_situacion(solo_activas=True) -> list[TipoSituacion]`
  (auto-filtra por `institucion_actual()`)
- `crear_tipo_situacion(dto) -> TipoSituacion`
  (stampa `institucion_id` via `_resolver_institucion`)
- `actualizar_tipo_situacion(tipo_id, dto) -> TipoSituacion`
- `desactivar_tipo_situacion(tipo_id) -> TipoSituacion`

Patron identico a `crear_categoria`/`actualizar_categoria`/`desactivar_categoria`.

En `registrar_comportamiento`: validar que si la preferencia
`tipo_situacion_obligatorio` esta activa y `dto.tipo_situacion_id is None`,
lanzar `ValueError("La clasificacion de situacion es obligatoria.")`.
La lectura de la preferencia se hace via `_get_prefs_convivencia()`.

### T7 — UI: Configuracion

Extender `configuracion_convivencia.py`: agregar una tercera seccion
(debajo de categorias y plantillas, o como tab adicional) para "Tipos de
Situacion". Aggrid con columnas: Nombre, Nivel, Activa. Botones
Nuevo/Editar/Desactivar. Solo visible a director/coordinador.

`form_dialog` con campos:
- nombre (text, requerido)
- nivel (select: 1/2/3)
- descripcion (textarea)
- protocolo (textarea, label: "Protocolo de atencion")

Extender `ConfiguracionConvivenciaPresenter` con state para tipos_situacion.

### T8 — UI: Formulario de registro de comportamiento

En la pagina donde se crea un `RegistroComportamiento` (hub de seguimiento
`seguimiento.py`), agregar un `ui.select` para tipo de situacion:
- Poblado con `listar_tipos_situacion(solo_activas=True)`
- Si la preferencia `tipo_situacion_obligatorio` esta activa, el select
  es requerido (validacion en frontend y en servicio)
- Si no, aparece con placeholder "Sin clasificar (opcional)"
- Solo visible cuando el tipo de registro es DIFICULTAD o CITACION
  (no tiene sentido clasificar fortalezas por gravedad)

### T9 — Tests

- Test de dominio: `TipoSituacion` y `NuevoTipoSituacionDTO` (validacion
  de nivel 1-3).
- Test de dominio: `RegistroComportamiento` con `tipo_situacion_id`.
- Test de dominio: fix de `NotaComportamiento.aprobado`.
- Test de servicio: CRUD de tipos_situacion con scoping por institucion.
- Test de servicio: `registrar_comportamiento` con y sin obligatoriedad.
- Test de CLAVES_CONOCIDAS: la nueva clave esta registrada.
- Test de presenter: state incluye tipos_situacion.

## Verificacion

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/ -q
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe init.py
```

Escenarios manuales:
- Coordinador crea un nuevo tipo "Situacion especial" nivel 2 desde config →
  aparece en el selector al crear un registro.
- Coordinador activa `tipo_situacion_obligatorio` en preferencias →
  intentar crear registro sin tipo lanza error.
- Registro viejo sin tipo_situacion_id → se muestra como "Sin clasificar".
- Desactivar un tipo → no aparece en selector pero registros historicos
  mantienen la referencia.

`init.py` verde.

## Dependencias

- Ninguna dependencia bloqueante. Puede implementarse independientemente.
- Reutiliza infraestructura de preferencias (convivencia_29).
- Reutiliza patron de catalogo configurable (convivencia_09/10).
