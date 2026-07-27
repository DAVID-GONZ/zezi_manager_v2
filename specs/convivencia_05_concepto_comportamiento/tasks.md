# convivencia_05 — Concepto cualitativo de comportamiento (cuant + cualit consolidado)

> Fase 2 (`convivencia_00_roadmap`). Depende de `convivencia_04` (RBAC) y `convivencia_04b` (enforcement).

## Contexto y decisión (David)

El comportamiento de periodo debe ser **cuantitativo + cualitativo** y esa dupla es la que **baja al boletín** (Fase 3). Al analizar el modelo actual:

- `NotaComportamiento.valor` — cuantitativo (0–100).
- `NotaComportamiento.desempeno_id` — FK a `niveles_desempeno` (cualitativo por rango: Bajo/Básico/Alto/Superior).
- `NotaComportamiento.observacion` — texto libre (concepto narrativo del director de grupo).

**Todo ya existe en el esquema**. Este paso NO añade columnas ni cambia el modelo — solo:
1. Consolida la **lectura combinada** cuant+cualit en un DTO nuevo `ConceptoComportamientoDTO`.
2. Añade un método de servicio que resuelve el nivel de desempeño automático (por rango) o el manual (si se guardó `desempeno_id`) y devuelve todo listo para el boletín.
3. Actualiza los docstrings para dejar claro que `observacion` **es el concepto narrativo que baja al boletín** (renombrado semántico opcional en la vista, pero el campo persiste como `observacion` para no romper el repo).

Este paso NO toca `/convivencia/notas` (ya funciona) — es preparación de datos para convivencia_06 (reporte del director de grupo) y para la Fase 3 (boletín).

## Puerta de aprobación
No toca esquema. Añade un **DTO nuevo** (`ConceptoComportamientoDTO`) al modelo — cambio puramente aditivo, no rompe nada existente. **No requiere puerta explícita** según leader.md (no cambia esquema ni comportamiento del modelo existente); si el implementer detecta que sí, para y reporta.

## Tareas

### T1 — DTO consolidado en el modelo
- En `src/domain/models/convivencia.py`, añadir `ConceptoComportamientoDTO(BaseModel)`:
  - `estudiante_id: int`
  - `periodo_id: int`
  - `grupo_id: int`
  - `valor: float | None` (None si no hay nota registrada)
  - `nivel_nombre: str | None` (Bajo/Básico/Alto/Superior — resuelto por rango o por `desempeno_id`)
  - `nivel_descripcion: str | None`
  - `concepto: str | None` (narrativa; espejo de `NotaComportamiento.observacion`)
  - `aprobado: bool` (por umbral configurable, default 60)
- Exportarlo en `__all__`.
- Actualizar docstring de `NotaComportamiento.observacion` documentando explícitamente que es el "concepto narrativo que baja al boletín" (semántica, no cambio de campo).

### T2 — Método en el servicio
- En `ConvivenciaService`, añadir:
  - `get_concepto_periodo(estudiante_id: int, periodo_id: int, nota_minima: float = 60.0) -> ConceptoComportamientoDTO`
    - Lee la nota con `self._repo.get_nota(estudiante_id, periodo_id)`.
    - Si no hay nota → devuelve DTO con `valor=None`, `aprobado=False`, resto None.
    - Si hay: si `desempeno_id` está seteado, lo consulta directo; si no, resuelve el nivel por rango consultando `niveles_desempeno` del año.
  - `listar_conceptos_grupo(grupo_id: int, periodo_id: int, nota_minima: float = 60.0) -> list[ConceptoComportamientoDTO]`
    - Combina `listar_notas_por_grupo` con el estudiantado del grupo para producir un DTO por estudiante (incluidos los que aún no tienen nota).
- Diseño del provider de niveles (evalúa el implementer):
  - Opción A: inyectar un `configuracion_service` provider lazy análogo a `catalogo_academico_svc_provider` en `__init__` para leer los niveles.
  - Opción B: pasar los niveles como argumento (menos limpio; el caller tendría que resolverlos).
  - Recomendado: A. Wiring en `container.py`.

### T3 — Tests
- Unit del DTO: valor fuera de rango se rechaza (o se acepta según diseño); aprobado true/false por umbral.
- Servicio: sin nota → DTO con valor None; con nota y `desempeno_id` seteado → usa ese; sin `desempeno_id` → resuelve por rango; `listar_conceptos_grupo` devuelve una entrada por estudiante del grupo (incluidos los sin nota).

### T4 — Verificación
- `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_imports.py --layer domain`
- `... scripts/check_imports.py --layer services`
- `... -m pytest tests/unit/ -q --tb=short`
- `... init.py` VERDE.
- `progress/impl_convivencia_05.md`.

## criterio_done
Existe `ConceptoComportamientoDTO` en el modelo, `get_concepto_periodo` y `listar_conceptos_grupo` en `ConvivenciaService` (con provider lazy a niveles), tests verdes, `init.py` verde. Preparación lista para convivencia_06 (reporte del director de grupo) y para la Fase 3 (boletín). Sin cambios de esquema ni de UI.
