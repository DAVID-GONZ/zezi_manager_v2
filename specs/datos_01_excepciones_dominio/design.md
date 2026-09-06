# Diseño: Jerarquía de excepciones de dominio (datos_01_excepciones_dominio)

> Prerrequisito declarado de `backend_12_endpoints_crud`
> (`roadmaps/backend_00_roadmap_sqlalchemy_api/roadmap.md`). Origen del problema:
> `progress/auditoria_datos_orm_api.md` §3.

---

## 0. Inventario verificado (medido, no estimado)

Conteo por AST sobre `src/services/*.py` con el intérprete del proyecto:

| Tipo señalado hoy | Sitios | Archivos |
|---|---|---|
| `raise ValueError` | **145** | 23 servicios |
| `raise RuntimeError` | **11** | `convivencia_service.py` (7), `evaluacion_service.py` (4) |
| **Total a tipar** | **156** | 23 servicios |

Consumidores que dependen hoy de esos tipos:

| Patrón | Sitios | Dónde |
|---|---|---|
| `except ValueError` | **92** | `src/interface/` (páginas y presenters) |
| `except (ValueError, RuntimeError)` | 9 | `src/interface/pages/admin/configuracion_sie.py` |
| `except PermissionError` | 7 | `src/interface/pages/` (convivencia, mi_cuenta) |

**Estos 92 + 9 sitios están FUERA del alcance de este paso.** Es la restricción que
determina la forma de la jerarquía (§2.2): si las nuevas excepciones dejaran de ser
capturables como `ValueError`, los 92 manejadores dejarían de coincidir en silencio y
todos los mensajes de negocio degradarían al `except Exception` genérico
(«Error inesperado. Intenta de nuevo.»). Sería una regresión funcional invisible para
los tests unitarios y visible para el usuario en cada formulario del sistema.

---

## 1. Archivos a crear y modificar

| Archivo | Responsabilidad |
|---|---|
| `src/domain/exceptions.py` | **NUEVO.** Raíz `ZeciError`, las 5 familias, el vocabulario cerrado `CodigoError`, la enumeración `CategoriaError` y las dos excepciones de permiso ya vigentes. Solo stdlib. |
| `src/services/solo_lectura.py` | `OperacionSoloLecturaError` pasa a importarse del dominio y se re-exporta; el resto del módulo no cambia. |
| `src/services/contexto_tenant.py` | `OperacionFueraDeInstitucionError` pasa a importarse del dominio y se re-exporta; el resto del módulo no cambia. |
| 23 servicios de `src/services/` | Sustitución de los 156 `raise` genéricos por la familia y el código correspondientes. |
| `tests/unit/domain/test_exceptions.py` | **NUEVO.** Invariantes de la jerarquía + guarda estructural sobre `src/services/`. |

`src/domain/exceptions.py` **no importa nada fuera de la stdlib** (`enum`, `typing`).
Cumple la regla de dependencias de `docs/architecture.md` §1: `services → domain`, y
los dos mecanismos neutrales pueden importar del dominio sin invertir ninguna flecha.

---

## 2. La jerarquía exacta

### 2.1 Raíz

```python
class ZeciError(Exception):
    """Raíz de toda condición de error originada en las reglas del negocio."""

    codigo: ClassVar[CodigoError]        # default de la familia
    categoria: ClassVar[CategoriaError]  # familia semántica, sin HTTP

    def __init__(
        self,
        mensaje: str,
        *,
        codigo: CodigoError | None = None,
        detalles: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(mensaje)        # UN solo argumento posicional — ver §6.1
        self.mensaje = mensaje
        self.codigo = codigo or type(self).codigo
        self.detalles: dict[str, object] = dict(detalles or {})

    def to_dict(self) -> dict[str, object]:
        return {
            "codigo": str(self.codigo),
            "mensaje": self.mensaje,
            "detalles": self.detalles,
        }
```

- **R2/R3/R4**: `codigo` es siempre un miembro de `CodigoError` (`StrEnum`). Pasar un
  literal fuera del vocabulario falla al construir el miembro de la enumeración, así
  que el vocabulario cerrado se cumple por construcción y la unicidad la garantiza la
  propia enumeración.
