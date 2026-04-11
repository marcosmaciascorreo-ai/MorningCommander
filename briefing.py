"""
briefing.py — Genera el mensaje de briefing diario
Obtiene clima, tipo de cambio, noticias (con Claude) y tareas.
"""

import asyncio
import re
import requests
import feedparser
from datetime import datetime

import anthropic

from config import ANTHROPIC_API_KEY, CIUDAD_LAT, CIUDAD_LON, CIUDAD_NAME
import db

# ── TRADUCCIONES ──────────────────────────────────────────────────────────────

WEATHERCODES: dict[int, str] = {
    0:  "Despejado ☀️",
    1:  "Mayormente despejado 🌤️",
    2:  "Parcialmente nublado ⛅",
    3:  "Nublado ☁️",
    45: "Niebla 🌫️",
    48: "Niebla con escarcha 🌫️",
    51: "Llovizna ligera 🌦️",
    53: "Llovizna moderada 🌦️",
    55: "Llovizna intensa 🌦️",
    61: "Lluvia ligera 🌧️",
    63: "Lluvia moderada 🌧️",
    65: "Lluvia intensa 🌧️",
    71: "Nieve ligera 🌨️",
    73: "Nieve moderada 🌨️",
    75: "Nieve intensa 🌨️",
    80: "Chubascos ligeros 🌦️",
    81: "Chubascos moderados 🌦️",
    82: "Chubascos violentos 🌦️",
    95: "Tormenta eléctrica ⛈️",
    99: "Tormenta con granizo ⛈️",
}

DIAS_ES   = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES_ES  = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
]


# ── CLIMA ─────────────────────────────────────────────────────────────────────

def _get_clima_sync() -> dict:
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={CIUDAD_LAT}&longitude={CIUDAD_LON}"
            f"&daily=temperature_2m_max,temperature_2m_min,weathercode,windspeed_10m_max"
            f"&hourly=relativehumidity_2m"
            f"&timezone=America%2FChihuahua"
            f"&forecast_days=1"
        )
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()

        daily = data["daily"]
        temp_max = round(daily["temperature_2m_max"][0])
        temp_min = round(daily["temperature_2m_min"][0])
        wcode    = int(daily["weathercode"][0])
        wind     = round(daily["windspeed_10m_max"][0])

        hourly_hum = data.get("hourly", {}).get("relativehumidity_2m", [])
        humidity = round(sum(hourly_hum) / len(hourly_hum)) if hourly_hum else 0

        condicion = WEATHERCODES.get(wcode, f"Código {wcode}")

        return {
            "temp_min":  temp_min,
            "temp_max":  temp_max,
            "condicion": condicion,
            "viento":    wind,
            "humedad":   humidity,
            "ok":        True,
        }
    except Exception:
        return {
            "temp_min":  "--",
            "temp_max":  "--",
            "condicion": "No disponible",
            "viento":    "--",
            "humedad":   "--",
            "ok":        False,
        }


# ── TIPO DE CAMBIO ────────────────────────────────────────────────────────────

def _get_tipo_cambio_sync() -> dict:
    try:
        resp = requests.get(
            "https://api.exchangerate-api.com/v4/latest/USD",
            timeout=5
        )
        resp.raise_for_status()
        data  = resp.json()
        rates = data["rates"]

        mxn        = float(rates.get("MXN", 0))
        eur_factor = float(rates.get("EUR", 1))  # EUR per 1 USD
        # EUR/MXN = (MXN per USD) / (EUR per USD)
        eur_mxn = mxn / eur_factor if eur_factor else 0

        return {"usd_mxn": f"{mxn:.2f}", "eur_mxn": f"{eur_mxn:.2f}", "ok": True}
    except Exception:
        return {"usd_mxn": "--", "eur_mxn": "--", "ok": False}


# ── NOTICIAS ──────────────────────────────────────────────────────────────────

RSS_FEEDS = [
    "https://feeds.bbci.co.uk/mundo/rss.xml",
    "https://www.elfinanciero.com.mx/arc/outboundfeeds/rss/",
]


def _clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _get_noticias_raw_sync() -> list[str]:
    titulares: list[str] = []
    for feed_url in RSS_FEEDS:
        try:
            resp = requests.get(feed_url, timeout=5)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:5]:
                titulo  = _clean_html(entry.get("title", "")).strip()
                resumen = _clean_html(
                    entry.get("summary", entry.get("description", ""))
                )[:200].strip()
                if titulo:
                    titulares.append(f"TITULAR: {titulo}\nRESUMEN: {resumen}")
        except Exception:
            continue
    return titulares[:10]


