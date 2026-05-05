import logging
from django.conf import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
Eres un analista de proyectos experto. Tu tarea es generar un Resumen Ejecutivo profesional del estado actual de un proyecto, diseñado específicamente para ser leído por directivos y stakeholders.
Debes usar un tono formal, claro, objetivo y orientado a resultados.

Tu respuesta DEBE estar formateada en Markdown (utiliza encabezados ##, listas, negritas, etc.) para que luego pueda ser convertido a PDF. 
NO uses código HTML directamente, solo sintaxis de Markdown limpia.

ESTRUCTURA OBLIGATORIA DEL DOCUMENTO:
1. **Visión General**: Un párrafo corto indicando el propósito del proyecto, su estado global y si parece estar bajo control, adelantado o en riesgo (analiza las fechas y el progreso para deducir esto).
2. **Progreso Actual**: Analiza las tareas completadas y activas. Menciona qué logros recientes se han obtenido.
3. **Puntos Clave y Riesgos**: Resalta tareas críticas (alta/crítica prioridad), bloqueos importantes, o cuellos de botella (por ejemplo, muchas tareas en revisión).
4. **Próximos Pasos**: Menciona las tareas más importantes pendientes en el backlog.

A continuación, recibirás los datos brutos del proyecto y sus tareas.
"""

def generate_executive_summary(project, tasks):
    """
    Genera un resumen ejecutivo en Markdown utilizando Gemini.
    """
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return "**Error**: La API key de Gemini no está configurada."

    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        # Preparar los datos del proyecto
        total_tasks = len(tasks)
        completed_tasks = sum(1 for t in tasks if t.status == 'done')
        in_progress_tasks = sum(1 for t in tasks if t.status in ['in_progress', 'in_review'])
        backlog_tasks = sum(1 for t in tasks if t.status == 'backlog')

        progress_pct = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        project_data = f"""
## Datos Generales del Proyecto
- **Nombre**: {project.name}
- **Estado**: {project.get_status_display()}
- **Prioridad**: {project.get_priority_display()}
- **Fecha de inicio**: {project.start_date or 'No definida'}
- **Fecha límite**: {project.due_date or 'No definida'}
- **Horas estimadas totales**: {project.hour_budget or 'No definidas'}
- **Progreso estimado basado en tareas**: {progress_pct:.1f}%

## Resumen de Tareas ({total_tasks} en total)
- **Completadas**: {completed_tasks}
- **En Progreso / Revisión**: {in_progress_tasks}
- **Pendientes (Backlog)**: {backlog_tasks}

## Detalle de Tareas:
"""
        for task in tasks:
            assignee = task.assignee.name or task.assignee.email if task.assignee else "Sin asignar"
            project_data += f"- [{task.get_status_display().upper()}] {task.title} (Prioridad: {task.get_priority_display()}, Asignado: {assignee})\n"

        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=project_data,
            config=genai.types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.3, # Baja temperatura para que sea analítico y serio
                max_output_tokens=2048,
            ),
        )

        return response.text.strip()

    except Exception as e:
        error_str = str(e)
        logger.error(f"Error generando resumen ejecutivo: {error_str}")
        return f"**Error interno al generar el resumen**: {error_str}"
