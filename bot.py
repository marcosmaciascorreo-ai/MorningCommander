"""
bot.py — Morning Commander
Bot personal de Telegram con briefing diario automatizado.
"""

import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

from config import TOKEN, MY_ID, HORA_ENVIO
import db
import briefing as briefing_module
import scheduler as sched_module

# ── LOGGING ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)   # silenciar spam de httpx
logger = logging.getLogger(__name__)

# ── ESTADOS DE CONVERSACIÓN ───────────────────────────────────────────────────

WAITING_TASK = 1
WAITING_HOUR = 2

# ── REFERENCIA GLOBAL A LA APLICACIÓN (usada por el scheduler) ────────────────

_app: Application | None = None

# ── HELPERS ───────────────────────────────────────────────────────────────────

def is_me(update: Update) -> bool:
    return update.effective_user.id == MY_ID


async def deny(update: Update):
    await update.message.reply_text("⛔ Bot personal, acceso restringido.")


AYUDA_TEXTO = (
    "📚 COMANDOS DISPONIBLES\n\n"
    "/start    — Bienvenida e información\n"
    "/tarea    — Agregar tarea para mañana\n"
    "/tareas   — Ver tareas pendientes\n"
    "/hecho    — Marcar tarea como completada\n"
    "/borrar   — Eliminar una tarea sin completar\n"
    "/briefing — Recibir el briefing ahora (prueba)\n"
    "/hora     — Cambiar la hora del envío diario\n"
    "/ayuda    — Ver este mensaje"
)

# ── COMANDOS ──────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Si MY_ID no está configurado todavía, solo mostrar el ID para que pueda configurarlo
    if MY_ID == 0:
        await update.message.reply_text(
            f"Bot no configurado aun.\n\n"
            f"Tu Telegram user_id es:\n"
            f"{user_id}\n\n"
            f"Copialo y pegalo en config.py en MY_ID, luego reinicia el bot.",
        )
        return

    if not is_me(update):
        await deny(update)
        return

    hora_actual = db.get_config("hora_envio", HORA_ENVIO)
    await update.message.reply_text(
        f"Morning Commander activo.\n\n"
        f"Te mandare tu briefing cada manana a las {hora_actual}.\n\n"
        f"Comandos disponibles:\n"
        f"/tarea    - Agregar tarea para manana\n"
        f"/tareas   - Ver tareas pendientes\n"
        f"/hecho    - Marcar tarea como completada\n"
        f"/borrar   - Eliminar una tarea\n"
        f"/briefing - Recibir el briefing ahora mismo (prueba)\n"
        f"/hora     - Cambiar la hora del envio diario\n"
        f"/ayuda    - Ver todos los comandos\n\n"
        f"Tu user_id es: {user_id}"
    )


async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_me(update):
        await deny(update)
        return
    await update.message.reply_text(AYUDA_TEXTO)


# ── /tarea ────────────────────────────────────────────────────────────────────

async def cmd_tarea_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_me(update):
        await deny(update)
        return ConversationHandler.END

    # Modo directo: /tarea Llamar al dentista
    if context.args:
        texto = " ".join(context.args).strip()
        db.agregar_tarea(texto)
        await update.message.reply_text(
            f"Tarea agregada: {texto}\n"
            f"Aparecera en tu briefing de manana.",
        )
        return ConversationHandler.END

    # Modo interactivo
    await update.message.reply_text("Que tarea quieres agregar?")
    return WAITING_TASK


async def cmd_tarea_recibir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    if texto:
        db.agregar_tarea(texto)
        await update.message.reply_text(
            f"Tarea agregada: {texto}\n"
            f"Aparecera en tu briefing de manana.",
        )
    else:
        await update.message.reply_text(
            "No entendí la tarea. Intenta de nuevo con /tarea"
        )
    return ConversationHandler.END


# ── /tareas ───────────────────────────────────────────────────────────────────

async def cmd_tareas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_me(update):
        await deny(update)
        return

    tareas = db.obtener_tareas()
    if not tareas:
        await update.message.reply_text(
            "No tienes tareas pendientes. Usa /tarea para agregar una. 🎯"
        )
        return

    lista = "\n".join(f"{i + 1}. {t[1]}" for i, t in enumerate(tareas))
    await update.message.reply_text(
        f"📋 TAREAS PENDIENTES ({len(tareas)})\n\n"
        f"{lista}\n\n"
        f"Usa /hecho para marcarlas como completadas."
    )


# ── /hecho y /borrar (con teclado inline) ─────────────────────────────────────

