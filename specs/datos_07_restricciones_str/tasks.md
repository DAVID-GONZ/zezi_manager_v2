# Tasks: datos_07_restricciones_str

> Checklist de tareas en orden de menor a mayor dependencia.
> Cada tarea produce exactamente un artefacto. El implementer completa las tareas
> en el orden indicado; el reviewer verifica cada una antes de avanzar.

---

## T1 — Tipos de longitud en `base.py`

**Artefacto:** `src/domain/models/base.py`

**Qué hacer:**

Añadir los alias de tipo al final del módulo (antes de `__all__`), usando
`Annotated` con `StringConstraints`. Exportarlos en `__all__`.

```python
from typing import Annotated
from pydantic import StringConstraints

DocumentoStr     = Annotated[str, StringConstraints(max_length=30)]
GrupoCodigoStr   = Annotated[str, StringConstraints(max_length=20)]
TelefonoStr      = Annotated[str, StringConstraints(max_length=20)]
EtiquetaStr      = Annotated[str, StringConstraints(max_length=50)]
CodigoStr        = Annotated[str, StringConstraints(max_length=50)]
DaneStr          = Annotated[str, StringConstraints(min_length=12, max_length=12)]
PasswordStr      = Annotated[str, StringConstraints(max_length=128)]
NombrePropioStr  = Annotated[str, StringConstraints(max_length=100)]
NombreAreaStr    = Annotated[str, StringConstraints(max_length=120)]
NombrePersonaStr = Annotated[str, StringConstraints(max_length=150)]
NombreInstStr    = Annotated[str, StringConstraints(max_length=200)]
DireccionStr     = Annotated[str, StringConstraints(max_length=200)]
EmailStr         = Annotated[str, StringConstraints(max_length=254)]
TextoCortStr     = Annotated[str, StringConstraints(max_length=500)]
RutaLocalStr     = Annotated[str, StringConstraints(max_length=500)]
TextoMedioStr    = Annotated[str, StringConstraints(max_length=1000)]
TextoLargoStr    = Annotated[str, StringConstraints(max_length=2000)]
UrlStr           = Annotated[str, StringConstraints(max_length=2048)]
```

No se elimina ni se modifica ninguna de las tres clases existentes
(`ZeciModel`, `EntidadDominio`, `DTODominio`).

**Comando de verificación:**

```powershell
python -c "from src.domain.models.base import CodigoStr, NombrePersonaStr, EmailStr, TextoLargoStr; print('OK')"
```

---

## T2 — Cotas en `usuario.py`

**Artefacto:** `src/domain/models/usuario.py`

**Qué hacer:**

1. Importar los tipos necesarios de `base.py`:
   `CodigoStr`, `NombrePersonaStr`, `EmailStr`, `TelefonoStr`, `PasswordStr`.

2. Cambiar las anotaciones de tipo de los campos indicados en la tabla de §2.1
   de `design.md`. Los `field_validator` existentes se conservan íntegros;
   solo cambia la declaración del campo. Ejemplo:
   ```python
   # Antes
   usuario: str
   # Después
   usuario: CodigoStr
   ```

3. Para `password_temporal` (tiene `Field(default=None, exclude=True, repr=False)`):
   ```python
   password_temporal: PasswordStr | None = Field(default=None, exclude=True, repr=False)
   ```

4. Actualizar `FiltroUsuariosDTO.busqueda`:
   ```python
   busqueda: NombrePersonaStr | None = None
   ```

**No modificar** las clases de solo lectura: `DocenteInfoDTO`, `AsignacionDocenteInfoDTO`,
`UsuarioResumenDTO`, `ResumenUsuariosDTO` (R13).

**Comando de verificación:**

```powershell
python -c "
from src.domain.models.usuario import Usuario, NuevoUsuarioDTO, ActualizarUsuarioDTO, FiltroUsuariosDTO
from pydantic import ValidationError
try:
    Usuario(usuario='x'*51, nombre_completo='Test User', rol='profesor')
    assert False, 'debio fallar'
except ValidationError:
    pass
try:
    NuevoUsuarioDTO(usuario='ok', nombre_completo='T'*151, rol='profesor')
    assert False, 'debio fallar'
except ValidationError:
    pass
print('T2 OK')
"
```

---

## T3 — Cotas en `institucion.py`

**Artefacto:** `src/domain/models/institucion.py`

**Qué hacer:**

