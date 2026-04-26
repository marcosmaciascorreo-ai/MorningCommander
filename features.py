"""
features.py — Funcionalidades adicionales de Morning Commander
"""

import asyncio
import base64
import io
import re
import requests
from datetime import date
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


# ── RECOMENDACION DE SERIE / PELICULA ─────────────────────────────────────────

def _recomendar_serie_sync(estado_animo: str) -> str:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": (
                    f"El usuario esta de humor: {estado_animo}\n\n"
                    "Recomienda 3 series o peliculas que esten disponibles hoy en "
                    "Netflix, HBO Max, Disney+ o Prime Video en Mexico.\n\n"
                    "Formato por recomendacion (sin asteriscos):\n"
                    "TITULO (Plataforma)\n"
                    "Genero: [genero]\n"
                    "Por que verla ahora: [1 linea que conecte con el estado de animo]\n"
                    "Temporadas/duracion: [dato util]\n\n"
                    "Elige cosas que realmente esten disponibles en Mexico. "
                    "Mezcla series y peliculas. Sin introduccion ni cierre."
                )
            }],
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "No pude generar recomendaciones. Intenta de nuevo."


async def recomendar_serie(estado_animo: str) -> str:
    return await asyncio.to_thread(_recomendar_serie_sync, estado_animo)


# ── RECETA RAPIDA ─────────────────────────────────────────────────────────────

def _sugerir_receta_sync(ingredientes: str) -> str:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": (
                    f"Ingredientes disponibles: {ingredientes}\n\n"
                    "Sugiere 1 receta rapida (menos de 30 minutos) que se pueda hacer con eso. "
                    "Puede agregar sal, aceite, ajo, cebolla y condimentos basicos si los necesita.\n\n"
                    "Formato:\n"
                    "NOMBRE DEL PLATILLO\n"
                    "Tiempo: [minutos]\n"
                    "Ingredientes: [lista en una linea]\n"
                    "Pasos:\n"
                    "1. ...\n"
                    "2. ...\n"
                    "Tip: [consejo del chef en 1 linea]\n\n"
                    "Sin asteriscos ni markdown."
                )
            }],
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "No pude generar la receta. Intenta de nuevo."


async def sugerir_receta(ingredientes: str) -> str:
    return await asyncio.to_thread(_sugerir_receta_sync, ingredientes)


# ── CHISTE DEL DIA ────────────────────────────────────────────────────────────

def _chiste_del_dia_sync() -> str:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        hoy = date.today().strftime("%Y-%m-%d")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=150,
            messages=[{
                "role": "user",
                "content": (
                    f"Fecha: {hoy}. Cuentame un chiste corto y gracioso, "
                    "estilo mexicano o de cultura latina. "
                    "Que sea limpio pero con algo de picardía. "
                    "Solo el chiste, sin comentarios ni explicaciones."
                )
            }],
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "Por que los programadores usan lentes? Porque no pueden C#. (Error generando chiste.)"


async def chiste_del_dia() -> str:
    return await asyncio.to_thread(_chiste_del_dia_sync)


# ── MENSAJE MOTIVACIONAL ──────────────────────────────────────────────────────

def _frase_motivacional_sync(contexto: str = "") -> str:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        extra = f"El usuario dice: {contexto}\n\n" if contexto else ""
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=200,
            messages=[{
                "role": "user",
                "content": (
                    f"{extra}"
                    "Da un mensaje motivacional corto y directo para alguien que trabaja "
                    "en finanzas en una maquiladora en Chihuahua, Mexico. "
                    "Que sea real y humano, no un poster de LinkedIn. "
                    "Maximo 4 lineas. Sin asteriscos."
                )
            }],
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "El mejor momento para empezar fue ayer. El segundo mejor es ahora."


async def frase_motivacional(contexto: str = "") -> str:
    return await asyncio.to_thread(_frase_motivacional_sync, contexto)


# ── CLIMA DE OTRA CIUDAD ──────────────────────────────────────────────────────

