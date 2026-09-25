# Diseño: Detalle del cambio, diff y filtros legibles (obs_09)

> **Requisitos:** `requirements.md` de esta misma carpeta.

## 1. Archivos a crear y modificar

| Archivo | Operación | Responsabilidad |
|---|---|---|
| `src/domain/models/auditoria.py` | modificar | `TipoCambioCampo`, `CampoDiffDTO`, `DetalleCambioDTO`; `FiltroAuditoriaDTO.registro_id` y `sin_institucion`. |
| `src/domain/tablas_auditables.py` | crear | Catálogo `tabla física → etiqueta de negocio`. Fuente única. |
| `src/services/auditoria_service.py` | modificar | `diff_cambio()`, `detalle_cambio()`, `resolver_actores()`. |
| `src/infrastructure/db/repositories/sqlite_auditoria_repo.py` | modificar | Filtros `registro_id` y `sin_institucion`. |
| `src/interface/presenters/admin/auditoria_presenter.py` | modificar | Estado de los filtros nuevos y view-model del detalle. |
| `src/interface/pages/admin/auditoria.py` | modificar | Diálogo de detalle, desplegable de tabla, filtros nuevos, columna de actor. |
| `tests/unit/services/test_auditoria_diff.py` | crear | Diff, redacción de sensibles, orden. |
| `tests/unit/domain/test_tablas_auditables.py` | crear | Cobertura del catálogo. |

## 2. El diff vive en servicios, no en el presenter

La memoria del proyecto es explícita: *los presenters solo producen view-model;
las reglas y los cálculos van a services/domain para que la API y Vue los
reutilicen*. Comparar dos estados de una entidad y decidir qué se oculta es una
regla, no una decoración de pantalla. Va a `AuditoriaService`.

```python
# src/domain/models/auditoria.py

class TipoCambioCampo(StrEnum):
    ANADIDO = "anadido"
    MODIFICADO = "modificado"
    ELIMINADO = "eliminado"
    SIN_CAMBIO = "sin_cambio"


class CampoDiffDTO(DTODominio):
    nombre: str
    valor_anterior: str | None = None
    valor_nuevo: str | None = None
    tipo: TipoCambioCampo
    oculto: bool = False          # campo sensible: los valores no se exponen


class DetalleCambioDTO(DTODominio):
    cambio: RegistroCambio
    actor_nombre: str
    etiqueta_tabla: str
    campos: list[CampoDiffDTO]
```

```python
# src/services/auditoria_service.py

_CAMPOS_SENSIBLES: frozenset[str] = frozenset({
    "password", "password_hash", "password_temporal", "token", "secreto",
})

def diff_cambio(
    self,
    cambio: RegistroCambio,
    *,
    incluir_sin_cambio: bool = False,
) -> list[CampoDiffDTO]:
    """
    Compara valor_anterior y valor_nuevo campo a campo.

    CREATE → todo ANADIDO. DELETE → todo ELIMINADO. UPDATE → por campo.
    Los campos sensibles se marcan `oculto=True` y viajan sin valores (R3).
    """
    anterior = cambio.anterior_como_dict or {}
    nuevo = cambio.nuevo_como_dict or {}
    campos: list[CampoDiffDTO] = []
    for nombre in sorted(set(anterior) | set(nuevo)):
        va, vn = anterior.get(nombre), nuevo.get(nombre)
        if va == vn:
            tipo = TipoCambioCampo.SIN_CAMBIO
            if not incluir_sin_cambio:
                continue
        elif nombre not in anterior:
            tipo = TipoCambioCampo.ANADIDO
        elif nombre not in nuevo:
            tipo = TipoCambioCampo.ELIMINADO
        else:
            tipo = TipoCambioCampo.MODIFICADO
        sensible = nombre.lower() in _CAMPOS_SENSIBLES
        campos.append(CampoDiffDTO(
            nombre=nombre,
            valor_anterior=None if sensible else _texto(va),
            valor_nuevo=None if sensible else _texto(vn),
            tipo=tipo,
            oculto=sensible,
        ))
    return campos
```

La lista negra es defensa en profundidad: `Usuario.password_temporal` ya lleva
`exclude=True` para no llegar nunca a `model_dump()`, pero el diff lee JSON
histórico que pudo escribirse antes de esa garantía, y un servicio nuevo puede
auditar un dict que no pase por el modelo.

## 3. Catálogo de tablas auditables

Sigue el patrón de `src/domain/modulos.py`: un módulo de dominio con un mapa
constante y una función de acceso con fallback.

