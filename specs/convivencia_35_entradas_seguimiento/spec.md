# convivencia_35_entradas_seguimiento — Spec

## Contexto

El campo `seguimiento` en `registro_comportamiento` es un TEXT unico que
se REEMPLAZA cada vez que se invoca `agregar_seguimiento`. En un colegio
real colombiano, el seguimiento de un caso de convivencia es una bitacora
cronologica con multiples entradas a lo largo de dias o semanas:

- "Dia 1: se hablo con el estudiante y se establecio compromiso verbal."
- "Dia 3: se cito al acudiente; no asistio."
- "Dia 5: segundo intento; el acudiente asistio y firmo compromiso."
- "Semana 3: revision del compromiso; estudiante ha mejorado."

La semantica destructiva del campo unico pierde el historial de acciones
y compromete la trazabilidad del debido proceso (Art. 26 Ley 1620). Esta
spec crea una tabla hija `entradas_seguimiento` que acumula entradas con
fecha automatica y autor, y mantiene el campo legacy como denormalizacion
para backwards compatibility.

Scope:
- `src/infrastructure/db/schema.py` (NUEVA tabla)
- `src/infrastructure/db/seed.py` (migracion de datos existentes)
- `src/domain/models/convivencia.py` (EXTENDER — nuevo modelo + DTO)
- `src/domain/ports/convivencia_repo.py` (EXTENDER)
- `src/infrastructure/db/repositories/sqlite_convivencia_repo.py` (EXTENDER)
- `src/services/convivencia_service.py` (EXTENDER + MODIFICAR)
- `src/interface/pages/convivencia/seguimiento.py` (MODIFICAR — timeline)
- `src/interface/presenters/convivencia/seguimiento_presenter.py` (EXTENDER)
- `tests/` (EXTENDER)

## Requisitos (EARS)

- **R1** — DEBE existir una tabla `entradas_seguimiento` con columnas:
  `id`, `registro_id` (FK CASCADE a `registro_comportamiento`),
  `fecha` (DATETIME, default CURRENT_TIMESTAMP), `texto` (TEXT NOT NULL),
  `usuario_id` (FK SET NULL a `usuarios`).
- **R2** — `agregar_entrada_seguimiento(dto, usuario_id, usuario_rol)`
  DEBE crear una nueva fila en `entradas_seguimiento` SIN eliminar las
  anteriores.
- **R3** — Al agregar una entrada, el campo legacy
  `registro_comportamiento.seguimiento` DEBE actualizarse con el texto
  de la ultima entrada (denormalizacion para compat con codigo existente
  que lea el campo).
- **R4** — `listar_entradas_seguimiento(registro_id)` DEBE retornar todas
  las entradas ordenadas por `fecha` ascendente.
- **R5** — Cada entrada DEBE registrar automaticamente la fecha de creacion
  (via `default_factory=datetime.now` en el modelo, `DEFAULT CURRENT_TIMESTAMP`
  en la BD).
- **R6** — RBAC: las mismas reglas que `agregar_seguimiento` actual — solo
  director de grupo (de ese grupo), director y coordinador pueden agregar
  entradas.
- **R7** — Migracion de datos existentes: todo `registro_comportamiento`
  con `seguimiento IS NOT NULL` DEBE generar UNA `EntradaSeguimiento` con
  el texto existente (idempotente — no duplicar si ya se migro).
- **R8** — El metodo legacy `agregar_seguimiento(registro_id, texto)` DEBE
  seguir funcionando: internamente delega en `agregar_entrada_seguimiento`
  y ademas actualiza el campo legacy.
- **R9** — La UI de detalle del registro en el hub de seguimiento DEBE
  mostrar una timeline cronologica de entradas (fecha + texto + autor) en
  lugar del campo de texto unico actual.
- **R10** — DEBE existir un boton "Agregar seguimiento" que abre un dialog
  con un textarea para el nuevo texto.

## Diseno

### T1 — Schema

En `schema.py`, seccion 8, nueva tabla:
```sql
CREATE TABLE IF NOT EXISTS entradas_seguimiento (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    registro_id INTEGER NOT NULL,
    fecha       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    texto       TEXT NOT NULL,
    usuario_id  INTEGER,
    FOREIGN KEY(registro_id) REFERENCES registro_comportamiento(id) ON DELETE CASCADE,
    FOREIGN KEY(usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
)
```

Indices:
```sql
CREATE INDEX IF NOT EXISTS idx_seg_registro ON entradas_seguimiento(registro_id)
CREATE INDEX IF NOT EXISTS idx_seg_fecha    ON entradas_seguimiento(fecha)
```

### T2 — Modelo de dominio

