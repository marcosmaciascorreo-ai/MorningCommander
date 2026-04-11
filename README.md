# ☀️ Morning Commander

Bot personal de Telegram que te manda un briefing diario automatizado cada mañana con clima, tipo de cambio, noticias resumidas por IA y tus tareas del día.

---

## Instalación rápida

### 1. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 2. Crear el bot en Telegram
1. Abre Telegram y busca **@BotFather**
2. Escribe `/newbot` y sigue las instrucciones
3. Copia el **token** que te da (ejemplo: `123456789:ABCdef...`)

### 3. Obtener tu API key de Anthropic
1. Ve a **console.anthropic.com**
2. Crea una cuenta o inicia sesión
3. Ve a *API Keys* y crea una nueva key

### 4. Configurar `config.py`
Abre `config.py` y llena los valores:

```python
TOKEN             = "123456789:ABCdef..."   # Token de @BotFather
MY_ID             = 0                        # Tu user_id (ver paso 5)
ANTHROPIC_API_KEY = "sk-ant-..."             # Tu API key de Anthropic
```

### 5. Obtener tu Telegram user_id
1. Corre el bot: `python bot.py`
2. Escríbele `/start` en Telegram
3. El bot te responde con tu user_id
4. Pega ese número en `MY_ID` en `config.py`
5. Reinicia el bot: `Ctrl+C` y `python bot.py` de nuevo

### 6. Probar que todo funciona
Escríbele `/briefing` al bot. Debe responder con el mensaje completo.

### 7. Dejar corriendo en segundo plano
```bash
# Windows (sin ventana de consola)
pythonw bot.py

# O con una ventana minimizada normal
python bot.py
```

---

## Comandos disponibles

| Comando | Descripción |
|---------|-------------|
| `/start` | Bienvenida e información del bot |
| `/tarea` | Agregar tarea para mañana |
| `/tareas` | Ver tareas pendientes |
| `/hecho` | Marcar tarea como completada |
| `/borrar` | Eliminar una tarea sin completar |
| `/briefing` | Recibir el briefing ahora (modo prueba) |
| `/hora` | Cambiar la hora del envío diario |
| `/ayuda` | Ver todos los comandos |

---

## Agregar tareas

**Modo rápido:**
```
/tarea Llamar al dentista para cita
```

**Modo interactivo:**
```
/tarea
→ Bot: ¿Qué tarea quieres agregar?
→ Tú: Llamar al dentista para cita
→ Bot: ✅ Tarea agregada
```

---

## Estructura del proyecto

```
morning_commander/
├── bot.py           # Bot principal + handlers de comandos
├── scheduler.py     # Lógica del envío programado (APScheduler)
├── briefing.py      # Genera el mensaje del briefing
├── db.py            # Operaciones de base de datos (SQLite)
├── config.py        # Variables de configuración
├── requirements.txt
├── morning.db       # Se crea automáticamente al primer uso
└── README.md
```

---

## APIs utilizadas

| API | URL | Key requerida |
|-----|-----|---------------|
| Clima | Open-Meteo | ❌ Gratis sin key |
| Tipo de cambio | ExchangeRate-API | ❌ Gratis sin key |
| Noticias | BBC Mundo RSS + El Financiero RSS | ❌ Gratis |
| Resumen IA | Claude Haiku (Anthropic) | ✅ Barato (~$0.001/día) |

---

## Notas

- El bot **solo responde a tu user_id**. Cualquier otro usuario recibe: `⛔ Bot personal, acceso restringido.`
- Si el bot se reinicia, el scheduler se reprograma automáticamente al arrancar.
- La base de datos `morning.db` se crea automáticamente en el primer uso.
- Si la API de Anthropic falla, el bot muestra los titulares crudos del RSS como fallback.
- Para cambiar la ciudad, edita `CIUDAD_LAT`, `CIUDAD_LON` y `CIUDAD_NAME` en `config.py`.
