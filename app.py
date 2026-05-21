"""
StyleSense — AI Haircut Advisor
Backend Flask principal
"""

import os
import json
import jwt as pyjwt
from jwt import PyJWKClient
from functools import wraps

from flask import Flask, render_template, request, jsonify, redirect
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-in-production")

# Supabase admin client (service role)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

_jwks_client: PyJWKClient | None = None

def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(
            f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json",
            cache_keys=True,
            lifespan=300,
        )
    return _jwks_client

def _key_prefix(k: str) -> str:
    return (k[:18] + "...") if len(k) > 18 else ("(vacío)" if not k else k)

print(f"[Supabase] URL={SUPABASE_URL or 'MISSING'}")
print(f"[Supabase] SERVICE_KEY prefix={_key_prefix(SUPABASE_SERVICE_KEY)}")
print(f"[Supabase] ANON_KEY    prefix={_key_prefix(SUPABASE_ANON_KEY)}")

_supabase_init_error: str | None = None
try:
    if SUPABASE_URL and SUPABASE_SERVICE_KEY:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print(f"[Supabase] Cliente OK")
    else:
        supabase = None
        print("[Supabase] FALLO: SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY no están configurados")
except Exception as e:
    supabase = None
    _supabase_init_error = str(e)
    print(f"[Supabase] FALLO al inicializar: {type(e).__name__}: {e}")
    if "Invalid API key" in str(e) or "invalid" in str(e).lower():
        print("[Supabase] DIAGNÓSTICO: La key debe ser formato JWT (empieza con eyJ...).")
        print("[Supabase]             Las keys sb_secret_... / sb_publishable_... NO son compatibles.")
        print("[Supabase]             Usa las Legacy API Keys: Supabase -> Settings -> API -> Legacy API Keys.")

# Import servicios de Claude
from api.claude_service import analyze_face, analyze_haircut_result


# ─── Global error handler (always return JSON, never HTML) ────────────────────

@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return jsonify({"error": e.description or str(e)}), e.code
    import traceback
    traceback.print_exc()
    return jsonify({"error": str(e) or "Error interno del servidor"}), 500

@app.errorhandler(404)
def handle_404(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Ruta no encontrada"}), 404
    return e

@app.errorhandler(405)
def handle_405(e):
    return jsonify({"error": "Método no permitido"}), 405


# ─── Auth Middleware ──────────────────────────────────────────────────────────

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Token de autorización requerido"}), 401

        token = auth_header[7:]
        try:
            signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
            payload = pyjwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256"],
                audience="authenticated",
                options={"verify_exp": True},
            )
            request.user_id = payload.get("sub")
        except pyjwt.ExpiredSignatureError:
            return jsonify({"error": "Token expirado. Vuelve a iniciar sesión."}), 401
        except pyjwt.InvalidTokenError:
            return jsonify({"error": "Token inválido"}), 401
        except Exception:
            return jsonify({"error": "Error de autenticación"}), 401

        return f(*args, **kwargs)
    return decorated


def get_config():
    return {
        "supabase_url": SUPABASE_URL,
        "supabase_anon_key": SUPABASE_ANON_KEY,
    }


# ─── Rutas de Páginas ─────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html", **get_config())

@app.route("/login")
def login():
    return render_template("login.html", **get_config())

@app.route("/register")
def register():
    return render_template("register.html", **get_config())

@app.route("/onboarding")
def onboarding():
    return render_template("onboarding.html", **get_config())

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html", **get_config())

@app.route("/analyze")
def analyze():
    return render_template("analyze.html", **get_config())

@app.route("/results/<analysis_id>")
def results(analysis_id):
    return render_template("results.html", analysis_id=analysis_id, **get_config())

@app.route("/feedback")
def feedback():
    return render_template("feedback.html", **get_config())


# ─── API: Perfil de Usuario ───────────────────────────────────────────────────

