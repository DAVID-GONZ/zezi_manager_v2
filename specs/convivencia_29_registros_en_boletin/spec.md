# convivencia_29_registros_en_boletin — Spec

## Contexto

Los `RegistroComportamiento` (fortaleza, dificultad, compromiso, citación al
acudiente, descargo) creados desde `observaciones.py` viven aislados del
boletín: `InformeService.convivencia_boletin` sólo lee `NotaComportamiento`
y `ObservacionPeriodo` (líneas 123-145 de `src/services/informe_service.py`).
Un director de grupo que registra "Citación acudiente — 2026-06-10" no ve
rastro en el boletín del estudiante.

Este spec define qué registros llegan al boletín, cómo se ordenan y cómo se
señalizan visualmente en PDF y Excel — sin duplicar información con las
observaciones públicas. **Decisión de David 2026-08-12: la política es
configurable por institución (directivo/coordinación), no hardcodeada.**

Scope:
- `src/services/preferencias_institucion_service.py` (EXTENDER — nuevas
  claves en categoría `CONVIVENCIA`).
- `src/domain/models/preferencia_institucion.py` (EXTENDER — campos en
  `PreferenciasDTO`; defaults conservadores).
- `src/interface/pages/institucion/hub_institucion.py` (EXTENDER — sección
  "Convivencia" del hub gana los nuevos controles).
- `src/services/convivencia_service.py` (MODIFICAR — nuevo helper
  `_registros_informables_periodo` que lee la config del tenant).
- `src/services/informe_service.py` (MODIFICAR — `convivencia_boletin` y
  `convivencia_boletin_anual` devuelven `registros`).
- `src/infrastructure/exporters/boletin_pdf.py` (MODIFICAR).
- `src/domain/models/convivencia.py` (EXTENDER — constante
  `TIPO_REGISTRO_DISPLAY`).
- `tests/unit/services/`, `tests/unit/interface/` (EXTENDER).

## Política de inclusión (configurable)

Nueva sección de preferencias `CONVIVENCIA` con las siguientes claves
(tipo JSON, editables solo por director/coordinador desde el hub):

| Clave                                | Tipo | Default | Descripción |
|--------------------------------------|------|---------|-------------|
| `registros_boletin_tipos`            | JSON | `["fortaleza","compromiso","citacion_acudiente"]` | Lista de `TipoRegistro` incluidos en boletín |
| `registros_boletin_dificultad_requiere_notificacion` | BOOL | `true`  | Si `true` y `dificultad` está en la lista, solo entra si `acudiente_notificado=True` |
| `registros_boletin_incluye_descargo` | BOOL | `false` | Los descargos entran solo si esto es `true` (aparte del filtro de lista) |
| `registros_boletin_dedup_observaciones` | BOOL | `true` | Si `true`, se excluye un registro cuyo id aparece como `registro_comportamiento_id` en una observación pública ya incluida |

Los defaults reproducen el comportamiento conservador que David había
aprobado antes de pedir configurabilidad. Todas las claves viven en la
categoría `CONVIVENCIA`. `hub_institucion` las expone bajo la sección
"Convivencia" con etiquetas legibles.

Aplicación en runtime: `ConvivenciaService._registros_informables_periodo`
resuelve el tenant vía `contexto_tenant.institucion_actual()` y lee las
preferencias con `PreferenciasInstitucionService.get_todas(institucion_id)`
(o el método existente). Si el servicio de preferencias no está disponible
(scripts/tests legacy sin wiring), aplica los defaults.

## Requisitos (EARS)

- **R1** — `PreferenciasInstitucionService` DEBE exponer y persistir las
  cuatro claves nuevas dentro de la categoría `CONVIVENCIA`. `PreferenciasDTO`
  DEBE incluir los cuatro campos con sus defaults.
- **R2** — El hub institucional DEBE permitir a director/coordinador editar
  las cuatro claves. Rol distinto NO DEBE ver los controles (readonly o
  ausentes; el guard de la página ya restringe el acceso al hub).
