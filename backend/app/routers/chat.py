"""
Router del Chat - Endpoint principal del Co-piloto.
Recibe preguntas en lenguaje natural y devuelve respuestas con interpretación.
"""

from fastapi import APIRouter
from app.models.schemas import AskRequest, AskResponse, ChartData
from app.services.data_loader import DataLoader
from app.services.analytics_engine import AnalyticsEngine
from app.services.llm_service import LLMService
import math

router = APIRouter()

# Se inicializan lazy
_data_loader: DataLoader = None
_llm_service: LLMService = None


def get_engine() -> AnalyticsEngine:
    global _data_loader
    if _data_loader is None:
        from main import data_loader
        _data_loader = data_loader
    return AnalyticsEngine(_data_loader.df)


def get_llm() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


def sanitize_json_value(value):
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, dict):
        return {k: sanitize_json_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_json_value(v) for v in value]
    return value


@router.post("/ask", response_model=AskResponse)
async def ask_copilot(request: AskRequest):
    """
    Endpoint principal del Co-piloto.
    Recibe una pregunta en lenguaje natural y devuelve:
    - answer: respuesta con datos
    - interpretation: interpretación de negocio (con o sin LLM)
    - chart_data: datos para graficar (opcional)
    """
    engine = get_engine()
    llm = get_llm()

    # 1. El motor analítico interpreta la pregunta y ejecuta el análisis
    result = engine.answer_question(request.question)

    # 2. El LLM enriquece la respuesta con interpretación de negocio
    safe_data = sanitize_json_value(result.get("data", {}))

    interpretation = await llm.generate_interpretation(
        question=request.question,
        analytics_answer=result["answer"],
        raw_data=safe_data,
    )

    # 3. Preparar datos de gráfico si los hay
    chart_data = None
    if result.get("chart"):
        chart = sanitize_json_value(result["chart"])
        chart_data = ChartData(
            chart_type=chart["type"],
            labels=chart["labels"],
            values=chart["values"],
            label=chart.get("label", ""),
        )

    return AskResponse(
        answer=result["answer"],
        interpretation=interpretation,
        chart_data=chart_data,
    )


@router.get("/suggested-questions")
async def suggested_questions():
    """Retorna preguntas sugeridas para el usuario."""
    return {
        "questions": [
            "¿Cuál fue la página más visitada?",
            "¿Dónde abandonan más los usuarios?",
            "¿Cuál es el flujo de navegación más común?",
            "¿Cuál fue el producto más consultado?",
            "¿Cómo es la interacción promedio por página?",
            "¿Qué patrones de conversión hay hacia pricing?",
            "¿Desde qué dispositivos nos visitan más?",
            "¿Qué páginas atraen tráfico pero no retienen?",
            "¿A qué hora hay más engagement?",
            "Dame un resumen general del sitio",
        ]
    }