WEATHERCODES_ES = {
    0: "Despejado", 1: "Mayormente despejado", 2: "Parcialmente nublado", 3: "Nublado",
    45: "Niebla", 48: "Niebla con escarcha",
    51: "Llovizna", 53: "Llovizna", 55: "Llovizna intensa",
    61: "Lluvia ligera", 63: "Lluvia", 65: "Lluvia intensa",
    71: "Nieve", 73: "Nieve", 75: "Nieve intensa",
    80: "Chubascos", 81: "Chubascos", 82: "Chubascos fuertes",
    95: "Tormenta", 99: "Tormenta con granizo",
}
WEATHER_EMOJIS = {
    0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️",
    45: "🌫️", 48: "🌫️",
    51: "🌦️", 53: "🌦️", 55: "🌦️",
    61: "🌧️", 63: "🌧️", 65: "🌧️",
    71: "🌨️", 73: "🌨️", 75: "🌨️",
    80: "🌦️", 81: "🌦️", 82: "🌦️",
    95: "⛈️", 99: "⛈️",
}
DIAS_ES = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]


def _clima_ciudad_sync(ciudad: str) -> str:
    try:
        # Paso 1: geocodificar
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": ciudad, "count": 1, "language": "es", "format": "json"},
            timeout=8,
        )
        geo.raise_for_status()
        resultados = geo.json().get("results", [])
        if not resultados:
            return f"No encontre la ciudad '{ciudad}'. Intenta con otro nombre."

        r      = resultados[0]
        lat    = r["latitude"]
        lon    = r["longitude"]
        nombre = r.get("name", ciudad)
        pais   = r.get("country", "")
        estado = r.get("admin1", "")
        lugar  = f"{nombre}, {estado}, {pais}".strip(", ")

        # Paso 2: pronostico 3 dias
        weather = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude":  lat,
                "longitude": lon,
                "daily":     "temperature_2m_max,temperature_2m_min,weather_code,weathercode",
                "timezone":  "auto",
                "forecast_days": 3,
            },
            timeout=10,
        )
        weather.raise_for_status()
        data  = weather.json()
        daily = data["daily"]
        wcs   = daily.get("weather_code") or daily.get("weathercode") or []
        fechas = daily.get("time", [])

        lineas = [f"CLIMA EN {lugar.upper()}", ""]
        for i in range(min(3, len(fechas))):
            wc    = int(wcs[i]) if i < len(wcs) else 0
            tmin  = round(daily["temperature_2m_min"][i])
            tmax  = round(daily["temperature_2m_max"][i])
            cond  = WEATHERCODES_ES.get(wc, "Variable")
            emoji = WEATHER_EMOJIS.get(wc, "🌡️")
            from datetime import datetime as _dt
            fecha = _dt.fromisoformat(fechas[i])
            dia   = DIAS_ES[fecha.weekday()]
            etiq  = "Hoy  " if i == 0 else (f"{dia}  " if i == 1 else f"{dia}  ")
            lineas.append(f"{etiq} {emoji} {tmin}°→{tmax}°  {cond}")

        return "\n".join(lineas)

    except Exception as e:
        return f"No pude obtener el clima de '{ciudad}'. ({e})"


async def clima_ciudad(ciudad: str) -> str:
    return await asyncio.to_thread(_clima_ciudad_sync, ciudad)


# ── PRECIO DE GASOLINA EN CHIHUAHUA ──────────────────────────────────────────

def _precio_gasolina_sync() -> str:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        hoy = date.today().strftime("%d de %B de %Y")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=200,
            messages=[{
                "role": "user",
                "content": (
                    f"Fecha de hoy: {hoy}.\n\n"
                    "Cual es el precio maximo por litro de gasolina en Chihuahua, Mexico "
                    "esta semana? Los precios los fija SHCP semanalmente.\n\n"
                    "Da los precios de:\n"
                    "- Magna (regular)\n"
                    "- Premium\n"
                    "- Diesel\n\n"
                    "Formato:\n"
                    "Magna:   $XX.XX / litro\n"
                    "Premium: $XX.XX / litro\n"
                    "Diesel:  $XX.XX / litro\n\n"
                    "Al final agrega: 'Precio maximo oficial SHCP. Verifica en: gob.mx/shcp'\n"
                    "Sin asteriscos. Sin explicaciones largas."
                )
            }],
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "No pude obtener el precio. Consulta el precio oficial en: gob.mx/shcp"


