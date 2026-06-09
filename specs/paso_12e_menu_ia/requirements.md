# Requisitos — paso_12e_menu_ia

## Contexto

La estructura actual de `NAV_ITEMS` (`layout.py:60-143`) mezcla criterios:
entidades (Estudiantes) con flujos diarios (Asistencia), administración con
configuración, dos "dashboards" (Dashboard + Tablero), choque semántico
(Convivencia → "Notas" vs Planilla de Notas), y Estudiantes huérfano en raíz
mientras Grupos/Asignaturas viven bajo Admin.

Este paso reestructura la información de navegación según el principio **"Aula
primero"**: agrupar por intención del usuario (qué quiere hacer), no por entidad
ni por capa técnica.

## Alcance

- `src/interface/design/layout.py` — `NAV_ITEMS` exclusivamente. La función
  `_rail()` o `_sidebar()` (según orden de pasos) NO cambia; solo cambia la
  data que consume.
- Renames de label, no de ruta. Las URLs siguen iguales.

**Fuera de scope:**
- Cambiar el patrón de navegación (rail): paso 12d.
- Cambiar páginas (renombrar archivos, mover módulos): NO.
- Crear nuevas rutas o nuevas páginas: NO.
- Cambiar permisos por rol: se mantienen exactamente como hoy (los roles que
  ven cada subitem hoy lo siguen viendo).

## Dependencias

Bloqueado solo por que `NAV_ITEMS` siga siendo la fuente. Si 12d se ejecuta antes
y cambia el render del menú, este paso opera sobre el mismo `NAV_ITEMS` sin
fricción.

## Requisitos funcionales

### R1 — Nueva estructura de NAV_ITEMS

Exactamente 6 grupos raíz (4 con hijos, 1 sin hijos antes del divider, 1 después):

```
1. Inicio                    (sin hijos, ruta /inicio, todos los roles)
2. Aula                      (5 hijos)
3. Académico                 (5 hijos)
4. Evaluación                (5 hijos)
5. Informes                  (5 hijos)
─── divider (admin/director) ───
6. Administración            (2 hijos)
```

### R2 — Mapeo exacto

**1. Inicio**
- icon: `home`
- ruta: `/inicio`
- rol: `["*"]`

**2. Aula** (icon: `co_present`, sin ruta directa)
| Label | Icon | Ruta | Roles |
|---|---|---|---|
| Planilla de Notas | `table_chart` | `/evaluacion/planilla` | admin, director, coordinador, profesor |
| Asistencia | `fact_check` | `/asistencia` | admin, director, coordinador, profesor |
| Observaciones | `comment` | `/convivencia/observaciones` | admin, director, coordinador, profesor |
| Comportamiento | `rule` | `/convivencia/comportamiento` | admin, director, coordinador, profesor |
| Seguimiento | `assignment` | `/convivencia/notas` | admin, director, coordinador, profesor |

(Renombro `fact_check` de Convivencia→Notas a `assignment` para evitar duplicar
con Asistencia. El item se llama "Seguimiento" en vez de "Notas".)

**3. Académico** (icon: `school`, sin ruta directa)
| Label | Icon | Ruta | Roles |
|---|---|---|---|
| Estudiantes | `school` | `/estudiantes` | admin, director, coordinador, profesor |
| Grupos | `group` | `/admin/grupos` | admin, director |
| Asignaturas | `book` | `/admin/asignaturas` | admin, director |
| Asignaciones | `assignment_ind` | `/admin/asignaciones` | admin, director |
| Horarios | `calendar_today` | `/horarios` | admin, director, coordinador, profesor |

Nota: Estudiantes con icon `school` choca con el padre `school`. Cambiar
padre a `co_present` (Aula) y dejar Académico con `school`. Estudiantes baja
a `person` para diferenciar.

Reajuste:
- Aula icon: `co_present`
- Académico icon: `school`
- Estudiantes icon: `person`

**4. Evaluación** (icon: `grading`, sin ruta directa)
| Label | Icon | Ruta | Roles |
|---|---|---|---|
| Configuración SIE | `tune` | `/evaluacion/configuracion` | admin, director, coordinador |
| Habilitaciones | `assignment_return` | `/evaluacion/habilitaciones` | admin, director, coordinador, profesor |
| Planes de Mejoramiento | `trending_up` | `/evaluacion/planes` | admin, director, coordinador, profesor |
| Cierre de Periodo | `lock` | `/evaluacion/cierre-periodo` | admin, director, coordinador |
| Cierre de Año | `lock_clock` | `/evaluacion/cierre-anio` | admin, director, coordinador |