1. Importar de `base.py`:
   `CodigoStr`, `NombreInstStr`, `NombrePersonaStr`, `NombrePropioStr`,
   `TelefonoStr`, `EmailStr`, `DireccionStr`, `RutaLocalStr`, `UrlStr`,
   `TextoCortStr`, `DaneStr`.

2. Aplicar los tipos a todos los campos listados en §2.2 de `design.md`
   para `Institucion`, `NuevaInstitucionDTO`, `ActualizarInstitucionDTO`,
   `NuevaInstitucionConDirectorDTO`.

3. Los `field_validator` existentes para `nombre`, `nombre_oficial`,
   `codigo_dane`, `director_usuario`, `director_nombre_completo`,
   `director_email` se conservan sin modificación (R7).

4. `InstitucionResumenDTO` y `ResultadoAprovisionamientoDTO` no se modifican (R13).

**Comando de verificación:**

```powershell
python -c "
from src.domain.models.institucion import Institucion, NuevaInstitucionConDirectorDTO
from pydantic import ValidationError
try:
    Institucion(nombre='X'*201)
    assert False
except ValidationError:
    pass
try:
    Institucion(nombre='Valido', logo_url='http://x.com/' + 'a'*2050)
    assert False
except ValidationError:
    pass
print('T3 OK')
"
```

---

## T4 — Cotas en `estudiante.py`

**Artefacto:** `src/domain/models/estudiante.py`

**Qué hacer:**

1. Importar de `base.py`:
   `DocumentoStr`, `NombrePropioStr`, `CodigoStr`, `DireccionStr`,
   `NombrePersonaStr`, `TextoCortStr`.

2. Aplicar los tipos a todos los campos listados en §2.3 de `design.md`
   para `Estudiante`, `NuevoEstudianteDTO`, `ActualizarEstudianteDTO`,
   `FiltroEstudiantesDTO`, `MovimientoEstudiante`.

3. `EstudianteResumenDTO` y `MovimientoEstudianteInfoDTO` no se modifican (R13).

4. Los `@computed_field` y `@property` (`nombre_completo`, `edad`, etc.)
   no se modifican (R12).

**Comando de verificación:**

```powershell
python -c "
from src.domain.models.estudiante import Estudiante, NuevoEstudianteDTO
from pydantic import ValidationError
try:
    Estudiante(numero_documento='X'*31, nombre='Ana', apellido='Garcia')
    assert False
except ValidationError:
    pass
try:
    NuevoEstudianteDTO(numero_documento='1234', nombre='Ana', apellido='G', direccion='D'*201)
    assert False
except ValidationError:
    pass
print('T4 OK')
"
```

---

## T5 — Cotas en `acudiente.py`

**Artefacto:** `src/domain/models/acudiente.py`

**Qué hacer:**

1. Importar de `base.py`:
   `DocumentoStr`, `NombrePersonaStr`, `TelefonoStr`, `EmailStr`, `DireccionStr`.

2. Aplicar los tipos a todos los campos listados en §2.4 de `design.md`
   para `Acudiente`, `NuevoAcudienteDTO`, `ActualizarAcudienteDTO`.

3. `AcudienteResumenDTO` no se modifica (R13).

4. `EstudianteAcudiente` y `VincularAcudienteDTO` no tienen campos de texto libres;
   no requieren cambios.

**Comando de verificación:**

```powershell
python -c "
from src.domain.models.acudiente import Acudiente, NuevoAcudienteDTO
from pydantic import ValidationError
try:
    Acudiente(numero_documento='1234', nombre_completo='Maria Lopez', parentesco='madre', celular='3001234567890123456789')
    assert False
except ValidationError:
    pass
try:
    NuevoAcudienteDTO(numero_documento='1234', nombre_completo='A'*151, parentesco='madre')
    assert False
except ValidationError:
    pass
print('T5 OK')
"
```

---

## T6 — Cotas en `convivencia.py`

**Artefacto:** `src/domain/models/convivencia.py`

**Qué hacer:**

1. Importar de `base.py`:
   `NombrePropioStr`, `TextoMedioStr`, `TextoLargoStr`.

