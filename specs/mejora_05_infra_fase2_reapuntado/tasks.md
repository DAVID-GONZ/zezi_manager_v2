# Tasks: Fase 2 refactor infra (mejora_05_infra_fase2_reapuntado)

> ⚠️ Re-apuntado ARCHIVO POR ARCHIVO con verificación de imports. Verificar con
> `.venv/Scripts/python.exe`. PARAR y revertir el archivo ante cualquier fallo de
> import; no avanzar con el árbol roto.

- [x] T1: Migrar los 4 imports de símbolos de dominio
      (`from src.services.infraestructura_service import DiaSemana|AreaConocimiento|Asignatura|Grupo|Sala`)
      en `horarios_hub.py`, `asignaturas.py`, `grupos.py`, `salas.py`.
      DESVIACIÓN: se migran al **sub-servicio dueño** (franja_service→DiaSemana,
      catalogo_academico_service→AreaConocimiento/Asignatura/Grupo, sala_service→Sala),
      NO a `src.domain.models` — porque `src/interface/pages` tiene PROHIBIDO importar
      `src.domain.models` (check_imports / convención §2, que init.py verifica). Los
      sub-servicios re-exportan esos tipos vía `__all__`.
  Verifica: `.venv/Scripts/python.exe -m pytest -q` && `python scripts/check_imports.py --layer interface`
  Produce: 0 imports de símbolos de dominio desde la fachada; suite verde ✓

- [x] T2: Re-apuntar los consumidores de **salas** y **catálogo** (áreas,
      asignaturas, grupos) a `sala_service()` / `catalogo_academico_service()`,
      archivo por archivo.
  Verifica: `.venv/Scripts/python.exe -m pytest -q` (verde tras cada archivo)
  Produce: 0 `infraestructura_service()` para esos métodos en esos archivos ✓

- [x] T3: Re-apuntar los consumidores de **franjas/plantillas** y **escenarios** a
      `franja_service()` / `escenario_horario_service()`.
  Verifica: `.venv/Scripts/python.exe -m pytest -q`
  Produce: 0 `infraestructura_service()` para esos métodos ✓

- [x] T4: Re-apuntar los consumidores de **restricciones/config de generación** a
      `restriccion_generacion_service()`.
  Verifica: `.venv/Scripts/python.exe -m pytest -q`
  Produce: 0 `infraestructura_service()` para esos métodos ✓

- [x] T5: Consolidar los métodos de bloques de horario en `HorarioService` (R3),
      re-apuntar sus consumidores y eliminar la copia de la infraestructura.
      `HorarioService.listar_horario_grupo` añadido; consumidor (context_selector)
      re-apuntado; los 6 passthroughs de bloques (listar_horario_grupo/_docente,
      guardar/eliminar_horario, existe_conflicto_horario, get_estadisticas)
      ELIMINADOS de la fachada (estaban muertos: nadie los consumía).
  Verifica: `.venv/Scripts/python.exe -m pytest -q`
  Produce: `HorarioService` dueño único de bloques; 0 duplicados ✓

- [~] T6: Interface re-apuntada (grep `src/interface/` → 0) y consumidor de
      producción `estudiante_service.get_grupo` movido a `catalogo_academico_service`.
      La fachada `InfraestructuraService` se CONSERVA como **residuo justificado**:
      (a) la inyecta `generador_horario_service` (agrega salas+escenario+restricción
      en un solo objeto, validado por tests de integración), y (b) ~8 tests de
      integración/unit ejercen su delegación (tenant, aislamiento, construir_restricciones).
      NO se recortó a ≤25 métodos ni se borró porque eso exige migrar esos ~8 tests +
      re-cablear el constructor del generador — fuera del alcance seguro de este paso
      de imports. `Container.infraestructura_service()` y su entrada en `diagnostico()`
      se mantienen (siguen válidas).
  Verifica: `grep -rn "infraestructura_service()" src/interface/` → 0 ✓ && `pytest -q` ✓
  Produce: fachada como residuo justificado (R4 estricto ≤25 diferido)

- [x] T7: Regenerar referencia de API, actualizar docs y verificar entorno completo.
  Verifica: `.venv/Scripts/python.exe tools/gen_api_reference.py` && `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe init.py`
  Produce: todos los checks verdes (ENTORNO OK); api_reference regenerada ✓

> Opcional (fuera de done): partir `RestriccionGeneracionService` (30→2 servicios)
> si se quiere el "≤25" estricto también ahí (ver design.md §7).
