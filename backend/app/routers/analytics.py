"""
Router de Analytics - Endpoints para cada tipo de insight.
"""

from fastapi import APIRouter, Query, UploadFile, File, HTTPException
from pathlib import Path
from app.services.data_loader import DataLoader
from app.services.analytics_engine import AnalyticsEngine

router = APIRouter()

# Referencia global al data loader (se inicializa en main.py)
_data_loader: DataLoader = None
DATA_DIR = Path("data")


def get_engine() -> AnalyticsEngine:
    global _data_loader
    if _data_loader is None:
        from main import data_loader
        _data_loader = data_loader
    return AnalyticsEngine(_data_loader.df)


# ─── INSIGHT 1: Páginas y Productos Top ───────────────────────

@router.get("/pages/top")
async def top_pages(limit: int = Query(10, ge=1, le=50)):
    """Ranking de páginas con más vistas e interacciones."""
    engine = get_engine()
    return {"data": engine.get_top_pages(limit), "insight": "top_pages"}


@router.get("/products/top")
async def top_products(limit: int = Query(10, ge=1, le=50)):
    """Ranking de productos más consultados."""
    engine = get_engine()
    return {"data": engine.get_top_products(limit), "insight": "top_products"}


# ─── INSIGHT 2: Puntos de Abandono ────────────────────────────

@router.get("/abandono")
async def abandono(limit: int = Query(10, ge=1, le=50)):
    """Páginas con mayor tasa de salida/abandono."""
    engine = get_engine()
    return {"data": engine.get_abandono(limit), "insight": "abandono"}


# ─── INSIGHT 3: Flujos de Navegación ─────────────────────────

@router.get("/flujos")
async def flujos(
    limit: int = Query(10, ge=1, le=50),
    length: int = Query(3, ge=2, le=5),
):
    """Secuencias de navegación más frecuentes."""
    engine = get_engine()
    return {"data": engine.get_flujos(limit, length), "insight": "flujos"}


# ─── INSIGHT 4: Interacción Promedio ──────────────────────────

@router.get("/interaccion")
async def interaccion(limit: int = Query(15, ge=1, le=50)):
    """Métricas promedio de interacción por página."""
    engine = get_engine()
    return {"data": engine.get_interaccion(limit), "insight": "interaccion"}


# ─── INSIGHT 5: Patrones de Conversión ───────────────────────

@router.get("/conversion")
async def conversion():
    """Comportamiento hacia páginas de alto interés."""
    engine = get_engine()
    return {"data": engine.get_conversion(), "insight": "conversion"}


# ─── INSIGHT 6: Segmentación ─────────────────────────────────

@router.get("/segmentation")
async def segmentation():
    """Distribución por dispositivo, país y navegador."""
    engine = get_engine()
    return {"data": engine.get_segmentation(), "insight": "segmentation"}


# ─── INSIGHT 7: Páginas Trampa ───────────────────────────────

@router.get("/trap-pages")
async def trap_pages(limit: int = Query(10, ge=1, le=50)):
    """Páginas con alto tráfico pero bajo engagement."""
    engine = get_engine()
    return {"data": engine.get_trap_pages(limit), "insight": "trap_pages"}


# ─── INSIGHT 8: Engagement por Hora ──────────────────────────

@router.get("/engagement-hourly")
async def engagement_hourly():
    """Engagement promedio por hora del día."""
    engine = get_engine()
    return {"data": engine.get_engagement_by_hour(), "insight": "engagement_hourly"}


# ─── Dataset Info ────────────────────────────────────────────

@router.get("/dataset/info")
async def dataset_info():
    """Información sobre el dataset cargado."""
    global _data_loader
    if _data_loader is None:
        from main import data_loader
        _data_loader = data_loader
    return {
        "columns": _data_loader.get_columns(),
        "total_rows": _data_loader.total_rows(),
        "total_sessions": _data_loader.total_sessions(),
        "is_loaded": _data_loader.is_loaded,
    }


@router.post("/dataset/upload")
async def dataset_upload(
    recordings_file: UploadFile = File(...),
    metrics_file: UploadFile | None = File(default=None),
):
    global _data_loader
    if _data_loader is None:
        from main import data_loader
        _data_loader = data_loader

    if not recordings_file.filename or not recordings_file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="recordings_file debe ser CSV")

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    recordings_path = DATA_DIR / "1_Data_Recordings.csv"
    recordings_content = await recordings_file.read()
    recordings_path.write_bytes(recordings_content)

    if metrics_file is not None:
        if not metrics_file.filename or not metrics_file.filename.lower().endswith(".csv"):
            raise HTTPException(status_code=400, detail="metrics_file debe ser CSV")
        metrics_path = DATA_DIR / "2_Data_Metrics.csv"
        metrics_content = await metrics_file.read()
        metrics_path.write_bytes(metrics_content)

    _data_loader.load_data(str(recordings_path))

    return {
        "status": "ok",
        "total_rows": _data_loader.total_rows(),
        "total_sessions": _data_loader.total_sessions(),
        "columns": _data_loader.get_columns(),
    }
