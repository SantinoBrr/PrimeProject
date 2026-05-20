"""
Servicio de integración con Claude API.
Maneja análisis de imágenes faciales y evaluación de cortes de cabello.
"""

import anthropic
import os
import json
import base64
import httpx

from .prompts import build_face_analysis_prompt, build_haircut_feedback_prompt

_client = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY no está configurada en las variables de entorno")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def fetch_image_as_base64(image_url: str) -> tuple:
    """Descarga una imagen desde una URL y la convierte a base64."""
    with httpx.Client(timeout=30, follow_redirects=True) as http:
        response = http.get(image_url)
        response.raise_for_status()

    content_type = response.headers.get("content-type", "image/jpeg").lower()
    if "png" in content_type:
        media_type = "image/png"
    elif "webp" in content_type:
        media_type = "image/webp"
    elif "gif" in content_type:
        media_type = "image/gif"
    else:
        media_type = "image/jpeg"

    image_data = base64.standard_b64encode(response.content).decode("utf-8")
    return image_data, media_type


def _parse_claude_json(raw_text: str) -> dict:
    """
    Parsea la respuesta de Claude asegurándose de extraer JSON puro,
    incluso si Claude devuelve bloques de código markdown.
    """
    text = raw_text.strip()

    if text.startswith("```"):
        lines = text.split("\n")
        start = 1
        end = len(lines) - 1
        for i, line in enumerate(lines):
            if line.startswith("```") and i > 0:
                end = i
                break
        text = "\n".join(lines[start:end]).strip()

    # Buscar el primer { y el último } para extraer JSON
    start_idx = text.find("{")
    end_idx = text.rfind("}")
    if start_idx != -1 and end_idx != -1:
        text = text[start_idx : end_idx + 1]

    return json.loads(text)


def analyze_face(image_url: str, user_profile: dict) -> dict:
    """
    Analiza la imagen facial del usuario y genera recomendaciones de cortes de cabello.

    Returns:
        dict con 'success', 'data' (o 'error' si falla)
    """
    client = get_client()

    try:
        image_data, media_type = fetch_image_as_base64(image_url)
    except Exception as e:
        return {"success": False, "error": f"No se pudo descargar la imagen: {str(e)}"}

    analysis_prompt = build_face_analysis_prompt(user_profile)

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=(
                "Eres un experto en análisis facial y recomendación de cortes de cabello. "
                "Siempre respondes en JSON válido EXACTAMENTE como se te solicita, "
                "sin texto adicional, sin markdown, sin explicaciones fuera del JSON. "
                "Tus recomendaciones son precisas, personalizadas y actualizadas a las tendencias de 2026."
            ),
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": analysis_prompt,
                        },
                    ],
                }
            ],
        )

        raw_response = message.content[0].text
        result = _parse_claude_json(raw_response)
        return {"success": True, "data": result}

    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": "Claude devolvió una respuesta que no se pudo parsear como JSON.",
            "details": str(e),
        }
    except anthropic.APIError as e:
        return {"success": False, "error": f"Error de API de Anthropic: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Error inesperado: {str(e)}"}


def analyze_haircut_result(
    result_image_url: str,
    original_recommendations: list,
    selected_haircut_name: str,
    user_profile: dict,
) -> dict:
    """
    Analiza el corte de cabello realizado y proporciona feedback comparado
    con la recomendación original.

    Returns:
        dict con 'success', 'data' (o 'error' si falla)
    """
    client = get_client()

    try:
        image_data, media_type = fetch_image_as_base64(result_image_url)
    except Exception as e:
        return {"success": False, "error": f"No se pudo descargar la imagen: {str(e)}"}

    feedback_prompt = build_haircut_feedback_prompt(
        original_recommendations, selected_haircut_name, user_profile
    )

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=(
                "Eres un maestro barbero evaluando cortes de cabello con ojo crítico y constructivo. "
                "Siempre respondes en JSON válido exactamente como se te solicita. "
                "Eres honesto, técnico y específico en tus evaluaciones."
            ),
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": feedback_prompt,
                        },
                    ],
                }
            ],
        )

        raw_response = message.content[0].text
        result = _parse_claude_json(raw_response)
        return {"success": True, "data": result}

    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": "No se pudo parsear la respuesta de Claude.",
            "details": str(e),
        }
    except anthropic.APIError as e:
        return {"success": False, "error": f"Error de API de Anthropic: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Error inesperado: {str(e)}"}
