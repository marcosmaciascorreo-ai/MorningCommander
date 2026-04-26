"""
briefing.py — Genera el briefing matutino y vespertino de Morning Commander
"""

import asyncio
import re
import requests
import feedparser
from datetime import datetime, timedelta

from openai import OpenAI

from config import OPENAI_API_KEY, CIUDAD_LAT, CIUDAD_LON, CIUDAD_NAME
import db

# ── TRADUCCIONES ──────────────────────────────────────────────────────────────

WEATHERCODES: dict[int, str] = {
    0:  "Despejado",
    1:  "Mayormente despejado",
    2:  "Parcialmente nublado",
    3:  "Nublado",
    45: "Niebla",
    48: "Niebla con escarcha",
    51: "Llovizna ligera",
    53: "Llovizna",
    55: "Llovizna intensa",
    61: "Lluvia ligera",
    63: "Lluvia",
    65: "Lluvia intensa",
    71: "Nieve ligera",
    73: "Nieve",
    75: "Nieve intensa",
    80: "Chubascos",
    81: "Chubascos",
    82: "Chubascos fuertes",
    95: "Tormenta",
    99: "Tormenta con granizo",
}

WEATHER_EMOJI: dict[int, str] = {
    0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️",
    45: "🌫️", 48: "🌫️",
    51: "🌦️", 53: "🌦️", 55: "🌦️",
    61: "🌧️", 63: "🌧️", 65: "🌧️",
    71: "🌨️", 73: "🌨️", 75: "🌨️",
    80: "🌦️", 81: "🌦️", 82: "🌦️",
    95: "⛈️", 99: "⛈️",
}

DIAS_ES  = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]
MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

# ── RSS FEEDS — MEXICO Y CHIHUAHUA ────────────────────────────────────────────

RSS_FEEDS_MX = [
    "https://www.eluniversal.com.mx/arc/outboundfeeds/rss/",
    "https://www.animalpolitico.com/feed",
    "https://www.elfinanciero.com.mx/arc/outboundfeeds/rss/",
    "https://www.jornada.com.mx/rss/edicion.xml",
]

RSS_FEEDS_CHI = [
    "https://www.nortedigital.mx/feed/",
    "https://www.elheraldodechihuahua.com.mx/rss",
]


# ── CLIMA 3 DIAS ──────────────────────────────────────────────────────────────

def _get_clima_3dias_sync() -> list[dict]:
    try:
        # Solicitar ambos nombres de campo (API antigua y nueva)
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={CIUDAD_LAT}&longitude={CIUDAD_LON}"
            f"&daily=temperature_2m_max,temperature_2m_min,weather_code,weathercode"
            f"&hourly=relativehumidity_2m,windspeed_10m"
            f"&timezone=America%2FChihuahua"
            f"&forecast_days=3"
        )
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data  = resp.json()
        daily = data["daily"]

        # Soporte para campo renombrado en la API de Open-Meteo
        wcodes_raw = daily.get("weather_code") or daily.get("weathercode") or []

        hourly_hum  = data.get("hourly", {}).get("relativehumidity_2m", [])
        hourly_wind = data.get("hourly", {}).get("windspeed_10m", [])
        humedad = round(sum(hourly_hum[:24])  / 24) if hourly_hum  else 0
        viento  = round(sum(hourly_wind[:24]) / 24) if hourly_wind else 0

        dias = []
        for i in range(3):
            wcode = int(wcodes_raw[i]) if i < len(wcodes_raw) else 0
            dias.append({
                "temp_min":  round(daily["temperature_2m_min"][i]),
                "temp_max":  round(daily["temperature_2m_max"][i]),
                "condicion": WEATHERCODES.get(wcode, "Variable"),
                "emoji":     WEATHER_EMOJI.get(wcode, "🌡️"),
                "humedad":   humedad if i == 0 else 0,
                "viento":    viento  if i == 0 else 0,
                "ok":        True,
            })
        return dias
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Error clima: {e}")
        fallback = {"temp_min": "--", "temp_max": "--", "condicion": "No disponible",
                    "emoji": "🌡️", "humedad": 0, "viento": 0, "ok": False}
        return [fallback, fallback, fallback]


# ── TIPO DE CAMBIO ────────────────────────────────────────────────────────────

def _get_tipo_cambio_sync() -> dict:
    try:
        resp = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=10)
        resp.raise_for_status()
        rates      = resp.json()["rates"]
        mxn        = float(rates.get("MXN", 0))
        eur_factor = float(rates.get("EUR", 1))
        eur_mxn    = mxn / eur_factor if eur_factor else 0
        return {"usd_mxn": f"{mxn:.2f}", "eur_mxn": f"{eur_mxn:.2f}", "ok": True}
    except Exception:
        return {"usd_mxn": "--", "eur_mxn": "--", "ok": False}


# ── NOTICIAS ──────────────────────────────────────────────────────────────────

