# rebrand_03_seed_data — Diseno

## Cambios en `src/infrastructure/db/seed.py`

### Emails de usuarios (17 ocurrencias, lineas 219-247)

Patron: `usuario@zeci.edu.co` -> `usuario@avedra.edu.co`

| Linea | Antes | Despues |
|---|---|---|
| 219 | `admin@zeci.edu.co` | `admin@avedra.edu.co` |
| 223 | `director@zeci.edu.co` | `director@avedra.edu.co` |
| 228 | `coordinador@zeci.edu.co` | `coordinador@avedra.edu.co` |
| 231-247 | `rgomez@zeci.edu.co` ... `tbeltran@zeci.edu.co` | `rgomez@avedra.edu.co` ... `tbeltran@avedra.edu.co` |

### Nombre de institucion (1 ocurrencia, linea 456)

| Linea | Antes | Despues |
|---|---|---|
| 456 | `"Institucion Educativa ZECI"` | `"Institucion Educativa Demo"` |

Se usa "Demo" en vez de "AVEDRA" porque AVEDRA es la marca del software,
no el nombre de un colegio. Una base de seed no deberia confundir al
usuario sugiriendo que el nombre de su institucion es el nombre del
producto.

## Riesgo

- **Bases nuevas:** sin impacto funcional, son datos de ejemplo.
- **Tests de integracion:** `test_institucion_repo.py:32` afirma
  `"Institucion Educativa ZECI"`. Se ajusta en Paso 4.