- **R6**: `codigo`, `mensaje` y `detalles` son tres atributos distintos; `to_dict()`
  es el payload que `backend_12` serializará sin tocar el dominio.
- **R5**: `str(exc)` sigue devolviendo el mensaje en español —los 92 manejadores de la
  interfaz que hacen `ui.notify(str(exc))` no cambian de comportamiento— pero ese
  texto deja de ser el contrato.

### 2.2 Las cinco familias

```python
class ReglaDeNegocioError(ZeciError, ValueError): ...
class NoEncontradoError(ZeciError, ValueError): ...
class ConflictoError(ZeciError, ValueError): ...
class PermisoDenegadoError(ZeciError, PermissionError): ...
class DependenciaNoDisponibleError(ZeciError, RuntimeError): ...
```

**La raíz `ZeciError` hereda de `Exception`, NO de `ValueError`.** La compatibilidad se
inyecta familia por familia, y esto es deliberado:

- Las tres familias que hoy se señalan con `ValueError` lo siguen siendo → los 92
  `except ValueError` de la interfaz siguen coincidiendo (**R17**).
- `PermisoDenegadoError` es `PermissionError` y **no** `ValueError` → conserva la
  semántica actual de los dos errores de permiso (**R16**) sin contaminar la rama de
  permisos con la de validación. Si la raíz heredara de `ValueError`, un
  `except ValueError` colocado antes de un `except PermissionError` capturaría los
  rechazos de solo lectura y de tenant ajeno, cambiando qué mensaje ve el usuario.
- `DependenciaNoDisponibleError` es `RuntimeError` → los 9
  `except (ValueError, RuntimeError)` de `configuracion_sie.py` siguen coincidiendo.

La herencia doble es un **puente transitorio y documentado**: cuando `backend_12`
introduzca un manejador único de `ZeciError` y la interfaz pase a capturar
`ZeciError`, los mixins `ValueError`/`RuntimeError` se retiran en un paso posterior.
El docstring del módulo debe decirlo con esas palabras, para que nadie los interprete
como parte del diseño final.

### 2.3 Subtipos de permiso ya vigentes

```python
class OperacionSoloLecturaError(PermisoDenegadoError):
    codigo = CodigoError.SOLO_LECTURA

class OperacionFueraDeInstitucionError(PermisoDenegadoError):
    codigo = CodigoError.FUERA_DE_INSTITUCION
```

Ambas se **definen en el dominio** y los dos módulos de servicios las **re-exportan**:

```python
# src/services/solo_lectura.py
from src.domain.exceptions import OperacionSoloLecturaError   # re-export

__all__ = ["OperacionSoloLecturaError", ...]                  # sin cambios
```

Consecuencias, todas deseadas:

- Es **la misma clase**, no una copia: `isinstance` y `pytest.raises` siguen
  funcionando desde cualquiera de las dos rutas de import. Los usos de
  `tests/unit/services/test_aislamiento_objeto_paso36.py` (12 sitios) y los imports
  desde `src/interface/` no se tocan.
- Siguen siendo `PermissionError` por herencia vía `PermisoDenegadoError`, así que los
  7 `except PermissionError` de las páginas mantienen su comportamiento (**R16**).
- Ganan `codigo`, `categoria` y `detalles` sin que su mensaje por defecto cambie: el
  `__init__` de `OperacionSoloLecturaError` conserva su mensaje actual palabra por
  palabra («Sesión en modo solo lectura (Ver como): no se permiten cambios.»).
- `verificar_escritura()` y `verificar_pertenencia()` **no cambian de cuerpo**.
  `verificar_pertenencia()` sí gana `detalles={"institucion_esperada": scope}`; el
  `institucion_id` del objeto ajeno **no** se incluye (**R12**: no revelar el recurso).

---

## 3. Vocabulario de códigos y categorías

### 3.1 `CategoriaError` — familia semántica, sin transporte

