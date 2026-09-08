# Design: datos_07_restricciones_str

> Decisiones técnicas del paso. Léase junto con `requirements.md`.
> Alcance: `src/domain/models/base.py` y los siete archivos de modelos listados en el scope.

---

## 1. Categorías semánticas de longitud (R4/R5)

Todas las cotas se declaran en `src/domain/models/base.py` como alias de tipo
`Annotated[str, StringConstraints(max_length=N)]`. El alias es la fuente única de verdad (R5):
cambiar el `max_length` en `base.py` propaga automáticamente la cota a todos los campos
que lo usan. No se escribe ningún número literal de longitud en las declaraciones
de campo individuales salvo en las excepciones documentadas en §5.

| Alias | max\_length | Cobertura semántica |
|---|---|---|
| `DocumentoStr` | 30 | Números de documento (TI, CC, CE, NUIP, PASAPORTE) |
| `GrupoCodigoStr` | 20 | Códigos de grupo escolar (601, A1, 1101-B, …) |
| `TelefonoStr` | 20 | Teléfono/celular con prefijo internacional y separadores |
| `EtiquetaStr` | 50 | Etiquetas de pantalla cortas (nombre nivel desempeño, sala, etiqueta franja) |
| `CodigoStr` | 50 | Identificadores cortos de sistema (username, código externo, NIT, código área) |
| `DaneStr` | 12 (min=12, max=12) | Código DANE: longitud fija exigida por estándar externo |
| `PasswordStr` | 128 | Campos que transportan contraseñas (política vigente) |
| `NombrePropioStr` | 100 | Nombres de persona (nombre/apellido individuales), nombres cortos de entidades académicas |
| `NombreAreaStr` | 120 | Nombres de área de conocimiento (Ley 115; nombres colombianos alcanzan ~80 chars) |
| `NombrePersonaStr` | 150 | Nombre completo de persona natural (nombre\_completo) |
| `NombreInstStr` | 200 | Nombres de institución educativa, nombres oficiales, referencias a resoluciones |
| `DireccionStr` | 200 | Direcciones físicas (calle + número + complemento) |
| `EmailStr` | 254 | Correo electrónico — máximo RFC 5321 para una dirección enrutable (R16) |
| `TextoCortStr` | 500 | Descripciones cortas, enunciados de logros, descripciones de escenario |
| `RutaLocalStr` | 500 | Rutas del sistema de archivos local |
| `TextoMedioStr` | 1 000 | Descripciones de registros de comportamiento, protocolos breves |
| `TextoLargoStr` | 2 000 | Textos narrativos libres (observaciones de periodo, seguimientos, plantillas) |
| `UrlStr` | 2 048 | URLs de recursos remotos (logo\_url); límite práctico de cliente HTTP |

`DaneStr` es la única categoría con `min_length` además de `max_length`
porque el DANE es un código externo de longitud fija exacta (12 dígitos). La validación de
que sean solo dígitos permanece en el `field_validator` existente.

---

## 2. Campos acotados por modelo y categoría

### 2.1 `usuario.py`

| Clase | Campo | Categoría | Nota |
|---|---|---|---|
| `Usuario` | `usuario` | `CodigoStr` | ya tiene validator max=50; categoría must match (R6) |
| `Usuario` | `nombre_completo` | `NombrePersonaStr` | ya tiene validator max=150 (R6) |
| `Usuario` | `email` | `EmailStr` | solo formato; añade max=254 |
| `Usuario` | `telefono` | `TelefonoStr` | sin max previo; añade max=20 |
| `Usuario` | `password_temporal` | `PasswordStr` | R20: transporta contraseña temporal; `exclude=True` permanece |
| `NuevoUsuarioDTO` | `usuario` | `CodigoStr` | ya tiene validator max=50 implícito (R6) |
| `NuevoUsuarioDTO` | `nombre_completo` | `NombrePersonaStr` | validator tiene min=3 pero no max; añade max=150 |
| `NuevoUsuarioDTO` | `email` | `EmailStr` | añade max=254 |
| `NuevoUsuarioDTO` | `telefono` | `TelefonoStr` | añade max=20 |
| `NuevoUsuarioDTO` | `password` | `PasswordStr` | R20; sin max previo |
| `ActualizarUsuarioDTO` | `nombre_completo` | `NombrePersonaStr` | validator tiene min pero no max |
| `ActualizarUsuarioDTO` | `email` | `EmailStr` | añade max=254 |
| `ActualizarUsuarioDTO` | `telefono` | `TelefonoStr` | añade max=20 |
| `FiltroUsuariosDTO` | `busqueda` | `NombrePersonaStr` | parámetro de búsqueda; cota de nombre completo |

