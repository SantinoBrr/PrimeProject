"""
Motor de prompts para análisis facial y recomendación de cortes de cabello.
Este es el núcleo del algoritmo — cada detalle del perfil del usuario
es incorporado para maximizar la precisión de las recomendaciones.
"""


HAIR_TYPE_CONTEXT = {
    "straight": (
        "cabello lacio — sin curva natural, cae hacia abajo. "
        "Es muy moldeable pero puede verse plano sin producto. "
        "Responde bien a cortes definidos. El shrinkage (encogimiento) es mínimo."
    ),
    "wavy": (
        "cabello ondulado — tiene movimiento natural con curvas suaves (tipo 2A-2C). "
        "Versátil: puede alisarse o potenciarse con difusor. "
        "En cortes cortos se activa más; en cortes largos puede pesar y perder onda."
    ),
    "curly": (
        "cabello rizado (tipo 3A-3C) — rulos definidos con bounce natural. "
        "CRÍTICO: el shrinkage puede ser del 30-50%, por lo que el cabello húmedo "
        "luce mucho más largo que seco. El barbero DEBE cortar en seco o conocer la "
        "técnica curly. Necesita hidratación constante."
    ),
    "coily": (
        "cabello muy rizado/afro (tipo 4A-4C) — textura muy cerrada, shrinkage de hasta 75%. "
        "Necesita barberos especializados en cabello afro. Los cortes deben contemplar "
        "el volumen del cabello seco, no húmedo. La hidratación es esencial."
    ),
    "kinky": (
        "cabello crespo muy apretado — máximo shrinkage, textura zig-zag. "
        "Muy versátil para estilos creativos. Requiere barberos especializados "
        "y productos específicos para cabello de alta porosidad."
    ),
}

GROWTH_CONTEXT = {
    "upward": (
        "DIRECCIÓN DE CRECIMIENTO → HACIA ARRIBA: "
        "El cabello crece predominantemente hacia arriba desde el cuero cabelludo. "
        "Esto es una ventaja para quiffs, pompadours y estilos con volumen en la cima. "
        "SIN EMBARGO: los cortes bajos/fades en los costados necesitan atención especial "
        "porque el cabello 'pelea' contra caer hacia abajo. "
        "Los estilos tipo caesar o French crop pueden ser difíciles de mantener planos."
    ),
    "sideways": (
        "DIRECCIÓN DE CRECIMIENTO → HACIA LOS LADOS: "
        "El cabello se proyecta lateralmente desde el cuero cabelludo. "
        "Los estilos peinados hacia un lado serán muy naturales. "
        "Los estilos hacia arriba (quiff, pompadour) necesitarán más producto y esfuerzo. "
        "Útil para undercuts y estilos asimétricos."
    ),
    "downward": (
        "DIRECCIÓN DE CRECIMIENTO → HACIA ABAJO: "
        "El cabello cae naturalmente, facilitando estilos lisos y peinados hacia adelante. "
        "Los estilos con volumen hacia arriba necesitarán secador + producto fuerte. "
        "Ideal para curtain haircuts, estilos franceses y look natural."
    ),
    "forward": (
        "DIRECCIÓN DE CRECIMIENTO → HACIA ADELANTE: "
        "El cabello crece hacia el frente, especialmente en la zona frontal y coronilla. "
        "Crea flecos naturales muy fáciles. Dificulta estilos 'back-swept'. "
        "Considerar al diseñar la línea frontal del corte."
    ),
    "mixed": (
        "DIRECCIÓN DE CRECIMIENTO → MIXTA/REMOLINOS: "
        "El cabello tiene múltiples patrones de crecimiento. "
        "ADVERTENCIA AL BARBERO: es FUNDAMENTAL analizar los remolinos antes de cortar. "
        "Un remolino en la coronilla afecta drasticamente el resultado final. "
        "Los cortes texturizados funcionan mejor que los lisos en estos casos."
    ),
}

