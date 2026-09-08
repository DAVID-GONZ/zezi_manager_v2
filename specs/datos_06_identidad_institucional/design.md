# Diseño técnico: datos_06_identidad_institucional

> Operación: modificar.
> Fuente de autoridad: `specs/datos_06_identidad_institucional/requirements.md`.

---

## 1. Campos eliminados de `ConfiguracionAnio`

### 1.1 Campos de identidad duplicados (8)

| Campo en ConfiguracionAnio | Campo canónico en Institucion  |
|---|---|
| `nombre_institucion`       | `nombre_oficial` / `nombre`    |
| `dane_code`                | `codigo_dane`                  |
| `rector`                   | `rector`                       |
| `direccion`                | `direccion`                    |
| `municipio`                | `municipio`                    |
| `telefono_institucion`     | `telefono`                     |
| `logo_path`                | `logo_path`                    |
| `resolucion_aprobacion`    | `resolucion_aprobacion`        |

Todos se eliminan del modelo Pydantic. Los validadores asociados
(`validar_nombre_institucion`, `limpiar_campo_opcional`) desaparecen también.
El campo computado `tiene_informacion_institucional` (que referencia `dane_code`
y `rector`) se elimina — la comprobación equivalente vive en
`InformacionInstitucionalDTO.desde_institucion`.

### 1.2 Campo muerto eliminado (1)

`logo_url` en `ConfiguracionAnio`: nunca aparece en los INSERT ni UPDATE del
repositorio SQLite (comprobado en `sqlite_configuracion_repo.py`). Tampoco
tiene lector de negocio. Se elimina del modelo.

### 1.3 Razón del enfoque modelo-primero

Eliminar los campos del modelo Pydantic hace que `model_dump()` ya no los incluya
y que el constructor rechace filas que los contengan. El repositorio SQLite pasa
de `SELECT *` a una lista de columnas explícita (solo campos académicos), de modo
que los campos muertos en la tabla SQLite no se envían al constructor y la BD no
necesita recrearse (decisión arquitectónica: sin migraciones en este entorno).

---

## 2. Cambios en los repositorios

### 2.1 `SqliteConfiguracionRepository` (único afectado)

Se define una constante `_COLS_ACADEMICOS` con los campos académicos:

```
id, anio, institucion_id, fecha_inicio_clases, fecha_fin_clases,
nota_minima_aprobacion, nota_minima_escala, nota_maxima_escala, activo
```

- `get_activa`, `get_by_id`, `get_by_anio`, `listar`: usan `SELECT {_COLS_ACADEMICOS}`.
- `guardar`: el INSERT deja de incluir los 8 campos de identidad y `logo_url`.
- `actualizar`: el UPDATE deja de incluir los mismos 9 campos.

Los 9 campos permanecen como columnas muertas en el fichero SQLite; el schema
DDL no cambia (sin migraciones).

### 2.2 `SqliteInstitucionRepository`

Sin cambios. `get_by_id` ya devuelve la entidad `Institucion` completa con todos
los campos de identidad.

### 2.3 `IConfiguracionRepository` / `IInstitucionRepository`

Sin nuevos métodos abstractos. Los cambios son de implementación interna del
repositorio SQLite.

---

## 3. Cambios en `configuracion_service.py`

### 3.1 `actualizar_info_institucional` (R7, R8)

**Antes**: aplica `ActualizarInfoInstitucionalDTO` sobre `ConfiguracionAnio` y
llama a `repo.actualizar`.

**Después**:
1. Resuelve la config por `anio_id`.
2. Si `config.institucion_id is None` → lanza `ReglaDeNegocioError` con mensaje
   que indica que el año no tiene institución asociada (R8).
3. Convierte el DTO vía `dto.to_actualizar_institucion_dto()` → `ActualizarInstitucionDTO`.
4. Delega en `Container.institucion_service().actualizar(config.institucion_id, inst_dto)`.
5. Retorna la config sin modificar (la identidad ya no vive en ella).

### 3.2 `get_info_institucional` (R3, R4, R5, R14, R15)

**Antes**: llama a `InformacionInstitucionalDTO.desde_configuracion(config)`, que
lee los campos de identidad de `ConfiguracionAnio`.

**Después**:
1. Resuelve la config por `anio_id`.
2. Si `config.institucion_id is None` → retorna un `InformacionInstitucionalDTO`
   con valores por defecto (`nombre_institucion="Institución Educativa"`,
   todos los opcionales como `None`). No lanza (R5). `dane_code` y `rector` se
   dejan como cadena vacía / None; si el caller intenta generar boletines, fallará
   en R15.

   > Nota: `InformacionInstitucionalDTO.dane_code` es `str` no opcional. Para el
   > caso sin institución se define un subtipo o se acepta `""` en el campo DTO
   > que representa "dato ausente" — ver §6.

