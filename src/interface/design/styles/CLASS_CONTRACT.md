# Contrato de clases del design system

> Esta es la **API pública** del CSS core: los nombres de clase que los componentes
> (hoy Python/NiceGUI, mañana Vue) deben aplicar para heredar el estilado sin tocar
> el CSS. Si un componente Vue reproduce estos nombres, **el CSS core transfiere intacto**.
>
> Patrón general: **`.componente` (base) + `.componente--variante` o `.componente-{codigo}`**.
> Verificado por `check_design.py` (regla G: no usar clases fuera de este contrato).

## Feedback / estado

| Componente | Base | Variantes | Aplicado por |
|---|---|---|---|
| **Alert banner** | `.alert` | `.alert--error` · `.alert--warning` · `.alert--success` · `.alert--info` | login, contraseñas, estudiantes |
| **Badge genérico** | `.badge` | `.badge-{success\|warning\|error\|info\|neutral\|primary\|purple}` | `status_badge(texto, variante)` |
| **Badge asistencia** | `.badge` | `.badge-{P\|FJ\|FI\|R\|E}` | `badge_asistencia(estado)` |
| **Badge desempeño** | `.badge` | `.badge-{bajo\|basico\|alto\|superior}` | `badge_desempeno(nivel)` |
| **Badge convivencia** (cellClass única en ag-grid, autocontenido) | — | `.badge-{fortaleza\|dificultad\|compromiso\|citacion\|descargo}` | comportamiento |
| **Toast** | `.andes-toast` | `.andes-toast--{success\|error\|warning\|info}` | `toast_*()` |
| **Empty state** | `.empty-state` | `.empty-state--{search\|error\|default}` | `empty_state(variante)` |

## Tarjetas / superficies

| Componente | Base | Variantes / hijos |
|---|---|---|
| **Card** | `.andes-card` | (padding/borde/sombra estándar) |
| **Stat card** | `.stat-card-wrapper` | modificador de color: `.primary\|.success\|.warning\|.error\|.danger\|.info`; hijos: `.stat-card-label`, `.stat-card-value`, `.stat-card-subtitle`, `.stat-card-icon-wrap` |
| **Panel** | `.panel-card` | hijo: `.panel-title`, `.panel-header` |
| **Period status** | `.period-status-card` | `.period-bar-track`, `.period-bar-fill` + `.warning\|.danger` |
| **Greeting hero** | `.greeting-hero` | `.greeting-name`, `.greeting-desc`, `.greeting-meta`, `.greeting-role` |
| **Quick action** | `.quick-action-card` | `.quick-action-icon`, `.action-label`, `.action-desc` |

## Botones

| Base | Variantes | Tamaños | Aplicado por |
|---|---|---|---|
| `.btn` | `.btn-{primary\|secondary\|danger\|ghost}` | `.btn-sm` · `.btn-lg` | `boton(variante, size)` |

## Diálogos

| Componente | Base | Variantes |
|---|---|---|
| **Form dialog** | `.form-dialog-card` | `.variant-{danger\|warning\|info\|success}`; anchos `.form-dialog-card-{sm\|md\|lg\|xl}`; hijos `.form-dialog-{header\|body\|title\|subtitle\|actions}` |
| **Confirm dialog** | `.confirm-dialog-card` | `.confirm-dialog-{head\|body\|foot}` |
| **Confirmation card** | `.andes-card .confirmation-card-{danger\|warning\|info}` | hijo `.confirm-card-title` |

## Encabezado de página

`.page-header-row` › `.page-header-title` + `.page-header-sub`

## Dominio

| Familia | Clases |
|---|---|
| **Asistencia** | `.asis-badge .asis-badge-{p\|fj\|fi\|r\|e}` · `.asis-stat .asis-stat-{p\|fj\|fi\|r\|e}` |
| **Desempeño** | `.tablero-kpi-trend .up\|.down` · `.tablero-nivel-badge` |
| **Parrilla horario** | `.parrilla-area-{0..9}` (color de asignatura) · `.parrilla-swatch` |

## Utilidades semánticas (token-based, portables)

Escala de espaciado/layout como clases (evitan apilar utilidades atómicas en la vista):
`.u-mt-{xs\|sm\|md\|lg}`, `.u-mb-*`, `.u-pa-*`, `.u-stack-{xs\|sm}`, `.form-row-{inline\|center\|between\|actions}`,
`.section-title-{lg\|xl}`, `.text-{primary\|secondary\|success\|warning\|error\|info}`.

## Reglas del contrato

1. **Un componente = una clase base semántica** (describe el rol, no la apariencia).
2. **Las variantes cuelgan de la base** (`--variante` o `-codigo`); nunca copies el cuerpo
   de la base en cada variante (usa selector agrupado / herencia).
3. **Nada de estilos inline** salvo valores calculados marcados `# DYNAMIC`.
4. **Colores solo vía tokens** (`var(--…)` en CSS, `Colors.*` en Python, `tokens.ts` en Vue).