STYLE_CONTEXT = {
    "classic": (
        "Estilo CLÁSICO: prefiere estilos atemporales con corte limpio, bien definido y conservador. "
        "Sin modas extremas. Referencias: side part, ivy league, business cut."
    ),
    "modern": (
        "Estilo MODERNO: le gustan las tendencias actuales pero accesibles. "
        "Puede explorar estilos trendy de 2026 sin ir a extremos."
    ),
    "casual": (
        "Estilo CASUAL: prioriza comodidad y aspecto desenfadado. "
        "Nada que requiera mucho mantenimiento. Look relajado y natural."
    ),
    "professional": (
        "Estilo PROFESIONAL/CORPORATIVO: necesita un look impecable para entornos formales. "
        "El corte debe ser apropiado para reuniones de negocios y entornos conservadores."
    ),
    "edgy": (
        "Estilo EDGY/ATREVIDO: busca cortes con carácter y personalidad. "
        "Abierto a diseños creativos, asimetrías, texturas inusuales. "
        "Puede incluir líneas de diseño o técnicas de barbería artística."
    ),
    "streetwear": (
        "Estilo STREETWEAR/URBANO: influenciado por cultura hip-hop, skateboard y moda urbana. "
        "Fades bien definidos, diseños, estilos de influencia afroamericana o latina."
    ),
    "mixed": (
        "Estilo VERSÁTIL: necesita un corte que funcione tanto en entornos formales como casuales. "
        "La adaptabilidad es clave."
    ),
}

MAINTENANCE_CONTEXT = {
    "low": (
        "MANTENIMIENTO MÍNIMO: máximo 5 minutos de peinado diario, sin productos complejos. "
        "Visita al barbero cada 5-6 semanas. El corte debe verse bien incluso al natural."
    ),
    "medium": (
        "MANTENIMIENTO MODERADO: dispuesto a 10-15 minutos diarios con productos básicos. "
        "Visita al barbero cada 3-4 semanas. Puede usar pomada, cera o crema de peinado."
    ),
    "high": (
        "MANTENIMIENTO ALTO: disfruta del proceso de estilizado. "
        "20-30 minutos diarios, productos especializados. "
        "Visita al barbero cada 2-3 semanas para mantener el corte impecable."
    ),
}

LIFESTYLE_CONTEXT = {
    "active": (
        "ESTILO DE VIDA ACTIVO: practica deportes o ejercicio frecuente. "
        "El cabello estará expuesto a sudor y movimiento. "
        "Priorizar cortes que se recuperen bien y no requieran re-estilizado post-ejercicio."
    ),
    "office": (
        "ENTORNO LABORAL FORMAL: pasa la mayor parte del tiempo en oficina o reuniones. "
        "El corte debe mantenerse presentable durante todo el día."
    ),
    "creative": (
        "SECTOR CREATIVO: trabaja en industrias con mayor libertad de expresión (diseño, arte, música, etc.). "
        "Más latitud para estilos llamativos y experimentales."
    ),
    "student": (
        "ESTUDIANTE: necesita versatilidad y practicidad. "
        "Generalmente busca algo fácil, económico de mantener y que funcione en múltiples contextos."
    ),
    "mixed": (
        "ESTILO DE VIDA MIXTO: alterna entre situaciones formales e informales. "
        "Necesita un corte versátil que se adapte a distintos contextos."
    ),
}


