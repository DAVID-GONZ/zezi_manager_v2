# convivencia_36_medidas_pedagogicas — Spec

## Contexto

En un colegio colombiano, cada situacion de convivencia conlleva una medida
pedagogica o correctiva proporcional a la gravedad (Art. 43-44 Decreto 1965).
Estas medidas van desde un dialogo pedagogico (Tipo I) hasta la no renovacion
de matricula (Tipo III extremo), y estan definidas en el Manual de Convivencia
de cada institucion.

El sistema actual registra QUE paso (dificultad, citacion...) pero no QUE
MEDIDA se aplico. El director de grupo no puede consultar "a cuantos
estudiantes se les aplico matricula condicional este ano" ni generar
reportes por tipo de medida.

Esta spec agrega un catalogo configurable `medidas_pedagogicas` por
institucion, con un campo `nivel_minimo` que controla desde que tipo de
situacion la medida es aplicable (filtra opciones en el formulario).

Scope:
- `src/infrastructure/db/schema.py` (NUEVA tabla + ALTER)
- `src/infrastructure/db/seed.py` (migracion + seed)
- `src/domain/models/catalogos_estandar.py` (EXTENDER)
- `src/domain/models/convivencia.py` (EXTENDER)
- `src/domain/ports/convivencia_repo.py` (EXTENDER)
- `src/infrastructure/db/repositories/sqlite_convivencia_repo.py` (EXTENDER)
- `src/services/convivencia_service.py` (EXTENDER)
- `src/interface/pages/convivencia/configuracion_convivencia.py` (EXTENDER)
- `src/interface/pages/convivencia/seguimiento.py` (MODIFICAR — form)
- `tests/` (EXTENDER)

## Requisitos (EARS)

- **R1** — DEBE existir una tabla `medidas_pedagogicas` con `institucion_id`
  FK, `nombre` (UNIQUE por institucion), `descripcion`, `nivel_minimo`
  (1-3, default 1), y `activa`.
- **R2** — `registro_comportamiento` DEBE tener una columna nullable
  `medida_id` (FK a `medidas_pedagogicas`, ON DELETE SET NULL).
- **R3** — Al aprovisionar una institucion, DEBEN insertarse medidas
  default alineadas con la practica colombiana (dialogo pedagogico,
  amonestacion verbal, amonestacion escrita, compromiso, citacion,
  remision a orientacion, matricula condicional, no renovacion).
- **R4** — Director y coordinador DEBEN poder crear, editar y desactivar
  medidas desde la pagina de configuracion de convivencia.
- **R5** — Profesor y otros roles NO DEBEN poder gestionar medidas.
- **R6** — `nivel_minimo` DEBE filtrar las opciones del selector: si el
  registro tiene `tipo_situacion.nivel = 1`, solo se ofrecen medidas con
  `nivel_minimo <= 1`. Si no hay tipo de situacion seleccionado, se
  muestran todas.
- **R7** — La medida es siempre opcional (no hay preferencia de
  obligatoriedad para medidas — depende del flujo institucional).
- **R8** — Registros existentes sin `medida_id` DEBEN seguir siendo
  validos.

## Diseno

### T1 — Schema y migracion

En `schema.py`, seccion 8:
```sql
CREATE TABLE IF NOT EXISTS medidas_pedagogicas (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre         TEXT    NOT NULL,
    descripcion    TEXT,
    nivel_minimo   INTEGER NOT NULL DEFAULT 1 CHECK(nivel_minimo BETWEEN 1 AND 3),
    activa         BOOLEAN NOT NULL DEFAULT 1,
    institucion_id INTEGER REFERENCES instituciones(id),
    UNIQUE(institucion_id, nombre)
)
```

En `seed.py`, ALTER TABLE idempotente:
```sql
ALTER TABLE registro_comportamiento ADD COLUMN medida_id INTEGER
    REFERENCES medidas_pedagogicas(id) ON DELETE SET NULL
```

### T2 — Catalogos estandar