### 2.2 `institucion.py`

| Clase | Campo | Categoría | Nota |
|---|---|---|---|
| `Institucion` | `nombre` | `NombreInstStr` | ya tiene validator max=200 (R6) |
| `Institucion` | `nit` | `CodigoStr` | sin max previo; NIT colombiano ≤13 chars con formato |
| `Institucion` | `codigo` | `CodigoStr` | sin max previo (código externo) |
| `Institucion` | `nombre_oficial` | `NombreInstStr` | ya tiene validator max=200 (R6) |
| `Institucion` | `codigo_dane` | `DaneStr` | ya tiene validator exacto=12 dígitos (R6) |
| `Institucion` | `rector` | `NombrePersonaStr` | nombre completo de persona |
| `Institucion` | `direccion` | `DireccionStr` | dirección física |
| `Institucion` | `pais` | `NombrePropioStr` | nombre de país |
| `Institucion` | `departamento` | `NombrePropioStr` | departamento de Colombia |
| `Institucion` | `municipio` | `NombrePropioStr` | municipio |
| `Institucion` | `telefono` | `TelefonoStr` | añade max=20 |
| `Institucion` | `logo_path` | `RutaLocalStr` | ruta de archivo (R21) |
| `Institucion` | `logo_url` | `UrlStr` | URL remoto (R21) |
| `Institucion` | `resolucion_aprobacion` | `NombreInstStr` | referencia larga de resolución |
| `Institucion` | `lema` | `TextoCortStr` | lema institucional |
| `Institucion` | `email_institucional` | `EmailStr` | R16; añade max=254 |
| `NuevaInstitucionDTO` | `nombre` | `NombreInstStr` | ya tiene validator max=200 (R6) |
| `NuevaInstitucionDTO` | `nit` | `CodigoStr` | sin max previo |
| `NuevaInstitucionDTO` | `codigo` | `CodigoStr` | sin max previo |
| `ActualizarInstitucionDTO` | `nombre` | `NombreInstStr` | sin validator en el DTO; entidad valida max=200 |
| `ActualizarInstitucionDTO` | `nit` | `CodigoStr` | sin max previo |
| `ActualizarInstitucionDTO` | `nombre_oficial` | `NombreInstStr` | entidad valida max=200 |
| `ActualizarInstitucionDTO` | `codigo_dane` | `DaneStr` | entidad valida exacto=12 |
| `ActualizarInstitucionDTO` | `rector` | `NombrePersonaStr` | |
| `ActualizarInstitucionDTO` | `direccion` | `DireccionStr` | |
| `ActualizarInstitucionDTO` | `pais` | `NombrePropioStr` | |
| `ActualizarInstitucionDTO` | `departamento` | `NombrePropioStr` | |
| `ActualizarInstitucionDTO` | `municipio` | `NombrePropioStr` | |
| `ActualizarInstitucionDTO` | `telefono` | `TelefonoStr` | |
| `ActualizarInstitucionDTO` | `logo_path` | `RutaLocalStr` | R21 |
| `ActualizarInstitucionDTO` | `logo_url` | `UrlStr` | R21 |
| `ActualizarInstitucionDTO` | `resolucion_aprobacion` | `NombreInstStr` | |
| `ActualizarInstitucionDTO` | `lema` | `TextoCortStr` | |
| `ActualizarInstitucionDTO` | `email_institucional` | `EmailStr` | R16 |
| `NuevaInstitucionConDirectorDTO` | `nombre` | `NombreInstStr` | ya tiene validator max=200 (R6) |
| `NuevaInstitucionConDirectorDTO` | `nombre_oficial` | `NombreInstStr` | ya tiene validator max=200 (R6) |
| `NuevaInstitucionConDirectorDTO` | `codigo_dane` | `DaneStr` | ya tiene validator exacto=12 (R6) |
| `NuevaInstitucionConDirectorDTO` | `pais` | `NombrePropioStr` | |
| `NuevaInstitucionConDirectorDTO` | `departamento` | `NombrePropioStr` | |
| `NuevaInstitucionConDirectorDTO` | `municipio` | `NombrePropioStr` | |
| `NuevaInstitucionConDirectorDTO` | `director_usuario` | `CodigoStr` | validator tiene min=3 y sin espacios; sin max → añade 50 |
| `NuevaInstitucionConDirectorDTO` | `director_nombre_completo` | `NombrePersonaStr` | validator min=3; sin max → añade 150 |
| `NuevaInstitucionConDirectorDTO` | `director_email` | `EmailStr` | R16 |