```python
class CategoriaError(StrEnum):
    VALIDACION    = "validacion"     # ReglaDeNegocioError
    NO_ENCONTRADO = "no_encontrado"  # NoEncontradoError
    CONFLICTO     = "conflicto"      # ConflictoError
    PERMISO       = "permiso"        # PermisoDenegadoError
    DEPENDENCIA   = "dependencia"    # DependenciaNoDisponibleError
```

Nombres semánticos, nunca números. **El dominio no conoce HTTP** (**R19**).

### 3.2 La correspondencia con HTTP vive fuera y no se escribe en este paso

`backend_12_endpoints_crud` declarará en la capa API una tabla de una sola línea por
familia:

| `CategoriaError` | Estado HTTP futuro |
|---|---|
| `VALIDACION` | 422 Unprocessable Entity |
| `NO_ENCONTRADO` | 404 Not Found |
| `CONFLICTO` | 409 Conflict |
| `PERMISO` | 403 Forbidden |
| `DEPENDENCIA` | 503 Service Unavailable |

Esta tabla es **documentación de intención**, no un artefacto de este paso. El
implementer **no** debe crear ningún módulo de mapeo HTTP: el punto entero del diseño
es que la API traduzca 5 categorías, no 156 mensajes.

### 3.3 `CodigoError` — vocabulario cerrado

`StrEnum` con dos niveles:

1. **Un default por familia**, siempre presente:
   `REGLA_NEGOCIO`, `NO_ENCONTRADO`, `CONFLICTO`, `PERMISO_DENEGADO`,
   `DEPENDENCIA_NO_DISPONIBLE`.
2. **Códigos específicos** solo donde un consumidor necesita distinguir la causa
   concreta. Ya identificados como necesarios:
   `SOLO_LECTURA`, `FUERA_DE_INSTITUCION`, `DOCUMENTO_DUPLICADO`,
   `USUARIO_DUPLICADO`, `PERIODO_CERRADO`, `ACTIVIDAD_CERRADA`,
   `PESOS_EXCEDEN_TOTAL`, `NOTA_FUERA_DE_ESCALA`, `SOLAPE_HORARIO`,
   `CARGA_DOCENTE_EXCEDIDA`, `ROL_NO_AUTORIZADO`, `PASSWORD_INCORRECTA`,
   `AUTENTICACION_NO_CONFIGURADA`, `REPOSITORIO_NO_DISPONIBLE`,
   `EXPORTADOR_NO_DISPONIBLE`.

**Regla de crecimiento:** el implementer añade un código específico solo si algún
consumidor —la UI hoy o un endpoint mañana— tiene que ramificar por esa causa. En
duda, usa el default de la familia. El objetivo es un vocabulario del orden de 25–30
miembros, no de 156.

---

## 4. Criterio de clasificación de los 156 sitios

### 4.1 Árbol de decisión (se aplica en este orden, primera coincidencia gana)

1. **¿Falta una dependencia del servicio, no un dato del usuario?** (repositorio,
   exportador o proveedor no inyectado) → `DependenciaNoDisponibleError`.
   Señal: el mensaje habla del propio servicio, no de la entidad
   («SIEERepository no disponible», «no tiene exporter inyectado»). El usuario no
   puede hacer nada para corregirlo.
2. **¿El actor carece de autorización?** → `PermisoDenegadoError`.
   Señal: «no tiene permiso», «no puede gestionar», rol insuficiente.
3. **¿Se pide una entidad por identificador y el repositorio devuelve nada?** →
   `NoEncontradoError`, con `detalles={"recurso": "<tabla>", "id": <valor>}`.
   Señal: «no existe», «no encontrado», «no hay ningún … para».
4. **¿La operación choca contra algo que ya existe o contra el estado actual de la
   entidad?** → `ConflictoError`.
   Señal: «ya existe», «ya está», «ya pertenece», «ya ocupada», «está cerrado»,
   «está desactivado». La entrada es válida; lo que impide la operación es el estado
   del sistema, y repetir la petición sin cambiar nada volvería a fallar igual.
5. **En cualquier otro caso** → `ReglaDeNegocioError`.
   Rangos, escalas, sumas de pesos, formatos, coherencias entre campos, límites.
   Corregir el dato de entrada haría que la operación tuviera éxito.

