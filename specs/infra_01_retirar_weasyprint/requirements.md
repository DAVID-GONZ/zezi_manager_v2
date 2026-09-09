# infra_01_retirar_weasyprint — Requisitos

## Contexto

El motor de PDF de ZECI es `reportlab`: Python puro, sin librerías nativas.
La cadena de exportación no depende de GTK/Pango ni de ningún binario del
sistema operativo, de modo que el mismo entorno virtual funciona en Windows,
Linux y contenedor sin pasos de instalación fuera de `pip`.

## Requisitos (EARS)

**R1** — Cuando el contenedor solicita el servicio de exportación, el sistema
retorna un exportador cuyo motor de PDF es `reportlab`, siempre que `reportlab`
y `openpyxl` estén instalados.

**R2** — Cuando `reportlab` no está instalado pero `openpyxl` sí, el sistema
retorna un exportador con Excel y CSV, y registra una advertencia que nombra
`reportlab` como la dependencia que habilita PDF.

**R3** — Cuando ni `reportlab` ni `openpyxl` están instalados, el sistema
retorna un exportador que solo produce CSV, y registra una advertencia que
nombra `openpyxl` y `reportlab`.

**R4** — Mientras el sistema arranca, la salida estándar no contiene
advertencias sobre librerías externas de renderizado ausentes.

**R5** — Cuando el exportador recibe HTML y no puede producir un PDF, el
sistema lanza `NotImplementedError` con un mensaje que nombra únicamente
motores instalables sin dependencias nativas.

**R6** — Cuando una página de informes no logra exportar a PDF, el sistema
muestra al usuario un aviso que nombra `reportlab` como la dependencia
faltante.

**R7** — El nombre de la clase exportadora, su docstring y el docstring del
puerto `IExporterService` nombran el motor que el sistema usa realmente.

**R8** — El archivo de dependencias declara exactamente los paquetes que el
sistema importa; no declara paquetes de renderizado que ningún módulo importa.

**R9** — Mientras la suite de tests se ejecuta, los tests del exportador
verifican el comportamiento descrito en R1–R5 llamando al código real de
`crear_exporter()` y del exportador, sin duplicar su lógica.

## Fuera de alcance

- Cambiar la fidelidad visual de los PDF existentes: `reportlab` ya es el motor
  efectivo en el entorno actual, de modo que la salida no cambia.
- Renombrar el archivo `pdf_exporter.py`, cuyo nombre ya es agnóstico del motor.
- Tocar `container.py`: su llamada a `crear_exporter()` no cambia de firma.