async def precio_gasolina() -> str:
    return await asyncio.to_thread(_precio_gasolina_sync)


# ── RESTAURANTE EN CHIHUAHUA ──────────────────────────────────────────────────

RESTAURANTES_CHI = [
    {"nombre": "La Casona",           "tipo": "Comida mexicana tradicional",      "zona": "Centro historico"},
    {"nombre": "Los Milagros",        "tipo": "Carnes y asados chihuahuenses",    "zona": "Zona Dorada"},
    {"nombre": "El Parral",           "tipo": "Platillos tipicos del norte",      "zona": "Centro"},
    {"nombre": "La Fazenda",          "tipo": "Churrasco brasileno",              "zona": "Periférico de la Juventud"},
    {"nombre": "Luther's BBQ",        "tipo": "Carnes ahumadas estilo americano", "zona": "Zona Dorada"},
    {"nombre": "Pangea",              "tipo": "Cocina de autor, fusion",          "zona": "Colonia Cuauhtemoc"},
    {"nombre": "Baikal",              "tipo": "Cocina internacional, mariscos",   "zona": "Colonia Magisterial"},
    {"nombre": "Tony Roma's",         "tipo": "Ribs y carnes americanas",         "zona": "Plaza Sendero"},
    {"nombre": "Casa Chueco",         "tipo": "Mariscos y caldos",                "zona": "Colonia Cuauhtemoc"},
    {"nombre": "El Rodeo",            "tipo": "Comida corrida mexicana",          "zona": "Varios en la ciudad"},
    {"nombre": "Rojo Bistro",         "tipo": "Brunch y cocina mexicana moderna", "zona": "Colonia Magisterial"},
    {"nombre": "La Parrilla Norteña", "tipo": "Arracheras y cortes norteños",     "zona": "Boulevard Ortiz Mena"},
    {"nombre": "Samurai",             "tipo": "Sushi y comida japonesa",          "zona": "Zona Dorada"},
    {"nombre": "Sushito",             "tipo": "Sushi mexicanizado, rolls especiales", "zona": "Colonia Bugambilias"},
    {"nombre": "El Charco de las Ranas", "tipo": "Mariscos estilo nayarita",      "zona": "Periférico"},
]


