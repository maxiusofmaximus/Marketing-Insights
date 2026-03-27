"""
LLM Service - Integración con modelos de lenguaje para respuestas inteligentes.
================================================================================
Toma los datos crudos del motor analítico y genera respuestas con
interpretación de negocio usando un LLM (Claude, OpenAI o Gemini).

Si no hay API key configurada, retorna las respuestas base del motor
analítico sin interpretación adicional.
"""

import os
import json
import httpx
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Prompt del sistema para el LLM
SYSTEM_PROMPT = """Eres un analista senior de marketing digital para CloudLabs Learning, 
una plataforma de laboratorios virtuales para educación STEM.

Tu rol es interpretar datos de comportamiento web y dar recomendaciones 
accionables al equipo de Marketing. 

REGLAS:
- Responde siempre en español
- Sé conciso pero útil (2-4 oraciones máximo)
- Siempre incluye una recomendación accionable
- Usa lenguaje simple, el equipo de Marketing no es técnico
- Menciona números específicos cuando los tengas
- Enfócate en el impacto para el negocio, no en lo técnico

FORMATO DE RESPUESTA:
[Dato principal con números]
[Interpretación de negocio / recomendación]
"""


class LLMService:
    """Genera interpretaciones de negocio usando un LLM."""

    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "ollama").lower()
        self.api_key = self._get_api_key()
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        self.is_available = self.provider == "ollama" or (self.api_key is not None and self.provider != "none")

        if self.is_available:
            if self.provider == "ollama":
                print(f"LLM local configurado: {self.ollama_model}")
            else:
                print(f"LLM configurado: {self.provider}")
        else:
            print("Sin LLM configurado. Respuestas serán sin interpretación de IA.")

    def _get_api_key(self) -> Optional[str]:
        if self.provider == "openai":
            return os.getenv("OPENAI_API_KEY")
        elif self.provider == "claude":
            return os.getenv("ANTHROPIC_API_KEY")
        elif self.provider == "gemini":
            return os.getenv("GEMINI_API_KEY")
        elif self.provider == "ollama":
            return "local"
        return None

    async def generate_interpretation(
        self, question: str, analytics_answer: str, raw_data: dict
    ) -> str:
        """
        Genera una interpretación de negocio para la respuesta analítica.
        Si no hay LLM, retorna la respuesta base.
        """
        if not self.is_available:
            return analytics_answer

        prompt = f"""El equipo de Marketing preguntó: "{question}"

Los datos muestran: {analytics_answer}

Datos detallados: {json.dumps(raw_data, ensure_ascii=False, default=str)[:2000]}

Genera una respuesta breve con el dato clave y una interpretación/recomendación 
accionable para el equipo de Marketing de CloudLabs."""

        try:
            if self.provider == "openai":
                return await self._call_openai(prompt)
            elif self.provider == "claude":
                return await self._call_claude(prompt)
            elif self.provider == "gemini":
                return await self._call_gemini(prompt)
            elif self.provider == "ollama":
                return await self._call_ollama(prompt)
        except Exception as e:
            print(f"Error LLM: {e}")
            return analytics_answer

        return analytics_answer

    async def _call_openai(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 300,
                    "temperature": 0.7,
                },
            )
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def _call_claude(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 300,
                    "system": SYSTEM_PROMPT,
                    "messages": [
                        {"role": "user", "content": prompt},
                    ],
                },
            )
            data = response.json()
            return data["content"][0]["text"]

    async def _call_gemini(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_key}",
                headers={"Content-Type": "application/json"},
                json={
                    "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                    "contents": [{"parts": [{"text": prompt}]}],
                },
            )
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    async def _call_ollama(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "system": SYSTEM_PROMPT,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.4},
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()