- **R3** — `ConvivenciaService.paquete_boletin_periodo(...)` (creado en
  `convivencia_32`; en esta spec se anticipa como helper
  `_registros_informables_periodo`) DEBE aplicar la política configurada:
  filtro por `registros_boletin_tipos`, gate por
  `registros_boletin_dificultad_requiere_notificacion`, gate por
  `registros_boletin_incluye_descargo`, deduplicación por
  `registros_boletin_dedup_observaciones`.
- **R4** — `InformeService.convivencia_boletin(estudiante_id, periodo_id)`
  DEBE devolver, además de las claves actuales, la clave `registros` con la
  lista `{fecha, tipo, descripcion}` filtrada por la política, ordenada por
  `fecha` ascendente.
- **R5** — `InformeService.convivencia_boletin_anual(estudiante_id, anio_id)`
  (creado en `convivencia_28`) DEBE devolver `registros` idénticamente
  filtrados y ordenados por `fecha` ascendente para todo el año.
- **R6** — El PDF DEBE renderizar los registros como una sub-sección
  `EVENTOS DE CONVIVENCIA:` con una línea por registro
  `- 2026-06-10 · Citación acudiente: <descripción>`. Solo se renderiza si
  `registros` no está vacía.
- **R7** — El Excel DEBE añadir una columna `Eventos Conv.` con
  `join(" | ", "<fecha> <tipo>: <desc>")` (mientras `convivencia_31` no
  aterrice; después migra a la hoja "Convivencia" separada).
- **R8** — Cambiar la configuración en el hub y regenerar el boletín DEBE
  producir un boletín distinto sin reiniciar el servidor (la lectura de
  preferencias es por request, no cache global).

## Diseño

### 1. Preferencias

En `PreferenciasDTO` (`src/domain/models/preferencia_institucion.py`):
```
registros_boletin_tipos: list[str] = Field(
    default_factory=lambda: ["fortaleza", "compromiso", "citacion_acudiente"]
)
registros_boletin_dificultad_requiere_notificacion: bool = True
registros_boletin_incluye_descargo: bool = False
registros_boletin_dedup_observaciones: bool = True
```

Semillas: `PreferenciasInstitucionService` al aprovisionar un tenant nuevo
(o al leer si faltan) usa los defaults del DTO.

### 2. Hub institucional

En `hub_institucion.py`, sección "Convivencia": añadir un bloque
"Eventos de convivencia en el boletín" con:
- Multi-select de tipos (opciones: `TIPO_REGISTRO_DISPLAY`).
- Checkbox: "Solo incluir dificultades cuando el acudiente ha sido notificado".
- Checkbox: "Incluir descargos".
- Checkbox: "No duplicar eventos que ya aparecen como observación pública".

Persistir con el patrón existente de guardado por sección del hub.

### 3. Runtime — ConvivenciaService

Constante en `src/domain/models/convivencia.py`:
```
TIPO_REGISTRO_DISPLAY: dict[str, str] = {
    "fortaleza":          "Fortaleza",
    "dificultad":         "Dificultad",
    "compromiso":         "Compromiso",
    "citacion_acudiente": "Citación acudiente",
    "descargo":           "Descargo",
}
```

Nuevo método privado:
```
def _registros_informables_periodo(
    self, estudiante_id: int, periodo_id: int,
    excluir_ids: set[int] | None = None,
) -> list[dict]:
    """Aplica la política configurada por preferencias del tenant."""
    prefs = self._get_prefs_convivencia()   # DTO con defaults si no hay svc
    tipos = set(prefs.registros_boletin_tipos)
    if not prefs.registros_boletin_incluye_descargo:
        tipos.discard("descargo")
    regs = self._repo.listar_registros(
        FiltroConvivenciaDTO(estudiante_id=estudiante_id, periodo_id=periodo_id)
    )
    excluir_ids = excluir_ids or set()
    resultado = []
    for r in regs:
        if r.tipo.value not in tipos:
            continue
        if (r.tipo.value == "dificultad"
                and prefs.registros_boletin_dificultad_requiere_notificacion
                and not r.acudiente_notificado):
            continue
        if prefs.registros_boletin_dedup_observaciones and r.id in excluir_ids:
            continue
        resultado.append({
            "fecha":       str(r.fecha),
            "tipo":        TIPO_REGISTRO_DISPLAY.get(r.tipo.value, r.tipo.value),
            "descripcion": r.descripcion,
        })
    resultado.sort(key=lambda d: d["fecha"])
    return resultado
```

