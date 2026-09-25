# Diseño: Exportación verificable y retención de la bitácora (obs_12)

> **Requisitos:** `requirements.md` de esta misma carpeta.

## 1. Archivos a crear y modificar

| Archivo | Operación | Responsabilidad |
|---|---|---|
| `src/services/auditoria_export_service.py` | crear | Compone el tramo, la hoja de verificación y delega en `IExporterService`. |
| `src/services/auditoria_retencion_service.py` | crear | Archiva y purga, en ese orden y nunca al revés. |
| `src/domain/models/auditoria.py` | modificar | `HojaVerificacionDTO`, `ResultadoArchivadoDTO`; `TipoEventoSesion` + 2 valores. |
| `src/domain/ports/auditoria_repo.py` | modificar | `listar_cambios_tramo`, `eliminar_hasta`, `rango_de`. |
| `src/infrastructure/db/repositories/sqlite_auditoria_repo.py` | modificar | Implementación de los tres. |
| `src/infrastructure/db/schema.py` | modificar | `CHECK` de `tipo_evento` + `AUDITORIA_EXPORTADA` y `AUDITORIA_PURGADA`. |
| `src/domain/policies/rbac_auditoria.py` | modificar | `puede_exportar_bitacora`, `puede_purgar_bitacora`. |
| `src/services/preferencias_institucion_service.py` | modificar | Ventana de retención por institución. |
| `src/interface/pages/admin/auditoria.py` | modificar | Exportar + archivar/purgar. |
| `src/interface/pages/institucion/auditoria.py` | modificar | Exportar (sin purga). |
| `docs/verificacion_bitacora.md` | crear | Procedimiento de comprobación por un tercero (R3). |
| `container.py` | modificar | Registro de los dos servicios nuevos. |

## 2. La exportación es evidencia, no un volcado

Un CSV de la bitácora sin más no prueba nada: cualquiera puede escribir un CSV.
Lo que hace verificable a esta bitácora es la cadena SHA-256, y la exportación
tiene que llevársela consigo.

```python
class HojaVerificacionDTO(DTODominio):
    generado_en: datetime
    generado_por: str                 # username del actor
    institucion: str | None
    tabla: str                        # 'audit_log' | 'auditoria'
    id_desde: int
    id_hasta: int
    fecha_desde: datetime | None
    fecha_hasta: datetime | None
    filas: int
    hash_primera_fila: str            # hash_cadena del primer registro del tramo
    hash_ultima_fila: str             # hash_cadena del último
    hash_contenido: str               # SHA-256 del CSV/PDF exportado
    integridad_ok: bool               # veredicto del tramo al exportar (R4)
    id_roto: int | None
```

En el CSV la hoja va como un bloque de cabecera comentado antes de los datos;
en el PDF, como primera página. `hash_contenido` se calcula sobre los bytes de
los datos **sin** la hoja —si no, sería un hash de sí mismo— y el
procedimiento de R3 lo explicita.

`docs/verificacion_bitacora.md` describe, en lenguaje reproducible por alguien
sin la aplicación: cómo recomputar `hash_contenido`, y cómo reconstruir la
cadena del tramo con la fórmula de `audit_chain.py`
(`SHA256(hash_previo || payload_canónico)`, JSON con claves ordenadas,
separadores `(",", ":")`, sin el `id`), partiendo de `hash_primera_fila` como
semilla. Sin ese documento, la hoja de verificación es decoración.

## 3. Redacción de sensibles y tope de filas

La exportación reutiliza `diff_cambio` de `obs_09` para serializar los valores,
de modo que la lista negra `_CAMPOS_SENSIBLES` se aplica una sola vez y en un
solo sitio (R6). No hay una segunda lista.

El tope (R7) es `settings.AUDITORIA_EXPORT_MAX_FILAS`, con un valor por defecto
de 50 000. Antes de exportar, el servicio llama a `contar_cambios` —el método
que `obs_08` añadió— y si el filtro lo supera devuelve un error de dominio
`ReglaDeNegocioError` con código estable; la UI lo traduce a un aviso que
propone acotar el rango. Truncar en silencio sería repetir el `_POR_PAGINA=100`
que `obs_05` tuvo que arreglar.

## 4. Archivar antes de purgar, siempre

```python
def archivar_y_purgar(
    self,
    tabla: str,
    hasta: datetime,
    *,
    scope: TenantScope,
    actor: str,
) -> ResultadoArchivadoDTO:
    """
    1. Delimita el tramo (rango de ids) hasta `hasta`.
    2. Verifica la cadena del tramo.
    3. Escribe el archivo JSONL + su hoja de verificación.
    4. Relee el archivo y confirma su hash.
    5. Solo entonces: elimina las filas y reancla el checkpoint.
    6. Registra AUDITORIA_PURGADA con ruta, hash, rango y nº de filas.
    """
```

