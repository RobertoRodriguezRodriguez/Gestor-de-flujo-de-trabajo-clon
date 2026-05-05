---
icon: lucide/zap
---

# Sprints

Los sprints permiten organizar el trabajo en iteraciones con fecha de inicio y fin. E-asy proporciona gráficos de burndown por sprint y un gráfico de velocidad del equipo.

## Estados de un sprint

| Estado | Descripción |
|--------|-------------|
| **Planificado** | El sprint está definido pero aún no ha empezado. |
| **Activo** | El sprint está en curso. Solo puede haber uno activo a la vez. |
| **Completado** | El sprint ha finalizado. |

## Crear un sprint

1. Ve a la pestaña **Sprints** del proyecto.
2. Rellena el formulario **Nuevo Sprint**:
   - **Nombre** — Ej. `Sprint 1`, `Semana 18`.
   - **Estado** — Estado inicial.
   - **Inicio / Fin** — Fechas y hora del sprint.
   - **Objetivo** — Descripción del objetivo de la iteración (opcional).
3. Pulsa **Crear Sprint**.

!!! note "Permisos"
    Solo los miembros con rol **Manager** u **Owner** pueden crear y editar sprints.

## Asignar tareas a un sprint

Desde el detalle de una tarea, selecciona el sprint en el campo **Sprint**. También puedes asignar desde el filtro de sprint en el tablero.

## Gráfico de Burndown

El burndown muestra el trabajo restante a lo largo de los días del sprint.

- **Línea ideal** (discontinua) — Progreso esperado si el trabajo se distribuye uniformemente.
- **Línea real** (sólida) — Tareas pendientes por día según las fechas de completado reales.
- **Indicador de ritmo** — Compara el progreso real con el ideal:

| Ritmo | Significado |
|-------|-------------|
| ✅ Por delante | Hay menos trabajo pendiente del esperado. |
| 🟡 Al día | El progreso sigue la línea ideal. |
| 🔴 Con retraso | Hay más trabajo pendiente del esperado. |
| ✓ Completado | El sprint finalizó. |

!!! info "Requisitos del burndown"
    El gráfico requiere que el sprint tenga fechas de inicio y fin y al menos una tarea. Las fechas de completado de las tareas se usan para trazar la línea real.

## Gráfico de Velocidad

El gráfico de velocidad muestra el rendimiento del equipo en los últimos sprints completados o activos (máximo 8).

- **Barras sólidas** — Sprints completados.
- **Barras semitransparentes** — Sprint activo en curso.
- **Línea de promedio** (discontinua) — Media de tareas/horas completadas.

Puedes alternar entre ver el eje en **Tareas** o **Horas estimadas** con el selector superior.

!!! tip
    El gráfico de horas solo aparece si algún sprint tiene horas estimadas registradas en sus tareas.
