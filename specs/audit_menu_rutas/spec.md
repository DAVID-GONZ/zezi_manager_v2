# Auditoría de Vinculación — Pages / Menú / Roles

> **Tipo:** Diagnóstico / no implementar.  
> **Alcance:** `src/interface/pages/**/*.py`, `src/interface/design/layout.py` (NAV_ITEMS),
> `main.py` (rutas `@ui.page`).  
> **Objetivo:** Verificar que cada page tenga una ruta registrada, una entrada de menú
> correspondiente y que los roles de filtrado del menú sean consistentes con los roles
> de acceso de la page. Señalar páginas huérfanas, rutas sin menú y potenciales
> inconsistencias de rol.

---

## 1. Mapa completo ruta → file → menú → roles

### 1.1 Rutas registradas en `main.py`

| Ruta | Archivo fuente | En NAV_ITEMS | Roles NAV |
|---|---|---|---|
| `/` | *(redirect interno)* | No | — |
| `/login` | `pages/login.py` | No (correcto, pública) | — |
| `/logout` | *(handler)* | No (correcto) | — |
| `/diagnostico` | *(handler interno)* | No (ver §2.4) | — |
| `/inicio` | `pages/inicio.py` | ✅ Dashboard | `["*"]` |
| `/estudiantes` | `pages/academico/estudiantes.py` | ✅ Estudiantes | `["admin","director","coordinador","profesor"]` |
| `/asistencia` | `pages/academico/registro_asistencia.py` | ✅ Asistencia | `["profesor","coordinador"]` |
| `/horarios` | `pages/academico/horarios.py` | ✅ Horarios | `["admin","director","coordinador"]` |
| `/academico/tablero` | `pages/academico/tablero_estadisticos.py` | ✅ Estadísticos (top-level) | `["profesor","director","coordinador"]` |
| `/evaluacion/planilla` | `pages/evaluacion/planilla_notas.py` | ✅ Planilla de Notas | `["profesor","coordinador"]` |
| `/evaluacion/configuracion` | `pages/evaluacion/configuracion_evaluacion.py` | ✅ Config. Evaluación | `["profesor","coordinador"]` |
| `/evaluacion/habilitaciones` | `pages/evaluacion/habilitaciones.py` | ✅ Habilitaciones | `["profesor","coordinador"]` |
| `/evaluacion/planes` | `pages/evaluacion/planes_mejoramiento.py` | ✅ Planes de Mejora | `["profesor","coordinador"]` |
| `/evaluacion/cierre-periodo` | `pages/evaluacion/cierre_periodo.py` | ✅ Cierre de Periodo | `["coordinador","director"]` |
| `/evaluacion/cierre-anio` | `pages/evaluacion/cierre_anio.py` | ✅ Cierre de Año | `["director"]` |
| `/convivencia/observaciones` | `pages/convivencia/observaciones.py` | ✅ Observaciones | `["coordinador","director"]` |
| `/convivencia/comportamiento` | `pages/convivencia/comportamiento.py` | ✅ Comportamiento | `["coordinador","director"]` |
| `/convivencia/notas` | `pages/convivencia/notas_convivencia.py` | ✅ Notas | `["coordinador","director"]` |
| `/informes/boletin-periodo` | `pages/informes/boletin_periodo.py` | ✅ Boletín Periodo | `["director","coordinador","profesor"]` |
| `/informes/boletin-anual` | `pages/informes/boletin_anual.py` | ✅ Boletín Anual | `["director","coordinador","profesor"]` |
| `/informes/consolidado-notas` | `pages/informes/consolidado_notas.py` | ✅ Consol. Notas | `["director","coordinador"]` |
| `/informes/consolidado-asistencia` | `pages/informes/consolidado_asistencia.py` | ✅ Consol. Asistencia | `["director","coordinador"]` |
| `/informes/estadisticos` | `pages/informes/estadisticos.py` | ✅ Estadísticos (en Informes) | `["director","coordinador","profesor"]` |
| `/admin/grupos` | `pages/admin/grupos.py` | ✅ Grupos | `["admin","director"]` |
| `/admin/asignaturas` | `pages/admin/asignaturas.py` | ✅ Asignaturas | `["admin","director"]` |
| `/admin/asignaciones` | `pages/admin/asignaciones.py` | ✅ Asignaciones | `["admin","director"]` |
| `/admin/configuracion` | `pages/admin/configuracion_sie.py` | ✅ Config. SIE | `["admin","director"]` |
| `/admin/configuracion-institucion` | `pages/admin/configuracion_institucion.py` | ✅ Info. Institucional | `["admin","director"]` |
| `/admin/usuarios` | `pages/admin/usuarios.py` | ✅ Usuarios | `["admin"]` |

**Resultado general:** todas las rutas activas tienen entrada de menú correspondiente,
salvo las excepciones documentadas en §2.

---

## 2. Hallazgos por categoría

### 2.1 Página huérfana — `convivencia/seguimiento.py`

