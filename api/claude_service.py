"""
Servicio de análisis con Google Gemini API.
Usa el SDK google-genai (reemplazo de google-generativeai deprecado).
"""

from google import genai
from google.genai import types
import PIL.Image
import io
import os
import json
import httpx

from .prompts import build_face_analysis_prompt, build_haircut_feedback_prompt

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY no está configurada en las variables de entorno")
        _client = genai.Client(api_key=api_key)
    return _client


def _fetch_image(image_url: str) -> PIL.Image.Image:
    with httpx.Client(timeout=30, follow_redirects=True) as http:
        response = http.get(image_url)
        response.raise_for_status()
    return PIL.Image.open(io.BytesIO(response.content))


def _image_to_part(image: PIL.Image.Image) -> types.Part:
    buf = io.BytesIO()
    image.save(buf, format="JPEG")
    return types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg")


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
        client = _get_client()
    except ValueError as e:
        return {"success": False, "error": str(e)}

    try:
        image = _fetch_image(image_url)
    except Exception as e:
        return {"success": False, "error": f"No se pudo descargar la imagen: {e}"}

    prompt = build_face_analysis_prompt(user_profile)

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt, _image_to_part(image)],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                max_output_tokens=6000,
                temperature=0.4,
            ),
        )
        result = _parse_json(response.text)
        return {"success": True, "data": result}
    except json.JSONDecodeError as e:
        return {"success": False, "error": "No se pudo parsear la respuesta como JSON.", "details": str(e)}
    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
            return {"success": False, "error": "Límite de la API de IA alcanzado. Activá facturación en Google AI Studio (ai.google.dev) y reintentá."}
        return {"success": False, "error": f"Error al analizar con IA: {e}"}


def analyze_haircut_result(
    result_image_url: str,
    original_recommendations: list,
    selected_haircut_name: str,
    user_profile: dict,
) -> dict:
    try:
        client = _get_client()
    except ValueError as e:
        return {"success": False, "error": str(e)}

    try:
        image = _fetch_image(result_image_url)
    except Exception as e:
        return {"success": False, "error": f"No se pudo descargar la imagen: {e}"}

    prompt = build_haircut_feedback_prompt(original_recommendations, selected_haircut_name, user_profile)

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt, _image_to_part(image)],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                max_output_tokens=2048,
                temperature=0.4,
            ),
        )
        result = _parse_json(response.text)
        return {"success": True, "data": result}
    except json.JSONDecodeError as e:
        return {"success": False, "error": "No se pudo parsear la respuesta.", "details": str(e)}
    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
            return {"success": False, "error": "Límite de la API de IA alcanzado. Activá facturación en Google AI Studio (ai.google.dev) y reintentá."}
        return {"success": False, "error": f"Error al analizar con IA: {e}"}