def build_face_analysis_prompt(user_profile: dict) -> str:
    """
    Construye el prompt maestro para que Claude analice el rostro y recomiende cortes.
    Cada dato del perfil se incorpora con contexto detallado para maximizar la precisión.
    """
    age = user_profile.get("age", "no especificada")
    country = user_profile.get("country", "no especificado")
    city = user_profile.get("city", "")
    hair_type = user_profile.get("hair_type", "straight")
    hair_density = user_profile.get("hair_density", "medium")
    growth_direction = user_profile.get("hair_growth_direction", "downward")
    style_pref = user_profile.get("style_preference", "modern")
    maintenance = user_profile.get("maintenance_level", "medium")
    lifestyle = user_profile.get("lifestyle", "mixed")
    additional_notes = user_profile.get("additional_notes", "").strip()

    location_str = f"{city}, {country}" if city else country

    hair_type_desc = HAIR_TYPE_CONTEXT.get(hair_type, hair_type)
    growth_desc = GROWTH_CONTEXT.get(growth_direction, growth_direction)
    style_desc = STYLE_CONTEXT.get(style_pref, style_pref)
    maintenance_desc = MAINTENANCE_CONTEXT.get(maintenance, maintenance)
    lifestyle_desc = LIFESTYLE_CONTEXT.get(lifestyle, lifestyle)

    density_map = {
        "fine": "cabello fino/delgado — necesita volumen y evitar cortes que lo aplanen más",
        "medium": "densidad media — el tipo más versátil para la mayoría de los cortes",
        "thick": "cabello grueso/abundante — puede necesitar texturización para reducir volumen",
    }
    density_desc = density_map.get(hair_density, hair_density)

    prompt = f"""Eres el mejor consultor de imagen capilar del mundo en 2026. Combinas la precisión técnica de un maestro barbero con el conocimiento de tendencias globales de un estilista de moda. Has analizado miles de rostros y conoces perfectamente las tendencias actuales de 2026 en Europa, Norteamérica, Latinoamérica y Asia.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PERFIL COMPLETO DEL USUARIO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

▸ Edad: {age} años
▸ Ubicación: {location_str}
▸ Tipo de cabello: {hair_type_desc}
▸ Densidad: {density_desc}
▸ {growth_desc}
▸ Preferencia de estilo: {style_desc}
▸ {maintenance_desc}
▸ {lifestyle_desc}
{f"▸ Notas adicionales del usuario: {additional_notes}" if additional_notes else ""}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TENDENCIAS VIGENTES EN MAYO 2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Considera estas tendencias de 2026 al hacer recomendaciones (filtra según edad/estilo del usuario):

• Bevel fades con líneas suaves y transiciones graduales (reemplazo del skin fade clásico)
• Textured crops con flecos irregulares y micro texturización en tijera
• Undercuts modernos con longitud en la cima y máxima definición en la línea
• Wolf cuts masculinos — capas pesadas, curtain bangs, look de los 70s reinterpretado
• Buzz cut artístico con fades de alta precisión y posibles diseños geométricos sutiles
• Medium-length masculino: lob masculino (longitud clavícula), curtain haircut evolucionado
• Curly/wavy natural movement: abrazar la textura en lugar de dominarla
• Retro revivals: shags de los 90s, bobs masculinos asimétricos
• Blunt cuts con peso definido y sin capas (minimalismo capilar)
• Cortes de inspiración asiática: two-block cut, perm natural, crop texturizado
• En Latinoamérica: variaciones de lo anterior con influencia urbana/reggaeton aesthetic

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROCESO DE ANÁLISIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PASO 1 — ANÁLISIS FACIAL DETALLADO:
Examina cuidadosamente la fotografía y determina:
• Forma del rostro: ovalado | redondo | cuadrado | rectangular/oblongo | corazón | diamante | triángulo
• Ancho frente vs ancho mandíbula vs ancho pómulos
• Longitud del rostro relativa al ancho (ratio)
• Definición de la línea mandibular y del mentón
• Posición y tamaño de las orejas
• Frente: alta/baja, amplia/estrecha
• Cuello: largo/corto/medio
• Cualquier característica que deba considerarse (orejas prominentes, frente amplia, etc.)

También clasifica las características en:
• PUNTOS FUERTES: rasgos faciales favorables que el corte ideal debe destacar
• PUNTOS NEUTROS: rasgos equilibrados que el corte puede mantener tal como están
• PUNTOS A MEJORAR: rasgos que se pueden equilibrar o disimular con el corte correcto

PASO 2 — EVALUACIÓN DE RESTRICCIONES CAPILARES:
Basándote en el tipo + densidad + dirección de crecimiento:
• ¿Qué cortes son naturalmente compatibles con este cabello?
• ¿Qué estilos serán difíciles de lograr o mantener?
• ¿Qué técnicas de corte son necesarias?

PASO 3 — SELECCIÓN DE TENDENCIAS 2026 COMPATIBLES:
Filtra las tendencias según:
• Compatibilidad con la forma del rostro
• Compatibilidad con el tipo de cabello
• Adecuación para la edad ({age} años) y ubicación ({location_str})
• Coherencia con el estilo personal ({style_pref}) y nivel de mantenimiento ({maintenance})

PASO 4 — GENERACIÓN DE 5 RECOMENDACIONES:
Ordénalas de mayor a menor compatibilidad total.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMATO DE RESPUESTA — JSON ESTRICTO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Responde ÚNICAMENTE con JSON válido, sin ningún texto antes o después, sin markdown, sin explicaciones fuera del JSON:

{{
  "faceShape": "nombre_en_español",
  "faceShapeConfidence": 82,
  "faceFeatures": {{
    "jawline": "descripción corta",
    "forehead": "descripción corta",
    "cheekbones": "descripción corta",
    "faceLength": "descripción corta",
    "neckLength": "corto|medio|largo",
    "ears": "descripción si es relevante",
    "distinctiveFeatures": "otras características notables o null"
  }},
  "facialPoints": {{
    "strong": [
      {{"feature": "nombre de la característica fuerte", "description": "por qué es un rasgo favorecedor y qué corte lo puede potenciar"}},
      {{"feature": "segundo punto fuerte", "description": "descripción y cómo destacarlo"}}
    ],
    "neutral": [
      {{"feature": "nombre de la característica neutral", "description": "descripción y qué considerar"}},
      {{"feature": "segundo punto neutral", "description": "descripción"}}
    ],
    "weak": [
      {{"feature": "nombre del área a mejorar", "description": "cómo el corte correcto puede equilibrar o disimular esta característica"}},
      {{"feature": "segundo punto a mejorar", "description": "estrategia de corte para compensarlo"}}
    ]
  }},
  "analysisText": "Párrafo de 3-4 oraciones explicando el análisis del rostro con precisión: proporciones específicas detectadas, cómo influyen en la elección del corte, y qué características destacar o equilibrar.",
  "recommendations": [
    {{
      "rank": 1,
      "name": "Nombre del Corte (en español o nombre técnico conocido)",
      "nameEn": "English name for search",
      "category": "fade|undercut|textured|natural|classic|crop|wolf|buzz|medium",
      "trendScore": 9.2,
      "suitabilityScore": 9.5,
      "description": "Descripción detallada de 2-3 oraciones del corte: qué lo define, cómo se ve, qué lo hace único.",
      "whySuitable": "2-3 oraciones explicando por qué este corte es ideal para ESTA forma de rostro específica con ESTE tipo de cabello.",
      "hairTypeNote": "Cómo el tipo/densidad/dirección de crecimiento del usuario afecta específicamente este corte.",
      "stylingSteps": [
        "Paso 1: acción específica con producto específico",
        "Paso 2: acción específica",
        "Paso 3: acción específica",
        "Paso 4 (opcional): acción específica"
      ],
      "barberScript": "Texto EXACTO que el usuario puede leer/mostrar al barbero: dimensiones específicas, técnicas, proporciones, referencias.",
      "products": [
        {{"name": "producto", "purpose": "para qué sirve en este estilo"}}
      ],
      "maintenanceLevel": "bajo|medio|alto",
      "barberFrequency": "cada X semanas",
      "imageSearchQuery": "specific 2026 haircut name for google images search",
      "youtubeQuery": "tutorial video search query in english",
      "difficultyToAchieve": "fácil|moderado|difícil",
      "budgetFriendly": true
    }}
  ],
  "haircutsToAvoid": [
    {{
      "name": "nombre del corte a evitar",
      "reason": "explicación específica de por qué no funciona con este rostro y/o cabello"
    }},
    {{
      "name": "segundo corte a evitar",
      "reason": "explicación específica"
    }},
    {{
      "name": "tercer corte a evitar",
      "reason": "explicación específica"
    }}
  ],
  "generalStylingTips": [
    "Consejo 1 personalizado y específico para este usuario",
    "Consejo 2",
    "Consejo 3",
    "Consejo 4"
  ],
  "overallAdvice": "Párrafo de consejo general holístico: considerando tipo de cabello, dirección de crecimiento, forma del rostro y estilo personal. Qué debe priorizar este usuario en su rutina capilar."
}}"""

    return prompt


