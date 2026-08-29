# tenant_04_tests_aislamiento — Suite de tests de aislamiento cross-tenant

> **Fase 1C del plan de aislamiento multi-tenant.**
> Verifica que el aislamiento funciona end-to-end. Estos tests son la red de
> seguridad permanente — sobreviven la migracion a SQLAlchemy y a la API.

## Contexto

Tras instalar el interceptor (tenant_01) y hacer las firmas obligatorias
(tenant_02, tenant_03), necesitamos tests que:
1. Verifiquen aislamiento con 2 instituciones reales.
2. Cubran el caso del ContextVar en None (simular event handler pre-fix).
3. Impidan regresion si alguien agrega un metodo de listado sin scope.

## Scope

```
tests/unit/services/test_tenant_isolation.py         (NUEVO)
tests/unit/services/test_solo_lectura_isolation.py   (NUEVO)
tests/integration/test_tenant_e2e.py                 (NUEVO, opcional)
```

## Tareas

### T1 — Fixture de 2 instituciones con datos aislados  [ ]

Crear fixture reutilizable (en conftest o en el archivo de test):
- Institucion A (id=1) con: 2 profesores, 3 estudiantes, 1 grupo, 1 config_anio.
- Institucion B (id=2) con: 2 profesores, 3 estudiantes, 1 grupo, 1 config_anio.
- Los datos NO deben solaparse (nombres distintos, documentos distintos).
- La fixture usa `usar_institucion(id)` context manager para el seeding.

**Verificacion:** La fixture se ejecuta sin error.

### T2 — Tests de aislamiento por servicio (usuario)  [ ]

En `test_tenant_isolation.py`:

```python
def test_director_institucion_A_no_ve_usuarios_B(db_2_instituciones):
    with usar_institucion(1):
        resultado = svc.listar_resumenes(FiltroUsuariosDTO(...))
        assert all(u.institucion_id == 1 for u in resultado)
        # Ningun usuario de institucion B aparece
        ids_b = {u.id for u in usuarios_inst_b}
        assert not any(u.id in ids_b for u in resultado)
```

Tests minimos:
- `test_listar_resumenes_scopeado`
- `test_listar_docentes_scopeado`
- `test_crear_usuario_asigna_institucion_correcta`

**Verificacion:** `python -m pytest tests/unit/services/test_tenant_isolation.py -v`

### T3 — Tests de aislamiento por servicio (estudiante, asignacion, convivencia)  [ ]

Misma mecanica que T2 pero para:
- `estudiante_service.listar_resumenes` — solo estudiantes del tenant.
- `asignacion_service.listar_info` — solo asignaciones del tenant.
- `convivencia_service.listar_categorias` — solo categorias del tenant.
- `configuracion_service.get_activa` — retorna config del tenant, no de otro.

**Verificacion:** Tests verdes.

### T4 — Test de admin cross-tenant (no romper la funcionalidad)  [ ]

```python
def test_admin_ve_todas_las_instituciones(db_2_instituciones):
    # Admin = institucion_actual() es None → scope "*"
    with usar_institucion(None):
        resultado = svc.listar_resumenes(FiltroUsuariosDTO(institucion_id="*"))
        instituciones_vistas = {u.institucion_id for u in resultado}
        assert 1 in instituciones_vistas
        assert 2 in instituciones_vistas
```

### T5 — Test de ContextVar=None sin interceptor (regresion)  [ ]

Simular el escenario pre-fix: `institucion_actual()` retorna None pero el
usuario es un director (no admin). Verificar que los servicios con
`TenantScope` obligatorio lanzan TypeError o que el `_aplicar_scope`
asigna `"*"` y la pagina pasa `ctx.institucion_id` explicito.

```python
def test_scope_none_con_tenant_scope_obligatorio():
    """Si el ContextVar esta en None y el servicio no pasa scope, debe fallar."""
    with usar_institucion(None):
        # Los metodos criticos ahora requieren institucion_id obligatorio
        # Llamar sin el parametro debe ser TypeError
        with pytest.raises(TypeError):
            repo.listar_grados()  # falta institucion_id
```

### T6 — Test de solo_lectura en event handlers  [ ]

En `test_solo_lectura_isolation.py`:

Verificar que `solo_lectura()` retorna el valor correcto cuando se
re-sincroniza via `SessionContext.desde_storage()`:

```python
def test_solo_lectura_se_resincroniza():
    # Simular impersonacion activa en storage
    app.storage.user["solo_lectura"] = True
    SessionContext.desde_storage()
    assert solo_lectura() is True

    # Simular fin de impersonacion
    app.storage.user["solo_lectura"] = False
    SessionContext.desde_storage()
    assert solo_lectura() is False
```

### T7 — Test estructural: grep de regresion  [ ]

Test que ejecuta un grep sobre `src/infrastructure/db/repositories/`:
- Busca el patron `def listar_.*institucion_id.*= None`.
- Debe retornar 0 coincidencias.
- Si alguien agrega un metodo con default None, el test falla.

```python
def test_ningun_listar_con_default_none():
    import re, pathlib
    repos_dir = pathlib.Path("src/infrastructure/db/repositories")
    pattern = re.compile(r"def\s+(listar_|contar_|buscar_).*institucion_id.*=\s*None")
    violaciones = []
    for f in repos_dir.glob("*.py"):
        for i, line in enumerate(f.read_text().splitlines(), 1):
            if pattern.search(line):
                violaciones.append(f"{f.name}:{i}: {line.strip()}")
    assert not violaciones, f"Metodos con default None:\n" + "\n".join(violaciones)
```

## Criterio de done
- [ ] Fixture de 2 instituciones funcionando
- [ ] Tests de aislamiento por servicio (usuario, estudiante, asignacion, convivencia, config)
- [ ] Test de admin cross-tenant verde
- [ ] Test de regresion ContextVar=None verde
- [ ] Test de solo_lectura verde
- [ ] Test estructural grep verde
- [ ] `python init.py` verde
