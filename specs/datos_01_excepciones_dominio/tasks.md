# Tasks: Jerarquía de excepciones de dominio (datos_01_excepciones_dominio)

> Intérprete del proyecto: `.venv/Scripts/python.exe`.
> Todas las tareas se limitan al SCOPE: `src/domain/exceptions.py`, los 23 servicios
> de `src/services/`, `src/services/solo_lectura.py`, `src/services/contexto_tenant.py`
> y `tests/unit/domain/test_exceptions.py`. **Ningún archivo de `src/interface/`,
> `src/infrastructure/` ni `src/domain/models/` se toca en este paso.**

## Comando de verificación por servicio (se repite en T6–T21)

Comprueba que en el archivo indicado no queda ningún `raise ValueError` ni
`raise RuntimeError`; sale con código 1 y lista los números de línea si quedan:

```
.venv/Scripts/python.exe -c "import ast,pathlib as P,sys;f='<ARCHIVO>';r=[n.lineno for n in ast.walk(ast.parse(P.Path(f).read_text('utf-8'))) if isinstance(n,ast.Raise) and getattr(getattr(n.exc,'func',0),'id','') in('ValueError','RuntimeError')];sys.exit(f'quedan genericos en {r}' if r else 0)"
```

Cada tarea de sustitución trae además una línea `Regresión:` con la suite que debe
seguir verde. La puerta de ruff (`F821` bloqueante) se corre **después de cada
servicio**, no solo al final (design §6.4).

---

## Bloque A — La jerarquía

- [ ] **T1**: Crear `src/domain/exceptions.py` con `CategoriaError`, `CodigoError`,
      la raíz `ZeciError` (`mensaje` / `codigo` / `detalles` / `to_dict()`), las cinco
      familias (`ReglaDeNegocioError`, `NoEncontradoError`, `ConflictoError`,
      `PermisoDenegadoError`, `DependenciaNoDisponibleError`) y los dos subtipos
      `OperacionSoloLecturaError` y `OperacionFueraDeInstitucionError`. Solo stdlib.
      El docstring declara que los mixins `ValueError`/`RuntimeError` son un puente
      transitorio (design §2.2).
  Verifica: `.venv/Scripts/python.exe -c "import ast,pathlib as P;t=ast.parse(P.Path('src/domain/exceptions.py').read_text('utf-8'));mods={n.module.split('.')[0] for n in ast.walk(t) if isinstance(n,ast.ImportFrom) and n.module};assert mods<={'enum','typing','collections'},mods;print('OK — solo stdlib')"`
  Produce: `src/domain/exceptions.py`

- [ ] **T2**: Crear `tests/unit/domain/test_exceptions.py` con las invariantes de la
      jerarquía: herencia de cada familia (`ValueError` / `PermissionError` /
      `RuntimeError`), MRO exacto de `PermisoDenegadoError` (design §6.1),
      `exc.args == (mensaje,)` y `str(exc) == mensaje`, unicidad de los miembros de
      `CodigoError`, `to_dict()` con las tres claves, `categoria` correcta por familia,
      y que `ZeciError` **no** es subclase de `ValueError`. Un comentario `# R<n>` por
      requisito cubierto (R1–R8, R16, R19).
  Verifica: `.venv/Scripts/python.exe -m pytest tests/unit/domain/test_exceptions.py -q`
  Produce: `tests/unit/domain/test_exceptions.py` verde

- [ ] **T3**: Modificar `src/services/solo_lectura.py` para importar
      `OperacionSoloLecturaError` de `src.domain.exceptions` y re-exportarla
      (**sin redefinirla ni subclasearla**, design §6.2). `__all__`, el mensaje por
      defecto y el cuerpo de `verificar_escritura()` / `requiere_escritura` no cambian.
  Verifica: `.venv/Scripts/python.exe -c "from src.domain.exceptions import OperacionSoloLecturaError as A;from src.services.solo_lectura import OperacionSoloLecturaError as B;assert A is B;assert issubclass(A,PermissionError);print('OK — misma clase, sigue PermissionError')"`
  Produce: `src/services/solo_lectura.py` modificado

