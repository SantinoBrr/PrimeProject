"""
Servicio de análisis con Google Gemini API (tier gratuito).
Mantiene la misma interfaz que el servicio anterior.
"""

import google.generativeai as genai
import PIL.Image
import io
import os
import json
import httpx

from .prompts import build_face_analysis_prompt, build_haircut_feedback_prompt

_configured = False


def _get_model(max_tokens: int = 4096):
    global _configured
    if not _configured:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY no está configurada en las variables de entorno")
        genai.configure(api_key=api_key)
        _configured = True

    return genai.GenerativeModel(
        "gemini-1.5-flash",
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            max_output_tokens=max_tokens,
            temperature=0.4,
        ),
    )


def _fetch_image(image_url: str) -> PIL.Image.Image:
    with httpx.Client(timeout=30, follow_redirects=True) as http:
        response = http.get(image_url)
        response.raise_for_status()
    return PIL.Image.open(io.BytesIO(response.content))


def _parse_json(raw_text: str) -> dict:
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        end = next((i for i, l in enumerate(lines) if l.startswith("```") and i > 0), len(lines) - 1)
        text = "\n".join(lines[1:end]).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    return json.loads(text)


def analyze_face(image_url: str, user_profile: dict) -> dict:
    try:
        model = _get_model(max_tokens=4096)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    try:
        image = _fetch_image(image_url)
    except Exception as e:
        return {"success": False, "error": f"No se pudo descargar la imagen: {e}"}

    prompt = build_face_analysis_prompt(user_profile)

    try:
        response = model.generate_content([prompt, image])
        result = _parse_json(response.text)
        return {"success": True, "data": result}
    except json.JSONDecodeError as e:
        return {"success": False, "error": "No se pudo parsear la respuesta como JSON.", "details": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Error al analizar con IA: {e}"}


def analyze_haircut_result(
    result_image_url: str,
    original_recommendations: list,
    selected_haircut_name: str,
    user_profile: dict,
) -> dict:
    try:
        model = _get_model(max_tokens=2048)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    try:
        image = _fetch_image(result_image_url)
    except Exception as e:
        return {"success": False, "error": f"No se pudo descargar la imagen: {e}"}

    prompt = build_haircut_feedback_prompt(original_recommendations, selected_haircut_name, user_profile)

    try:
        response = model.generate_content([prompt, image])
        result = _parse_json(response.text)
        return {"success": True, "data": result}
    except json.JSONDecodeError as e:
        return {"success": False, "error": "No se pudo parsear la respuesta.", "details": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Error al analizar con IA: {e}"}