Nota: "Configuración SIE" pierde permisos del rol profesor (hoy también lo ve);
NO — mantenerlo como hoy: ["admin", "director", "coordinador", "profesor"] si
ese era el caso original. **Decisión:** preservar los roles **idénticos** a los
de hoy en cada ruta. La tabla anterior los lista; el implementer verifica
contra el original y ajusta si difiero. **Regla:** si hay duda, mantener el
rol original.

**5. Informes** (icon: `summarize`, sin ruta directa)
| Label | Icon | Ruta | Roles |
|---|---|---|---|
| Tablero | `analytics` | `/academico/tablero` | admin, director, coordinador, profesor |
| Boletín de Periodo | `description` | `/informes/boletin-periodo` | admin, director, coordinador, profesor |
| Boletín Anual | `description` | `/informes/boletin-anual` | admin, director, coordinador, profesor |
| Consolidado de Notas | `bar_chart` | `/informes/consolidado-notas` | admin, director, coordinador |
| Consolidado de Asistencia | `event_note` | `/informes/consolidado-asistencia` | admin, director, coordinador |
| Estadísticos | `analytics` | `/informes/estadisticos` | admin, director, coordinador, profesor |

Nota: dos items con icon `analytics` (Tablero y Estadísticos). Cambiar Tablero
a `dashboard` y dejar Estadísticos con `analytics`.

**— Divider —** (rol: admin, director)

**6. Administración** (icon: `settings`, sin ruta directa)
| Label | Icon | Ruta | Roles |
|---|---|---|---|
| Usuarios | `badge` | `/admin/usuarios` | admin, director |
| Información Institucional | `business` | `/admin/configuracion-institucion` | admin, director |

### R3 — Renames de label (no rutas)

Solo se renombran labels visibles al usuario. Las rutas (URLs) son intocables.

| Antes | Después |
|---|---|
| Dashboard | Inicio |
| Convivencia → Notas | Seguimiento (bajo Aula) |
| Config. Evaluación | Configuración SIE |
| Consol. Notas | Consolidado de Notas |
| Consol. Asistencia | Consolidado de Asistencia |
| Info. Institucional | Información Institucional |
| Boletín Periodo | Boletín de Periodo |

### R4 — Permisos por rol intactos

El implementer compara fila por fila los roles asignados HOY a cada ruta en
`NAV_ITEMS` con la nueva estructura. Si hay diferencia, prevalece el set de
HOY. Esto evita romper accidentalmente el acceso de algún rol.

### R5 — Pending flag

Si algún item tenía `pending: True` en el original (ej. items en desarrollo),
se preserva en la nueva estructura.

### R6 — Sin regresión de rutas

Todas las rutas que existían en el menú anterior siguen existiendo y accesibles
en el nuevo menú. Test:

```python
def test_navitems_preserva_rutas():
    """Cada ruta del NAV_ITEMS anterior debe seguir presente en el nuevo."""
    rutas_actuales = {…lista hardcoded de las rutas previas…}
    nuevas = {item["ruta"] for item in flatten(NAV_ITEMS) if "ruta" in item}
    faltantes = rutas_actuales - nuevas
    assert not faltantes, f"Rutas perdidas: {faltantes}"
```

### R7 — Tests funcionales

Adicionalmente:

- `test_navitems_grupos_raiz`: NAV_ITEMS tiene exactamente 6 grupos visibles
  (incluyendo Administración).
- `test_navitems_filtro_rol_profesor`: filtrando por rol "profesor", ve
  Inicio + Aula(5) + Académico(2: Estudiantes, Horarios) + Evaluación(parcial) +
  Informes(parcial). No ve Administración ni Grupos/Asignaturas/Asignaciones.

### R8 — Sin regresión

- `python init.py` verde.
- Tests previos + 3 nuevos verdes.

## Requisitos no funcionales

- Cambio mínimo: solo `NAV_ITEMS` se reescribe; el resto del `layout.py` queda
  intacto.
- Iconos: todos son Material Symbols Rounded existentes (no se inventan nombres).
- Sin emojis.