El orden no es una preferencia: cualquier fallo en los pasos 1-4 aborta sin
haber borrado nada. El paso 5 es el único destructivo y es el último.

**Por qué esto no viola el invariante append-only.** El puerto declara que la
auditoría nunca se modifica ni se elimina, y ese invariante protege un valor
concreto: que nadie pueda hacer desaparecer un hecho. El archivado no lo hace
desaparecer: lo mueve a un archivo firmado y **deja dentro de la bitácora un
evento que dice exactamente qué se movió, cuándo, quién y con qué hash**. Lo
que se prohíbe sigue prohibido: no hay `UPDATE`, y no hay `DELETE` que no deje
constancia. El docstring del puerto se actualiza para decir esto, en vez de
quedar contradicho en silencio.

**El hueco en la cadena y el checkpoint (R11).** Al eliminar las filas
`[1, k]`, la fila `k+1` sigue encadenando contra el `hash_cadena` de `k`, que
ya no existe en la tabla. La verificación incremental de `obs_08` reanuda desde
un punto de control con semilla almacenada, así que basta con reanclar ese
punto de control a `(k, hash_de_k)` durante la purga —el hash se conserva en el
archivo y en el evento—. Una verificación **completa** posterior no puede
recomputar el tramo ausente y debe arrancar desde `k` como nuevo origen: es la
misma limitación de ancla externa que `audit_chain.py` ya documenta (R14).

## 5. Ventana de retención por institución

`PreferenciasInstitucionService` ya es el sitio donde vive la configuración por
tenant. Se añade `retencion_auditoria_meses: int | None`, con `None` = sin
purga y un valor por defecto conservador (60 meses, cinco cursos). La
preferencia **no dispara nada por sí sola**: solo precarga la fecha propuesta
en el diálogo de archivado. La purga sigue siendo un acto explícito con
confirmación (R12), nunca una tarea programada.

Esta es una decisión consciente: una purga automática sobre datos con valor
probatorio, en un producto que todavía no tiene copias de seguridad
verificadas, es un modo de perder evidencia sin que nadie se entere.

## 6. Eventos nuevos y RBAC

```python
class TipoEventoSesion(StrEnum):
    ...
    AUDITORIA_EXPORTADA = "AUDITORIA_EXPORTADA"
    AUDITORIA_PURGADA = "AUDITORIA_PURGADA"
```

El `CHECK` de `tipo_evento` en `schema.py` se amplía con los dos valores. Esto
recrea la base; se agrupa con cualquier otro cambio de esquema del paso para
abrirla una sola vez.

```python
def puede_exportar_bitacora(actor_rol) -> bool:   # admin, director, coordinador
def puede_purgar_bitacora(actor_rol) -> bool:     # solo admin (R13)
```

## 7. UI

`/admin/auditoria` gana dos controles: «Exportar» (menú CSV / PDF) y
«Archivar y purgar», este último con `confirm_dialog` mostrando la fecha de
corte, el número de filas afectadas y la ruta de destino antes de nada.
`/institucion/auditoria` gana solo «Exportar». Ambos usan componentes ya
contratados; no hay clases nuevas.

## 8. Alternativa descartada

**No purgar nunca: solo archivar y dejar las filas en la base.**
Es la opción más segura para la evidencia y la más barata de implementar —sin
`DELETE`, sin reanclaje, sin hueco en la cadena—. Se descarta porque no cumple
el requisito que motiva el paso: una base que conserva indefinidamente datos
personales de menores identificables no es defendible ante la Ley 1581, y
«tenemos una copia y además el original» no es una política de retención, es su
ausencia. El diseño mitiga el riesgo poniendo el borrado detrás de un archivado
verificado, de una confirmación explícita y del rol más restringido.

## 9. Orden de implementación recomendado

1. `HojaVerificacionDTO` y los dos eventos nuevos (dominio + `CHECK`).
2. `listar_cambios_tramo` / `rango_de` en el puerto y el repo.
3. `auditoria_export_service.py` + tests (hoja, redacción, tope).
4. `docs/verificacion_bitacora.md` + un test que recompute la cadena de un
   tramo exportado siguiendo el procedimiento escrito.
5. `eliminar_hasta` en el repo + `auditoria_retencion_service.py` + tests del
   orden de operaciones y del reanclaje.
6. RBAC, preferencia de retención, `container.py` y UI.