def build_haircut_feedback_prompt(
    original_recommendations: list,
    selected_haircut_name: str,
    user_profile: dict,
) -> str:
    """
    Construye el prompt para evaluar qué tan bien se realizó el corte
    comparado con la recomendación original.
    """
    selected_rec = next(
        (r for r in original_recommendations if r.get("name") == selected_haircut_name),
        original_recommendations[0] if original_recommendations else {},
    )

    other_recs = [r for r in original_recommendations[:3] if r.get("name") != selected_haircut_name]
    other_recs_text = "\n".join(
        f"  • {r.get('name', 'N/A')}: {r.get('description', '')[:80]}..."
        for r in other_recs
    )

    hair_type = user_profile.get("hair_type", "no especificado")
    growth = user_profile.get("hair_growth_direction", "no especificado")

    prompt = f"""Eres un maestro barbero con 25 años de experiencia, evaluando el resultado de un corte de cabello con ojo crítico pero constructivo.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTEXTO DE LA EVALUACIÓN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Corte que el usuario eligió hacerse: "{selected_haircut_name}"

Descripción original del corte recomendado:
{selected_rec.get('description', 'No disponible')}

Instrucciones que debían darse al barbero:
{selected_rec.get('barberScript', selected_rec.get('barberInstructions', 'No disponible'))}

Otros cortes que también habían sido recomendados:
{other_recs_text if other_recs_text else "Solo había una recomendación principal."}

Perfil capilar del usuario:
• Tipo de cabello: {hair_type}
• Dirección de crecimiento: {growth}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TAREA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Analiza la fotografía del corte realizado y evalúa con criterio técnico:
1. ¿Qué tan bien se ejecutó el corte comparado con la descripción ideal?
2. ¿Qué aspectos quedaron bien?
3. ¿Qué aspectos específicos podrían mejorar y CÓMO?
4. ¿Qué debe pedirle al barbero en la próxima visita?

Sé específico, técnico y constructivo. Evita críticas vagas.

Responde ÚNICAMENTE con JSON válido, sin texto adicional:

{{
  "overallScore": 8.5,
  "verdict": "excellent|good|acceptable|needs_work",
  "scoreBreakdown": {{
    "shapeAccuracy": 8,
    "proportions": 9,
    "blendingTransitions": 7,
    "lineDefinition": 8,
    "textureAndFinish": 8,
    "styleMatch": 9
  }},
  "whatWorkedWell": [
    "Aspecto positivo 1 muy específico",
    "Aspecto positivo 2",
    "Aspecto positivo 3"
  ],
  "improvementAreas": [
    {{
      "area": "nombre del área técnica (ej: fade en sienes)",
      "issue": "qué está mal exactamente",
      "howToFix": "instrucción específica para el barbero para corregirlo"
    }}
  ],
  "overallFeedback": "Evaluación general de 2-3 oraciones: honesta, específica y constructiva.",
  "isCloseToIdeal": true,
  "nextAppointmentInstructions": "Texto exacto que puede mostrarle al barbero en la próxima visita para ajustar el corte.",
  "maintenanceTip": "Consejo específico para los próximos días/semanas para mantener este corte en su mejor forma.",
  "daysBetweenCuts": 21
}}"""

    return prompt