def _generar_resumen_claude_sync(titulares_raw: list[str]) -> str | None:
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        prompt = (
            "Eres el editor de un briefing matutino personal.\n"
            "Tienes estos titulares y resúmenes de noticias del día:\n\n"
            + "\n\n".join(titulares_raw)
            + "\n\nTu tarea:\n"
            "1. Elige las 4 noticias MÁS importantes e impactantes\n"
            "2. Agrúpalas por tema con un emoji y categoría: POLÍTICA MX, ECONOMÍA, TECNOLOGÍA, MUNDO, etc.\n"
            "3. Para cada noticia escribe 2 líneas MÁXIMO: primera línea el hecho, segunda línea el por qué importa o qué sigue\n"
            "4. Estilo: directo, sin rodeos, como TikTok — nada de \"según fuentes\" ni relleno\n"
            "5. NO uses markdown, NO uses asteriscos, solo texto plano con saltos de línea\n"
            "6. Formato exacto por noticia:\n"
            "[EMOJI] [CATEGORÍA EN MAYÚSCULAS]\n"
            "[Hecho principal en una línea]\n"
            "[Por qué importa o qué sigue en una línea]\n\n"
            "Responde SOLO con las 4 noticias formateadas, sin introducción ni cierre."
        )
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception:
        return None


def _fallback_noticias(titulares: list[str]) -> str:
    """Muestra los primeros 4 titulares crudos si Claude falla."""
    lines = []
    for raw in titulares[:4]:
        # Extract just the title line
        titulo = raw.split("\n")[0].replace("TITULAR: ", "").strip()
        if titulo:
            lines.append(f"• {titulo}")
    return "\n".join(lines) if lines else "📰 Noticias no disponibles."


# ── ENSAMBLAJE DEL BRIEFING ───────────────────────────────────────────────────

async def generar_briefing() -> str:
    """Genera el mensaje completo del briefing. Async para no bloquear el bot."""
    now = datetime.now()

    # Fecha en español
    dia_semana = DIAS_ES[now.weekday()]
    dia        = now.day
    mes        = MESES_ES[now.month - 1]
    semana     = now.isocalendar()[1]

    # Fetch externo en paralelo (no bloquea el event loop)
    clima, cambio, titulares = await asyncio.gather(
        asyncio.to_thread(_get_clima_sync),
        asyncio.to_thread(_get_tipo_cambio_sync),
        asyncio.to_thread(_get_noticias_raw_sync),
    )

    # Generar resumen de noticias con Claude (o fallback)
    if ANTHROPIC_API_KEY and titulares:
        noticias_str = await asyncio.to_thread(
            _generar_resumen_claude_sync, titulares
        )
        if not noticias_str:
            noticias_str = _fallback_noticias(titulares)
    elif titulares:
        noticias_str = _fallback_noticias(titulares)
    else:
        noticias_str = "📰 Noticias no disponibles en este momento."

    # Datos locales (SQLite — rápido, OK en hilo principal)
    tareas = db.obtener_tareas()
    frase_texto, frase_autor = db.obtener_frase()

    if tareas:
        tareas_str = "\n".join(f"{i + 1}. {t[1]}" for i, t in enumerate(tareas))
    else:
        tareas_str = "Sin tareas pendientes. ¡Día libre! 🎯"

    mensaje = (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"☀️ BUENOS DÍAS, MARCOS\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 {dia_semana} {dia} de {mes} · Semana {semana}\n"
        f"\n"
        f"🌤️ {CIUDAD_NAME.upper()} — HOY\n"
        f"🌡️ {clima['temp_min']}°C → {clima['temp_max']}°C · {clima['condicion']}\n"
        f"💨 Viento {clima['viento']} km/h · 💧 Humedad {clima['humedad']}%\n"
        f"\n"
        f"💵 TIPO DE CAMBIO\n"
        f"🇺🇸 USD/MXN: ${cambio['usd_mxn']}\n"
        f"🇪🇺 EUR/MXN: ${cambio['eur_mxn']}\n"
        f"\n"
        f"📲 LO QUE PASÓ HOY\n"
        f"━━━━━━━━━━━━\n"
        f"{noticias_str}\n"
        f"━━━━━━━━━━━━\n"
        f"\n"
        f"✅ TUS TAREAS DE HOY\n"
        f"{tareas_str}\n"
        f"\n"
        f"💬 FRASE DEL DÍA\n"
        f'"{frase_texto}"\n'
        f"— {frase_autor}\n"
        f"\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"/tarea para agregar algo nuevo"
    )

    return mensaje
