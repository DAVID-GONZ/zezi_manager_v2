# rebrand_01_strings_ui — Requisitos

## Contexto

La marca del producto cambio de ZECI Manager a AVEDRA (Administracion y
Visualizacion Educativa para la Direccion y el Registro Academico). Este
paso cambia los strings que el usuario final ve: pantalla de login, barra
de titulo del navegador, y pies de pagina de documentos exportados.

## Requisitos (EARS)

**R1** — Cuando la aplicacion arranca, el titulo del navegador muestra
"AVEDRA", no "ZECI Manager".

**R2** — Cuando el usuario abre la pantalla de login, el nombre del
producto visible es "AVEDRA".

**R3** — Cuando el sistema exporta un documento PDF (observador), el pie
de pagina dice "Sistema AVEDRA", no "Sistema ZECI Manager".

**R4** — Cuando el sistema exporta un documento Excel (observador), el pie
de pagina dice "Sistema AVEDRA", no "Sistema ZECI Manager".

**R5** — Cuando `config.py` se importa, `AppConfig.APP_NAME` retorna
"AVEDRA".

**R6** — Los docstrings de `main.py`, `login.py` y `theme.py` dicen
"AVEDRA" donde antes decian "ZECI Manager".

## Fuera de alcance

- Cambios en seed data (Paso 3).
- Cambios en loggers o clases internas (Paso 2).
- Cambios en tests (Paso 4).
- El design system "Aula Serena" no cambia de nombre.