### 2.3 `estudiante.py`

| Clase | Campo | Categoría | Nota |
|---|---|---|---|
| `Estudiante` | `numero_documento` | `DocumentoStr` | TI: ≤12, CC: ≤10, NUIP: ≤11; max=30 con margen doble |
| `Estudiante` | `nombre` | `NombrePropioStr` | ya tiene validator max=100 (R6) |
| `Estudiante` | `apellido` | `NombrePropioStr` | ya tiene validator max=100 (R6) |
| `Estudiante` | `id_publico` | `CodigoStr` | identificador interno generado |
| `Estudiante` | `direccion` | `DireccionStr` | sin max previo |
| `NuevoEstudianteDTO` | `numero_documento` | `DocumentoStr` | validator normaliza; sin max |
| `NuevoEstudianteDTO` | `nombre` | `NombrePropioStr` | ya tiene validator max=100 (R6) |
| `NuevoEstudianteDTO` | `apellido` | `NombrePropioStr` | ya tiene validator max=100 (R6) |
| `NuevoEstudianteDTO` | `direccion` | `DireccionStr` | sin max previo |
| `ActualizarEstudianteDTO` | `nombre` | `NombrePropioStr` | ya tiene validator max=100 (R6) |
| `ActualizarEstudianteDTO` | `apellido` | `NombrePropioStr` | ya tiene validator max=100 (R6) |
| `ActualizarEstudianteDTO` | `direccion` | `DireccionStr` | sin max previo |
| `FiltroEstudiantesDTO` | `busqueda` | `NombrePersonaStr` | nombre completo o documento |
| `MovimientoEstudiante` | `motivo` | `TextoCortStr` | motivo libre del movimiento |

### 2.4 `acudiente.py`

| Clase | Campo | Categoría | Nota |
|---|---|---|---|
| `Acudiente` | `numero_documento` | `DocumentoStr` | incluye PASAPORTE (hasta ~20 chars); max=30 con margen |
| `Acudiente` | `nombre_completo` | `NombrePersonaStr` | ya tiene validator max=150 (R6) |
| `Acudiente` | `celular` | `TelefonoStr` | validator strip; sin max |
| `Acudiente` | `email` | `EmailStr` | formato validado; añade max=254 (R16) |
| `Acudiente` | `direccion` | `DireccionStr` | sin max previo |
| `NuevoAcudienteDTO` | `numero_documento` | `DocumentoStr` | sin max previo |
| `NuevoAcudienteDTO` | `nombre_completo` | `NombrePersonaStr` | validator solo min=3; añade max=150 |
| `NuevoAcudienteDTO` | `email` | `EmailStr` | formato mínimo validado; añade max=254 |
| `ActualizarAcudienteDTO` | `nombre_completo` | `NombrePersonaStr` | validator solo min=3; añade max=150 |

