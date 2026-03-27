"""
Marketing Copilot Backend - CloudLabs Hackathon Talento Tech 2026
================================================================
API REST que procesa datos de comportamiento web de Microsoft Clarity
y expone insights para el equipo de Marketing.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import analytics, chat, dashboard
from app.services.data_loader import DataLoader

# ─── Inicializar app ───────────────────────────────────────────
app = FastAPI(
    title="Marketing Copilot API",
    description="Co-piloto de Marketing impulsado por análisis de datos e IA",
    version="1.0.0",
)

# ─── CORS (para que Angular pueda consumir la API) ─────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, restringir al dominio de Angular
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Cargar datos al iniciar ───────────────────────────────────
data_loader = DataLoader()


@app.on_event("startup")
async def startup_event():
    """Carga y procesa el dataset al arrancar el servidor."""
    data_loader.load_data()
    print("Dataset cargado exitosamente")
    print(f"   {data_loader.total_sessions()} sesiones")
    print(f"   {data_loader.total_rows()} registros")
    print(f"   Columnas: {list(data_loader.df.columns)}")


# ─── Registrar routers ─────────────────────────────────────────
app.include_router(analytics.router, prefix="/api", tags=["Analytics"])
app.include_router(chat.router, prefix="/api", tags=["Chat / Copilot"])
app.include_router(dashboard.router, prefix="/api", tags=["Dashboard"])


@app.get("/")
async def root():
    return {
        "message": "Marketing Copilot API - CloudLabs",
        "docs": "/docs",
        "status": "running",
    }


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "dataset_loaded": data_loader.is_loaded,
        "total_rows": data_loader.total_rows() if data_loader.is_loaded else 0,
    }
