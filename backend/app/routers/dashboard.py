"""
Router del Dashboard - Resumen ejecutivo para la vista principal.
"""

from fastapi import APIRouter
from app.services.data_loader import DataLoader
from app.services.analytics_engine import AnalyticsEngine
import math

router = APIRouter()

_data_loader: DataLoader = None


def get_engine() -> AnalyticsEngine:
    global _data_loader
    if _data_loader is None:
        from main import data_loader
        _data_loader = data_loader
    return AnalyticsEngine(_data_loader.df)


def sanitize_json_value(value):
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, dict):
        return {k: sanitize_json_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_json_value(v) for v in value]
    return value


@router.get("/dashboard")
async def dashboard():
    """
    Retorna todos los datos necesarios para el dashboard principal.
    Un solo endpoint que el frontend consume al cargar.
    """
    engine = get_engine()

    payload = {
        "summary": engine.get_dashboard_summary(),
        "top_pages": engine.get_top_pages(10),
        "top_products": engine.get_top_products(5),
        "abandono": engine.get_abandono(10),
        "flujos": engine.get_flujos(5),
        "interaccion": engine.get_interaccion(10),
        "conversion": engine.get_conversion(),
        "segmentation": engine.get_segmentation(),
        "trap_pages": engine.get_trap_pages(5),
        "engagement_hourly": engine.get_engagement_by_hour(),
    }
    return sanitize_json_value(payload)