### 4.2 Discriminante fino entre 4 y 5 (la única frontera que se presta a error)

> **¿Cambiando *el dato que envío* la operación pasaría?**
> Sí → regla de negocio (5). No, hay que cambiar *el estado del sistema* → conflicto (4).

Casos reales de este repositorio que caen del lado no obvio:

| Mensaje | Familia | Por qué |
|---|---|---|
| «La materia ya tiene {n} bloque(s) asignado(s); límite: {max}.» | **Regla de negocio** | Contiene «ya tiene» pero es un límite del plan; el «ya» es un contador, no un duplicado. |
| «El estudiante ya pertenece a ese grupo; no hay traslado que registrar.» | **Conflicto** | El estado actual hace la operación vacía. |
| «El periodo con id {id} está cerrado.» | **Conflicto** | Estado de la entidad, no dato de entrada. |
| «La sala ya está ocupada en ese horario.» | **Conflicto** | Colisión con un registro existente. |
| «El docente superaría su carga máxima de {n} bloques/semana.» | **Regla de negocio** | Umbral configurable evaluado sobre la petición. |
| «El servicio de autenticación no está configurado.» | **Dependencia** | Hoy es un `ValueError`; la regla 1 gana sobre la 5. |

### 4.3 Reparto esperado tras aplicar el árbol

Clasificación automática preliminar por palabras clave, ejecutada sobre los 156
sitios. **No es autoritativa** —§4.2 muestra al menos tres casos que la heurística
coloca mal— pero sirve al implementer como inventario de partida y al reviewer como
orden de magnitud:

| Familia | Sitios (aprox.) |
|---|---|
| `ReglaDeNegocioError` | ~58 |
| `NoEncontradoError` | ~51 |
| `ConflictoError` | ~30 |
| `DependenciaNoDisponibleError` | 11 + 2 (los dos `ValueError` de autenticación) |
| `PermisoDenegadoError` | ~4 |

Una desviación de ±10 respecto a esta tabla es normal y no es un defecto. Una
desviación que deje `PermisoDenegadoError` en 0 o `NoEncontradoError` por debajo de 30
indica que el árbol no se aplicó.

### 4.4 Qué NO se toca

- Los `raise ValueError` dentro de `@field_validator`/`@model_validator` de
  `src/domain/models/`. Pydantic los captura y los convierte en `ValidationError`;
  cambiarlos por `ZeciError` rompería la validación. **Fuera de alcance.**
- Los `raise ValueError` de `src/infrastructure/`. Los errores de infraestructura son
  otro problema, con dueño propio (`backend_06_queries_sqlalchemy`, §1.3 de la
  auditoría).
- Los `except (ValueError, TypeError)` internos de los propios servicios que envuelven
  conversiones (`int(...)`, `datetime.fromisoformat(...)`): siguen capturando errores
  del lenguaje, no de dominio, y no se modifican. Atención en
  `horario_service.py` (3 sitios) y en `convivencia_service.py:1773`
  (`except RuntimeError`): si el `raise` que capturan pasa a una familia nueva, la
  cláusula `except` debe seguir cubriéndolo —lo hace, por la herencia del puente— pero
  el implementer debe verificarlo explícitamente en esos 4 sitios.
- **Ningún mensaje en español cambia de redacción en este paso.** El texto se traslada
  literalmente al nuevo tipo. Así, cualquier diferencia en un test existente delata un
  error de sustitución y no un cambio de copy (**R20**).

---

## 5. Alternativa de diseño descartada

**Alternativa considerada:** jerarquía «limpia» sin herencia múltiple —
`ZeciError(Exception)` y las cinco familias heredando solo de `ZeciError` — y
actualizar en el mismo paso los 92 `except ValueError` y los 9
`except (ValueError, RuntimeError)` de `src/interface/` para que capturen `ZeciError`.

**Por qué se descarta:**