- [ ] **T4**: Modificar `src/services/contexto_tenant.py` para importar
      `OperacionFueraDeInstitucionError` de `src.domain.exceptions` y re-exportarla.
      `verificar_pertenencia()` añade `detalles={"institucion_esperada": scope}` y
      **no** incluye el `institucion_id` del objeto ajeno (R12). El resto del módulo
      no cambia.
  Verifica: `.venv/Scripts/python.exe -c "from src.domain.exceptions import OperacionFueraDeInstitucionError as A;from src.services.contexto_tenant import OperacionFueraDeInstitucionError as B;assert A is B;assert issubclass(A,PermissionError);print('OK — misma clase, sigue PermissionError')"`
  Produce: `src/services/contexto_tenant.py` modificado

- [ ] **T5**: Confirmar que los dos mecanismos de permiso no regresionan: la suite de
      aislamiento por objeto y las suites de solo lectura siguen verdes sin haber
      tocado ni un test.
  Verifica: `.venv/Scripts/python.exe -m pytest tests/unit/services -q -k "aislamiento or solo_lectura or tenant"`
  Produce: suites de permiso/tenant verdes

---

## Bloque B — Sustitución por servicio

> Orden: primero el piloto (T6). El reviewer valida el patrón ahí antes de que el
> implementer replique en los 22 restantes.

- [ ] **T6** *(piloto)*: `src/services/institucion_service.py` — 4 sitios
      (3 `NoEncontradoError`, 1 `ConflictoError`).
  Verifica: comando por servicio con `<ARCHIVO> = src/services/institucion_service.py`
  Regresión: `.venv/Scripts/python.exe -m pytest tests/unit/services -q -k institucion`
  Produce: `src/services/institucion_service.py` sin `raise` genéricos

- [ ] **T7**: `src/services/convivencia_service.py` — 22 sitios (15 `ValueError`,
      7 `RuntimeError`). Los 7 `RuntimeError` de proveedores/exportador no inyectados
      pasan a `DependenciaNoDisponibleError`; verificar el `except RuntimeError` de la
      línea ~1773 (design §4.4).
  Verifica: comando por servicio con `<ARCHIVO> = src/services/convivencia_service.py`
  Regresión: `.venv/Scripts/python.exe -m pytest tests/unit/services -q -k convivencia`
  Produce: `src/services/convivencia_service.py` sin `raise` genéricos

- [ ] **T8**: `src/services/evaluacion_service.py` — 19 sitios (15 `ValueError`,
      4 `RuntimeError` de `SIEERepository no disponible` → `DependenciaNoDisponibleError`).
  Verifica: comando por servicio con `<ARCHIVO> = src/services/evaluacion_service.py`
  Regresión: `.venv/Scripts/python.exe -m pytest tests/unit/services -q -k "evaluacion or nota"`
  Produce: `src/services/evaluacion_service.py` sin `raise` genéricos

- [ ] **T9**: `src/services/horario_service.py` — 13 sitios. Solapes de docente/grupo/
      sala → `ConflictoError` (`SOLAPE_HORARIO`); límites de bloques y carga docente →
      `ReglaDeNegocioError`. Verificar los 3 `except (ValueError, TypeError)` internos.
  Verifica: comando por servicio con `<ARCHIVO> = src/services/horario_service.py`
  Regresión: `.venv/Scripts/python.exe -m pytest tests/unit/services -q -k horario`
  Produce: `src/services/horario_service.py` sin `raise` genéricos

- [ ] **T10**: `src/services/plan_mejoramiento_service.py` — 13 sitios.
  Verifica: comando por servicio con `<ARCHIVO> = src/services/plan_mejoramiento_service.py`
  Regresión: `.venv/Scripts/python.exe -m pytest tests/unit/services -q -k "plan or mejoramiento"`
  Produce: `src/services/plan_mejoramiento_service.py` sin `raise` genéricos

