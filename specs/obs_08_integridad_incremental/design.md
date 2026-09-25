# Diseño: Verificación incremental y agregados en SQL (obs_08)

> **Requisitos:** `requirements.md` de esta misma carpeta.

## 1. Archivos a crear y modificar

| Archivo | Operación | Responsabilidad |
|---|---|---|
| `src/domain/models/auditoria.py` | modificar | `EstadoIntegridadDTO`, `ResumenUsoDTO` ampliado. |
| `src/domain/ports/auditoria_repo.py` | modificar | `contar_eventos`, `contar_cambios`, `resumen_eventos`, verificación con `desde_id`. |
| `src/infrastructure/db/schema.py` | modificar | Tabla `verificacion_auditoria` (punto de control). |
| `src/infrastructure/db/repositories/sqlite_auditoria_repo.py` | modificar | Conteos, agregados y verificación por lotes con checkpoint. |
| `src/services/auditoria_service.py` | modificar | `resumen_uso` sobre SQL; `verificar_integridad(completa=False)`. |
| `src/interface/presenters/admin/auditoria_presenter.py` | modificar | `total_cambios` / `total_sesiones` en el estado. |
| `src/interface/pages/admin/auditoria.py` | modificar | Total junto a la paginación; alcance de la verificación. |
| `src/interface/pages/inicio.py` | modificar | KPIs con el DTO ampliado. |
| `tests/unit/infrastructure/test_auditoria_volumen.py` | crear | Test de rendimiento con 50 000 filas. |

## 2. Por qué una cadena de hash se puede verificar por tramos

`hash_cadena[i] = SHA256(hash_cadena[i-1] || payload[i])`. Verificar el tramo
`[k+1, n]` no necesita recalcular `[0, k]`: basta con **sembrar** el cálculo con
`hash_cadena[k]` tal como está almacenado. Si alguien alteró una fila del tramo
`[0, k]`, su hash almacenado ya no cuadraría, pero el tramo posterior seguiría
encadenando contra el valor almacenado y verificaría en verde.

Ese es exactamente el compromiso que este paso acepta, y por eso R8 y R9
existen: la verificación rápida responde «íntegra **desde** el punto de control»
y la UI lo dice con esas palabras, mientras la verificación completa —más cara y
explícita— sigue disponible. Prometer integridad total en cada pulsación con un
coste de O(1) sería mentir.

## 3. Punto de control

```sql
CREATE TABLE IF NOT EXISTS verificacion_auditoria (
    tabla          TEXT PRIMARY KEY,      -- 'auditoria' | 'audit_log'
    ultimo_id      INTEGER NOT NULL,      -- última fila verificada como íntegra
    ultimo_hash    TEXT    NOT NULL,      -- su hash_cadena: semilla del tramo siguiente
    verificado_en  DATETIME NOT NULL
)
```

No participa en ninguna cadena: es metadato operativo, no evidencia. Si se
pierde, la verificación siguiente arranca desde el origen y lo reconstruye.

## 4. Verificación por lotes

```python
_LOTE = 5_000

def _verificar_cadena(self, tabla: str, *, desde_id: int | None = None) -> int | None:
    """
    Verifica el tramo (desde_id, ∞) sembrando con el hash de `desde_id`.
    Con desde_id=None verifica desde el origen. Nunca carga la tabla entera.
    """
    payload_de, row_a_entidad = self._mapeadores(tabla)
    hash_previo = None if desde_id is None else self._hash_de(tabla, desde_id)
    ultimo_id, ultimo_hash = desde_id, hash_previo
    cursor_id = desde_id or 0

    with self._get_conn() as conn:
        while True:
            rows = conn.execute(
                f"SELECT * FROM {tabla} "
                f"WHERE hash_cadena IS NOT NULL AND id > ? "
                f"ORDER BY id ASC LIMIT ?",
                (cursor_id, _LOTE),
            ).fetchall()
            if not rows:
                break
            for r in rows:
                esperado = calcular_hash(hash_previo, payload_de(row_a_entidad(r)))
                if esperado != r["hash_cadena"]:
                    return int(r["id"])          # R10: se sale sin tocar el checkpoint
                hash_previo = r["hash_cadena"]
                ultimo_id, ultimo_hash = int(r["id"]), r["hash_cadena"]
            cursor_id = ultimo_id

    if ultimo_id is not None:
        self._guardar_checkpoint(tabla, ultimo_id, ultimo_hash)
    return None
```