1. **Sale del alcance aprobado.** El SCOPE del paso son `src/domain/exceptions.py`,
   los 23 servicios, los 2 mecanismos neutrales y un test. Tocar 30 páginas y varios
   presenters convertiría un paso mecánico y revisable en un paso que atraviesa toda
   la capa de interfaz.
2. **El modo de fallo es silencioso.** Un `except ValueError` olvidado no produce
   ningún error de importación, ningún fallo de ruff ni ningún test rojo: produce que
   un mensaje de negocio («Ya existe un estudiante con ese documento») se convierta en
   «Error inesperado. Intenta de nuevo.» en la pantalla del usuario. Con 101 sitios,
   la probabilidad de olvidar alguno es alta y la de detectarlo en revisión, baja.
3. **El beneficio es nulo hoy.** La herencia doble no impide nada que la API vaya a
   necesitar: `backend_12` ramifica por `categoria`/`codigo`, no por la posición en el
   árbol de tipos. Retirar los mixins más adelante es un cambio de una línea por
   familia, y para entonces la interfaz ya capturará `ZeciError`.

**Coste aceptado de la opción elegida:** durante la transición, un
`except ValueError` genérico en la interfaz sigue capturando errores de dominio junto
a los errores de conversión del lenguaje. Es exactamente la situación actual, ni mejor
ni peor, y termina cuando la interfaz migre a `ZeciError`.

---

## 6. Consideraciones de implementación (riesgos conocidos)

### 6.1 `PermisoDenegadoError` hereda de `PermissionError`, que es un `OSError`

`PermissionError` desciende de `OSError`, y `OSError` reinterpreta sus argumentos
posicionales como `(errno, strerror)` cuando recibe dos o más:

```python
OSError("a", "b").errno      # 'a'  — args reinterpretados
```

`ZeciError.__init__` debe llamar a `super().__init__(mensaje)` con **exactamente un
argumento posicional**; el código y los detalles viajan como *keyword-only* y como
atributos de instancia. Un test debe fijar esto: `exc.args == (mensaje,)` y
`str(exc) == mensaje` para `OperacionSoloLecturaError`.

El MRO de `PermisoDenegadoError(ZeciError, PermissionError)` es válido y linealiza
como `PermisoDenegadoError → ZeciError → PermissionError → OSError → Exception`. Un
test debe afirmarlo explícitamente para que un reordenamiento futuro de las bases
falle en rojo.

### 6.2 El re-export debe preservar la identidad de clase

Prohibido redefinir `OperacionSoloLecturaError` en `solo_lectura.py` heredando de la
del dominio: crearía **dos clases distintas** y un `pytest.raises` que importe la del
dominio no capturaría la que lanza el servicio. Solo
`from src.domain.exceptions import ...` y mantener el nombre en `__all__`.

### 6.3 La guarda estructural vive en el test de dominio

El SCOPE solo autoriza `tests/unit/domain/test_exceptions.py`, así que la guarda que
verifica «ningún `raise ValueError`/`RuntimeError` queda en `src/services/`» se
implementa ahí, recorriendo `src/services/*.py` con `ast`. Es una ubicación anómala
—un test de dominio que inspecciona servicios— y debe llevar un comentario que lo
explique, para que un paso futuro pueda promoverla a `scripts/init.py`, que es su
sitio natural junto a la puerta de ruff.

### 6.4 Puerta de ruff

`F821` es bloqueante en `scripts/init.py`. Una sustitución que olvide importar la
familia usada en un servicio se detecta ahí, no en los tests: la puerta debe correrse
después de **cada** servicio sustituido, no solo al final. Precedente registrado en
`CLAUDE.md`: un `F821` en `estudiantes.py` escribía en la base y reventaba después.

### 6.5 Auditoría y solo lectura no se ven afectados

Ningún `raise` sustituido está dentro de un bloque que decida si se audita o no; la
sustitución no altera flujo de control, solo el tipo señalado. Si el implementer
necesita reordenar código para sustituir un `raise`, es señal de que ese sitio
requiere análisis aparte: debe anotarlo en `progress/impl_datos_01.md` en lugar de
improvisar (regla de fixes quirúrgicos, `docs/conventions.md` §7).