def _clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _get_noticias_raw_sync() -> dict:
    result = {"mx": [], "chi": []}

    for feed_url in RSS_FEEDS_MX:
        try:
            resp = requests.get(feed_url, timeout=5)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:4]:
                titulo  = _clean_html(entry.get("title", "")).strip()
                resumen = _clean_html(
                    entry.get("summary", entry.get("description", ""))
                )[:150].strip()
                if titulo:
                    result["mx"].append(f"TITULAR: {titulo}\nRESUMEN: {resumen}")
        except Exception:
            continue

    for feed_url in RSS_FEEDS_CHI:
        try:
            resp = requests.get(feed_url, timeout=5)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:3]:
                titulo = _clean_html(entry.get("title", "")).strip()
                if titulo:
                    result["chi"].append(f"TITULAR: {titulo}")
        except Exception:
            continue

    return result


def _generar_resumen_openai_sync(noticias_raw: dict) -> str | None:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)

        titulares_mx  = "\n\n".join(noticias_raw["mx"][:8])
        titulares_chi = "\n".join(noticias_raw["chi"][:3])

        prompt = (
            f"Eres el editor de un briefing matutino para un hombre en {CIUDAD_NAME}, Mexico.\n\n"
            "NOTICIAS NACIONALES:\n" + titulares_mx
            + ("\n\nNOTICIAS CHIHUAHUA:\n" + titulares_chi if titulares_chi else "")
            + "\n\nSelecciona 4 noticias priorizando:\n"
            "1. Chihuahua local si hay algo relevante\n"
            "2. Mexico: politica, economia, seguridad\n"
            "3. Mundo solo si es muy impactante\n\n"
            "FORMATO EXACTO — una noticia por bloque:\n"
            "[EMOJI] [CATEGORIA EN MAYUSCULAS]\n"
            "[UN RENGLON: hecho + consecuencia o dato clave]\n\n"
            "Ejemplo:\n"
            "ECONOMIA\n"
            "Peso cae 0.8% tras decision de la Fed — creditos bancarios podrian encarecerse.\n\n"
            "Reglas: 1 renglon por noticia, sin asteriscos, sin markdown, sin introduccion ni cierre."
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=280,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return None


def _fallback_noticias(noticias_raw: dict) -> str:
    todas = noticias_raw["mx"][:3] + noticias_raw["chi"][:1]
    lines = []
    for raw in todas[:4]:
        titulo = raw.split("\n")[0].replace("TITULAR: ", "").strip()
        if titulo:
            lines.append(f"- {titulo}")
    return "\n".join(lines) if lines else "Noticias no disponibles en este momento."


# ── CALENDARIO (iCal) ─────────────────────────────────────────────────────────

def _get_eventos_calendario_sync(dias_adelante: int = 0) -> list[dict]:
    ical_url = db.get_config("ical_url", "")
    if not ical_url:
        return []
    try:
        import icalendar
        resp   = requests.get(ical_url, timeout=5)
        resp.raise_for_status()
        cal    = icalendar.Calendar.from_ical(resp.content)
        target = (datetime.now() + timedelta(days=dias_adelante)).date()

        eventos = []
        for comp in cal.walk():
            if comp.name != "VEVENT":
                continue
            dtstart = comp.get("dtstart")
            if not dtstart:
                continue
            dt         = dtstart.dt
            event_date = dt.date() if hasattr(dt, "date") else dt
            if event_date == target:
                hora   = dt.strftime("%H:%M") if hasattr(dt, "hour") else "Todo el dia"
                titulo = str(comp.get("summary", "Sin titulo"))
                eventos.append({"hora": hora, "titulo": titulo})

        return sorted(eventos, key=lambda x: x["hora"])
    except ImportError:
        return []
    except Exception:
        return []


# ── BRIEFING MATUTINO ─────────────────────────────────────────────────────────

async def generar_briefing() -> str:
    now        = datetime.now()
    dia_semana = DIAS_ES[now.weekday()]
    dia        = now.day
    mes        = MESES_ES[now.month - 1]
    semana     = now.isocalendar()[1]
    es_lunes   = now.weekday() == 0

    # Fetch paralelo
    dias_clima, cambio, noticias_raw = await asyncio.gather(
        asyncio.to_thread(_get_clima_3dias_sync),
        asyncio.to_thread(_get_tipo_cambio_sync),
        asyncio.to_thread(_get_noticias_raw_sync),
    )

    # Noticias con GPT o fallback
    if OPENAI_API_KEY and (noticias_raw["mx"] or noticias_raw["chi"]):
        noticias_str = await asyncio.to_thread(_generar_resumen_openai_sync, noticias_raw)
        if not noticias_str:
            noticias_str = _fallback_noticias(noticias_raw)
    else:
        noticias_str = _fallback_noticias(noticias_raw)

    # Calendario hoy
    eventos_hoy = await asyncio.to_thread(_get_eventos_calendario_sync, 0)

    # DB sync
    tareas = db.obtener_tareas()
    frase_texto, frase_autor = db.obtener_frase()

    # Clima 3 dias
    hoy_c  = dias_clima[0]
    man_c  = dias_clima[1]
    pman_c = dias_clima[2]
    lbl_man  = DIAS_ES[(now.weekday() + 1) % 7][:3]
    lbl_pman = DIAS_ES[(now.weekday() + 2) % 7][:3]

    tareas_str = (
        "\n".join(f"{i+1}. {t[1]}" for i, t in enumerate(tareas))
        if tareas else "Sin tareas pendientes. Dia libre!"
    )

    # Seccion agenda hoy
    agenda_str = ""
    if eventos_hoy:
        lineas = "\n".join(f"   {ev['hora']}  {ev['titulo']}" for ev in eventos_hoy)
        agenda_str = f"\n📅 TU AGENDA HOY\n{lineas}\n"

    # Seccion especial lunes: agenda de toda la semana
    lunes_str = ""
    if es_lunes:
        lineas_semana = []
        for d in range(1, 5):
            evs = await asyncio.to_thread(_get_eventos_calendario_sync, d)
            if evs:
                lbl = DIAS_ES[(now.weekday() + d) % 7][:3]
                for ev in evs[:2]:
                    lineas_semana.append(f"   {lbl}  {ev['hora']}  {ev['titulo']}")
        if lineas_semana:
            lunes_str = "\n📋 TU SEMANA\n" + "\n".join(lineas_semana) + "\n"

    mensaje = (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"☀️ BUENOS DIAS, MARCOS\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 {dia_semana} {dia} de {mes} · Semana {semana}\n"
        f"\n"
        f"🌤️ {CIUDAD_NAME.upper()} — PRONOSTICO 3 DIAS\n"
        f"Hoy   🌡️ {hoy_c['temp_min']}°→{hoy_c['temp_max']}°  {hoy_c['emoji']} {hoy_c['condicion']}\n"
        f"{lbl_man}   🌡️ {man_c['temp_min']}°→{man_c['temp_max']}°  {man_c['emoji']} {man_c['condicion']}\n"
        f"{lbl_pman}   🌡️ {pman_c['temp_min']}°→{pman_c['temp_max']}°  {pman_c['emoji']} {pman_c['condicion']}\n"
        f"💨 Viento {hoy_c['viento']} km/h · 💧 Humedad {hoy_c['humedad']}%\n"
        f"\n"
        f"💵 TIPO DE CAMBIO\n"
        f"🇺🇸 USD/MXN: ${cambio['usd_mxn']}\n"
        f"🇪🇺 EUR/MXN: ${cambio['eur_mxn']}\n"
        f"{agenda_str}"
        f"{lunes_str}"
        f"\n"
        f"📲 MEXICO HOY\n"
        f"━━━━━━━━━━━━\n"
        f"{noticias_str}\n"
        f"━━━━━━━━━━━━\n"
        f"\n"
        f"✅ TUS TAREAS\n"
        f"{tareas_str}\n"
        f"\n"
        f"💬 FRASE DEL DIA\n"
        f'"{frase_texto}"\n'
        f"— {frase_autor}\n"
        f"\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"/tarea para agregar algo nuevo"
    )

    return mensaje


# ── BRIEFING VESPERTINO (6PM) ─────────────────────────────────────────────────

async def generar_briefing_tarde() -> str:
    now     = datetime.now()
    dia_man = DIAS_ES[(now.weekday() + 1) % 7]

    # Datos
    dias_clima    = await asyncio.to_thread(_get_clima_3dias_sync)
    eventos_man   = await asyncio.to_thread(_get_eventos_calendario_sync, 1)
    tareas        = db.obtener_tareas()

    man_c = dias_clima[1] if len(dias_clima) > 1 else dias_clima[0]

    tareas_str = (
        "\n".join(f"- {t[1]}" for t in tareas)
        if tareas else "Todo listo. Sin pendientes para manana."
    )

    agenda_str = ""
    if eventos_man:
        lineas = "\n".join(f"   {ev['hora']}  {ev['titulo']}" for ev in eventos_man)
        agenda_str = f"\n📅 MANANA EN TU AGENDA\n{lineas}\n"

    mensaje = (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌆 RESUMEN DEL DIA\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Son las 6pm · Como te fue?\n"
        f"\n"
        f"📋 PENDIENTES\n"
        f"{tareas_str}\n"
        f"\n"
        f"🌤️ MANANA — {dia_man.upper()}\n"
        f"🌡️ {man_c['temp_min']}°→{man_c['temp_max']}°  {man_c['emoji']} {man_c['condicion']}\n"
        f"{agenda_str}"
        f"\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"/hecho para cerrar tareas del dia"
    )

    return mensaje
