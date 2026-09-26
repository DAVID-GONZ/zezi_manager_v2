# Requisitos: Normalizar plan_mejoramiento (backend_02c_normalizar_plan_mejoramiento)

> Ámbito: llevar `sqlite_plan_mejoramiento_repo.py` al mismo patrón
> `conn=None` del resto de repositorios. Resuelve D7 de la auditoría.

---

## Inyección de conexión

R1: EL repositorio DEBE aceptar una conexión inyectada en su constructor
    (`__init__(self, conn=None)`), siguiendo el patrón de los otros 19
    repositorios.

R2: CUANDO no se inyecta conexión, EL repositorio DEBE usar
    `get_connection()` del módulo `connection.py`, no abrir su propia
    `sqlite3.connect()`.

R3: EL repositorio NO DEBE importar `sqlite3` directamente ni definir
    su propia función `_get_conn()` ni `_db_path()`.

---

## Configuración de conexión

R4: TODA conexión que use el repositorio DEBE tener `check_same_thread=False`
    (NiceGUI usa múltiples hilos) y WAL habilitado — lo que `get_connection()`
    ya garantiza.

R5: EL repositorio DEBE usar `sqlite3.Row` como `row_factory`, consistente
    con el resto.

---

## Tests de integración

R6: NINGÚN test de integración de plan_mejoramiento DEBE tocar
    `data/app.db` (la base de desarrollo real).

R7: LOS tests DEBEN usar la BD en memoria provista por las fixtures de
    conftest (`db_conn`, `db_seed`).

R8: LOS tests DEBEN seguir produciendo el mismo resultado funcional
    que antes.

---

## Preservación

R9: LA interfaz pública del repositorio (métodos del puerto
    `IPlanMejoramientoRepository`) NO DEBE cambiar.

R10: EL comportamiento transaccional DEBE conservarse: commit tras
     escritura exitosa, rollback en error.
