---
icon: lucide/folder-open
---

# Proyectos

Un proyecto es el contenedor principal de trabajo dentro de una organización. Agrupa tareas, sprints, miembros y el presupuesto de horas.

## Crear un proyecto

1. Accede a **Mis proyectos** desde el menú principal.
2. Pulsa **Nuevo proyecto**.
3. Rellena los campos:

| Campo | Descripción |
|-------|-------------|
| **Nombre** | Nombre descriptivo del proyecto. |
| **Clave** | Prefijo de hasta 10 caracteres (ej. `TM`). Se usa para identificar tareas: `TM-1`, `TM-2`… |
| **Organización** | Organización a la que pertenece el proyecto. |
| **Estado** | `Planificación` · `Activo` · `En pausa` · `Completado` · `Cancelado` |
| **Prioridad** | `Baja` · `Media` · `Alta` · `Crítica` |
| **Inicio / Fin** | Fechas opcionales del proyecto. |
| **Presupuesto de horas** | Horas estimadas totales. Se contrasta con las horas registradas. |

!!! warning "Clave única"
    La clave del proyecto debe ser única dentro de la organización y no puede cambiarse una vez creado el proyecto.

## Roles de miembro

Cada usuario del proyecto tiene un rol que determina los permisos:

| Rol | Ver | Crear tareas | Editar tareas | Gestionar sprints | Editar proyecto | Añadir miembros |
|-----|:---:|:---:|:---:|:---:|:---:|:---:|
| **Viewer** | ✓ | | | | | |
| **Developer** | ✓ | ✓ | ✓ | | | |
| **Manager** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Owner** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

## Pestañas del proyecto

Desde el detalle del proyecto encontrarás:

- **Tablero** — Vista kanban con filtros por asignado, prioridad, sprint y etiqueta. Los contadores de cada filtro muestran cuántas tareas corresponden a esa opción.
- **Lista** — Tabla de todas las tareas del proyecto.
- **Sprints** — Gestión de sprints y gráficos de burndown y velocidad.
- **Horas** — Resumen de horas registradas por tarea y por miembro.
- **Miembros** — Lista de miembros y sus roles.
- **Etiquetas** — Etiquetas de color del proyecto.

El botón **Roadmap** en la barra superior abre la vista de línea de tiempo del proyecto.

## Perfiles de usuario

Desde la lista de miembros o desde el avatar de un usuario asignado en una tarea, puedes ver el perfil público de cualquier miembro del proyecto.

El perfil muestra:

- Nombre, email e imagen de perfil.
- Estado de actividad (ver más abajo).
- Proyectos compartidos.

## Estado de actividad

Cada usuario tiene un indicador de actividad calculado automáticamente:

| Estado | Condición |
|--------|-----------|
| 🟢 **En línea** | Activo en los últimos 5 minutos. |
| 🟡 **Ausente** | Última actividad entre 5 y 30 minutos. |
| ⚪ **Desconectado** | Sin actividad en los últimos 30 minutos. |

El estado se actualiza en tiempo real en el encabezado del perfil y en la lista de miembros del proyecto.

## Filtros del tablero

El tablero incluye filtros rápidos que se pueden combinar:

- **Asignado** — Filtra por miembro (o "Sin asignar"). Cada opción muestra el número de tareas asignadas.
- **Prioridad** — Filtra por nivel de prioridad con conteo de tareas.
- **Sprint** — Filtra por sprint (o tareas sin sprint).
- **Etiqueta** — Filtra por una o varias etiquetas.

Pulsa **Limpiar** para resetear todos los filtros.

## Etiquetas

Las etiquetas permiten categorizar tareas con un nombre y un color personalizado. Son específicas de cada proyecto.

Para crear una etiqueta:
1. Ve a la pestaña **Etiquetas**.
2. Introduce el nombre y elige un color.
3. Pulsa **Crear etiqueta**.