```
src/interface/pages/convivencia/seguimiento.py
  → Contenido: vacío (0 bytes)
  → Rutas @ui.page: ninguna
  → Entrada en NAV_ITEMS: ninguna
  → Referencia en main.py: ninguna
```

El archivo existe como remanente del diseño original donde el tercer ítem de
Convivencia se llamaba "Seguimiento" con ruta `/convivencia/seguimiento`. En el
paso `paso_10g_convivencia` se renombró a "Notas" con ruta `/convivencia/notas`,
y se creó `notas_convivencia.py`, pero el archivo vacío `seguimiento.py` no fue
eliminado. Es código muerto seguro de borrar.

### 2.2 "Estadísticos" duplicado en el menú — ✅ RESUELTO (2026-05-21)

| Ítem | Ruta | Ubicación en menú | Label actual |
|---|---|---|---|
| Tablero (top-level) | `/academico/tablero` | Nivel raíz, entre Horarios y Administración | `"Tablero"` ← renombrado |
| Estadísticos (en Informes) | `/informes/estadisticos` | Sub-ítem del grupo Informes | `"Estadísticos"` ← sin cambio |

**Acción tomada:** el ítem top-level fue renombrado de `"Estadísticos"` a `"Tablero"` en
`layout.py` NAV_ITEMS. El label de Informes queda como `"Estadísticos"`.

**Diferencia funcional:** `tablero_estadisticos.py` es el tablero KPI personal de asistencia
+ notas con heatmap y ag-Grid, vinculado al contexto del usuario (asignación activa).
`estadisticos.py` es el centro de generación de informes exportables con filtros libres
(spec: `paso_11a_estadisticos_informes`).

### 2.3 Inconsistencia de nomenclatura de ruta: `/asistencia`

- Ruta registrada: `/asistencia` (plana, sin prefijo de módulo)
- Archivo: `src/interface/pages/academico/registro_asistencia.py`
- Patrón del resto del módulo académico: `/academico/tablero`, `/academico/estudiantes`
  (aunque `/estudiantes` también es plana)

El prefijo `academico/` se usa para el tablero pero no para estudiantes, asistencia
ni horarios. La convención de rutas no es uniforme:
- **Con prefijo `academico/`:** `/academico/tablero`
- **Sin prefijo:** `/estudiantes`, `/asistencia`, `/horarios`

No es un error funcional pero reduce la legibilidad del árbol de rutas.

### 2.4 Ruta `/diagnostico` — oculta intencionalmente

Registrada en `main.py`, no aparece en NAV_ITEMS ni es accesible desde el menú.
Es un endpoint de salud/debug del sistema. No requiere acción, pero conviene
documentarlo explícitamente en `main.py` para futuros mantenedores.

---

## 3. Análisis de roles por módulo

### 3.1 Matriz de visibilidad por rol

| Módulo | admin | director | coordinador | profesor |
|---|---|---|---|---|
| Dashboard `/inicio` | ✅ | ✅ | ✅ | ✅ |
| Estudiantes `/estudiantes` | ✅ | ✅ | ✅ | ✅ |
| Asistencia `/asistencia` | ❌ | ❌ | ✅ | ✅ |
| Calificaciones (grupo) | ❌ | ✅ | ✅ | ✅ |
| — Planilla | ❌ | ❌ | ✅ | ✅ |
| — Config. Evaluación | ❌ | ❌ | ✅ | ✅ |
| — Habilitaciones | ❌ | ❌ | ✅ | ✅ |
| — Planes de Mejora | ❌ | ❌ | ✅ | ✅ |
| — Cierre de Periodo | ❌ | ✅ | ✅ | ❌ |
| — Cierre de Año | ❌ | ✅ | ❌ | ❌ |
| Convivencia (grupo) | ❌ | ✅ | ✅ | ❌ |
| Informes (grupo) | ❌ | ✅ | ✅ | ✅ (3/5) |
| — Boletín Periodo | ❌ | ✅ | ✅ | ✅ |
| — Boletín Anual | ❌ | ✅ | ✅ | ✅ |
| — Consol. Notas | ❌ | ✅ | ✅ | ❌ |
| — Consol. Asistencia | ❌ | ✅ | ✅ | ❌ |
| — Estadísticos Informes | ❌ | ✅ | ✅ | ✅ |
| Horarios `/horarios` | ✅ | ✅ | ✅ | ❌ |
| Estadísticos `/academico/tablero` | ❌ | ✅ | ✅ | ✅ |
| Administración (grupo) | ✅ | ✅ | ❌ | ❌ |
| — Usuarios | ✅ | ❌ | ❌ | ❌ |

### 3.2 Casos que merecen revisión de negocio

**[B1] `profesor` no puede ver Horarios**

El rol `profesor` no tiene entrada en el menú de Horarios (`/horarios`). Si un
docente necesita consultar su propio horario, no tiene acceso desde el menú.
La route `/horarios` acepta `["admin","director","coordinador"]`.

Preguntar: ¿el profesor consulta su horario desde otra vista o es una restricción
intencional de diseño (el coordinador carga los horarios, no los visualiza el profesor)?