### 2.5 `convivencia.py`

| Clase | Campo | Categoría | Nota |
|---|---|---|---|
| `TipoSituacion` | `nombre` | `NombrePropioStr` | nombre corto como "Tipo I: Situación leve" |
| `TipoSituacion` | `descripcion` | `TextoMedioStr` | descripción opcional |
| `TipoSituacion` | `protocolo` | `TextoLargoStr` | protocolo de atención puede ser extenso |
| `MedidaPedagogica` | `nombre` | `NombrePropioStr` | |
| `MedidaPedagogica` | `descripcion` | `TextoMedioStr` | |
| `CategoriaObservacion` | `nombre` | `NombrePropioStr` | |
| `PlantillaObservacion` | `texto` | `TextoLargoStr` | texto reutilizable para observaciones |
| `ObservacionPeriodo` | `texto` | `TextoLargoStr` | ya tiene validator max=2000 (R6) |
| `EntradaSeguimiento` | `texto` | `TextoLargoStr` | ya tiene validator max=2000 (R6) |
| `RegistroComportamiento` | `descripcion` | `TextoMedioStr` | ya tiene validator max=1000 (R6) |
| `NotaComportamiento` | `observacion` | `TextoLargoStr` | concepto narrativo |
| `NuevoTipoSituacionDTO` | `nombre` | `NombrePropioStr` | |
| `NuevoTipoSituacionDTO` | `descripcion` | `TextoMedioStr` | |
| `NuevoTipoSituacionDTO` | `protocolo` | `TextoLargoStr` | |
| `NuevaMedidaPedagogicaDTO` | `nombre` | `NombrePropioStr` | |
| `NuevaMedidaPedagogicaDTO` | `descripcion` | `TextoMedioStr` | |
| `NuevaCategoriaDTO` | `nombre` | `NombrePropioStr` | |
| `NuevaPlantillaDTO` | `texto` | `TextoLargoStr` | |
| `NuevaObservacionDTO` | `texto` | `TextoLargoStr` | validator solo non-empty; añade max=2000 vía tipo |
| `NuevoRegistroComportamientoDTO` | `descripcion` | `TextoMedioStr` | validator solo non-empty; añade max=1000 vía tipo |
| `NuevaEntradaSeguimientoDTO` | `texto` | `TextoLargoStr` | validator solo non-empty; añade max=2000 vía tipo |
| `NuevaNotaComportamientoDTO` | `observacion` | `TextoLargoStr` | |
| `NuevaAlertaSeguimientoDTO` | `descripcion` | `TextoMedioStr` | |

### 2.6 `configuracion.py`

| Clase | Campo | Categoría | Nota |
|---|---|---|---|
| `NivelDesempeno` | `nombre` | `EtiquetaStr` | ya tiene validator max=50 (R6) |
| `NivelDesempeno` | `descripcion` | `TextoCortStr` | sin max previo |
| `CriterioPromocion` | — | — | sin campos de texto libres |
| `NuevoNivelDesempenoDTO` | `nombre` | `EtiquetaStr` | validator solo non-empty; entidad valida max=50; añade tipo |
| `NuevoNivelDesempenoDTO` | `descripcion` | `TextoCortStr` | sin max previo |
| `ActualizarNivelDesempenoDTO` | `nombre` | `EtiquetaStr` | |
| `ActualizarNivelDesempenoDTO` | `descripcion` | `TextoCortStr` | |
| `ActualizarInfoInstitucionalDTO` | `nombre_institucion` | `NombreInstStr` | validator solo non-empty |
| `ActualizarInfoInstitucionalDTO` | `dane_code` | `DaneStr` | validación de formato en Institucion |
| `ActualizarInfoInstitucionalDTO` | `rector` | `NombrePersonaStr` | |
| `ActualizarInfoInstitucionalDTO` | `direccion` | `DireccionStr` | |
| `ActualizarInfoInstitucionalDTO` | `municipio` | `NombrePropioStr` | |
| `ActualizarInfoInstitucionalDTO` | `telefono_institucion` | `TelefonoStr` | |
| `ActualizarInfoInstitucionalDTO` | `logo_path` | `RutaLocalStr` | R21 |
| `ActualizarInfoInstitucionalDTO` | `resolucion_aprobacion` | `NombreInstStr` | |