async def _mostrar_menu_tareas(update: Update, accion: str):
    tareas = db.obtener_tareas()
    if not tareas:
        await update.message.reply_text("No tienes tareas pendientes.")
        return

    keyboard = [
        [InlineKeyboardButton(
            f"{i + 1}. {t[1][:50]}{'…' if len(t[1]) > 50 else ''}",
            callback_data=f"{accion}_{t[0]}"
        )]
        for i, t in enumerate(tareas)
    ]
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")])

    texto = (
        "¿Cuál tarea completaste?" if accion == "hecho"
        else "¿Cuál tarea quieres eliminar?"
    )
    await update.message.reply_text(
        texto,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def cmd_hecho(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_me(update):
        await deny(update)
        return
    await _mostrar_menu_tareas(update, "hecho")


async def cmd_borrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_me(update):
        await deny(update)
        return
    await _mostrar_menu_tareas(update, "borrar")


async def callback_tareas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cancelar":
        await query.edit_message_text("Cancelado.")
        return

    accion, tarea_id_str = query.data.rsplit("_", 1)
    tarea_id = int(tarea_id_str)

    if accion == "hecho":
        texto = db.completar_tarea(tarea_id)
        if texto:
            await query.edit_message_text(
                f"Tarea completada: {texto}. Bien hecho!"
            )
        else:
            await query.edit_message_text("No encontre esa tarea.")

    elif accion == "borrar":
        texto = db.borrar_tarea(tarea_id)
        if texto:
            await query.edit_message_text(
                f"Tarea eliminada: {texto}"
            )
        else:
            await query.edit_message_text("No encontre esa tarea.")


# ── /briefing (modo prueba) ───────────────────────────────────────────────────

async def cmd_briefing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_me(update):
        await deny(update)
        return

    await update.message.reply_text("⏳ Generando tu briefing...")
    try:
        mensaje = await briefing_module.generar_briefing()
        await update.message.reply_text(mensaje)
    except Exception as e:
        logger.error(f"Error generando briefing: {e}")
        await update.message.reply_text(
            "❌ Hubo un error generando el briefing. Revisa los logs."
        )


# ── /hora ─────────────────────────────────────────────────────────────────────

async def cmd_hora_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_me(update):
        await deny(update)
        return ConversationHandler.END

    hora_actual = db.get_config("hora_envio", HORA_ENVIO)
    await update.message.reply_text(
        f"⏰ Hora actual de envío: {hora_actual}\n\n"
        f"¿A qué hora quieres recibir tu briefing?\n"
        f"Escribe en formato HH:MM (ej: 06:00)"
    )
    return WAITING_HOUR


async def cmd_hora_recibir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()

    try:
        partes = texto.split(":")
        if len(partes) != 2:
            raise ValueError
        hora, minuto = int(partes[0]), int(partes[1])
        if not (0 <= hora <= 23 and 0 <= minuto <= 59):
            raise ValueError
        nueva_hora = f"{hora:02d}:{minuto:02d}"
    except (ValueError, AttributeError):
        await update.message.reply_text(
            "Formato inválido. Usa HH:MM (ej: 06:30). Intenta de nuevo:"
        )
        return WAITING_HOUR

    db.set_config("hora_envio", nueva_hora)
    sched_module.programar_briefing(_enviar_briefing_automatico, nueva_hora)

    await update.message.reply_text(
        f"✅ Briefing programado para las {nueva_hora} todos los días."
    )
    return ConversationHandler.END


# ── MENSAJE DESCONOCIDO ───────────────────────────────────────────────────────

async def cmd_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_me(update):
        await deny(update)
        return
    await update.message.reply_text(
        "No reconozco ese comando.\n\n" + AYUDA_TEXTO
    )


# ── CANCELAR (sale de cualquier conversación) ─────────────────────────────────

async def cmd_cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operación cancelada.")
    return ConversationHandler.END


# ── SCHEDULER CALLBACK ────────────────────────────────────────────────────────

async def _enviar_briefing_automatico():
    """Llamado por APScheduler para enviar el briefing diario."""
    global _app
    if _app is None:
        logger.error("_app no inicializada, no se puede enviar el briefing.")
        return
    try:
        mensaje = await briefing_module.generar_briefing()
        await _app.bot.send_message(chat_id=MY_ID, text=mensaje)
        logger.info("Briefing diario enviado correctamente.")
    except Exception as e:
        logger.error(f"Error al enviar briefing automático: {e}")


# ── POST INIT (se llama al arrancar la aplicación) ────────────────────────────

async def post_init(application: Application) -> None:
    global _app
    _app = application

    hora = db.get_config("hora_envio", HORA_ENVIO)
    sched_module.init_scheduler(_enviar_briefing_automatico, hora)

    print(f"[OK] Morning Commander activo. Briefing programado para las {hora}")
    logger.info(f"Bot inicializado. Briefing programado para las {hora}.")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    # 1. Inicializar base de datos (crea tablas y frases si es primera vez)
    db.init_db()

    # 2. Construir la aplicación
    app = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )

    # ── ConversationHandler para /tarea ──
    tarea_conv = ConversationHandler(
        entry_points=[CommandHandler("tarea", cmd_tarea_start)],
        states={
            WAITING_TASK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_tarea_recibir)
            ]
        },
        fallbacks=[
            CommandHandler("cancelar", cmd_cancelar),
            MessageHandler(filters.COMMAND, cmd_cancelar),  # cualquier otro comando cancela
        ],
    )

    # ── ConversationHandler para /hora ──
    hora_conv = ConversationHandler(
        entry_points=[CommandHandler("hora", cmd_hora_start)],
        states={
            WAITING_HOUR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_hora_recibir)
            ]
        },
        fallbacks=[
            CommandHandler("cancelar", cmd_cancelar),
            MessageHandler(filters.COMMAND, cmd_cancelar),
        ],
    )

    # ── Registrar handlers ──
    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("ayuda",    cmd_ayuda))
    app.add_handler(CommandHandler("tareas",   cmd_tareas))
    app.add_handler(CommandHandler("hecho",    cmd_hecho))
    app.add_handler(CommandHandler("borrar",   cmd_borrar))
    app.add_handler(CommandHandler("briefing", cmd_briefing))
    app.add_handler(tarea_conv)
    app.add_handler(hora_conv)
    app.add_handler(CallbackQueryHandler(callback_tareas))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_unknown)
    )

    # 3. Arrancar el bot
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
