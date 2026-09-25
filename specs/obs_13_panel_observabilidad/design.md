# Diseño: Panel de observabilidad de plataforma (obs_13)

> **Requisitos:** `requirements.md` de esta misma carpeta.

## 1. Archivos a crear y modificar

| Archivo | Operación | Responsabilidad |
|---|---|---|
| `src/domain/ports/log_reader.py` | crear | Puerto `ILogReader`. |
| `src/infrastructure/logging/jsonl_log_reader.py` | crear | Lee la cola del JSONL con tope de bytes. |
| `src/services/observabilidad_service.py` | crear | Compone salud, log, alertas y KPIs. |
| `src/domain/models/observabilidad.py` | crear | DTOs de salud, entrada de log y alerta. |
| `src/domain/policies/alerta_ip.py` | modificar | `alertas_activas()` sin mutar estado. |
| `src/interface/presenters/admin/observabilidad_presenter.py` | crear | View-state por bloque. |
| `src/interface/pages/admin/observabilidad.py` | crear | Página. |
| `main.py` | modificar | Registro de la ruta. |
| `src/interface/design/layout.py` | modificar | Entrada de NAV en Administración. |
| `src/interface/pages/inicio.py` | modificar | Quinta tarjeta en `_ADMIN_CARDS`. |
| `container.py` | modificar | `log_reader` y `observabilidad_service`. |
| `tests/unit/interface/auth/test_matriz_rutas_completa.py` | modificar | `ACCESO_ESPERADO`. |

## 2. Dos preguntas distintas, dos páginas

`/diagnostico` responde «¿se puede construir el sistema?» — un smoke test de
arranque cuyo resultado es idéntico en cada recarga mientras el código no
cambie. `/admin/observabilidad` responde «¿cómo va el sistema ahora?», y su
contenido cambia entre dos recargas.

Fusionarlas sería tentador porque las dos son «cosas técnicas del admin», pero
producirían una página que mezcla un resultado estático con cuatro bloques
vivos. `/diagnostico` se queda como está (R15), incluido su lanzador «Ver
como», que no tiene nada que ver con la observabilidad pero sí con las
herramientas de plataforma.

## 3. Puerto de lectura de log

Leer un archivo es infraestructura. El servicio no abre archivos.

```python
# src/domain/ports/log_reader.py
class ILogReader(ABC):
    @abstractmethod
    def leer_ultimos(
        self,
        n: int = 200,
        *,
        nivel: str | None = None,
        tipo_evento: str | None = None,
    ) -> list[dict]:
        """
        Últimas n entradas del log estructurado, más recientes primero.

        Devuelve dicts de primitivos. Una línea ilegible se descarta sin
        romper la lectura. Un archivo ausente devuelve lista vacía.
        """
        ...

    @abstractmethod
    def disponible(self) -> bool:
        """True si el archivo configurado existe y es legible."""
        ...
```

`disponible()` está separado a propósito: permite distinguir «no hay eventos»
de «no puedo leer el log», que es la diferencia entre un estado vacío tranquilo
y uno que exige acción (R7).

## 4. Lector JSONL: solo la cola

```python
_TOPE_BYTES = 512 * 1024   # medio MB de cola, no los 10 MB del archivo rotado

def leer_ultimos(self, n=200, *, nivel=None, tipo_evento=None) -> list[dict]:
    ruta = settings.SECURITY_LOG_FILE
    if ruta is None or not ruta.exists():
        return []
    tam = ruta.stat().st_size
    with ruta.open("rb") as fh:
        fh.seek(max(0, tam - _TOPE_BYTES))
        crudo = fh.read().decode("utf-8", errors="replace")
    lineas = crudo.splitlines()
    if tam > _TOPE_BYTES and lineas:
        lineas = lineas[1:]          # la primera puede venir cortada por el seek
    entradas = []
    for linea in reversed(lineas):
        try:
            doc = json.loads(linea)
        except json.JSONDecodeError:
            continue                 # línea a medio escribir: se descarta
        entradas.append({k: v for k, v in doc.items() if k in _CAMPOS_PERMITIDOS})
        if len(entradas) >= n:
            break
    return entradas
```

El filtrado contra `_CAMPOS_PERMITIDOS` al **leer** (R8) es redundante con el
formatter, que ya filtra al escribir, y esa redundancia es deliberada: el
archivo puede contener líneas escritas por una versión anterior del formatter,
o por otro proceso que escriba en la misma ruta.

`_TOPE_BYTES` acota el coste (R6): el handler rota a 10 MB con 30 copias, y
cargar eso entero para mostrar 200 líneas sería exactamente el error que
`obs_08` corrigió en la verificación de cadena.

## 5. Servicio de observabilidad

