"""
features.py — Funcionalidades adicionales de Morning Commander
- Asistente SAP/Excel para maquiladora
- Recomendaciones de podcasts entretenidos
"""

import asyncio
from openai import OpenAI
from config import OPENAI_API_KEY


# ── SAP / EXCEL HELPER ────────────────────────────────────────────────────────

def _consulta_sap_excel_sync(descripcion: str) -> str:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=600,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un experto en SAP ERP y Excel para el area de finanzas "
                        "en empresas maquiladoras de Mexico (industria manufacturera).\n\n"
                        "Cuando el usuario describe una situacion o problema:\n"
                        "1. Identifica la transaccion SAP exacta si aplica "
                        "(FB60, F-43, MB51, VF01, MIRO, F110, etc.)\n"
                        "2. Da los pasos exactos en orden numerado\n"
                        "3. Menciona los campos criticos a llenar\n"
                        "4. Si es Excel: da la formula exacta lista para copiar\n"
                        "5. Advierte el error mas comun en 1 linea\n\n"
                        "Responde en espanol. Maximo 15 lineas. Sin markdown ni asteriscos."
                    ),
                },
                {"role": "user", "content": descripcion},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"No pude procesar la consulta. Intenta de nuevo. ({e})"


async def consulta_sap_excel(descripcion: str) -> str:
    return await asyncio.to_thread(_consulta_sap_excel_sync, descripcion)


# ── RECOMENDACIONES DE PODCASTS ───────────────────────────────────────────────

def _recomendar_podcasts_sync() -> str:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        prompt = (
            "Recomienda 3 podcasts o episodios MUY especificos y reales "
            "para un mexicano de 30 anos que busca entretenimiento y distraccion.\n\n"
            "Lo que quiere escuchar:\n"
            "- Historias reales fascinantes o casos de crimen\n"
            "- Humor, cultura pop, entretenimiento\n"
            "- Datos curiosos y raros del mundo\n"
            "- Storytelling que engancha\n"
            "NO quiere: productividad, finanzas, crossfit, autoayuda.\n\n"
            "Formato para cada recomendacion (texto plano, sin asteriscos ni guiones):\n\n"
            "NOMBRE DEL PODCAST\n"
            "Episodio recomendado: [nombre especifico del episodio]\n"
            "Por que vale la pena: [1 linea]\n"
            "Disponible en: [Spotify / YouTube / Apple Podcasts]\n\n"
            "Que sean reales, verificables y disponibles hoy. "
            "Prioriza podcasts en espanol o latinoamericanos."
        )
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "No se pudieron generar recomendaciones en este momento. Intenta de nuevo."


async def recomendar_podcasts() -> str:
    return await asyncio.to_thread(_recomendar_podcasts_sync)
