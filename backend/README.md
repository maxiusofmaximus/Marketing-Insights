# Marketing Copilot Backend - CloudLabs

**Hackathon Talento Tech 2026** — Co-piloto de Marketing impulsado por análisis de datos e IA.

## Qué hace

API REST que procesa datos de comportamiento web de Microsoft Clarity y expone:
- **8 tipos de insights** analíticos (5 requeridos + 3 adicionales)
- **Chat endpoint** que responde preguntas en lenguaje natural
- **Dashboard endpoint** con resumen ejecutivo completo
- **Integración opcional con LLM** (Claude, OpenAI o Gemini)

## Requisitos

- Python 3.10+
- pip

## Instalación rápida

```bash
# 1. Clonar y entrar al directorio
cd marketing-copilot-backend

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate    # Mac/Linux
venv\Scripts\activate       # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. (Opcional) Configurar LLM
cp .env.example .env
# Editar .env con tu API key

# 5. Poner el dataset CSV en /data
# Si no hay CSV, genera datos de ejemplo automáticamente

# 6. Arrancar el servidor
uvicorn main:app --reload --port 8000
```

## Uso del Dataset

Coloca el CSV de Microsoft Clarity en la carpeta `data/`.  
El sistema detecta automáticamente las columnas y las normaliza.  
Si no hay CSV, genera datos de ejemplo para desarrollo.

## Endpoints

### Chat (Co-piloto)
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/ask` | Pregunta en lenguaje natural |
| GET | `/api/suggested-questions` | Preguntas sugeridas |

### Dashboard
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/dashboard` | Resumen completo para dashboard |

### Analytics
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/pages/top` | Páginas más visitadas |
| GET | `/api/products/top` | Productos más consultados |
| GET | `/api/abandono` | Puntos de abandono |
| GET | `/api/flujos` | Flujos de navegación |
| GET | `/api/interaccion` | Interacción promedio |
| GET | `/api/conversion` | Patrones de conversión |
| GET | `/api/segmentation` | Segmentación dispositivo/país |
| GET | `/api/trap-pages` | Páginas trampa |
| GET | `/api/engagement-hourly` | Engagement por hora |
| GET | `/api/dataset/info` | Info del dataset |

### Sistema
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Raíz |
| GET | `/api/health` | Estado del servidor |
| GET | `/docs` | Documentación Swagger |

## Ejemplo: POST /api/ask

```json
// Request
{ "question": "¿Cuál fue la página más visitada?" }

// Response
{
  "answer": "La página más visitada es '/home' con 540 vistas (18% del total).",
  "interpretation": "📊 /home lidera con 540 vistas...\n💡 Recomendación: optimizar el CTA...",
  "chart_data": {
    "chart_type": "horizontal_bar",
    "labels": ["/home", "/pricing", "/products", ...],
    "values": [540, 360, 300, ...],
    "label": "Vistas"
  }
}
```

## Estructura del proyecto

```
marketing-copilot-backend/
├── main.py                      # Punto de entrada FastAPI
├── requirements.txt             # Dependencias
├── .env.example                 # Template de variables de entorno
├── data/                        # Aquí va el CSV de Clarity
├── app/
│   ├── models/
│   │   └── schemas.py           # Modelos Pydantic (request/response)
│   ├── routers/
│   │   ├── analytics.py         # Endpoints de insights
│   │   ├── chat.py              # Endpoint del copilot (/ask)
│   │   └── dashboard.py         # Endpoint del dashboard
│   └── services/
│       ├── data_loader.py       # Carga y limpieza del CSV
│       ├── analytics_engine.py  # Motor de cálculo de métricas
│       └── llm_service.py       # Integración con LLM
└── docs/                        # Documentación adicional
```

## Tecnologías

- **FastAPI** — Framework web async
- **Pandas** — Análisis de datos
- **NumPy** — Procesamiento numérico
- **Pydantic** — Validación de datos
- **httpx** — Cliente HTTP async (para LLM)
- **uvicorn** — Servidor ASGI

## Equipo

Hackathon Talento Tech 2026 — Reto Caldas
