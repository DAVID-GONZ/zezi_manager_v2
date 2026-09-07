# Tareas: datos_05_enums_y_puerta

> SCOPE — únicos archivos que pueden crearse o editarse:
> `src/domain/models/{infraestructura,convivencia,institucion,dtos,preferencia_institucion}.py`,
> `scripts/check_enums.py` (nuevo), `scripts/init.py`,
> `tests/unit/domain/test_enums_schema.py` (nuevo).
>
> **`src/infrastructure/db/schema.py` está fuera del scope y no se toca** (design D1).
> Si alguna tarea pareciera exigirlo → **PARAR y reportar al leader**: cambiar el esquema
> requiere puerta de aprobación de David.

Puerta obligatoria tras **cada** tarea:

```
.venv/Scripts/python.exe -m ruff check . --select F821,F811,F632,F702,B006,B008,B023,E9 --output-format concise
```

---

## T1 — La puerta, antes que las enumeraciones  [ ]

**Por qué primero:** escrita al final, la puerta solo confirmaría el trabajo ya hecho.
Escrita primero, empieza señalando las 5 divergencias reales y sirve de criterio de
avance para T2 y T3.

**Artefacto:** `scripts/check_enums.py` según D3: empareja por igualdad exacta del
conjunto de valores, informa columna, candidata más próxima y diferencias en cada lado,
soporta dos listas de exenciones documentadas, fuerza UTF-8 en su salida y sale con código
distinto de cero ante divergencia.

Requisitos: R6, R7, R8, R10, R11, R13, R14.

**Verificación:**
```
.venv/Scripts/python.exe scripts/check_enums.py
```

Al terminar T1 debe reportar exactamente **5 restricciones sin enumeración**
(`franjas.tipo`, `salas.tipo`, `franjas_reunion.modo`, `config_generacion.estado`,
`observaciones_periodo.origen`), **5 enumeraciones sin restricción con destino
`backend_04`** y **2 exenciones legítimas** (`TipoResultadoBusqueda`, `FormatoInforme`).
Si el recuento no sale, el emparejamiento está mal y no se sigue.

---

## T2 — Las 5 enumeraciones que faltan  [ ]

**Artefacto:** `TipoFranja`, `TipoSala`, `ModoFranjaReunion` y `EstadoConfigGeneracion` en
`infraestructura.py`; `OrigenObservacion` en `convivencia.py`. Los campos correspondientes
pasan a estar tipados por su enumeración, conservando exactamente el mismo valor por
omisión.

Requisitos: R1, R2, R3, R4, R15.

`StrEnum`, no `Enum` (D2): garantiza que el valor almacenado no cambia y que los
repositorios no necesitan conversión.

**Verificación:**
```
.venv/Scripts/python.exe scripts/check_enums.py
.venv/Scripts/python.exe -m pytest -q -m "not slow and not integration and not e2e and not browser"
```
La puerta debe bajar de 5 restricciones sin enumeración a **0**.

Comprobar además R2 y R15:
```
.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'.'); from src.domain.models.infraestructura import Sala; s=Sala.model_validate({'nombre':'A','tipo':'aula'}); print(repr(s.tipo), s.tipo=='aula')"
```
Debe imprimir el miembro y `True`: el valor textual no cambia.

---

## T3 — Hidratación de los valores existentes  [ ]

**Artefacto:** tests que construyan cada uno de los 5 modelos afectados a partir de todos
los valores que la base admite hoy para ese campo, comprobando que ninguno falla (R16).

**Verificación:**
```
.venv/Scripts/python.exe -m pytest tests/unit/domain/test_enums_schema.py -q
.venv/Scripts/python.exe -m pytest -q -m "integration or slow"
```

**Línea base obligatoria:** ejecutar el segundo comando **antes** de la tarea y anotar el
recuento. Hay 30 fallos preexistentes por firmas de `tenant_02`/`tenant_03`, ajenos a este
paso; el criterio es **no aumentarlo** (`CLAUDE.md`).

Verificar en particular que un valor ajeno al conjunto **se rechaza** (R2, R3), y que el
rechazo identifica campo y valor.

---

## T4 — Test de alineación en la suite  [ ]

**Artefacto:** `tests/unit/domain/test_enums_schema.py` verifica los 30 pares alineados
desde la suite, de modo que la protección exista aunque la puerta no se ejecute.

Requisitos: R5, R9.

**Verificación:**
```
.venv/Scripts/python.exe -m pytest tests/unit/domain/test_enums_schema.py -q
```

Comprobar que **detecta** una divergencia: alterar temporalmente un miembro de una
enumeración, ver el test en rojo, revertir. Un test que no se ha visto fallar no prueba
nada.

---

## T5 — Encadenar la puerta en `init.py`  [ ]

**Artefacto:** `scripts/init.py` ejecuta `check_enums.py` junto a las demás puertas, antes
de los tests, y aborta si falla.

Requisitos: R9, R11, R12.

**Verificación:**
```
.venv/Scripts/python.exe scripts/init.py
```
TODO VERDE, y el bloque de la comprobación visible en la salida.

Medir R12: el tiempo total no debe crecer de forma apreciable frente a los ~18 s previos.
Comprobar también que una divergencia **detiene** la puerta: introducir una a propósito,
ver `init.py` en rojo, revertir.

---

## T6 — Cierre  [ ]

**Artefacto:** `progress/impl_datos_05.md` con las enumeraciones añadidas, el contenido
final de las dos listas de exenciones y la deuda de los 5 `CHECK` que faltan, con su
destino explícito en `backend_04_metadata_schema`.

**Verificación:**
```
.venv/Scripts/python.exe scripts/init.py
```
TODO VERDE. Sin esto el paso no se declara `done` (`CLAUDE.md`).