@app.route("/api/profile", methods=["GET"])
@require_auth
def api_get_profile():
    if not supabase:
        return jsonify({"error": "Supabase no configurado"}), 500

    try:
        result = (
            supabase.table("user_profiles")
            .select("*")
            .eq("id", request.user_id)
            .maybe_single()
            .execute()
        )
        if result.data:
            return jsonify({"success": True, "profile": result.data})
        return jsonify({"success": False, "error": "Perfil no encontrado"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/profile", methods=["POST"])
@require_auth
def api_save_profile():
    if not supabase:
        return jsonify({"error": "Supabase no configurado"}), 500

    data = request.get_json()
    if not data:
        return jsonify({"error": "No se recibieron datos"}), 400

    profile_data = {
        "id": request.user_id,
        "full_name": data.get("full_name", ""),
        "age": data.get("age"),
        "country": data.get("country", ""),
        "city": data.get("city", ""),
        "hair_type": data.get("hair_type", "straight"),
        "hair_density": data.get("hair_density", "medium"),
        "hair_growth_direction": data.get("hair_growth_direction", "downward"),
        "style_preference": data.get("style_preference", "modern"),
        "maintenance_level": data.get("maintenance_level", "medium"),
        "lifestyle": data.get("lifestyle", "mixed"),
        "additional_notes": data.get("additional_notes", ""),
        "profile_complete": True,
    }

    try:
        result = supabase.table("user_profiles").upsert(profile_data).execute()
        if result.data:
            return jsonify({"success": True, "profile": result.data[0]})
        return jsonify({"success": False, "error": "No se pudo guardar el perfil"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ─── API: Análisis de Rostro ──────────────────────────────────────────────────

@app.route("/api/analyze-face", methods=["POST"])
@require_auth
def api_analyze_face():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No se recibieron datos"}), 400

    image_url = data.get("image_url")
    if not image_url:
        return jsonify({"error": "image_url es requerido"}), 400

    # Obtener el perfil del usuario
    user_profile = {}
    if supabase:
        try:
            profile_result = (
                supabase.table("user_profiles")
                .select("*")
                .eq("id", request.user_id)
                .maybe_single()
                .execute()
            )
            user_profile = profile_result.data or {}
        except Exception:
            user_profile = {}
    else:
        user_profile = data.get("user_profile", {})

    if not user_profile or not user_profile.get("profile_complete"):
        return jsonify({"error": "Perfil de usuario no encontrado. Completá el onboarding primero."}), 400

    result = analyze_face(image_url, user_profile)

    if not result.get("success"):
        return jsonify({"error": result.get("error", "Error desconocido")}), 500

    # Guardar el análisis
    if supabase:
        try:
            face_features = result["data"].get("faceFeatures") or {}
            facial_points = result["data"].get("facialPoints")
            if facial_points:
                face_features = {**face_features, "facialPoints": facial_points}
            analysis_data = {
                "user_id": request.user_id,
                "face_image_url": image_url,
                "face_shape": result["data"].get("faceShape"),
                "face_features": face_features,
                "analysis_text": result["data"].get("analysisText"),
                "recommendations": result["data"].get("recommendations"),
                "haircuts_to_avoid": result["data"].get("haircutsToAvoid"),
                "styling_tips": json.dumps(result["data"].get("generalStylingTips", [])),
                "overall_advice": result["data"].get("overallAdvice"),
            }
            save_result = supabase.table("hair_analyses").insert(analysis_data).execute()
            if save_result.data:
                result["data"]["analysis_id"] = save_result.data[0]["id"]
        except Exception:
            pass

    return jsonify({"success": True, "data": result["data"]})


@app.route("/api/analysis/<analysis_id>", methods=["GET"])
@require_auth
def api_get_analysis(analysis_id):
    if not supabase:
        return jsonify({"error": "Supabase no configurado"}), 500

    try:
        result = (
            supabase.table("hair_analyses")
            .select("*")
            .eq("id", analysis_id)
            .eq("user_id", request.user_id)
            .maybe_single()
            .execute()
        )
        if result.data:
            return jsonify({"success": True, "analysis": result.data})
        return jsonify({"success": False, "error": "Análisis no encontrado"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/analyses", methods=["GET"])
@require_auth
def api_list_analyses():
    if not supabase:
        return jsonify({"success": True, "analyses": []})

    try:
        result = (
            supabase.table("hair_analyses")
            .select("id, face_shape, analysis_text, created_at")
            .eq("user_id", request.user_id)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        return jsonify({"success": True, "analyses": result.data or []})
    except Exception:
        return jsonify({"success": True, "analyses": []})


# ─── API: Feedback del Corte ──────────────────────────────────────────────────

@app.route("/api/analyze-result", methods=["POST"])
@require_auth
def api_analyze_result():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No se recibieron datos"}), 400

    result_image_url = data.get("result_image_url")
    selected_haircut = data.get("selected_haircut")
    analysis_id = data.get("analysis_id")

    if not all([result_image_url, selected_haircut]):
        return jsonify({"error": "Faltan datos requeridos"}), 400

    original_recommendations = []
    user_profile = {}

    if supabase and analysis_id:
        try:
            analysis_result = (
                supabase.table("hair_analyses")
                .select("recommendations")
                .eq("id", analysis_id)
                .eq("user_id", request.user_id)
                .maybe_single()
                .execute()
            )
            if analysis_result.data:
                original_recommendations = analysis_result.data.get("recommendations", [])
        except Exception:
            pass

        try:
            profile_result = (
                supabase.table("user_profiles")
                .select("*")
                .eq("id", request.user_id)
                .maybe_single()
                .execute()
            )
            user_profile = profile_result.data or {}
        except Exception:
            user_profile = {}
    else:
        original_recommendations = data.get("original_recommendations", [])
        user_profile = data.get("user_profile", {})

    result = analyze_haircut_result(
        result_image_url, original_recommendations, selected_haircut, user_profile
    )

    if not result.get("success"):
        return jsonify({"error": result.get("error", "Error desconocido")}), 500

    if supabase:
        try:
            result_data = {
                "user_id": request.user_id,
                "analysis_id": analysis_id,
                "selected_haircut": selected_haircut,
                "result_image_url": result_image_url,
                "feedback": result["data"],
                "score": result["data"].get("overallScore"),
            }
            supabase.table("haircut_results").insert(result_data).execute()
        except Exception:
            pass

    return jsonify({"success": True, "data": result["data"]})


@app.route("/api/results", methods=["GET"])
@require_auth
def api_list_results():
    if not supabase:
        return jsonify({"success": True, "results": []})

    try:
        result = (
            supabase.table("haircut_results")
            .select("id, selected_haircut, score, created_at")
            .eq("user_id", request.user_id)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        return jsonify({"success": True, "results": result.data or []})
    except Exception:
        return jsonify({"success": True, "results": []})


# ─── API: Storage ─────────────────────────────────────────────────────────────

@app.route("/api/upload-url", methods=["POST"])
@require_auth
def api_get_upload_url():
    if not supabase:
        return jsonify({"error": "Supabase no configurado"}), 500

    data = request.get_json()
    bucket = data.get("bucket", "face-images")
    file_name = data.get("file_name", "photo.jpg")
    path = f"{request.user_id}/{file_name}"

    try:
        signed = supabase.storage.from_(bucket).create_signed_upload_url(path)
        return jsonify({"success": True, "signed_url": signed})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug, port=5000, host="0.0.0.0")