El `SELECT *` se mantiene porque el payload necesita todas las columnas
persistidas; lo que cambia es que nunca hay más de `_LOTE` filas vivas. La
función pura `primer_eslabon_roto` de `audit_chain.py` sigue siendo la fuente de
verdad del algoritmo para el caso completo; el bucle por lotes usa
`calcular_hash`, la otra mitad del mismo módulo, sin duplicar la regla.

## 5. Firma pública

```python
# Puerto — métodos CONCRETOS con default neutro (R3), como verificar_cadena_*
def verificar_cadena_eventos(self, *, completa: bool = False) -> int | None:
    return None

def contar_eventos(self, filtro: FiltroAuditoriaDTO) -> int:
    return 0

def resumen_eventos(
    self,
    desde: datetime,
    hasta: datetime | None = None,
    institucion_id: TenantScope = "*",
) -> dict:
    return {}
```

`completa=False` (el caso normal) reanuda desde el checkpoint; `completa=True`
ignora el checkpoint y verifica desde el origen (R8).

## 6. Agregados en SQL

```sql
-- Conteo por tipo en la ventana
SELECT tipo_evento, COUNT(*) AS n
  FROM auditoria
 WHERE fecha_hora >= ? AND (? IS NULL OR institucion_id = ?)
 GROUP BY tipo_evento;

-- Logins de hoy
SELECT COUNT(*) FROM auditoria
 WHERE tipo_evento = 'LOGIN_EXITOSO' AND fecha_hora >= ?;

-- Usuarios distintos con login en la ventana
SELECT COUNT(DISTINCT COALESCE(usuario_id, usuario)) FROM auditoria
 WHERE tipo_evento = 'LOGIN_EXITOSO' AND fecha_hora >= ?;
```

`COALESCE(usuario_id, usuario)` reproduce en SQL la regla que hoy vive en el
bucle de Python (contar por id, y por username cuando no hay id). Los índices
`idx_audit_fecha` e `idx_audit_tipo` ya existen y sirven a las tres consultas.

`resumen_uso` queda así:

```python
def resumen_uso(self, dias: int = 7, scope: TenantScope = "*") -> ResumenUsoDTO:
    dias = max(1, dias)
    ahora = datetime.now()
    agg = self._repo.resumen_eventos(ahora - timedelta(days=dias), institucion_id=scope)
    por_tipo = agg.get("por_tipo", {})
    return ResumenUsoDTO(
        logins_hoy=agg.get("logins_hoy", 0),
        logins_periodo=por_tipo.get("LOGIN_EXITOSO", 0),
        accesos_denegados=agg.get("denegados_criticos", 0),   # criterio de obs_07
        usuarios_activos=agg.get("usuarios_distintos", 0),
        sesiones_periodo=por_tipo.get("LOGIN_EXITOSO", 0),
        dias=dias,
    )
```

## 7. `EstadoIntegridadDTO`

`verificar_integridad()` devuelve hoy un `dict` de primitivos, decisión
deliberada de `seguridad_03` para no acoplar la interfaz al dominio. Se mantiene
el `dict` y se le añaden las claves de alcance que R9 necesita:

```python
{
  "eventos_ok": bool, "cambios_ok": bool,
  "evento_roto_id": int | None, "cambio_roto_id": int | None,
  "alcance": "incremental" | "completa",           # NUEVO
  "desde_id_eventos": int | None,                  # NUEVO
  "desde_id_cambios": int | None,                  # NUEVO
  "verificado_en": str | None,                     # NUEVO — ISO-8601
}
```

La página distingue dos textos en el badge: «Íntegra (completa)» frente a
«Íntegra desde #12480 · 19-09 14:02», y ofrece un segundo botón
«Verificación completa» con aviso de que puede tardar.

## 8. Alternativa descartada

**Ejecutar la verificación completa en background con `run.io_bound` y cachear
el resultado.**
Evita congelar la UI sin cambiar el algoritmo, y era la opción de menor coste.
Se descarta porque no resuelve el problema, lo esconde: el trabajo sigue siendo
O(n) sobre toda la tabla en cada pulsación, solo que ahora ocupa un worker y
compite con las peticiones reales. Con una tabla que crece de forma monótona,
la única solución que se sostiene es no releer lo ya verificado. El background
sigue siendo la respuesta correcta para la verificación **completa** de R8, y
ahí se usará.

## 9. Orden de implementación recomendado

1. `verificacion_auditoria` en `schema.py`.
2. Conteos y agregados en el puerto y en el repo SQLite (+ tests de contrato).
3. Verificación por lotes con checkpoint (+ test de eslabón roto antes y
   después del punto de control).
4. `resumen_uso` y `verificar_integridad` en el servicio.
5. Presenter, página y KPIs de `inicio.py`.
6. Test de volumen (50 000 filas).