### 2.7 `infraestructura.py`

| Clase | Campo | Categoría | Nota |
|---|---|---|---|
| `AreaConocimiento` | `nombre` | `NombreAreaStr` | ya tiene validator max=120 (R6) |
| `AreaConocimiento` | `codigo` | `EtiquetaStr` | sin max; código de área como "MAT", "CNAT" |
| `Asignatura` | `nombre` | `NombrePropioStr` | ya tiene validator max=100 (R6) |
| `Asignatura` | `codigo` | `EtiquetaStr` | sin max previo |
| `Asignatura` | `tipo_sala_requerido` | `EtiquetaStr` | sin max; valor como "Laboratorio" |
| `Grupo` | `codigo` | `GrupoCodigoStr` | ya tiene validator max=20 (R6) |
| `Grupo` | `nombre` | `NombrePropioStr` | sin max previo; "Décimo A" típico |
| `EscenarioHorario` | `nombre` | `NombrePropioStr` | sin max previo |
| `EscenarioHorario` | `descripcion` | `TextoCortStr` | sin max previo |
| `Horario` | `sala` | `EtiquetaStr` | default "Aula"; sin max previo |
| `Logro` | `descripcion` | `TextoCortStr` | ya tiene validator max=500 (R6) |
| `Franja` | `etiqueta` | `EtiquetaStr` | sin max previo |
| `PlantillaFranja` | `nombre` | `NombrePropioStr` | sin max previo |
| `Grado` | `nombre` | `EtiquetaStr` | nombre de grado como "Undécimo" |
| `ConfigGeneracion` | `nombre` | `NombrePropioStr` | sin max previo |
| `FranjaReunion` | `nombre` | `NombrePropioStr` | sin max previo |
| `Sala` | `nombre` | `NombrePropioStr` | sin max previo; "Laboratorio de Física" |
| `NuevaAreaDTO` | `codigo` | `EtiquetaStr` | sin max previo |
| `NuevaAsignaturaDTO` | `codigo` | `EtiquetaStr` | sin max previo |
| `NuevaAsignaturaDTO` | `tipo_sala_requerido` | `EtiquetaStr` | sin max previo |
| `NuevoGrupoDTO` | `nombre` | `NombrePropioStr` | sin max previo |
| `NuevoEscenarioDTO` | `nombre` | `NombrePropioStr` | sin max previo |
| `NuevoEscenarioDTO` | `descripcion` | `TextoCortStr` | sin max previo |
| `NuevaSalaDTO` | `nombre` | `NombrePropioStr` | sin max previo |
| `NuevoHorarioDTO` | `sala` | `EtiquetaStr` | sin max previo |
| `NuevoLogroDTO` | `descripcion` | `TextoCortStr` | validator solo non-empty; entidad valida max=500 |
| `NuevaPlantillaFranjaDTO` | `nombre` | `NombrePropioStr` | sin max; validado en to_plantilla() |
| `NuevaFranjaDTO` | `etiqueta` | `EtiquetaStr` | sin max previo |
| `NuevaConfigGeneracionDTO` | `nombre` | `NombrePropioStr` | sin max previo |

---

## 3. Campos SIN cota y razón (R15)

### R12 — valor calculado por composición de campos ya acotados