- [ ] **T11**: `src/services/usuario_service.py` — 11 sitios. Los 3 de rol insuficiente
      → `PermisoDenegadoError` (`ROL_NO_AUTORIZADO`); los 2 de «servicio de
      autenticación no está configurado» → `DependenciaNoDisponibleError`; el de
      contraseña actual incorrecta → `ReglaDeNegocioError` (`PASSWORD_INCORRECTA`),
      **sin** exponer la contraseña en `detalles` (R7).
  Verifica: comando por servicio con `<ARCHIVO> = src/services/usuario_service.py`
  Regresión: `.venv/Scripts/python.exe -m pytest tests/unit/services -q -k "usuario or password or rbac"`
  Produce: `src/services/usuario_service.py` sin `raise` genéricos

- [ ] **T12**: `src/services/configuracion_service.py` — 10 sitios.
  Verifica: comando por servicio con `<ARCHIVO> = src/services/configuracion_service.py`
  Regresión: `.venv/Scripts/python.exe -m pytest tests/unit/services -q -k configuracion`
  Produce: `src/services/configuracion_service.py` sin `raise` genéricos

- [ ] **T13**: `src/services/estudiante_service.py` — 10 sitios. Documento duplicado →
      `ConflictoError` (`DOCUMENTO_DUPLICADO`); rol sin permiso de gestión →
      `PermisoDenegadoError`; grupo destino inexistente → `NoEncontradoError`.
  Verifica: comando por servicio con `<ARCHIVO> = src/services/estudiante_service.py`
  Regresión: `.venv/Scripts/python.exe -m pytest tests/unit/services -q -k estudiante`
  Produce: `src/services/estudiante_service.py` sin `raise` genéricos

- [ ] **T14**: `src/services/asignacion_service.py` — 8 sitios.
  Verifica: comando por servicio con `<ARCHIVO> = src/services/asignacion_service.py`
  Regresión: `.venv/Scripts/python.exe -m pytest tests/unit/services -q -k asignacion`
  Produce: `src/services/asignacion_service.py` sin `raise` genéricos

- [ ] **T15**: `src/services/nivelacion_service.py` — 7 sitios.
  Verifica: comando por servicio con `<ARCHIVO> = src/services/nivelacion_service.py`
  Regresión: `.venv/Scripts/python.exe -m pytest tests/unit/services -q -k nivelacion`
  Produce: `src/services/nivelacion_service.py` sin `raise` genéricos

- [ ] **T16**: `src/services/cierre_service.py` — 6 sitios. Periodo ya cerrado →
      `ConflictoError` (`PERIODO_CERRADO`).
  Verifica: comando por servicio con `<ARCHIVO> = src/services/cierre_service.py`
  Regresión: `.venv/Scripts/python.exe -m pytest tests/unit/services -q -k cierre`
  Produce: `src/services/cierre_service.py` sin `raise` genéricos

- [ ] **T17**: `src/services/informe_service.py` — 6 sitios (todos regla de negocio).
  Verifica: comando por servicio con `<ARCHIVO> = src/services/informe_service.py`
  Regresión: `.venv/Scripts/python.exe -m pytest tests/unit/services -q -k informe`
  Produce: `src/services/informe_service.py` sin `raise` genéricos

- [ ] **T18**: `src/services/periodo_service.py` — 6 sitios. Suma de pesos > 100 % →
      `ReglaDeNegocioError` (`PESOS_EXCEDEN_TOTAL`); periodo duplicado en el año →
      `ConflictoError`; hito sobre periodo cerrado → `ConflictoError`.
  Verifica: comando por servicio con `<ARCHIVO> = src/services/periodo_service.py`
  Regresión: `.venv/Scripts/python.exe -m pytest tests/unit/services -q -k periodo`
  Produce: `src/services/periodo_service.py` sin `raise` genéricos

---

## Bloque C — Servicios de 1 a 3 sitios (agrupados por área)