En `convivencia.py`:
```python
class EntradaSeguimiento(BaseModel):
    id: int | None = None
    registro_id: int
    fecha: datetime = Field(default_factory=datetime.now)
    texto: str
    usuario_id: int | None = None
    usuario_nombre: str | None = None  # solo lectura, resuelto en repo/servicio

    @field_validator("texto", mode="before")
    @classmethod
    def validar_texto(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El texto de seguimiento no puede estar vacio.")
        if len(v) > 2000:
            raise ValueError(f"El texto no puede exceder 2000 caracteres (tiene {len(v)}).")
        return v

class NuevaEntradaSeguimientoDTO(BaseModel):
    registro_id: int
    texto: str

    @field_validator("texto", mode="before")
    @classmethod
    def validar_texto(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El texto no puede estar vacio.")
        return v
```

### T3 — Port y repositorio

En `convivencia_repo.py`:
```python
@abstractmethod
def listar_entradas_seguimiento(self, registro_id: int) -> list[EntradaSeguimiento]: ...

@abstractmethod
def guardar_entrada_seguimiento(self, entrada: EntradaSeguimiento) -> EntradaSeguimiento: ...
```

En `sqlite_convivencia_repo.py`: implementar con INSERT + SELECT.
El `listar_entradas_seguimiento` hace JOIN con `usuarios` para resolver
`usuario_nombre` (patron: `u.nombre || ' ' || u.apellido`). Orden por
`fecha ASC`.

### T4 — Servicio

Nuevo metodo:
```python
@requiere_escritura
def agregar_entrada_seguimiento(
    self,
    dto: NuevaEntradaSeguimientoDTO,
    usuario_id: int | None = None,
    usuario_rol: str | None = None,
) -> EntradaSeguimiento:
    registro = self._get_registro_o_lanzar(dto.registro_id)
    self._verificar_autorizacion(usuario_rol, usuario_id, registro.grupo_id)
    entrada = EntradaSeguimiento(
        registro_id=dto.registro_id,
        texto=dto.texto,
        usuario_id=usuario_id,
    )
    entrada = self._repo.guardar_entrada_seguimiento(entrada)
    # Denormalizacion: actualizar campo legacy
    registro_actualizado = registro.agregar_seguimiento(dto.texto)
    self._repo.actualizar_registro(registro_actualizado)
    return entrada
```

Nuevo metodo de lectura:
```python
def listar_entradas_seguimiento(self, registro_id: int) -> list[EntradaSeguimiento]:
    return self._repo.listar_entradas_seguimiento(registro_id)
```

Modificar `agregar_seguimiento` existente: delegar a `agregar_entrada_seguimiento`
para que tambien cree la entrada en la tabla hija. Mantener la firma publica
compatible.

### T5 — Migracion de datos

En `seed.py`, nueva funcion `_migrate_entradas_seguimiento(conn)`:
```python
# Crear tabla si no existe (ya la crea schema.py, pero por seguridad)
# Migrar datos existentes:
conn.execute("""
    INSERT INTO entradas_seguimiento (registro_id, texto, usuario_id, fecha)
    SELECT rc.id, rc.seguimiento, rc.usuario_registro_id,
           COALESCE(rc.fecha, CURRENT_TIMESTAMP)
    FROM registro_comportamiento rc
    WHERE rc.seguimiento IS NOT NULL
      AND rc.id NOT IN (SELECT registro_id FROM entradas_seguimiento)
""")
```
Llamar desde `seed_base()`.

### T6 — UI: Timeline en seguimiento

En `seguimiento.py`, en el panel de detalle de un registro seleccionado:
- Reemplazar el texto plano de `seguimiento` con una timeline vertical.
- Cada entrada: fecha (en negrita, formato "dd/mm/yyyy HH:mm"), texto,
  nombre del responsable.
- Boton "Agregar seguimiento" abre `form_dialog` con un textarea.
- Al guardar, llama a `Container.convivencia_service().agregar_entrada_seguimiento(dto, ...)`.
- Refrescar la timeline.

Extender `SeguimientoPresenter` con state:
```python
"entradas_seguimiento": []  # list[EntradaSeguimiento]
```

### T7 — Tests

- Test de dominio: `EntradaSeguimiento` validacion de texto.
- Test de repo: guardar y listar entradas, orden cronologico.
- Test de servicio: `agregar_entrada_seguimiento` + denormalizacion del
  campo legacy + RBAC.
- Test de migracion: registros con seguimiento existente producen una
  entrada tras la migracion.

## Verificacion

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/ -q
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe init.py
```

Escenarios manuales:
- Crear registro de dificultad → agregar 3 entradas de seguimiento en
  dias distintos → timeline muestra las 3 con fecha, texto y autor.
- El campo legacy `seguimiento` del registro tiene el texto de la ultima
  entrada.
- Registros existentes con texto de seguimiento: al migrar, la timeline
  muestra la entrada migrada.

`init.py` verde.

## Dependencias

- Ninguna dependencia bloqueante directa.
- Puede implementarse en paralelo con convivencia_34.
- El observador del estudiante (convivencia_37) consumira las entradas
  de esta tabla para armar la cronologia completa.