def _sugerir_restaurante_sync() -> str:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        hoy = date.today()
        dias = {0: "lunes", 1: "martes", 2: "miercoles", 3: "jueves",
                4: "viernes", 5: "sabado", 6: "domingo"}
        dia = dias[hoy.weekday()]

        catalogo = "\n".join(
            f'{i+1}. {r["nombre"]} — {r["tipo"]} ({r["zona"]})'
            for i, r in enumerate(RESTAURANTES_CHI)
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=250,
            messages=[{
                "role": "user",
                "content": (
                    f"Hoy es {dia}. Elige 1 restaurante de esta lista para recomendar hoy "
                    f"a alguien en Chihuahua.\n\n"
                    f"LISTA:\n{catalogo}\n\n"
                    "Formato:\n"
                    "NOMBRE DEL RESTAURANTE\n"
                    "Tipo: [tipo de cocina]\n"
                    "Zona: [ubicacion]\n"
                    "Por que hoy: [1 linea convincente]\n"
                    "Pide: [platillo especifico que debes ordenar]\n\n"
                    "Sin asteriscos. Solo el bloque del restaurante elegido."
                )
            }],
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "No pude generar la sugerencia. Intenta de nuevo."


async def sugerir_restaurante() -> str:
    return await asyncio.to_thread(_sugerir_restaurante_sync)


# ── EVENTOS EN CHIHUAHUA ──────────────────────────────────────────────────────

_RSS_CHI_EVENTOS = [
    "https://www.nortedigital.mx/feed/",
    "https://www.elheraldodechihuahua.com.mx/rss",
]

_PALABRAS_EVENTO = [
    "festival", "concierto", "expo", "feria", "evento", "obra", "teatro",
    "exposicion", "inauguracion", "temporada", "torneo", "carrera", "funcion",
    "muestra", "presentacion", "taller", "conferencia",
]


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _eventos_chihuahua_sync() -> str:
    titulares = []
    for url in _RSS_CHI_EVENTOS:
        try:
            import feedparser
            resp = requests.get(url, timeout=8)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:15]:
                titulo = _clean(entry.get("title", ""))
                if any(p in titulo.lower() for p in _PALABRAS_EVENTO):
                    titulares.append(titulo)
        except Exception:
            continue

    if not titulares:
        # Sin RSS, usar GPT con conocimiento general
        try:
            client = OpenAI(api_key=OPENAI_API_KEY)
            hoy = date.today()
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=300,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Mes: {hoy.strftime('%B %Y')}. "
                        "Sugiere 4 eventos culturales, conciertos o actividades que "
                        "suelen ocurrir en Chihuahua en esta epoca del año. "
                        "Que sean tipicos y reales (Feria de Santa Rita, eventos del ICHICULT, "
                        "Teatro de los Heroes, etc.). "
                        "Formato: una linea por evento. Sin asteriscos."
                    )
                }],
            )
            return "EVENTOS EN CHIHUAHUA (sugerencias tipicas de la temporada)\n\n" + response.choices[0].message.content.strip()
        except Exception:
            return "No encontre eventos. Consulta la pagina del ICHICULT o Norte Digital."

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        texto = "\n".join(titulares[:10])
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": (
                    f"Estos son titulares de noticias de Chihuahua sobre eventos:\n{texto}\n\n"
                    "Resume los 4 mas relevantes. Formato: una linea por evento. "
                    "Si no hay suficiente info, di 'Ver detalles en Norte Digital'. Sin asteriscos."
                )
            }],
        )
        return "EVENTOS EN CHIHUAHUA\n\n" + response.choices[0].message.content.strip()
    except Exception:
        return "EVENTOS EN CHIHUAHUA\n\n" + "\n".join(f"- {t}" for t in titulares[:5])


async def eventos_chihuahua() -> str:
    return await asyncio.to_thread(_eventos_chihuahua_sync)


# ── NOTICIAS SOLO CHIHUAHUA ───────────────────────────────────────────────────

_RSS_CHI_NOTICIAS = [
    "https://www.nortedigital.mx/feed/",
    "https://www.elheraldodechihuahua.com.mx/rss",
]


def _noticias_chihuahua_sync() -> str:
    titulares = []
    for url in _RSS_CHI_NOTICIAS:
        try:
            import feedparser
            resp = requests.get(url, timeout=8)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:6]:
                titulo = _clean(entry.get("title", ""))
                if titulo:
                    titulares.append(titulo)
        except Exception:
            continue

    if not titulares:
        return "No se pudieron obtener noticias de Chihuahua en este momento.\nIntenta en: nortedigital.mx"

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        texto = "\n".join(titulares[:10])
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": (
                    f"Titulares de noticias locales de Chihuahua:\n{texto}\n\n"
                    "Selecciona los 5 mas importantes y resumelos en 1 linea cada uno. "
                    "Prioriza seguridad, gobierno, economia local, eventos. "
                    "Formato: una linea por noticia con emoji relevante al inicio. Sin asteriscos."
                )
            }],
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "\n".join(f"- {t}" for t in titulares[:6])


async def noticias_chihuahua() -> str:
    return await asyncio.to_thread(_noticias_chihuahua_sync)


# ── PLAYLIST ──────────────────────────────────────────────────────────────────

def _generar_playlist_sync(actividad: str) -> str:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=700,
            messages=[{
                "role": "user",
                "content": (
                    f"Crea una playlist de 10 canciones para: {actividad}\n\n"
                    "El usuario es mexicano, le gusta musica variada. "
                    "Mezcla generos que peguen con la actividad.\n\n"
                    "Formato por cancion (sin asteriscos ni numeracion con punto):\n"
                    "TITULO — ARTISTA\n"
                    "Spotify: https://open.spotify.com/search/[titulo+artista url-encoded]\n\n"
                    "Incluye una linea al final con el 'mood' general de la playlist en 5 palabras."
                )
            }],
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "No pude generar la playlist. Intenta de nuevo."