2. Aplicar los tipos a todos los campos listados en §2.5 de `design.md`
   para `TipoSituacion`, `MedidaPedagogica`, `CategoriaObservacion`,
   `PlantillaObservacion`, `ObservacionPeriodo`, `EntradaSeguimiento`,
   `RegistroComportamiento`, `NotaComportamiento`, `NuevoTipoSituacionDTO`,
   `NuevaMedidaPedagogicaDTO`, `NuevaCategoriaDTO`, `NuevaPlantillaDTO`,
   `NuevaObservacionDTO`, `NuevoRegistroComportamientoDTO`,
   `NuevaEntradaSeguimientoDTO`, `NuevaNotaComportamientoDTO`,
   `NuevaAlertaSeguimientoDTO`.

3. Las clases de solo lectura en el archivo (DTOs de proyección) no se modifican (R13).

4. Los `field_validator` existentes se conservan íntegros (R7).

**Comando de verificación:**

```powershell
python -c "
from src.domain.models.convivencia import ObservacionPeriodo, NuevoRegistroComportamientoDTO, TipoSituacion
from pydantic import ValidationError
import datetime
try:
    ObservacionPeriodo(estudiante_id=1, asignacion_id=1, periodo_id=1, texto='x'*2001)
    assert False
except ValidationError:
    pass
try:
    TipoSituacion(nombre='N'*101)
    assert False
except ValidationError:
    pass
print('T6 OK')
"
```

---

## T7 — Cotas en `configuracion.py`

**Artefacto:** `src/domain/models/configuracion.py`

**Qué hacer:**

1. Importar de `base.py`:
   `EtiquetaStr`, `TextoCortStr`, `NombreInstStr`, `DaneStr`,
   `NombrePersonaStr`, `NombrePropioStr`, `DireccionStr`, `TelefonoStr`,
   `RutaLocalStr`.

2. Aplicar los tipos a todos los campos listados en §2.6 de `design.md`
   para `NivelDesempeno`, `NuevoNivelDesempenoDTO`, `ActualizarNivelDesempenoDTO`,
   `ActualizarInfoInstitucionalDTO`.

3. `InformacionInstitucionalDTO` no se modifica (R13).

4. `ConfiguracionAnio`, `NuevaConfiguracionAnioDTO`, `ActualizarConfiguracionAnioDTO`,
   `CriterioPromocion` no tienen campos de texto libre; no requieren cambios.

**Comando de verificación:**

```powershell
python -c "
from src.domain.models.configuracion import NivelDesempeno, ActualizarInfoInstitucionalDTO
from pydantic import ValidationError
try:
    NivelDesempeno(anio_id=1, nombre='N'*51, rango_min=0, rango_max=100)
    assert False
except ValidationError:
    pass
try:
    ActualizarInfoInstitucionalDTO(nombre_institucion='I'*201)
    assert False
except ValidationError:
    pass
print('T7 OK')
"
```

---

## T8 — Cotas en `infraestructura.py`

**Artefacto:** `src/domain/models/infraestructura.py`

**Qué hacer:**

1. Importar de `base.py`:
   `NombreAreaStr`, `NombrePropioStr`, `GrupoCodigoStr`, `EtiquetaStr`,
   `TextoCortStr`.

2. Aplicar los tipos a todos los campos listados en §2.7 de `design.md`
   para `AreaConocimiento`, `Asignatura`, `Grupo`, `EscenarioHorario`,
   `Horario`, `Logro`, `Franja`, `PlantillaFranja`, `Grado`,
   `ConfigGeneracion`, `FranjaReunion`, `Sala`,
   `NuevaAreaDTO`, `NuevaAsignaturaDTO`, `NuevoGrupoDTO`,
   `NuevoEscenarioDTO`, `NuevaSalaDTO`, `NuevoHorarioDTO`,
   `NuevoLogroDTO`, `NuevaPlantillaFranjaDTO`, `NuevaFranjaDTO`,
   `NuevaConfigGeneracionDTO`.

3. Los campos de solo lectura (HorarioInfo, ResultadoGeneracionDTO,
   BloqueGeneradoDTO, MetricasCalidadDTO, FilaReporteDTO, etc.) no se
   modifican (R13).

4. Los campos R14 (`jornada`, `dia_semana`, `hora_inicio`, `hora_fin`,
   `created_at`, `updated_at`) no se modifican (R14).

5. `AreaConocimiento.color` permanece como `str | None` sin tipo de
   categoría. Se documenta inline con `# excepcion: hex color max=7; ver design.md §3`.

**Comando de verificación:**

