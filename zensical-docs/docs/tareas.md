---
icon: lucide/check-square
---

# Tareas

Las tareas son la unidad básica de trabajo. Cada tarea pertenece a un proyecto y recibe un identificador único basado en la clave del proyecto (`TM-1`, `TM-2`…).

## Tipos de tarea

| Tipo | Uso |
|------|-----|
| **Tarea** | Unidad de trabajo genérica. |
| **Historia** | Historia de usuario con criterios de aceptación. |
| **Bug** | Defecto o comportamiento inesperado. |
| **Épica** | Agrupación de alto nivel de varias historias o tareas. |
| **Subtarea** | Tarea hija vinculada a una tarea padre. |

## Estados

Las tareas avanzan por los siguientes estados:

```
Backlog → Por hacer → En progreso → En revisión → Hecho
```

Al marcar una tarea como **Hecho** se registra automáticamente la fecha de completado, usada en los gráficos de burndown y velocidad.

## Prioridades

| Prioridad | Descripción |
|-----------|-------------|
| **Baja** | Sin urgencia. |
| **Media** | Prioridad normal. |
| **Alta** | Requiere atención próxima. |
| **Crítica** | Bloquea el trabajo del equipo. |

## Campos de una tarea

| Campo | Descripción |
|-------|-------------|
| **Título** | Nombre de la tarea (máx. 300 caracteres). |
| **Descripción** | Detalle del trabajo a realizar. |
| **Tipo** | Tarea · Historia · Bug · Épica · Subtarea |
| **Estado** | Flujo de trabajo. |
| **Prioridad** | Urgencia. |
| **Asignado a** | Miembro responsable de la tarea. |
| **Sprint** | Sprint al que pertenece (opcional). |
| **Horas estimadas** | Estimación de esfuerzo en horas. |
| **Inicio / Vencimiento** | Fechas de la tarea. Una tarea vencida se marca visualmente en el tablero. |
| **Etiquetas** | Etiquetas de categorización del proyecto. |

## Subtareas

Una tarea puede tener subtareas. Para crearlas:

1. Abre la tarea padre.
2. En la sección **Subtareas**, pulsa **Nueva subtarea**.
3. Las subtareas tienen su propio estado y asignado, pero heredan el proyecto.

!!! note
    Las subtareas no aparecen en el tablero principal — solo la tarea padre. Se gestionan desde el detalle de la tarea padre.

## Markdown

Las descripciones de tarea y los comentarios se renderizan como **Markdown** (GitHub Flavored Markdown). Se soportan:

- Negritas, cursivas, encabezados, listas, código en línea y bloques de código.
- Saltos de línea automáticos.
- El contenido se sanea con DOMPurify antes de mostrarse.

## Comentarios

Cada tarea tiene un hilo de comentarios. Los comentarios admiten Markdown y soportan borrado suave (`deleted_at`) para mantener el historial.

## Adjuntos

Puedes subir ficheros adjuntos a una tarea. Se almacenan en el directorio `attachments/` del servidor.

## Registro de horas

Desde el detalle de la tarea puedes registrar horas de trabajo:

- **Horas** — Cantidad de tiempo trabajado.
- **Nota** — Descripción opcional del trabajo realizado.
- **Fecha** — Día al que corresponde el registro (por defecto, hoy).

Las horas registradas se consolidan en la pestaña **Horas** del proyecto.

## Borrado lógico

Las tareas eliminadas no se borran permanentemente de la base de datos. Se marcan con una fecha en el campo `deleted_at` (borrado suave), lo que permite auditoría y recuperación si es necesario.

## Tablero kanban

El tablero organiza las tareas en columnas por estado. Puedes:

- **Arrastrar y soltar** tarjetas entre columnas para cambiar el estado.
- **Filtrar** por asignado, prioridad, sprint o etiqueta.
- **Crear** una tarea directamente desde la columna deseada pulsando **+ Agregar tarea**.

!!! tip "Tareas vencidas"
    Las tarjetas cuya fecha de vencimiento ha pasado se muestran con un borde de color diferente para identificarlas fácilmente.