async def generar_playlist(actividad: str) -> str:
    return await asyncio.to_thread(_generar_playlist_sync, actividad)


# ── IDEA DE CITA / PLAN ESPECIAL ──────────────────────────────────────────────

def _idea_cita_sync(ocasion: str) -> str:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": (
                    f"Ocasion: {ocasion}\n\n"
                    "Diseña un plan especifico para una cita o salida en Chihuahua, Mexico. "
                    "Que sea romantico, memorable y ejecutable este fin de semana.\n\n"
                    "Incluye:\n"
                    "PLAN DEL DIA\n"
                    "Hora inicio: [hora sugerida]\n\n"
                    "1. [Primera parada — lugar real en Chihuahua + por que]\n"
                    "2. [Segunda parada — restaurante especifico + que pedir]\n"
                    "3. [Tercer momento — actividad, brindis, detalle especial]\n\n"
                    "Toque especial: [algo que haga el plan memorable, sencillo pero diferente]\n"
                    "Presupuesto aprox: [rango en pesos]\n\n"
                    "Que los lugares sean reales en Chihuahua. Sin asteriscos."
                )
            }],
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "No pude generar el plan. Intenta de nuevo."


async def idea_cita(ocasion: str) -> str:
    return await asyncio.to_thread(_idea_cita_sync, ocasion)


# ── CONTRAPUNTO ───────────────────────────────────────────────────────────────

def _contrapunto_sync(posicion: str) -> str:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=400,
            messages=[{
                "role": "system",
                "content": (
                    "Eres un devil's advocate brillante. El usuario te da su posicion o creencia. "
                    "Tu trabajo es darle el mejor argumento en contra posible, solido y honesto, "
                    "no para ganar, sino para que el usuario piense mejor antes de actuar o decidir.\n\n"
                    "Estructura:\n"
                    "EL ARGUMENTO CONTRARIO\n"
                    "[El punto mas fuerte en contra, bien desarrollado]\n\n"
                    "LO QUE NO ESTAS CONSIDERANDO\n"
                    "[1-2 puntos ciegos frecuentes en esta posicion]\n\n"
                    "PREGUNTA INCOMODA\n"
                    "[Una sola pregunta que ponga a prueba la posicion]\n\n"
                    "Responde en espanol. Sin asteriscos. Directo y sin rodeos."
                ),
            }, {
                "role": "user",
                "content": posicion,
            }],
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "No pude generar el contrapunto. Intenta de nuevo."


async def contrapunto(posicion: str) -> str:
    return await asyncio.to_thread(_contrapunto_sync, posicion)


# ── FOTO / IMAGEN ─────────────────────────────────────────────────────────────

_PROMPTS_FOTO = {
    "recibo": (
        "Analiza este ticket o recibo y extrae:\n"
        "ESTABLECIMIENTO: [nombre si aparece]\n"
        "FECHA: [si aparece]\n"
        "ITEMS:\n[lista de productos con precio]\n"
        "TOTAL: $X\n"
        "CATEGORIA: [comida / gasolina / farmacia / ropa / etc]\n"
        "Sin asteriscos."
    ),
    "identificar": (
        "Identifica lo que hay en esta imagen:\n"
        "QUE ES: [nombre preciso]\n"
        "DESCRIPCION: [2-3 caracteristicas clave]\n"
        "DATO UTIL: [algo practico o curioso sobre esto]\n"
        "Si no puedes identificarlo con certeza, di lo mas probable y por que."
    ),
    "nutricion": (
        "Analiza nutricionalmente la comida en esta imagen:\n"
        "PLATILLO: [nombre]\n"
        "PORCION ESTIMADA: [tamano aproximado]\n"
        "CALORIAS APROX: X kcal\n"
        "PROTEINA: Xg   CARBS: Xg   GRASA: Xg\n"
        "SEMAFORO: [Verde / Amarillo / Rojo] — [razon en una linea]\n"
        "Nota: es estimacion visual. Sin asteriscos."
    ),
    "problema": (
        "Analiza el problema que se ve en esta imagen:\n"
        "PROBLEMA: [que esta mal]\n"
        "CAUSA PROBABLE: [por que ocurrio]\n"
        "PASOS PARA ARREGLARLO:\n1. ...\n2. ...\n"
        "NECESITAS: [herramientas o materiales]\n"
        "DIFICULTAD: [Facil / Medio / Llama a un profesional]\n"
        "Sin asteriscos."
    ),
    "etiqueta": (
        "Lee la etiqueta de este producto:\n"
        "PRODUCTO: [nombre]\n"
        "PARA QUE SIRVE: [uso en lenguaje simple]\n"
        "INGREDIENTES A NOTAR: [los mas relevantes o de cuidado]\n"
        "ALERTAS: [alergenos, contraindicaciones, precauciones]\n"
        "LO QUE LA GENTE NO LEE: [dato util que suele ignorarse]\n"
        "Sin tecnicismos innecesarios."
    ),
}