```powershell
python -c "
from src.domain.models.infraestructura import AreaConocimiento, Grupo, Logro
from pydantic import ValidationError
try:
    AreaConocimiento(nombre='N'*121)
    assert False
except ValidationError:
    pass
try:
    Grupo(codigo='G'*21)
    assert False
except ValidationError:
    pass
try:
    Logro(asignacion_id=1, periodo_id=1, descripcion='D'*501)
    assert False
except ValidationError:
    pass
print('T8 OK')
"
```

---

## T9 — Test estructural `test_restricciones_str.py`

**Artefacto:** `tests/unit/domain/test_restricciones_str.py`

**Qué hacer:**

Crear el archivo con tres tests:

### `test_todos_los_campos_str_tienen_cota` (R22, R24)

Recorre `MODELOS_EN_SCOPE` (lista de clases). Para cada clase, itera
`model_fields`. Para cada campo cuya anotación sea `str` o `str | None`:

1. Intenta extraer `max_length` de `StringConstraints` en la metadata
   del tipo `Annotated`.
2. Si no hay `max_length`, busca el campo en `EXCLUSIONES[clase]`.
3. Si no está en ninguno de los dos: `pytest.fail(...)` con mensaje que
   indique clase y campo.

### `test_cotas_coherentes_con_validators_existentes` (R23)

Itera `COTAS_CON_VALIDATOR_EXISTENTE: dict[tuple[type, str], int]`,
que recoge todos los pares (clase, campo) que ya tenían un `field_validator`
comprobando longitud máxima, con el valor que ese validator exige:

```python
COTAS_CON_VALIDATOR_EXISTENTE = {
    (Usuario, "usuario"): 50,
    (Usuario, "nombre_completo"): 150,
    (Estudiante, "nombre"): 100,
    (Estudiante, "apellido"): 100,
    (NuevoEstudianteDTO, "nombre"): 100,
    (NuevoEstudianteDTO, "apellido"): 100,
    (ActualizarEstudianteDTO, "nombre"): 100,
    (ActualizarEstudianteDTO, "apellido"): 100,
    (Acudiente, "nombre_completo"): 150,
    (Institucion, "nombre"): 200,
    (Institucion, "nombre_oficial"): 200,
    (NuevaInstitucionDTO, "nombre"): 200,
    (NuevaInstitucionConDirectorDTO, "nombre"): 200,
    (NuevaInstitucionConDirectorDTO, "nombre_oficial"): 200,
    (AreaConocimiento, "nombre"): 120,
    (Asignatura, "nombre"): 100,
    (Grupo, "codigo"): 20,
    (NivelDesempeno, "nombre"): 50,
    (ObservacionPeriodo, "texto"): 2000,
    (EntradaSeguimiento, "texto"): 2000,
    (RegistroComportamiento, "descripcion"): 1000,
    (Logro, "descripcion"): 500,
}
```

Para cada entrada, afirma que el `max_length` declarado en el tipo `Annotated`
del campo coincide con el valor esperado.

### `test_email_formato_preservado` (R17)

Verifica que los modelos con campo `email` (o `email_institucional`,
`director_email`) siguen rechazando cadenas sin `@`, cadenas con dominio
sin `.` y aceptan un email válido normalizado a minúsculas. Usa los modelos
`Usuario`, `Acudiente`, `Institucion` como representativos.

**Función auxiliar interna `_max_length_de_campo(field_info) -> int | None`**

```python
from pydantic import StringConstraints
from pydantic.fields import FieldInfo

def _max_length_de_campo(field_info: FieldInfo) -> int | None:
    for meta in field_info.metadata:
        if isinstance(meta, StringConstraints) and meta.max_length is not None:
            return meta.max_length
    return None
```

**Comando de verificación:**

```powershell
python -m pytest tests/unit/domain/test_restricciones_str.py -v
```

---

## T10 — Verificación global

**Artefacto:** ninguno nuevo (verificación de integración del paso completo)

**Qué hacer:**

Ejecutar el harness completo. Deben estar verdes:
- Las tres suites de tests del paso (`test_restricciones_str.py`)
- Todos los tests de dominio preexistentes que usen los modelos modificados
- La puerta `init.py`

**Comando de verificación:**

```powershell
python init.py
```

Si `init.py` reporta errores en tests de dominio preexistentes, el implementer
debe corregirlos antes de declarar el paso terminado. No se acepta un verde
parcial.
