import os

# ============================================================
# MORNING COMMANDER — CONFIGURACIÓN
# Todos los valores vienen de variables de entorno.
# Configuralas en Railway (o en tu sistema local).
# ============================================================

TOKEN          = os.environ.get("TOKEN",          "")
MY_ID          = int(os.environ.get("MY_ID",      "0"))
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# Coordenadas de tu ciudad
CIUDAD_LAT  = float(os.environ.get("CIUDAD_LAT",  "28.6353"))
CIUDAD_LON  = float(os.environ.get("CIUDAD_LON",  "-106.0889"))
CIUDAD_NAME = os.environ.get("CIUDAD_NAME", "Chihuahua")

# Hora del briefing diario (formato 24h HH:MM)
HORA_ENVIO  = os.environ.get("HORA_ENVIO", "05:50")
