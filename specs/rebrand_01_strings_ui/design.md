# rebrand_01_strings_ui — Diseno

## Cambios por archivo

| Archivo | Linea | Antes | Despues |
|---|---|---|---|
| `config.py` | 72 | `APP_NAME: str = "ZECI Manager"` | `APP_NAME: str = "AVEDRA"` |
| `main.py` | 2 | `main.py — Punto de entrada de ZECI Manager v2.0` | `main.py — Punto de entrada de AVEDRA v2.0` |
| `src/interface/pages/login.py` | 2 | `login.py — Pagina de inicio de sesion de ZECI Manager v2.0` | `login.py — Pagina de inicio de sesion de AVEDRA v2.0` |
| `src/interface/design/theme.py` | 2 | `theme.py — ThemeManager para ZECI Manager v2.0` | `theme.py — ThemeManager para AVEDRA v2.0` |
| `src/infrastructure/exporters/observador_pdf.py` | 556 | `"Sistema ZECI Manager"` | `"Sistema AVEDRA"` |
| `src/infrastructure/exporters/observador_excel.py` | 474 | `"Sistema ZECI Manager"` | `"Sistema AVEDRA"` |

## Riesgo

Nulo. Son cambios de string literal sin efecto en logica. Los tests de
exportadores que afirman el membrete usan datos de la institucion (ya
dinamicos desde `informes_01`), no el pie de pagina del sistema.

## Nota sobre config.py

`APP_NAME` se usa en `config.py:86` como ejemplo de URL de Postgres
(`zeci` en el path de la URL). Ese string es un ejemplo en un comentario
de ayuda, no un valor funcional; se actualiza tambien.
