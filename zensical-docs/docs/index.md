---
icon: lucide/layout-dashboard
---

# E-asy — Gestor de flujo de trabajo

El Gestor de Flujo de Trabajo es una plataforma de gestión de proyectos y tareas diseñada para equipos de desarrollo. Combina un tablero kanban, gestión de sprints, seguimiento de horas y analítica en una sola herramienta.

## Funcionalidades principales

<div class="grid cards" markdown>

- :material-folder-open: **Proyectos**

    Organiza el trabajo en proyectos dentro de organizaciones. Cada proyecto tiene su propio tablero, lista de miembros, sprints y presupuesto de horas.

- :material-checkbox-marked-circle: **Tareas**

    Crea tareas de tipo *tarea*, *historia*, *bug*, *épica* o *subtarea*. Asígnalas a miembros, establece prioridades y fechas de vencimiento.

- :material-lightning-bolt: **Sprints**

    Planifica iteraciones con fechas de inicio y fin. Visualiza el progreso con el gráfico de burndown y mide la velocidad del equipo sprint a sprint.

- :material-clock-outline: **Horas**

    Registra horas por tarea. Define un presupuesto por proyecto y supervisa el consumo en tiempo real.

- :material-chart-bar: **Analítica**

    Gráficos de velocidad, burndown y distribución de tareas por estado y asignado, directamente en el panel del proyecto.

- :material-api: **API REST**

    API con autenticación JWT para integrar E-asy con herramientas externas.

</div>

## Estructura general

```
Organización
└── Proyecto  (clave: "TM")
    ├── Miembros  (owner · manager · developer · viewer)
    ├── Sprints   (planificado · activo · completado)
    ├── Tareas    (TM-1, TM-2 …)
    │   ├── Subtareas
    │   ├── Comentarios
    │   ├── Adjuntos
    │   └── Registro de horas
    └── Etiquetas
```

## Tecnología

| Capa | Tecnología |
|------|-----------|
| Backend | Django 5.0.4 + PostgreSQL |
| Autenticación | JWT (SimpleJWT) + OTP (2FA) |
| API | Django REST Framework |
| Ficheros estáticos | WhiteNoise |
| Exportación | openpyxl (Excel) |
