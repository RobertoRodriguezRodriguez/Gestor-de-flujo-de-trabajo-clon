"""
Servicio de IA para crear proyectos con lenguaje natural usando Google Gemini.
Solo disponible para usuarios premium.
"""
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres un asistente de gestión de proyectos. Tu trabajo es interpretar la descripción en lenguaje natural de un proyecto y extraer datos estructurados.

Debes devolver ÚNICAMENTE un JSON válido (sin markdown, sin ```json, sin explicaciones) con la siguiente estructura:

{
  "name": "Nombre del proyecto (max 200 chars)",
  "key": "CLAVE (2-5 letras mayúsculas, abreviatura del nombre)",
  "description": "Descripción detallada del proyecto en markdown",
  "status": "planning|active|on_hold|completed|cancelled",
  "priority": "low|medium|high|critical",
  "start_date": "YYYY-MM-DD o null",
  "due_date": "YYYY-MM-DD o null",
  "hour_budget": number o null,
  "tasks": [
    {
      "title": "Título de la tarea",
      "type": "task|bug|story|epic|subtask",
      "priority": "low|medium|high|critical",
      "description": "Descripción breve de la tarea",
      "estimated_hours": number o null
    }
  ]
}

Reglas:
- El campo "key" debe ser una abreviatura corta y clara del nombre del proyecto (2-5 letras, MAYÚSCULAS). Ejemplo: "Portal del Cliente" → "PC", "Rediseño Web Corporativa" → "RWC".
- Si no se menciona un estado, usa "planning".
- Si no se menciona prioridad, usa "medium".
- Si se mencionan fechas, conviértelas al formato YYYY-MM-DD. Hoy es {today}.
- Si se menciona una bolsa de horas, inclúyela en hour_budget.
- Genera entre 3 y 10 tareas relevantes basadas en la descripción. Si el usuario menciona tareas específicas, inclúyelas. Si no, sugiere tareas lógicas para el tipo de proyecto descrito.
- Las tareas deben tener tipos variados y apropiados (task, story, epic, etc.).
- Responde SOLO con el JSON, sin texto adicional.
"""


def parse_project_from_natural_language(description: str) -> dict:
    """
    Envía la descripción del usuario a Gemini y devuelve los datos
    estructurados del proyecto.

    Returns:
        dict con los campos del proyecto o {"error": "mensaje"} si falla.
    """
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return {"error": "La API key de Gemini no está configurada. Contacta al administrador."}

    try:
        from google import genai

        client = genai.Client(api_key=api_key)

        from datetime import date
        today = date.today().isoformat()
        system_instruction = SYSTEM_PROMPT.replace("{today}", today)

        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=description,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.3,
                max_output_tokens=4096,
            ),
        )

        raw_text = response.text.strip()

        # Limpiar posibles wrappers de markdown
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()

        data = json.loads(raw_text)

        # Validar campos obligatorios
        if not data.get("name"):
            return {"error": "La IA no pudo extraer el nombre del proyecto. Intenta con una descripción más detallada."}
        if not data.get("key"):
            data["key"] = data["name"][:5].upper().replace(" ", "")

        # Sanitizar key
        data["key"] = data["key"][:10].upper().replace(" ", "")

        # Validar choices
        valid_statuses = {"planning", "active", "on_hold", "completed", "cancelled"}
        valid_priorities = {"low", "medium", "high", "critical"}
        valid_task_types = {"task", "bug", "story", "epic", "subtask"}

        if data.get("status") not in valid_statuses:
            data["status"] = "planning"
        if data.get("priority") not in valid_priorities:
            data["priority"] = "medium"

        # Sanitizar tareas
        tasks = data.get("tasks", [])
        clean_tasks = []
        for task in tasks:
            if not task.get("title"):
                continue
            if task.get("type") not in valid_task_types:
                task["type"] = "task"
            if task.get("priority") not in valid_priorities:
                task["priority"] = "medium"
            clean_tasks.append({
                "title": task["title"][:300],
                "type": task["type"],
                "priority": task["priority"],
                "description": task.get("description", "")[:2000],
                "estimated_hours": task.get("estimated_hours"),
            })
        data["tasks"] = clean_tasks

        return data

    except json.JSONDecodeError as e:
        logger.error(f"Error parseando JSON de Gemini: {e}\nRespuesta: {raw_text[:500]}")
        return {"error": "La IA generó una respuesta inválida. Inténtalo de nuevo."}
    except Exception as e:
        error_str = str(e)
        logger.error(f"Error llamando a Gemini: {error_str}")

        # Mensajes amigables para errores comunes
        if '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str:
            return {"error": "Se ha alcanzado el límite de peticiones a la IA. Por favor, espera un minuto e inténtalo de nuevo."}
        if '403' in error_str or 'PERMISSION_DENIED' in error_str:
            return {"error": "La API key de Gemini no es válida o no tiene permisos. Contacta al administrador."}
        if '500' in error_str or '503' in error_str:
            return {"error": "El servicio de IA no está disponible temporalmente. Inténtalo en unos minutos."}

        return {"error": "Error al contactar con el servicio de IA. Inténtalo de nuevo."}
