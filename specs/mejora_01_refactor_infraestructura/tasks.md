# Tasks: Descomposición de InfraestructuraService (mejora_01_refactor_infraestructura)

> **Enfoque IMPORT-SAFE (decisión de David):** fachada por delegación. Se extrae
> la LÓGICA a sub-servicios cohesivos, pero `InfraestructuraService` **conserva
> todos sus métodos públicos y sus re-exports**, delegando en los nuevos servicios
> vía `Container`. Así los 17 archivos / 60 llamadas de la interfaz y los 4 imports
> directos (`DiaSemana, AreaConocimiento, Asignatura, Grupo, Sala`) **NO se tocan y
> NO se rompen**. El re-apuntado de consumidores y el retiro de la fachada quedan
> para una mejora posterior de bajo riesgo.

## Invariantes de import (verificar en CADA task)
- `src/interface/**` **no se modifica** en este spec (0 líneas cambiadas).
- `src/services/infraestructura_service.py` **mantiene sus imports/re-exports de
  nivel de módulo** (los símbolos `DiaSemana, AreaConocimiento, Asignatura, Grupo,
  Sala` siguen importables desde ahí).
- Verificación de imports tras cada task (con el venv):
  `.venv/Scripts/python.exe -c "from src.services.infraestructura_service import DiaSemana, AreaConocimiento, Asignatura, Grupo, Sala; print('re-exports OK')"`
  y `Container.diagnostico()` sin errores.

---

- [x] T1: Crear `src/services/sala_service.py` (`SalaService`) con la LÓGICA de los
      métodos de salas (movida, no reescrita). En `InfraestructuraService`, esos
      métodos pasan a delegar en `Container.sala_service()`. Añadir
      `Container.sala_service()` + incluirlo en `Container.diagnostico()`.
  Verifica: `.venv/Scripts/python.exe -m pytest tests/unit/services/ tests/integration/ -q` && re-exports OK
  Produce: `src/services/sala_service.py`; InfraestructuraService delega; interfaz intacta

- [x] T2: Ídem para `src/services/franja_service.py` (`FranjaService`): plantillas y
      franjas. Delegación desde InfraestructuraService + Container + diagnostico.
  Verifica: `.venv/Scripts/python.exe -m pytest tests/unit/services/ tests/integration/ -q` && re-exports OK
  Produce: `src/services/franja_service.py`; delegación; interfaz intacta

- [x] T3: Ídem para `src/services/escenario_horario_service.py`
      (`EscenarioHorarioService`): escenarios + listar_horario_*_escenario.
  Verifica: `.venv/Scripts/python.exe -m pytest tests/unit/services/ tests/integration/ -q` && re-exports OK
  Produce: `src/services/escenario_horario_service.py`; delegación; interfaz intacta

- [x] T4: Ídem para `src/services/restriccion_generacion_service.py`
      (`RestriccionGeneracionService`): config de generación, ventanas, bloques
      anclados, franjas de reunión, límites y disponibilidad docente.
  Verifica: `.venv/Scripts/python.exe -m pytest tests/unit/services/ tests/integration/ -q` && re-exports OK
  Produce: `src/services/restriccion_generacion_service.py`; delegación; interfaz intacta

- [x] T5: Ídem para `src/services/catalogo_academico_service.py`
      (`CatalogoAcademicoService`): CRUD de áreas, asignaturas y grupos.
  Verifica: `.venv/Scripts/python.exe -m pytest tests/unit/services/ tests/integration/ -q` && re-exports OK
  Produce: `src/services/catalogo_academico_service.py`; delegación; interfaz intacta

- [x] T6: Regenerar la referencia de API y verificar entorno completo con el venv.
  Verifica: `.venv/Scripts/python.exe tools/gen_api_reference.py` && `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe init.py`
  Produce: todos los checks verdes; nuevos servicios cohesivos (≤ ~25 métodos c/u);
           `InfraestructuraService` queda como fachada de delegación (interfaz intacta)

> **Fuera de alcance de este spec (mejora posterior):** re-apuntar los 60 call
> sites de la interfaz a los nuevos servicios, retirar la fachada y consolidar
> horarios en `HorarioService` (spec R8). Se hará cuando se pueda verificar sin
> riesgo de romper imports.