- [ ] **T19**: Área horarios e infraestructura física — `franja_service.py` (3),
      `restriccion_generacion_service.py` (3), `sala_service.py` (2),
      `generador_horario_service.py` (1). 9 sitios.
  Verifica: `.venv/Scripts/python.exe -c "import ast,pathlib as P,sys;fs=['src/services/franja_service.py','src/services/restriccion_generacion_service.py','src/services/sala_service.py','src/services/generador_horario_service.py'];r=[(f,n.lineno) for f in fs for n in ast.walk(ast.parse(P.Path(f).read_text('utf-8'))) if isinstance(n,ast.Raise) and getattr(getattr(n.exc,'func',0),'id','') in('ValueError','RuntimeError')];sys.exit(f'quedan genericos en {r}' if r else 0)"`
  Regresión: `.venv/Scripts/python.exe -m pytest tests/unit/services -q -k "franja or sala or generador or restriccion"`
  Produce: los 4 servicios sin `raise` genéricos

- [ ] **T20**: Área académica y convivencia menor — `catalogo_academico_service.py` (3),
      `habilitacion_service.py` (3), `alerta_service.py` (2). 8 sitios.
  Verifica: `.venv/Scripts/python.exe -c "import ast,pathlib as P,sys;fs=['src/services/catalogo_academico_service.py','src/services/habilitacion_service.py','src/services/alerta_service.py'];r=[(f,n.lineno) for f in fs for n in ast.walk(ast.parse(P.Path(f).read_text('utf-8'))) if isinstance(n,ast.Raise) and getattr(getattr(n.exc,'func',0),'id','') in('ValueError','RuntimeError')];sys.exit(f'quedan genericos en {r}' if r else 0)"`
  Regresión: `.venv/Scripts/python.exe -m pytest tests/unit/services -q -k "catalogo or habilitacion or alerta"`
  Produce: los 3 servicios sin `raise` genéricos

- [ ] **T21**: Resto — `asistencia_service.py` (2),
      `aprovisionamiento_institucion_service.py` (1),
      `preferencias_institucion_service.py` (1). 4 sitios.
  Verifica: `.venv/Scripts/python.exe -c "import ast,pathlib as P,sys;fs=['src/services/asistencia_service.py','src/services/aprovisionamiento_institucion_service.py','src/services/preferencias_institucion_service.py'];r=[(f,n.lineno) for f in fs for n in ast.walk(ast.parse(P.Path(f).read_text('utf-8'))) if isinstance(n,ast.Raise) and getattr(getattr(n.exc,'func',0),'id','') in('ValueError','RuntimeError')];sys.exit(f'quedan genericos en {r}' if r else 0)"`
  Regresión: `.venv/Scripts/python.exe -m pytest tests/unit/services -q -k "asistencia or aprovisionamiento or preferencias"`
  Produce: los 3 servicios sin `raise` genéricos

---

## Bloque D — Cierre

- [ ] **T22**: Añadir a `tests/unit/domain/test_exceptions.py` la guarda estructural
      que recorre **todos** los `src/services/*.py` con `ast` y falla si queda un solo
      `raise ValueError` / `raise RuntimeError`, más una segunda guarda que afirma que
      cada `ZeciError` lanzado desde servicios usa un miembro de `CodigoError`. Incluir
      el comentario que explica la ubicación anómala (design §6.3) y `# R18`, `# R20`.
  Verifica: `.venv/Scripts/python.exe -m pytest tests/unit/domain/test_exceptions.py -q`
  Produce: `tests/unit/domain/test_exceptions.py` con la guarda, verde

- [ ] **T23**: Verificar el entorno completo: puerta de ruff bloqueante + suite.
  Verifica: `.venv/Scripts/python.exe scripts/init.py`
  Produce: todos los checks verdes

---

## Criterio de done

- Los 156 sitios sustituidos: 145 `raise ValueError` + 11 `raise RuntimeError` → 0.
- Ningún mensaje en español cambió de redacción (design §4.4).
- Ningún archivo fuera del SCOPE modificado (`git diff --name-only` lo confirma).
- `scripts/init.py` verde.