**[B2] `admin` no ve módulos académicos**

El rol `admin` es de gestión del sistema (usuarios, configuración SIE, institución,
grupos, asignaturas, asignaciones). No tiene acceso a Calificaciones, Convivencia,
ni Informes. Si el admin necesita hacer soporte o auditoría de datos académicos,
no tiene vista disponible.

Preguntar: ¿existe un rol "superadmin" planificado, o el admin tiene acceso
directo a BD para esos casos?

**[B3] `profesor` ve Estudiantes con roles completos**

`/estudiantes` es visible para profesor con los mismos roles que admin/director.
La page `estudiantes.py` tiene botones de CRUD (crear, editar, eliminar) que
probablemente deberían estar restringidos a admin/director en la lógica de la page,
no solo en el menú. Verificar que los botones de acción en `estudiantes.py` respeten
el rol del usuario autenticado antes de renderizarse.

**[B4] `director` no ve Planilla de Notas ni Config. Evaluación**

Cierre de Periodo y Cierre de Año sí son visibles para director, pero Planilla y
Config. Evaluación solo para `["profesor","coordinador"]`. El director puede cerrar
periodos sin poder ver la planilla que cierra. Puede ser intencional (el director
no ingresa notas, solo cierra) pero conviene confirmar.

---

## 4. Verificación de coherencia interna de NAV_ITEMS

### 4.1 Ítems del grupo Calificaciones — rol del grupo vs hijos

| Padre | Roles padre | Hijo | Roles hijo |
|---|---|---|---|
| Calificaciones | `["profesor","coordinador","director"]` | Planilla | `["profesor","coordinador"]` |
| Calificaciones | `["profesor","coordinador","director"]` | Config. Evaluación | `["profesor","coordinador"]` |
| Calificaciones | `["profesor","coordinador","director"]` | Habilitaciones | `["profesor","coordinador"]` |
| Calificaciones | `["profesor","coordinador","director"]` | Planes de Mejora | `["profesor","coordinador"]` |
| Calificaciones | `["profesor","coordinador","director"]` | Cierre de Periodo | `["coordinador","director"]` |
| Calificaciones | `["profesor","coordinador","director"]` | Cierre de Año | `["director"]` |

**Resultado:** el grupo padre `director` no tiene ítems directamente accesibles
para él, excepto Cierre de Periodo y Cierre de Año. El grupo sí aparece en el menú
del director porque el padre lo permite y el filtrado de hijos funciona correctamente
(los hijos inaccesibles simplemente no se renderizan).

### 4.2 Informes — verificación misma lógica

Todos los hijos tienen roles que son subconjuntos del rol padre `["director","coordinador","profesor"]`.
Sin inconsistencia.

### 4.3 Administración — Usuarios solo para `admin`

`Usuarios (/admin/usuarios)` es el único ítem cuyo rol hijo (`["admin"]`) es más
restrictivo que el grupo padre (`["admin","director"]`). El director entra al grupo
Administración y ve Grupos, Asignaturas, Asignaciones, Config. SIE, Info. Institucional,
pero NO ve Usuarios. El filtrado por rol en el sidebar renderiza correctamente
solo los hijos permitidos. Sin inconsistencia.

---

## 5. Rutas en `pages/` sin ruta `@ui.page` registrada

Verificación de todos los archivos `.py` en `pages/` que no tienen `@ui.page`:

| Archivo | Tiene @ui.page | Registrado en main.py |
|---|---|---|
| `pages/__init__.py` | No (correcto, init) | — |
| `pages/admin/__init__.py` | No (correcto) | — |
| `pages/academico/__init__.py` | No (correcto) | — |
| `pages/evaluacion/__init__.py` | No (correcto) | — |
| `pages/convivencia/__init__.py` | No (correcto) | — |
| `pages/informes/__init__.py` | No (correcto) | — |
| **`pages/convivencia/seguimiento.py`** | **No** | **No** ← Huérfano (ver §2.1) |

---

## 6. Resumen ejecutivo

| Hallazgo | Tipo | Severidad |
|---|---|---|
| `convivencia/seguimiento.py` vacío y sin ruta | Página huérfana | Media (ruido, no error) |
| "Estadísticos" aparece dos veces en menú con label idéntico | UX confuso | Alta |
| Nomenclatura de rutas inconsistente (`/academico/tablero` vs `/horarios`) | Deuda técnica | Baja |
| `profesor` sin acceso a Horarios desde menú | Decisión de negocio a confirmar | Media |
| `admin` sin acceso a módulos académicos | Decisión de negocio a confirmar | Media |
| `profesor` ve Estudiantes: verificar CRUD en la page según rol | Posible fallo de autorización en UI | Alta (verificar) |
| `director` no ve Planilla aunque sí cierra periodos | Decisión de negocio a confirmar | Baja |
| `/diagnostico` sin documentar como ruta interna | Deuda de documentación | Baja |

---

*Generado: 2026-05-21. Base de código: commit `00bcbc0`.*
