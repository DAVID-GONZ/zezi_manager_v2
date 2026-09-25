# Diseño: Bitácora institucional para el equipo directivo (obs_11)

> **Requisitos:** `requirements.md` de esta misma carpeta.

## 1. Archivos a crear y modificar

| Archivo | Operación | Responsabilidad |
|---|---|---|
| `src/interface/pages/institucion/auditoria.py` | crear | Página institucional, solo lectura. |
| `src/interface/presenters/institucion/auditoria_presenter.py` | crear | View-state con scope inmutable. |
| `src/domain/policies/rbac_auditoria.py` | modificar | `puede_ver_bitacora_institucional`. |
| `src/services/auditoria_service.py` | modificar | `TenantScope` obligatorio en las dos lecturas. |
| `src/interface/pages/admin/auditoria.py` | modificar | Pasa `scope="*"` explícito. |
| `main.py` | modificar | `registrar_pagina("/institucion/auditoria", ..., roles=_DIR_COORD)`. |
| `src/interface/design/layout.py` | modificar | Entrada de NAV en la sección Dirección. |
| `tests/unit/interface/auth/test_matriz_rutas_completa.py` | modificar | `ACCESO_ESPERADO`. |
| `tests/unit/services/test_tenant_isolation.py` | modificar | Test de aislamiento de la vía nueva. |

## 2. El scope es obligatorio, no opcional

`obs_05` tuvo que arreglar un bug de esta familia: `FiltroAuditoriaDTO` tenía
`institucion_id`, el repositorio lo aplicaba, y el presenter simplemente nunca
lo asignaba, así que el DTO viajaba con `None` y la consulta salía
cross-tenant. Ese fallo fue inocuo porque el único consumidor era admin. Con un
director al otro lado, el mismo olvido es una fuga de datos entre colegios.

La lección ya está codificada en el proyecto: `tenant_02` y `tenant_03`
migraron 38 métodos de repositorio de `institucion_id: int | None = None` a
`TenantScope` obligatorio, precisamente porque un default silencioso convierte
un descuido en una filtración. Este paso aplica la misma regla a las dos
lecturas de auditoría:

```python
# ANTES
def listar_cambios(self, filtro: FiltroAuditoriaDTO) -> list[RegistroCambio]: ...

# DESPUÉS — omitir scope es TypeError, no cross-tenant silencioso
def listar_cambios(
    self,
    filtro: FiltroAuditoriaDTO,
    scope: TenantScope,
) -> list[RegistroCambio]: ...
```

El servicio resuelve el filtro efectivo, y el filtro del usuario **no puede
ensancharlo**:

```python
def _filtro_con_scope(
    self,
    filtro: FiltroAuditoriaDTO,
    scope: TenantScope,
) -> FiltroAuditoriaDTO:
    """
    Aplica el scope como límite, no como criterio.

    scope="*"  → el filtro del usuario manda (admin cross-tenant).
    scope=int  → institucion_id se fuerza al scope y sin_institucion se apaga,
                 pase lo que pase en el DTO que llega de la UI.
    """
    if scope == "*":
        return filtro
    return filtro.model_copy(update={"institucion_id": scope, "sin_institucion": False})
```

`model_copy(update=...)`, no `.dict()`: la regla dura del proyecto.

`/admin/auditoria` pasa `scope="*"` de forma explícita en sus dos llamadas. El
cambio de firma es intencionadamente ruidoso: cualquier llamador que no se
actualice revienta en el arranque, no en producción.

## 3. Presenter institucional

Ruta espejo de la página: `src/interface/presenters/institucion/auditoria_presenter.py`.

```python
class AuditoriaInstitucionalPresenter:
    """View-state de la bitácora institucional. El scope no es parte del estado."""

    def __init__(self, institucion_id: int) -> None:
        self._institucion_id = institucion_id       # privado: la UI no lo toca
        self.estado: dict = {
            "desde": None, "hasta": None,
            "usuario_id": None, "tabla": None, "accion": None,
            "tipo_evento": None, "registro_id": None,
            "pagina": 1,
            "cambios": [], "sesiones": [],
            "total_cambios": 0, "total_sesiones": 0,
            "hay_siguiente_cambios": False, "hay_siguiente_sesiones": False,
            "detalle": None, "actores": {},
        }

    @property
    def scope(self) -> TenantScope:
        return self._institucion_id
```