```python
"""tablas_auditables.py — nombre físico de tabla → etiqueta de negocio."""
from __future__ import annotations

ETIQUETAS_TABLA: dict[str, str] = {
    "observaciones": "Observaciones de convivencia",
    "asistencia_registros": "Registros de asistencia",
    "notas": "Notas y evaluación",
    "usuarios": "Cuentas de usuario",
    "estudiantes": "Estudiantes",
    # ... una entrada por tabla que aparezca en audit_log.tabla
}


def etiqueta_de_tabla(tabla: str) -> str:
    """Etiqueta legible, o el nombre físico si la tabla no está catalogada (R5)."""
    return ETIQUETAS_TABLA.get(tabla, tabla)
```

El test de cobertura no exige que el catálogo sea exhaustivo —lo sería solo
hasta la próxima tabla— sino que **toda clave del catálogo exista en el
esquema**. Así el catálogo no acumula entradas muertas, que es el modo de fallo
registrado de `RESTRICCIONES_DEUDA`: cinco entradas fantasma que hoy pueden
enmascarar regresiones.

## 4. Resolución de actores en una consulta (R8)

```python
def resolver_actores(self, cambios: list[RegistroCambio]) -> dict[int, str]:
    """
    Mapa usuario_id → nombre para la página visible. Una sola consulta.
    """
    ids = {c.usuario_id for c in cambios if c.usuario_id is not None}
    if not ids:
        return {}
    return {u.id: u.nombre_completo for u in self._usuario_repo.get_varios(ids)}
```

Orden de resolución en la UI, de más a menos fiable (R9):
nombre completo resuelto → `cambio.usuario` (snapshot de `obs_06`) →
`Usuario #<id>` → `—`.

Si `get_varios` no existe en el repositorio de usuarios, la task
correspondiente lo añade al puerto; lo que no se acepta es una consulta por
fila dentro del bucle de render.

## 5. Presenter y diálogo

`AuditoriaPresenter.estado` gana:

```python
"registro_id": None,        # filtro por entidad concreta
"sin_institucion": False,   # opción explícita del filtro de institución
"detalle": None,            # DetalleCambioDTO | None — cambio abierto
"actores": {},              # usuario_id → nombre, de la página actual
```

con `set_registro(valor)`, `set_institucion(valor)` ampliado para reconocer el
centinela «sin institución», `abrir_detalle(dto)` y `cerrar_detalle()`.
`construir_filtro()` propaga `registro_id` y `sin_institucion`.

El presenter **no** calcula el diff ni las etiquetas: recibe el
`DetalleCambioDTO` ya construido por el servicio (R13).

El diálogo usa `custom_dialog` del design system y clases ya contratadas
(`.panel-card`, `.badge-*`, `.empty-state`). Los tres tipos de cambio se
distinguen con las variantes de badge existentes:

| Tipo de cambio | Variante |
|---|---|
| `ANADIDO` | `success` |
| `MODIFICADO` | `info` |
| `ELIMINADO` | `error` |

Si hiciera falta una clase nueva para la rejilla del diff, se añade a
`CLASS_CONTRACT.md` y el CSS va en `styles/components/`, nunca en `adapter/`.

## 6. Filtros en el repositorio

```python
if filtro.registro_id is not None:
    sql += " AND registro_id = ?"
    params.append(filtro.registro_id)
if filtro.sin_institucion:
    sql += " AND institucion_id IS NULL"
elif filtro.institucion_id is not None:
    sql += " AND institucion_id = ?"
    params.append(filtro.institucion_id)
```

`sin_institucion` y `institucion_id` son excluyentes y el orden del `if` lo
garantiza: no hay estado en el que se apliquen los dos.

## 7. Alternativa descartada

**Mostrar el JSON crudo de `valor_anterior` y `valor_nuevo` en dos columnas.**
Es la opción de una tarde: cero lógica nueva, cero DTOs, cero tests de diff.
Se descarta porque no resuelve el problema real. El usuario de esta pantalla es
un rector o un coordinador respondiendo a una queja, no un desarrollador
leyendo JSON; y un volcado crudo expondría además los campos sensibles que R3
manda ocultar. Un diff calculado en servicios, por añadidura, es lo que la API
REST podrá servir tal cual.

## 8. Orden de implementación recomendado

1. `tablas_auditables.py` + su test de cobertura.
2. DTOs de diff en `auditoria.py`.
3. `diff_cambio` / `detalle_cambio` / `resolver_actores` en el servicio + tests.
4. Filtros `registro_id` y `sin_institucion` en el DTO y en el repo.
5. Presenter.
6. Página: desplegable de tabla, filtros nuevos, columna de actor, diálogo.