| Clase | Campo | Razón |
|---|---|---|
| `Estudiante` | `nombre_completo` (computed\_field) | `nombre` + `" "` + `apellido`, ambos acotados a NombrePropioStr |
| `Estudiante` | `documento_display` (property) | `tipo_documento` enum + `" "` + `numero_documento` (DocumentoStr) |
| `Acudiente` | `documento_display` (property) | idem |
| `Acudiente` | `contacto_display` (property) | compuesto desde `celular` y `email`, ambos acotados |
| `Usuario` | `nombre_display` (property) | compuesto desde `nombre_completo` y `usuario`, ambos acotados |
| `Grupo` | `descripcion_completa` (property) | compuesto desde `codigo` y `nombre`, ambos acotados |
| `Grupo` | `descripcion_corta` (property) | `nombre` o `codigo`, ambos acotados |
| `HorarioInfo` | properties de display | compuestos desde campos ya acotados |
| `Horario` | `franja_display` (property) | compuesto desde `dia_semana` enum y horas `time` |

Estas son `@property` o `@computed_field`; no aparecen en `model_fields` y no son
objeto de la comprobación automática.

### R13 — objetos de proyección producidos para lectura; nunca reciben datos de un cliente

Las clases siguientes se construyen exclusivamente desde datos ya validados (JOINs, agregaciones,
métodos `desde_*`); no reciben entrada cruda de un cliente:

`DocenteInfoDTO`, `AsignacionDocenteInfoDTO`, `UsuarioResumenDTO`, `InstitucionResumenDTO`,
`ResultadoAprovisionamientoDTO`, `EstudianteResumenDTO`, `MovimientoEstudianteInfoDTO`,
`AcudienteResumenDTO`, `ConceptoComportamientoDTO`, `ReporteConvivenciaFilaDTO`,
`Seguimiento360DTO`, `PuntoSerieDTO`, `ResumenConvivenciaDTO`, `ResumenUsuariosDTO`,
`InformacionInstitucionalDTO`, `HorarioInfo`, `HorarioEstadisticasDTO`, `MetricasCalidadDTO`,
`ResultadoGeneracionDTO`, `BloqueGeneradoDTO`, `FilaReporteDTO`, `ResultadoLoteDTO`.

Todos sus campos de texto quedan exentos. El test de R22 los excluye explícitamente.

### R14 — conjunto de valores cerrado por enumeración o representación de tiempo

| Clase/campo | Razón |
|---|---|
| Todos los campos `StrEnum` (Rol, TipoDocumento, Genero, Jornada, DiaSemana, TipoFranja, etc.) | R14: enumeración cerrada |
| `PlantillaFranja.jornada` (str validado contra `JORNADAS_VALIDAS`) | R14: conjunto cerrado destinado a enum |
| `PlantillaFranja.created_at`, `EscenarioHorario.created_at`, `ConfigGeneracion.created_at/updated_at` | R14: representan un instante de tiempo en ISO 8601 |
| `DisponibilidadDocente.dia_semana`, `BloqueAnclado.dia_semana`, `FranjaReunion.dia_semana` | R14: validados contra `DIAS_VALIDOS` (conjunto cerrado) |
| `Franja.hora_inicio/hora_fin` (str `HH:MM`) | R14: representación de hora |
| `NuevaPlantillaFranjaDTO.jornada`, `NuevaFranjaDTO.hora_inicio/hora_fin` | R14 |

### Excepción documentada fuera de R12/R13/R14

| Clase | Campo | Razón | Valor inline |
|---|---|---|---|
| `AreaConocimiento` | `color` | Hex CSS: valores válidos son `#RGB` (4 chars) o `#RRGGBB` (7 chars). El validator retorna `None` para cualquier valor inválido. Es una cadena de formato fijo, no una categoría de longitud libre. | `max_length=7` |

---

## 4. Implementación de R17 — validación de email sin dependencia externa (R18)

Los validadores de email en los siete archivos ya implementan la lógica mínima:
normalización a minúsculas, cadena vacía → None, presencia de `@`, dominio con `.`.