```python
class ObservabilidadService:
    """Compone el estado operativo del sistema. Solo lectura."""

    def salud(self) -> SaludDTO:
        """
        Veredicto de integridad, versión, uptime, tamaño de base y último backup.
        Reutiliza verify_db_integrity(): el mismo criterio que /health, no uno paralelo.
        """

    def eventos_seguridad(self, n=200, *, nivel=None, tipo_evento=None) -> list[EntradaLogDTO]: ...

    def alertas_ip(self) -> list[AlertaIPDTO]: ...

    def uso_diario(self, dias: int = 14) -> list[PuntoUsoDTO]: ...
```

- **Uptime**: instante de arranque capturado en `main.py` al iniciar y leído
  desde `settings` o desde un módulo de arranque. No se infiere de la fecha del
  proceso ni del archivo.
- **Salud**: llama a `verify_db_integrity()`, la misma función que `/health`.
  Duplicar el criterio garantizaría que las dos respuestas divergen algún día.
- **Último backup**: mientras no exista tooling de backup —`seguridad_web_10`
  sigue pendiente— se resuelve inspeccionando el directorio configurado y, si
  no hay ninguno, se devuelve `None` para que la UI diga «sin backup
  registrado» (R3). Mentir con un cero sería peor que la ausencia del dato.
- **Uso diario** (R12): `GROUP BY date(fecha_hora)` sobre los agregados que
  `obs_08` ya expone, no un recuento en Python.

## 6. `alertas_activas()` no muta

```python
def alertas_activas() -> list[tuple[str, int, float]]:
    """
    IPs con fallos dentro de la ventana vigente: (ip, fallos, segundos_restantes).

    No purga entradas caducadas ni reinicia contadores: es una lectura. La
    caducidad la sigue aplicando registrar_fallo_ip al siguiente fallo.
    """
    ahora = time.monotonic()
    vivas = []
    for ip, estado in _estados.items():
        if estado.fallos == 0:
            continue
        restante = VENTANA_SEGUNDOS - (ahora - estado.primer_fallo_en)
        if restante > 0:
            vivas.append((ip, estado.fallos, restante))
    return vivas
```

Que una función de lectura no mute el estado no es un detalle de estilo aquí:
si `alertas_activas()` purgara, abrir el panel cambiaría el comportamiento del
bloqueo, y el observador alteraría lo observado.

`reset_ip(ip)` ya existe y es lo que usa R10 para limpiar. La limpieza se
audita (R11) con `gestion_usuario`-style: evento con actor y la IP como
`objetivo`, campo que `obs_06` añadió a la whitelist.

**Limitación que la UI debe declarar**: `_estados` es un dict de proceso. Con
varios workers, el panel muestra las alertas de *su* proceso, no las del
sistema. Se indica en el texto de la sección; la solución real es estado
compartido y pertenece a `seguridad_web_05`.

## 7. Presenter y página

`estado` con un bloque por sección, cada uno con sus datos y su propio error
(R13):

```python
self.estado = {
    "salud": None,        "error_salud": None,
    "eventos": [],        "error_eventos": None,
    "alertas": [],        "error_alertas": None,
    "uso": [],            "error_uso": None,
    "filtro_nivel": None, "filtro_tipo": None,
}
```

Un bloque que falla pinta su error y los demás se renderizan. El presenter no
calcula nada: recibe DTOs ya compuestos (R14).

Componentes reutilizados: `stats_grid` para la salud, `data_table` para el log,
`alerts_panel` para las alertas de IP, `mini_chart` para la serie diaria,
`empty_state` para los vacíos. Todos existen y están contratados; no hay clases
nuevas ni CSS nuevo.

## 8. Alternativa descartada

**Integrar un APM externo (Sentry, OpenTelemetry) en lugar de construir el
panel.**
Da mucho más —trazas, agrupación de errores, alertas por correo— con menos
código propio. Se descarta por ahora por dos razones concretas: el despliegue
es por institución y sobre SQLite, así que habría que configurar y pagar un
destino por colegio; y el destinatario del dato es el rector, que no va a
entrar en un panel de terceros en inglés. La decisión se revisa cuando
`backend_00` lleve el producto a PostgreSQL en la nube, donde un colector
central sí tiene sentido; y este panel seguirá siendo útil entonces como vista
de primer nivel dentro del producto.

## 9. Orden de implementación recomendado

1. DTOs de `observabilidad.py`.
2. `ILogReader` + `jsonl_log_reader.py` + tests (archivo ausente, línea rota,
   archivo mayor que el tope).
3. `alertas_activas()` + test de no mutación.
4. `ObservabilidadService` + tests.
5. `container.py`.
6. Presenter + página + ruta + NAV + `ACCESO_ESPERADO` + tarjeta en `inicio.py`.