Diferencia deliberada con `AuditoriaPresenter`: aquí **no existe** la clave
`institucion_id` en `estado`, ni `sin_institucion`. Lo que no está en el estado
no se puede cambiar desde un `on_change`. El scope entra por el constructor,
desde `ctx.institucion_id`, y sale por una propiedad de solo lectura.

No se hereda del presenter de admin: la herencia traería las claves que este
paso quiere que no existan, y un `del` en el `__init__` del hijo sería justo la
clase de truco que hace frágil un guard.

## 4. Página

`src/interface/pages/institucion/auditoria.py`, page-delegate igual que el
resto: la ruta y el guard se registran en `main.py`; la página solo comprueba
sesión y renderiza.

```python
def auditoria_institucional_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return
    if ctx.institucion_id is None:              # R12
        _render_sin_tenant(ctx)
        return
    presenter = AuditoriaInstitucionalPresenter(ctx.institucion_id)
    ...
```

Diferencias visibles frente a la de admin:

| Elemento | `/admin/auditoria` | `/institucion/auditoria` |
|---|---|---|
| Filtro de institución | sí | **no** (R5) |
| Verificar integridad | sí | **no** (R5) |
| Filtro «Sin institución» | sí | **no** |
| Encabezado de entidad | nombre de tabla | etiqueta de negocio (R7) |
| Detalle con diff | sí | sí |
| Paginación con total | sí | sí |
| Exportación | — | llega en `obs_12` |

Los componentes se reutilizan tal cual (`data_table`, `date_range_input`,
`filter_select`, `empty_state`, el diálogo de detalle de `obs_09`): ninguna
clase nueva y, por tanto, ningún cambio en `CLASS_CONTRACT.md`.

## 5. Navegación

`layout.py` tiene ya el bloque «Dirección» con `"rol": ["director"]`. La
entrada nueva se añade ahí y el bloque pasa a `["director", "coordinador"]`
solo si el coordinador debe ver también las otras entradas; si no, se añade un
bloque propio. En cualquier caso la visibilidad efectiva la decide
`_rol_permitido_en_ruta`, que consulta el registro central de rutas: la lista
del NAV nunca es la fuente de verdad (R9).

## 6. Aislamiento verificado, no supuesto

`tenant_04` dejó una suite con fixture de dos instituciones. El test nuevo vive
ahí y ataca por el camino real:

```python
def test_director_no_ve_bitacora_de_otro_tenant(dos_instituciones):
    # Cambios sembrados en ambas instituciones.
    filtro = FiltroAuditoriaDTO(institucion_id=2)     # el usuario intenta ensanchar
    filas = svc.listar_cambios(filtro, scope=1)       # el scope manda
    assert all(c.institucion_id in (1, None) for c in filas)
```

El caso importante no es el filtro vacío, es el filtro **hostil**: un DTO que
pide otra institución debe ser ignorado, no obedecido.

## 7. Alternativa descartada

**Ampliar el guard de `/admin/auditoria` a `{admin, director, coordinador}` y
esconder por rol los controles que sobran.**
Es un cambio de una línea en `main.py` más cuatro condicionales en la página.
Se descarta porque convierte una página en dos vistas superpuestas cuyo
comportamiento depende de `if ctx.usuario_rol == "admin"` repartidos por el
archivo — el patrón que `paso_35` eliminó al centralizar la autorización. Y
sobre todo: el filtro de institución seguiría existiendo en el árbol de la
página, a un descuido de distancia de servir datos de otro colegio. Dos rutas
con dos presenters es más código y menos superficie de error.

## 8. Orden de implementación recomendado

1. `TenantScope` obligatorio en el servicio + actualización de `/admin/auditoria`.
2. Test de aislamiento con filtro hostil (falla primero, en rojo).
3. `puede_ver_bitacora_institucional` en `rbac_auditoria.py`.
4. Presenter institucional + su test.
5. Página + registro de ruta + `ACCESO_ESPERADO`.
6. NAV.
