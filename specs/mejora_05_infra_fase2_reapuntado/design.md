# Diseño: Fase 2 refactor infra (mejora_05_infra_fase2_reapuntado)

## 1. Mapa de re-apuntado (método → servicio destino)

Cada llamada `Container.infraestructura_service().X()` pasa a
`Container.<destino>_service().X()`, según el subdominio de `X` (ya cableados en
`Container` por `mejora_01`):

| Subdominio | Servicio destino |
|---|---|
| salas, asignar_sala_a_grupo | `Container.sala_service()` |
| plantillas, franjas | `Container.franja_service()` |
| escenarios, horario por escenario | `Container.escenario_horario_service()` |
| config generación, ventanas, bloques anclados, franjas reunión, límites, disponibilidad | `Container.restriccion_generacion_service()` |
| áreas, asignaturas, grupos | `Container.catalogo_academico_service()` |
| bloques de horario (guardar/eliminar/listar/conflicto/estadísticas) | `Container.horario_service()` (tras R3) |

## 2. Re-exports de dominio (crítico para imports — R2)

Los 4 archivos que hacen `from src.services.infraestructura_service import
DiaSemana | AreaConocimiento | Asignatura | Grupo | Sala` deben migrar ese import a
su **origen de dominio** (`from src.domain.models.infraestructura import ...`), no
a otro servicio. Verificar el nuevo import antes de borrar el viejo.

## 3. Procedimiento por archivo (import-safe, uno a la vez)

Para cada uno de los 17 archivos de `src/interface/` que usan la fachada:
1. Sustituir cada `infraestructura_service().X()` por `<destino>_service().X()`.
2. Migrar los imports de símbolos de dominio a `src.domain.models.infraestructura`.
3. Verificar imports de ESE archivo:
   `.venv/Scripts/python.exe -c "import importlib; importlib.import_module('<módulo.del.archivo>')"`
4. `check_imports.py --layer interface` + suite completa con `.venv` → verde.
5. `grep -n "infraestructura_service()" <archivo>` debe dar 0 antes de pasar al
   siguiente.

## 4. Consolidación de horarios (R3)

Mover los métodos de bloques de horario de `InfraestructuraService` a
`HorarioService` (dueño canónico) — solo tras re-apuntar sus consumidores. Eliminar
la copia de la infraestructura (sin dejar duplicado).

## 5. Retiro de la fachada (R4)

Cuando `grep -rn "infraestructura_service()" src/interface/` dé 0, retirar
`InfraestructuraService` (o dejar un residuo mínimo si algún método no encajó en
ningún subdominio). Retirar también `Container.infraestructura_service()` si queda
sin consumidores.

## 6. Alternativa descartada

Re-apuntar **todo de golpe** (buscar-reemplazar global). Descartado: es
precisamente el riesgo de imports que David pidió evitar; un fallo dejaría muchos
archivos rotos a la vez, difícil de aislar. Archivo por archivo con suite verde
entre cada uno es más lento pero seguro.

## 7. Opcional — partir RestriccionGeneracionService

Si se quiere cumplir el "≤25 métodos" también aquí (tiene 30), partir en
`ConfigGeneracionService` (config + duplicar) y `RestriccionService` (ventanas,
bloques anclados, franjas reunión, límites, disponibilidad). Es opcional y puede
quedar fuera de esta mejora.

## Nota de implementación (riesgo conocido)

El riesgo es un import migrado mal (símbolo movido a un módulo que no lo exporta).
Mitigación: el paso 3 importa el módulo del archivo explícitamente antes de correr
la suite; si el import falla, se revierte ese archivo y se corrige sin avanzar.