`_get_prefs_convivencia()` es un helper que:
- Lee vía `_preferencias_svc_provider()` (nuevo constructor arg, opcional).
- Si el provider es `None`, retorna una instancia `PreferenciasDTO()` con
  defaults del modelo.
- El wiring en `container.py` inyecta el provider al construir
  `ConvivenciaService` (patrón existente para otros providers).

### 4. `InformeService`

- `convivencia_boletin`: calcula `excluir_ids` a partir de las obs públicas
  ya cargadas (`o.registro_comportamiento_id for o in obs if not None`) y
  añade `"registros"` invocando el helper del `ConvivenciaService`
  (en preparación para `convivencia_32`, hoy directo si el servicio ya está
  a mano; si no, mediante el propio `_convivencia_repo` con el filtro por
  defecto — TODO documentado hasta 32).
- Idem para `convivencia_boletin_anual` (iterando periodos).

### 5. PDF — `boletin_pdf._observaciones_y_firmas`

- Añadir parámetro nuevo `convivencia_anual: dict | None = None` (spec 28)
  y aceptar `convivencia`/`convivencia_anual` con clave `registros`.
- Tras el bloque de observaciones (viñetas agrupadas por categoría según
  spec 28), si hay `registros`:
  - Espaciador + `<Paragraph bold>EVENTOS DE CONVIVENCIA:</Paragraph>`
  - Un `<Paragraph normal>` por evento con el formato de R6.
- Toda la sub-sección vive dentro de la misma caja "OBSERVACIONES Y
  RECOMENDACIONES".

### 6. Excel

- Añadir columna `Eventos Conv.` a cada fila del bucle de asignaturas
  (contenido idéntico entre filas — asumido en transición). Se retira
  cuando `convivencia_31` mueva todo a hoja aparte.

## Tareas

- **T1** — Extender `PreferenciasDTO` con los cuatro campos y actualizar
  el service para leer/escribir las claves en categoría `CONVIVENCIA`.
- **T2** — Añadir la constante `TIPO_REGISTRO_DISPLAY` en dominio;
  refactorizar `observaciones.py` para usarla (retirar el dict local).
- **T3** — Añadir `_registros_informables_periodo` en `ConvivenciaService`,
  con inyección opcional del `_preferencias_svc_provider`. Wiring en
  `container.py`.
- **T4** — Extender `convivencia_boletin` (periodo) con `registros`.
- **T5** — Extender `convivencia_boletin_anual` (anual) con `registros`
  (depende de `convivencia_28`).
- **T6** — Extender `boletin_pdf._observaciones_y_firmas` para renderizar
  la sub-sección de eventos, en modo periodo y anual.
- **T7** — Añadir columna `Eventos Conv.` a ambas ramas Excel (transición).
- **T8** — Sección "Eventos de convivencia en el boletín" en el hub
  institucional (multi-select + 3 checkboxes) con RBAC del hub existente.
- **T9** — Tests: preferencias (defaults + persistencia), servicio
  (todos los ramos de la política, deduplicación, orden por fecha), hub
  (smoke de render con rol director), boletines (render con y sin registros).

## Verificación

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/unit/services/ -q
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/unit/interface/ -q
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe init.py
```

Escenarios manuales:
- Director activa "descargo" en el hub → un descargo del estudiante aparece
  en el boletín.
- Director desactiva "citación" → la citación deja de aparecer sin cambiar
  código, solo regenerando el PDF.
- Registro de dificultad no notificado + gate activo → NO aparece; al
  marcarlo como notificado y regenerar → aparece.
- Observación pública con `registro_comportamiento_id` apuntando a un
  registro presente + dedup activo → el registro NO se lista como evento.

`init.py` verde.

## Dependencias

- `convivencia_28_boletin_anual_convivencia` (para R5 y renderizado anual).
- Reutiliza `mejora_08_preferencias_institucion` (infraestructura ya lista).
