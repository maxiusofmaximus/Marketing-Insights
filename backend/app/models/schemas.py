"""
Modelos de datos (schemas) para requests y responses de la API.
Pydantic valida automáticamente los datos que entran y salen.
"""

from pydantic import BaseModel
from typing import Optional


# ─── REQUEST ───────────────────────────────────────────────────

class AskRequest(BaseModel):
    """Pregunta del usuario en lenguaje natural."""
    question: str

    class Config:
        json_schema_extra = {
            "example": {
                "question": "¿Cuál fue la página con más visitas?"
            }
        }


# ─── RESPONSES ─────────────────────────────────────────────────

class ChartData(BaseModel):
    """Datos para renderizar un gráfico en el frontend."""
    chart_type: str  # "bar", "horizontal_bar", "pie", "line"
    labels: list[str]
    values: list[float]
    label: str = ""  # Nombre de la serie


class AskResponse(BaseModel):
    """Respuesta del copilot a una pregunta."""
    answer: str
    interpretation: str
    chart_data: Optional[ChartData] = None


class PageMetric(BaseModel):
    page: str
    views: int
    interactions: int = 0


class AbandonoMetric(BaseModel):
    page: str
    exit_count: int
    total_visits: int
    exit_rate: float  # Porcentaje 0-100


class FlujoMetric(BaseModel):
    sequence: list[str]
    count: int
    percentage: float


class InteraccionMetric(BaseModel):
    page: str
    avg_clicks: float
    avg_scroll: float
    avg_time: float  # segundos


class ConversionMetric(BaseModel):
    page: str
    sessions_reached: int
    total_sessions: int
    reach_rate: float
    avg_engagement_before: float


class DashboardResponse(BaseModel):
    total_sessions: int
    total_users: int
    avg_pages_per_session: float
    avg_session_duration: float  # segundos
    avg_bounce_rate: float
    top_pages: list[PageMetric]
    top_abandono: list[AbandonoMetric]
    top_countries: list[dict]
    top_devices: list[dict]


class InsightExtra(BaseModel):
    title: str
    description: str
    value: str
    recommendation: str
    chart_data: Optional[ChartData] = None
