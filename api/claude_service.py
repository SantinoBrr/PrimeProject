"""
Servicio de análisis con Groq API (Llama 4 Scout Vision).
"""

from groq import Groq
import PIL.Image
import io
import os
import json
import base64
import httpx

from .prompts import build_face_analysis_prompt, build_haircut_feedback_prompt

_client: Groq | None = None
_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY no está configurada en las variables de entorno")
        _client = Groq(api_key=api_key)
    return _client


def _fetch_image(image_url: str) -> PIL.Image.Image:
    with httpx.Client(timeout=30, follow_redirects=True) as http:
        response = http.get(image_url)
        response.raise_for_status()
    return PIL.Image.open(io.BytesIO(response.content))


def _image_to_b64(image: PIL.Image.Image) -> str:
    buf = io.BytesIO()
    image.save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


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


def _handle_error(e: Exception) -> dict:
    err = str(e)
    if "429" in err or "rate_limit" in err.lower() or "quota" in err.lower():
        return {"success": False, "error": "Límite de la API alcanzado. Intentá de nuevo en unos minutos."}
    return {"success": False, "error": f"Error al analizar con IA: {e}"}


def analyze_face(image_url: str, user_profile: dict) -> dict:
    try:
        client = _get_client()
    except ValueError as e:
        return {"success": False, "error": str(e)}

    try:
        image = _fetch_image(image_url)
    except Exception as e:
        return {"success": False, "error": f"No se pudo descargar la imagen: {e}"}

    b64 = _image_to_b64(image)
    prompt = build_face_analysis_prompt(user_profile)

    try:
        response = client.chat.completions.create(
            model=_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    ],
                }
            ],
            max_tokens=6000,
            temperature=0.4,
        )
        result = _parse_json(response.choices[0].message.content)
        return {"success": True, "data": result}
    except json.JSONDecodeError as e:
        return {"success": False, "error": "No se pudo parsear la respuesta como JSON.", "details": str(e)}
    except Exception as e:
        return _handle_error(e)


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

    b64 = _image_to_b64(image)
    prompt = build_haircut_feedback_prompt(original_recommendations, selected_haircut_name, user_profile)

    try:
        response = client.chat.completions.create(
            model=_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    ],
                }
            ],
            max_tokens=2048,
            temperature=0.4,
        )
        result = _parse_json(response.choices[0].message.content)
        return {"success": True, "data": result}
    except json.JSONDecodeError as e:
        return {"success": False, "error": "No se pudo parsear la respuesta.", "details": str(e)}
    except Exception as e:
        return _handle_error(e)
