import os

# ============================================================
# MORNING COMMANDER — CONFIGURACION
# En Railway los valores vienen de variables de entorno.
# ============================================================

TOKEN          = os.environ.get("TOKEN",          "")
MY_ID          = int(os.environ.get("MY_ID",      "0"))
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# Coordenadas de tu ciudad
CIUDAD_LAT  = float(os.environ.get("CIUDAD_LAT",  "28.6353"))
CIUDAD_LON  = float(os.environ.get("CIUDAD_LON",  "-106.0889"))
CIUDAD_NAME = os.environ.get("CIUDAD_NAME", "Chihuahua")

# Hora del briefing matutino (HH:MM)
HORA_ENVIO      = os.environ.get("HORA_ENVIO",      "05:50")

# Hora del briefing vespertino (HH:MM)
HORA_ENVIO_TARDE = os.environ.get("HORA_ENVIO_TARDE", "18:00")
