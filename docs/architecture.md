# Arquitectura — ZECI Manager v2.0

> Esta es la referencia arquitectónica para todos los agentes.
> Documentos detallados en los archivos del proyecto (ver §1).

---

## 1. Documentos de referencia (leer antes de implementar)

| Documento | Contenido |
|---|---|
| `ESTADO_ACTUAL_v2.md` | Inventario completo de capas, componentes implementados, inconsistencias pendientes |
| `DISEÑO_ARQUITECTURA_v2.md` | Principio de dependencias, patrones por capa, Container, design system |
| `03_HOJA_DE_RUTA_MIGRACION.md` | Los 10 pasos, criterios de done, riesgos, restricciones para el agente |

---

## 2. Regla de dependencias (no negociable)

```
interface → services → domain ← infrastructure
                                      ↑
                                 container.py
```

El dominio no importa nada externo. La infraestructura implementa los contratos del dominio. Los servicios orquestan sin saber de SQL ni de NiceGUI. La interfaz consume servicios, nunca repositorios.

**Una violación de esta regla es un bug, no una decisión de diseño.**

---

## 3. Principio de migración: reorganizar, no reescribir

Cada función SQL, cada cálculo de negocio, cada componente UI ya existe en v1.0. La tarea es:

| Operación | Cuándo aplicarla |
|---|---|
| **MOVER** | El código existe en `pages/` o `modules/` — cortarlo y pegarlo en el lugar correcto sin cambiar la lógica. |
| **ENVOLVER** | Existe un componente legacy (auth.py, state.py) — crear una clase que implementa la interfaz y delega. |
| **SUSTITUIR** | Hay un `dict` o `DataFrame` en una firma — reemplazarlo por la entidad Pydantic correspondiente. |
| **CREAR** | El código genuinamente no existe (interfaces ABC, container, FakeRepository). |

Si el agente está "reescribiendo" lógica, se equivocó de operación.

---

## 4. El Container es el único punto de instanciación

Ningún módulo fuera de `container.py` crea instancias de repositorios o servicios. El patrón en páginas:

```python
from container import Container

svc = Container.estudiante_service()   # ✅
repo = SqliteEstudianteRepository()    # ❌ nunca en páginas
```

---

## 5. Pandas vive solo en infraestructura

`fetch_df` retorna un DataFrame. El repositorio lo mapea a entidades Pydantic y lo devuelve. Los servicios y las páginas nunca ven DataFrames ni `groupby`.

Los cálculos de métricas agregadas (dashboard, promedios por grupo) van como `GROUP BY` en SQL dentro del repositorio, no como `groupby`/`iterrows` en Python.

---

## 6. Auditoría transversal

Todo método mutador de servicio termina con `_auditar()`. La auditoría no contamina la lógica de negocio. Ver `docs/conventions.md` §4 para la firma exacta.

---

## 7. Design system — convención de color

En la capa de interfaz, los colores viven en `styles.css` como variables CSS y clases, no en Python. La única excepción son los gráficos ECharts, que usan un bloque `_EC_*` al inicio del módulo derivado de `tokens.py`.

Ver `DISEÑO_ARQUITECTURA_v2.md` §7.1 para la tabla completa.