**No se añade ninguna biblioteca nueva.** En este paso, el validador solo gana
la cota de longitud mediante el tipo `EmailStr` (max=254), que protege contra
cadenas arbitrariamente largas antes de que el validator de formato corra.

El mensaje de error de formato ("El email no tiene un formato válido") permanece
sin cambios en todos los modelos (R7). Como los validadores usan `mode="before"`,
se ejecutan antes de la comprobación del tipo `Annotated`; el exceso de formato
llega al validator primero y el usuario ve el mensaje original.

---

## 5. Estrategia de preservación de mensajes de error existentes (R6/R7)

En Pydantic v2 los `field_validator` con `mode="before"` se ejecutan **antes** de
la validación del tipo `Annotated`. Por tanto:

- Si un campo tiene un validator `mode="before"` que revisa `len(v) > N`, ese
  validator sigue siendo el primero en ejecutarse y emite el mensaje personalizado.
- La cota del tipo `Annotated` actúa como barrera secundaria para campos sin
  validator explícito o cuando el validator `mode="before"` no captura la longitud.

Para campos cuyo validator actual **no** comprueba longitud máxima (solo mínimo o
formato), el nuevo tipo añade la cota y el mensaje de Pydantic
("String should have at most N characters") es el primer y único aviso.
Esto no viola R7 porque esos campos no tenían mensaje de error de longitud previo.

---

## 6. Estrategia para R22/R23/R24 — test estructural

**Archivo:** `tests/unit/domain/test_restricciones_str.py`

### test_todos_los_campos_str_tienen_cota (R22, R24)

```
Para cada clase en MODELOS_EN_SCOPE:
  Para cada campo en model_fields:
    si el tipo del campo es str o str | None:
      - extraer max_length de StringConstraints en la metadata de Annotated
      - si no hay max_length → buscar el campo en EXCLUSIONES[clase]
      - si no está en exclusiones → FAIL con mensaje explicativo
```

`EXCLUSIONES` es un dict `{Clase: {nombre_campo: "R12"|"R13"|"R14"|"excepcion"}}`.
Añadir un campo nuevo sin cota hace fallar el test (R24) porque no estará en
`EXCLUSIONES` ni tendrá el tipo acotado.

### test_cotas_coherentes_con_validators_existentes (R23)

```
Para cada (Clase, campo, max_esperado) en COTAS_CON_VALIDATOR_EXISTENTE:
  - leer max_length del tipo Annotated del campo
  - assert max_length == max_esperado
```

`COTAS_CON_VALIDATOR_EXISTENTE` es un dict con los pares (clase, campo) que
**ya tenían** un `field_validator` comprobando longitud máxima, y el valor
que ese validator exige. Si el tipo y el validator divergen, el test falla (R6, R8).

### Función auxiliar `_max_length_de_campo(field_info) -> int | None`

Recorre `field_info.metadata` buscando una instancia de `StringConstraints` y
retorna su `max_length`. Retorna `None` si no encuentra ninguna.

---

## 7. Alternativa descartada: `Field(max_length=N)` en lugar de `Annotated`

**Descripción:** Usar `Field(max_length=50)` directamente en cada declaración de campo
en lugar de definir alias de tipo en `base.py`.

**Por qué se descarta:**

1. **Viola R5.** No existe "tipo reutilizable con nombre propio". Si 40 campos usan
   `max_length=50` y el valor debe cambiar, hay que editar 40 lugares.
2. **Viola R4.** El número literal `50` aparece en la declaración del campo, no en
   un único lugar.
3. **No es introspectable de forma homogénea.** `Field(max_length=N)` almacena la cota
   en `field_info.metadata` de manera diferente a `StringConstraints`; el test de
   R22 tendría que manejar dos rutas de introspección.
4. **Menor legibilidad.** `campo: CodigoStr` comunica la semántica del campo;
   `campo: str = Field(max_length=50)` solo comunica la restricción numérica.