def _analizar_foto_sync(image_bytes: bytes, tipo: str) -> str:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        prompt = _PROMPTS_FOTO.get(tipo, "Describe detalladamente lo que ves en esta imagen.")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                ],
            }],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"No pude analizar la imagen. Intenta de nuevo. ({e})"


async def analizar_foto(image_bytes: bytes, tipo: str) -> str:
    return await asyncio.to_thread(_analizar_foto_sync, image_bytes, tipo)


# ── AUDIO / VOZ ───────────────────────────────────────────────────────────────

def _transcribir_sync(audio_bytes: bytes, filename: str = "audio.ogg") -> str:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        buf = io.BytesIO(audio_bytes)
        buf.name = filename
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=buf,
            language="es",
        )
        return transcript.text.strip()
    except Exception as e:
        return f"No pude transcribir el audio. ({e})"


def _minuta_sync(audio_bytes: bytes, filename: str = "audio.ogg") -> str:
    texto = _transcribir_sync(audio_bytes, filename)
    if texto.startswith("No pude"):
        return texto
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=600,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Del texto de una reunion o conversacion, extrae:\n\n"
                        "TEMAS TRATADOS:\n[lista]\n\n"
                        "ACUERDOS Y DECISIONES:\n- [acuerdo + responsable si se menciona]\n\n"
                        "PENDIENTES / PROXIMOS PASOS:\n- [tarea + quien + fecha si se menciona]\n\n"
                        "PUNTOS IMPORTANTES:\n- [algo que no debe perderse]\n\n"
                        "Responde en espanol. Sin asteriscos."
                    ),
                },
                {"role": "user", "content": f"Transcripcion:\n{texto}"},
            ],
        )
        acta = response.choices[0].message.content.strip()
        return f"TRANSCRIPCION\n{texto}\n\n---\nMINUTA\n{acta}"
    except Exception as e:
        return f"Transcripcion lista pero no pude generar la minuta. ({e})\n\nTEXTO:\n{texto}"


async def transcribir_audio(audio_bytes: bytes, filename: str = "audio.ogg") -> str:
    return await asyncio.to_thread(_transcribir_sync, audio_bytes, filename)


async def generar_minuta(audio_bytes: bytes, filename: str = "audio.ogg") -> str:
    return await asyncio.to_thread(_minuta_sync, audio_bytes, filename)


# ── QUE FALTA ─────────────────────────────────────────────────────────────────

def _que_falta_sync(plan: str) -> str:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=400,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un consultor con experiencia. El usuario describe un plan, proyecto o decision. "
                        "Tu trabajo es identificar puntos ciegos y preguntas sin responder.\n\n"
                        "LO QUE NO ESTAS CONSIDERANDO:\n"
                        "1. [punto ciego mas importante]\n"
                        "2. [segundo punto]\n"
                        "3. [tercero]\n\n"
                        "PREGUNTAS SIN RESPONDER:\n"
                        "- [pregunta critica que el plan no aborda]\n\n"
                        "RIESGO PRINCIPAL: [lo que mas puede hacer fallar esto]\n\n"
                        "Responde en espanol. Sin asteriscos. Directo."
                    ),
                },
                {"role": "user", "content": plan},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "No pude analizar el plan. Intenta de nuevo."


async def que_falta(plan: str) -> str:
    return await asyncio.to_thread(_que_falta_sync, plan)