3. Si hay `institucion_id` → obtiene la entidad `Institucion` vía
   `Container.institucion_service().get(config.institucion_id)`.
4. Llama a `InformacionInstitucionalDTO.desde_institucion(inst, config.anio, config.nota_minima_aprobacion)` (R14).
5. `desde_institucion` ya valida `dane_code` y `rector` y lanza si faltan (R15).

### 3.3 `crear_anio` (R2)

Se elimina el bloque "Auto-snapshot (mejora_06)" que copiaba la identidad de la
institución al nuevo año. El año nace solo con campos académicos.

---

## 4. Cambios en `informe_service.py` (R14–R16)

### 4.1 Nuevo parámetro de constructor

```python
config_svc_provider: Callable[[], ConfiguracionService] | None = None
```

Sigue el patrón `convivencia_svc_provider` ya presente. Lazy para evitar ciclos.

### 4.2 Nuevo método `get_informacion_institucional`

```python
def get_informacion_institucional(self, anio_id: int) -> InformacionInstitucionalDTO:
```

Punto de acceso único (R16) para los generadores de boletines e informes. Delega
en `ConfiguracionService.get_info_institucional(anio_id)`. Si no hay
`config_svc_provider`, lanza `DependenciaNoDisponibleError`.

La generación de boletines PDF debe llamar a este método para obtener los datos
del membrete, en lugar de leer directamente de `ConfiguracionAnio`.

---

## 5. Cambios en `configuracion.py` (DTOs)

### 5.1 `NuevaConfiguracionAnioDTO`

Se elimina el campo `nombre_institucion: str = "Institución Educativa"`. El DTO
ya no transporta ni implanta identidad en el año nuevo.

### 5.2 `ActualizarInfoInstitucionalDTO`

- Se elimina el método `aplicar_a(config: ConfiguracionAnio)` (ya no hay nada que aplicar en config).
- Se añade el método `to_actualizar_institucion_dto() -> ActualizarInstitucionDTO` que
  construye el DTO de institución a partir del mapeo de nombres:
  `nombre_institucion → nombre_oficial`, `dane_code → codigo_dane`,
  `telefono_institucion → telefono`, resto 1:1.
- El DTO en sí permanece para no romper los callers existentes (páginas).

### 5.3 `InformacionInstitucionalDTO`

- Se elimina el método de clase `desde_configuracion`. Los datos de identidad ya
  no están en `ConfiguracionAnio`.
- Se mantiene `desde_institucion` sin cambios.
- Para el caso sin institución (R5), el campo `dane_code` se declara `str | None`
  (cambiando de `str` a `str | None`) y `rector` permanece `str | None`. Esto
  permite construir el DTO con `None` cuando no hay institución, sin que el
  servicio de boletines explote antes de la validación de R15.

---

## 6. Dónde viven las validaciones

| Validación | Capa | Razón |
|---|---|---|
| Formato 12 dígitos del código DANE | `domain / Institucion.validar_codigo_dane` | Regla pura de dominio, R9 |
| `nombre_oficial` no vacío | `domain / Institucion.validar_nombre_oficial` | Regla pura de dominio |
| DANE + rector presentes para boletines | `domain / InformacionInstitucionalDTO.desde_institucion` | Política de dominio, R15 |
| Año sin institución → rechazar actualizar identidad | `services / configuracion_service.actualizar_info_institucional` | Regla de negocio entre entidades |
| Nota mínima en rango | `domain / ConfiguracionAnio` | Sin cambios |

La validación DANE (R9) es única porque vive en la entidad `Institucion` y se
ejecuta tanto en la creación como en la actualización, independientemente del
punto de entrada.

---

## 7. Alternativa descartada: campo computado en ConfiguracionAnio

**Idea**: en lugar de eliminar los campos de identidad de `ConfiguracionAnio`,
marcarlos como `@computed_field` que lean desde la institución dueña.

**Descartada porque**:
1. `domain/` no puede importar repos ni servicios (regla de dependencias §2 de
   `docs/conventions.md`). Un `@computed_field` que lee de la BD violaría la
   arquitectura limpia.
2. Mantendría los campos en `model_dump()`, lo que rompería R2 (el repo
   seguiría pudiendo escribirlos accidentalmente).
3. Añadiría una dependencia oculta entre la entidad de dominio y la capa de
   infraestructura, haciendo el modelo difícil de testear de forma unitaria.
