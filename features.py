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

# Catalogo curado con links verificados (Spotify direct o search)
PODCASTS_CURADOS = [
    {
        "nombre": "Leyendas Legendarias",
        "genero": "comedia, cultura pop mexicana, humor",
        "link": "https://open.spotify.com/show/2Dp0p9JElM2NzpNm8EWKEZ",
    },
    {
        "nombre": "Relatos del Lado Oscuro",
        "genero": "historias de terror, misterio y crimen real",
        "link": "https://open.spotify.com/show/4rOoJ6Egrf8K2IrywzwOMk",
    },
    {
        "nombre": "True Crime Mexico",
        "genero": "crimen real en Mexico, investigaciones",
        "link": "https://open.spotify.com/search/True%20Crime%20Mexico",
    },
    {
        "nombre": "Cosas de Internet",
        "genero": "cultura internet, memes, fenomenos virales",
        "link": "https://open.spotify.com/search/Cosas%20de%20Internet%20podcast",
    },
    {
        "nombre": "El Podcast de Historia",
        "genero": "historia fascinante contada de forma entretenida",
        "link": "https://open.spotify.com/search/El%20Podcast%20de%20Historia",
    },
    {
        "nombre": "No Hay Tos",
        "genero": "comedia mexicana, anecdotas, entrevistas",
        "link": "https://open.spotify.com/search/No%20Hay%20Tos%20podcast",
    },
    {
        "nombre": "Crimenes que Estremecieron a Mexico",
        "genero": "crimen real, casos policiales mexicanos",
        "link": "https://open.spotify.com/search/Crimenes%20que%20Estremecieron%20a%20Mexico",
    },
    {
        "nombre": "Pendientes",
        "genero": "storytelling latinoamericano, historias reales impactantes",
        "link": "https://open.spotify.com/search/Pendientes%20podcast%20mexico",
    },
    {
        "nombre": "El Explicador",
        "genero": "datos curiosos, ciencia pop, cosas raras del mundo",
        "link": "https://open.spotify.com/search/El%20Explicador%20podcast",
    },
    {
        "nombre": "Malas Noticias",
        "genero": "humor negro, noticias absurdas comentadas",
        "link": "https://open.spotify.com/search/Malas%20Noticias%20podcast%20mexico",
    },
]


def _recomendar_podcasts_sync() -> str:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)

        catalogo_texto = "\n".join(
            f'{i+1}. {p["nombre"]} ({p["genero"]})'
            for i, p in enumerate(PODCASTS_CURADOS)
        )

        prompt = (
            "De este catalogo de podcasts, elige 3 que se vean mas interesantes HOY "
            "para un mexicano de 30 anos que quiere entretenerse, no aprender ni mejorar.\n\n"
            f"CATALOGO:\n{catalogo_texto}\n\n"
            "Para cada uno, sugiere UN episodio especifico (real o tipico del podcast) "
            "y explica en 1 linea por que engancha.\n\n"
            "Responde solo con los 3 bloques, sin introducciones. "
            "Formato exacto por podcast:\n"
            "NOMBRE\n"
            "Episodio: [titulo del episodio]\n"
            "Por que escucharlo: [1 linea]\n"
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        gpt_text = response.choices[0].message.content.strip()

        # Adjuntar links del catalogo a los nombres que aparezcan en la respuesta
        links_agregados = set()
        lineas_con_links = []
        for linea in gpt_text.splitlines():
            lineas_con_links.append(linea)
            for p in PODCASTS_CURADOS:
                if p["nombre"].lower() in linea.lower() and p["nombre"] not in links_agregados:
                    lineas_con_links.append(f"Escucharlo: {p['link']}")
                    links_agregados.add(p["nombre"])
                    break

        return "\n".join(lineas_con_links)

    except Exception:
        return "No se pudieron generar recomendaciones en este momento. Intenta de nuevo."


async def recomendar_podcasts() -> str:
    return await asyncio.to_thread(_recomendar_podcasts_sync)


# ── ACTIVIDADES DE FIN DE SEMANA ──────────────────────────────────────────────

def _actividades_finde_sync() -> str:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        from datetime import date
        hoy = date.today()
        dias = {0: "lunes", 1: "martes", 2: "miercoles", 3: "jueves",
                4: "viernes", 5: "sabado", 6: "domingo"}
        dia_semana = dias[hoy.weekday()]
        mes = hoy.strftime("%B")

        prompt = (
            f"Sugiere 5 actividades o salidas para este fin de semana en Chihuahua, Mexico. "
            f"Hoy es {dia_semana} {hoy.day} de {mes}.\n\n"
            "Mezcla opciones de distintos tipos:\n"
            "- Restaurantes o lugares para comer/cenar especificos de Chihuahua\n"
            "- Actividades al aire libre (parques, cerros, colonias)\n"
            "- Cultura o entretenimiento (museos, cine, eventos)\n"
            "- Algo diferente o poco conocido\n"
            "- Una opcion relajada para quedarse cerca de casa\n\n"
            "Formato por actividad:\n"
            "NOMBRE O LUGAR\n"
            "Tipo: [comer / aire libre / cultura / plan diferente / relajado]\n"
            "Por que ir: [1 linea]\n"
            "Tip: [detalle practico: horario, costo aprox, recomendacion]\n\n"
            "Que sean lugares reales de Chihuahua. Sin asteriscos ni guiones."
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=700,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "No pude generar sugerencias en este momento. Intenta de nuevo."


async def actividades_finde() -> str:
    return await asyncio.to_thread(_actividades_finde_sync)
