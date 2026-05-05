import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

BOARD_CHAT_SYSTEM_PROMPT = """Eres el "Board Chat", un asistente inteligente integrado en un tablero Kanban de gestión de proyectos.
Recibirás el estado actual de las tareas del tablero y los miembros disponibles en formato JSON, además de una instrucción o pregunta del usuario en lenguaje natural.
Tu trabajo es analizar la instrucción y proponer los cambios necesarios en el tablero.

Debes devolver ÚNICAMENTE un JSON válido (sin etiquetas markdown adicionales como ```json) con la siguiente estructura:

{
  "message": "Mensaje en lenguaje natural para el usuario explicando lo que vas a hacer o respondiendo a su pregunta. Sé conciso y amigable.",
  "actions": [
    {
      "action": "update_status",
      "task_id": "ID exacto de la tarea",
      "new_status": "todo|in_progress|in_review|done"
    },
    {
      "action": "edit_task",
      "task_id": "ID exacto de la tarea a editar",
      "title": "Nuevo título (opcional)",
      "priority": "low|medium|high|critical (opcional)",
      "assignee_id": "ID del miembro al que se asigna, o null para desasignar (opcional)",
      "description": "Nueva descripción (opcional)"
    },
    {
      "action": "create_task",
      "title": "Título descriptivo",
      "type": "task|bug|story|subtask",
      "status": "todo",
      "parent_id": "ID exacto de la tarea padre (solo si es subtarea, de lo contrario omitir o null)",
      "assignee_id": "ID del miembro al que se asigna (buscar en la lista de miembros, si no hay coincidencia clara omitir)"
    }
  ]
}

Reglas Estrictas:
1. Las posibles acciones son `update_status`, `edit_task` y `create_task`.
2. Para `update_status` y `edit_task`, el `task_id` debe coincidir exactamente con el ID de la tarea.
3. En `edit_task`, puedes incluir solo los campos que deban cambiar. Si te piden asignar una tarea a Ana, envía `{"action": "edit_task", "task_id": "...", "assignee_id": "ID_DE_ANA"}`.
4. Si el usuario hace una pregunta analítica ("¿Cuántas tareas tiene Ana?"), responde en "message" y deja "actions" vacío [].
5. NO inventes IDs de tareas. Si el usuario pide crear subtareas para cada tarea en un estado, usa los IDs reales de esas tareas como `parent_id`.
6. Si la solicitud no tiene sentido o falta información, explícalo en "message" y devuelve "actions" vacío.
"""

def chat_with_board(prompt: str, board_data: dict) -> dict:
    """
    Envía la instrucción del usuario y el estado del tablero a Gemini para obtener una respuesta y acciones propuestas.
    """
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return {"error": "La API key de Gemini no está configurada."}

    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        # Preparamos el contexto
        context = f"ESTADO ACTUAL DEL TABLERO:\n{json.dumps(board_data, ensure_ascii=False, indent=2)}\n\nINSTRUCCIÓN DEL USUARIO:\n{prompt}"

        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=context,
            config=genai.types.GenerateContentConfig(
                system_instruction=BOARD_CHAT_SYSTEM_PROMPT,
                temperature=0.1,  # Baja temperatura para asegurar formato y fidelidad a los IDs
                max_output_tokens=4096,
                response_mime_type="application/json",
            ),
        )

        raw_text = response.text.strip()
        data = json.loads(raw_text)

        # Validar estructura básica
        if "message" not in data or "actions" not in data:
            return {"error": "Formato de respuesta inválido de la IA.", "message": raw_text}
            
        return data

    except json.JSONDecodeError as e:
        logger.error(f"Error parseando JSON de Gemini Board Chat: {e}\nRespuesta: {raw_text[:500]}")
        return {"error": "La IA generó una respuesta que no es un JSON válido."}
    except Exception as e:
        logger.error(f"Error llamando a Gemini en Board Chat: {e}")
        error_str = str(e)
        if '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str:
            return {"error": "Se ha alcanzado el límite de peticiones. Espera un minuto."}
        if '403' in error_str or 'PERMISSION_DENIED' in error_str:
            return {"error": "Error de permisos con la API key de Gemini."}
        
        return {"error": "Error al contactar con el servicio de IA."}