En `catalogos_estandar.py`:
```python
MEDIDAS_PEDAGOGICAS_CO: list[tuple[str, str, int]] = [
    ("Dialogo pedagogico", "Conversacion formativa con el estudiante", 1),
    ("Amonestacion verbal", "Llamado de atencion verbal con registro en el observador", 1),
    ("Amonestacion escrita", "Registro formal escrito en el observador del estudiante", 1),
    ("Compromiso de convivencia", "Acuerdo firmado por estudiante y acudiente", 1),
    ("Citacion a acudiente", "Convocatoria formal al representante legal", 2),
    ("Remision a orientacion escolar", "Derivacion al profesional de apoyo psicosocial", 2),
    ("Matricula condicional", "Continuidad sujeta a cumplimiento de compromisos", 3),
    ("No renovacion de matricula", "Decision del Comite de Convivencia Escolar", 3),
]
```

### T3 — Modelo de dominio

En `convivencia.py`:
```python
class MedidaPedagogica(BaseModel):
    id: int | None = None
    nombre: str
    descripcion: str | None = None
    nivel_minimo: int = 1
    activa: bool = True
    institucion_id: int | None = None

class NuevaMedidaPedagogicaDTO(BaseModel):
    nombre: str
    descripcion: str | None = None
    nivel_minimo: int = 1

    @field_validator("nivel_minimo")
    @classmethod
    def validar_nivel(cls, v: int) -> int:
        if not (1 <= v <= 3):
            raise ValueError("El nivel minimo debe ser 1, 2 o 3.")
        return v
```

Agregar a `RegistroComportamiento`: `medida_id: int | None = None`
Agregar a `NuevoRegistroComportamientoDTO`: `medida_id: int | None = None`

### T4 — Port, repo, servicio

Patron identico a `tipos_situacion` (convivencia_34):
- Port: `listar_medidas`, `get_medida`, `guardar_medida`, `actualizar_medida`
- Repo: SQL con `WHERE institucion_id = ?`
- Servicio: `listar_medidas_pedagogicas`, `crear_medida_pedagogica`,
  `actualizar_medida_pedagogica`, `desactivar_medida_pedagogica`
- Actualizar `guardar_registro` y `actualizar_registro` para `medida_id`

### T5 — UI: Configuracion

Extender `configuracion_convivencia.py` con seccion "Medidas Pedagogicas".
Aggrid: Nombre, Descripcion, Nivel minimo, Activa. Botones Nuevo/Editar/Desactivar.
Solo director/coordinador.

### T6 — UI: Formulario de registro

En el formulario de creacion de `RegistroComportamiento`:
- Agregar `ui.select` para medida pedagogica.
- Filtrar opciones por `nivel_minimo <= tipo_situacion.nivel` cuando hay
  tipo_situacion seleccionado. Sin tipo → mostrar todas.
- Siempre opcional (placeholder "Sin medida").
- Solo visible cuando el tipo de registro es negativo (DIFICULTAD, CITACION).

### T7 — Tests

- Test de dominio: MedidaPedagogica, validacion de nivel_minimo.
- Test de servicio: CRUD con scoping.
- Test de filtro por nivel: medidas con nivel_minimo=3 no aparecen para
  tipo_situacion nivel 1.

## Verificacion

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/ -q
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe init.py
```

Escenarios manuales:
- Coordinador crea medida "Servicio social" nivel 2 → aparece en selector
  cuando el tipo de situacion es nivel 2 o 3, no cuando es nivel 1.
- Registro con medida "Dialogo pedagogico" → se guarda y se muestra en
  detalle del registro.

`init.py` verde.

## Dependencias

- Depende de convivencia_34 (tipos_situacion) para el filtro por
  `nivel_minimo` en el formulario. Sin convivencia_34, el selector
  de medidas mostraria todas las opciones (sin filtro por nivel).
- Puede implementarse en paralelo si se acepta que el filtro por nivel
  se active una vez que tipos_situacion exista.
