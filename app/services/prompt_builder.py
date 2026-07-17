from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PromptPayload:
    """Representa el prompt final que se enviara al modelo."""

    system_message: str
    user_message: str


SYSTEM_PROMPT = """
Eres un asistente de ChatPDF especializado en responder preguntas usando unicamente el contexto recuperado.

Reglas obligatorias:
1. Responde solo con informacion presente en el contexto.
2. No inventes datos, fechas, nombres ni conclusiones.
3. Si el contexto no contiene evidencia suficiente, responde exactamente:
"No encontre informacion suficiente en el contexto para responder con seguridad."
4. No uses conocimiento externo.
5. Cuando respondas, sintetiza con precision y menciona paginas cuando sea util.
6. No cites fragmentos que no aparezcan en el contexto.
""".strip()


def build_chat_prompt(question: str, context: str) -> PromptPayload:
    normalized_question = question.strip()
    normalized_context = context.strip()

    user_message = f"""
Pregunta del usuario:
{normalized_question}

Contexto recuperado:
{normalized_context}

Instrucciones de salida:
- Responde en espanol.
- Usa solo la informacion del contexto.
- Si faltan datos para responder con certeza, devuelve exactamente la frase indicada por el sistema.
- Prioriza claridad y precision sobre longitud.
""".strip()

    return PromptPayload(
        system_message=SYSTEM_PROMPT,
        user_message=user_message,
    )


def build_summary_prompt(context: str) -> PromptPayload:
    """Genera un resumen conciso del documento a partir de sus primeros chunks."""
    return PromptPayload(
        system_message=(
            "Eres un asistente académico experto en síntesis de documentos. "
            "Tu tarea es generar un resumen claro, preciso y estructurado "
            "basado únicamente en el contenido proporcionado. "
            "Responde siempre en español. No inventes información."
        ),
        user_message=(
            f"A partir del siguiente contenido del documento, genera un resumen "
            f"de 3 a 5 oraciones que capture los puntos más importantes:\n\n"
            f"{context}\n\n"
            f"Resumen:"
        ),
    )


def build_questions_prompt(context: str) -> PromptPayload:
    """Genera 3 preguntas relevantes sobre el documento."""
    return PromptPayload(
        system_message=(
            "Eres un asistente académico. Tu tarea es generar exactamente 3 preguntas "
            "relevantes, claras y específicas basadas en el contenido del documento. "
            "Responde ÚNICAMENTE con las 3 preguntas, una por línea, sin numeración, "
            "sin guiones, sin explicaciones adicionales. Solo las preguntas en español."
        ),
        user_message=(
            f"Basándote en el siguiente contenido, genera 3 preguntas concretas "
            f"que un estudiante podría hacerse sobre este material:\n\n"
            f"{context}\n\n"
            f"Preguntas:"
        ),
    )
