# Diseño: Historial de cambios en la ficha de negocio (obs_10)

> **Requisitos:** `requirements.md` de esta misma carpeta.

## 1. Archivos a crear y modificar

| Archivo | Operación | Responsabilidad |
|---|---|---|
| `src/domain/policies/rbac_auditoria.py` | crear | `puede_ver_historial(actor_rol)`. Pura. |
| `src/services/auditoria_service.py` | modificar | `historial_de(tabla, registro_id, scope)`. |
| `src/interface/design/components/historial_cambios.py` | crear | Componente de presentación pura. |
| `src/interface/design/styles/components/historial.css` | crear (si hace falta) | Estilos del timeline, con tokens. |
| `src/interface/design/styles/CLASS_CONTRACT.md` | modificar (si hace falta) | Clases nuevas del componente. |
| `src/interface/presenters/admin/historial_presenter.py` | crear | View-state del diálogo (abierto, cargando, items). |
| `src/interface/pages/convivencia/observaciones.py` | modificar | Enganche. |
| `src/interface/pages/evaluacion/planilla_notas.py` | modificar | Enganche. |
| `src/interface/pages/academico/estudiantes.py` | modificar | Enganche. |
| `src/interface/pages/admin/usuarios.py` | modificar | Enganche. |

## 2. Política RBAC

```python
"""rbac_auditoria.py — quién puede leer la huella de auditoría."""
from __future__ import annotations

_ROLES_AUDITORES: frozenset[str] = frozenset({"admin", "director", "coordinador"})


def _normalizar(rol: object) -> str:
    if rol is None:
        return ""
    return str(getattr(rol, "value", rol)).strip().lower()


def puede_ver_historial(actor_rol: object) -> bool:
    """True si el rol puede leer el historial de cambios de un registro."""
    return _normalizar(actor_rol) in _ROLES_AUDITORES
```

Mismo contrato que `rbac_usuarios`: acepta string o enum, se usa en las dos
capas. `obs_11` añadirá aquí `puede_ver_bitacora_institucional`, y el módulo
queda como el único sitio donde vive «quién audita qué».

## 3. Servicio

```python
def historial_de(
    self,
    tabla: str,
    registro_id: int,
    scope: TenantScope,
) -> list[DetalleCambioDTO]:
    """
    Historial cronológico de un registro, ya resuelto a detalle.

    Consume listar_cambios_por_registro (orden ascendente) y compone cada
    entrada con el diff, la etiqueta de tabla y el nombre del actor.
    """
    cambios = self._repo.listar_cambios_por_registro(tabla, registro_id)
    if scope != "*":
        cambios = [c for c in cambios if c.institucion_id in (scope, None)]
    actores = self.resolver_actores(cambios)
    return [self._componer_detalle(c, actores) for c in cambios]
```

El filtrado por scope se hace en el servicio porque
`listar_cambios_por_registro` no recibe filtro y su firma pertenece al contrato
que `obs_09` ya usa. Las filas con `institucion_id IS NULL` se incluyen: son
las escritas antes de que `mejora_07-T7` poblara la columna, y excluirlas
crearía agujeros silenciosos en el historial — justo el modo de fallo que
`obs_09` corrigió con la opción «Sin institución».

`_componer_detalle` es el helper que `obs_09` ya necesita para
`detalle_cambio`; aquí se reutiliza, no se duplica.

## 4. Componente

`activity_feed.py` existe pero su `ActivityItem(etiqueta, categoria,
timestamp)` no admite un diff: se descarta ampliarlo porque lo usa el portal
para otra cosa y ensancharlo acoplaría dos vistas sin relación. El componente
nuevo sigue su misma forma —dataclass de entrada, `section_panel` como
contenedor, cero llamadas a servicios— para que ambos se lean igual.

```python
@dataclass
class HistorialItem:
    """Una entrada del historial, ya resuelta. Sin dependencias de servicio."""

    fecha: str
    actor: str
    accion: str                    # CREATE | UPDATE | DELETE
    campos: list[CampoDiffDTO]


def historial_cambios(items: list[HistorialItem]) -> None:
    """Línea temporal de cambios de un registro. Presentación pura (R6)."""
```

Estado vacío con `empty_state(variante="default", icono="history", ...)` (R8),
que ya está en el contrato.

Clases: se intenta primero con las contratadas (`.panel-card`, `.badge-*`,
`.empty-state`, utilidades `u-*`). Si el timeline necesita las suyas, se añaden
al contrato como `.historial-item`, `.historial-meta`, `.historial-campo`,
`.historial-valor--anterior`, `.historial-valor--nuevo`, con CSS en
`styles/components/historial.css` y **solo tokens**: sin hex, sin px literales
y sin ningún selector `.q-*` (regla N: el componente se porta a Vue tal cual).

## 5. Presenter

```python
class HistorialPresenter:
    """View-state del diálogo de historial. Sin NiceGUI, sin reglas de negocio."""

    def __init__(self) -> None:
        self.estado: dict = {
            "abierto": False,
            "cargando": False,
            "tabla": None,
            "registro_id": None,
            "items": [],       # list[HistorialItem]
            "error": None,
        }

    def abrir(self, tabla: str, registro_id: int) -> None: ...
    def cerrar(self) -> None: ...
    def set_items(self, items) -> None: ...
    def set_error(self, mensaje: str | None) -> None: ...
```

La carga es perezosa (R11): `abrir()` marca `cargando=True`, la página llama al
servicio y luego `set_items`. Abrir la ficha sin pulsar el botón no toca
`audit_log`.

## 6. Enganches

En las cuatro fichas, el mismo patrón y en este orden:

```python
from src.domain.policies.rbac_auditoria import puede_ver_historial

if puede_ver_historial(ctx.usuario_rol):
    btn_icon(
        "history",
        on_click=lambda: _abrir_historial("observaciones", obs.id),
        tooltip="Historial de cambios",
    )
```

| Ficha | Archivo | `tabla` |
|---|---|---|
| Observación de convivencia | `pages/convivencia/observaciones.py` | `observaciones` |
| Nota | `pages/evaluacion/planilla_notas.py` | la tabla que audita `evaluacion_service` |
| Estudiante | `pages/academico/estudiantes.py` | `estudiantes` |
| Usuario | `pages/admin/usuarios.py` | `usuarios` |

El nombre exacto de cada tabla se toma del argumento `tabla=` de la llamada a
`auditar_cambio` del servicio correspondiente, no se supone: si el servicio
audita con un nombre y la ficha consulta con otro, el historial sale vacío sin
dar error, que es el peor de los fallos posibles aquí. La task de enganche
verifica cada par contra el código del servicio.

## 7. Alternativa descartada

**Un botón «Historial» que navegue a `/admin/auditoria` con el filtro
`tabla`+`registro_id` ya aplicado.**
Cuesta media hora y aprovecha entero el trabajo de `obs_09`. Se descarta por
dos razones: saca al usuario de su tarea hacia una pantalla de administración
con vocabulario técnico, y `/admin/auditoria` es admin-only, así que el
coordinador —el destinatario natural de esta función— rebotaría contra el
guard. El historial tiene que vivir donde vive la pregunta.

## 8. Orden de implementación recomendado

1. `rbac_auditoria.py` + su test puro.
2. `historial_de` en el servicio + test con scope de dos instituciones.
3. Componente + presenter + tests.
4. Los cuatro enganches, verificando el nombre de tabla contra cada servicio.
5. Contrato de clases y CSS si el componente los necesitó.
