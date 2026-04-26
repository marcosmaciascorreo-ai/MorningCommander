"""
bot.py — Morning Commander · Bot personal de Telegram
"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

from config import TOKEN, MY_ID, HORA_ENVIO, HORA_ENVIO_TARDE
import db
import briefing as briefing_module
import features as features_module
import scheduler as sched_module

# ── LOGGING ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# ── ESTADOS ───────────────────────────────────────────────────────────────────

WAITING_TASK = 1
WAITING_HOUR = 2
WAITING_SAP  = 3

# ── REFERENCIA GLOBAL ─────────────────────────────────────────────────────────

_app: Application | None = None

# ── HELPERS ───────────────────────────────────────────────────────────────────

def is_me(update: Update) -> bool:
    return update.effective_user.id == MY_ID

async def deny(update: Update):
    await update.message.reply_text("Bot personal, acceso restringido.")

AYUDA_TEXTO = (
    "COMANDOS DISPONIBLES\n\n"
    "/briefing     — Briefing matutino ahora\n"
    "/tarde        — Resumen vespertino ahora\n"
    "/tarea        — Agregar tarea\n"
    "/tareas       — Ver tareas pendientes\n"
    "/hecho        — Marcar tarea completada\n"
    "/borrar       — Eliminar tarea\n"
    "/sap          — Ayuda con SAP o Excel\n"
    "/podcast      — Recomendaciones de podcasts (con links)\n"
    "/finde        — Que hacer este fin de semana en Chihuahua\n"
    "/hora         — Cambiar hora del briefing manana\n"
    "/config_cal   — Conectar Google Calendar (iCal)\n"
    "/estado       — Ver estado del scheduler\n"
    "/ayuda        — Ver este mensaje"
)

# ── /start ────────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if MY_ID == 0:
        await update.message.reply_text(
            f"Bot no configurado aun.\n\n"
            f"Tu Telegram user_id es:\n{user_id}\n\n"
            f"Pegalo en config.py en MY_ID y reinicia el bot."
        )
        return

    if not is_me(update):
        await deny(update)
        return

    hora_actual = db.get_config("hora_envio", HORA_ENVIO)
    hora_tarde  = db.get_config("hora_envio_tarde", HORA_ENVIO_TARDE)
    await update.message.reply_text(
        f"Morning Commander activo.\n\n"
        f"Briefing manana: {hora_actual}\n"
        f"Resumen tarde:   {hora_tarde}\n\n"
        + AYUDA_TEXTO
    )

# ── /ayuda ────────────────────────────────────────────────────────────────────

async def cmd_ayuda(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    if not is_me(update):
        await deny(update)
        return
    await update.message.reply_text(AYUDA_TEXTO)

# ── /briefing ─────────────────────────────────────────────────────────────────

async def cmd_briefing(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    if not is_me(update):
        await deny(update)
        return
    await update.message.reply_text("Generando tu briefing...")
    try:
        mensaje = await briefing_module.generar_briefing()
        await update.message.reply_text(mensaje)
    except Exception as e:
        logger.error(f"Error en /briefing: {e}")
        await update.message.reply_text(f"Error generando el briefing: {e}")

# ── /tarde ────────────────────────────────────────────────────────────────────

async def cmd_tarde(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    if not is_me(update):
        await deny(update)
        return
    await update.message.reply_text("Generando tu resumen del dia...")
    try:
        mensaje = await briefing_module.generar_briefing_tarde()
        await update.message.reply_text(mensaje)
    except Exception as e:
        logger.error(f"Error en /tarde: {e}")
        await update.message.reply_text(f"Error generando el resumen: {e}")

# ── /tarea ────────────────────────────────────────────────────────────────────

async def cmd_tarea_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_me(update):
        await deny(update)
        return ConversationHandler.END

    if context.args:
        texto = " ".join(context.args).strip()
        db.agregar_tarea(texto)
        await update.message.reply_text(f"Tarea agregada: {texto}")
        return ConversationHandler.END

    await update.message.reply_text("Que tarea quieres agregar?")
    return WAITING_TASK

async def cmd_tarea_recibir(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    if texto:
        db.agregar_tarea(texto)
        await update.message.reply_text(f"Tarea agregada: {texto}")
    else:
        await update.message.reply_text("No entendi la tarea. Usa /tarea de nuevo.")
    return ConversationHandler.END

# ── /tareas ───────────────────────────────────────────────────────────────────

async def cmd_tareas(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    if not is_me(update):
        await deny(update)
        return
    tareas = db.obtener_tareas()
    if not tareas:
        await update.message.reply_text("Sin tareas pendientes. Usa /tarea para agregar una.")
        return
    lista = "\n".join(f"{i+1}. {t[1]}" for i, t in enumerate(tareas))
    await update.message.reply_text(f"TAREAS PENDIENTES ({len(tareas)})\n\n{lista}\n\nUsa /hecho para completarlas.")

# ── /hecho y /borrar ──────────────────────────────────────────────────────────

async def _mostrar_menu_tareas(update: Update, accion: str):
    tareas = db.obtener_tareas()
    if not tareas:
        await update.message.reply_text("Sin tareas pendientes.")
        return
    keyboard = [
        [InlineKeyboardButton(
            f"{i+1}. {t[1][:50]}{'...' if len(t[1]) > 50 else ''}",
            callback_data=f"{accion}_{t[0]}"
        )]
        for i, t in enumerate(tareas)
    ]
    keyboard.append([InlineKeyboardButton("Cancelar", callback_data="cancelar")])
    texto = "Cual tarea completaste?" if accion == "hecho" else "Cual tarea quieres eliminar?"
    await update.message.reply_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))

async def cmd_hecho(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    if not is_me(update):
        await deny(update)
        return
    await _mostrar_menu_tareas(update, "hecho")

async def cmd_borrar(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    if not is_me(update):
        await deny(update)
        return
    await _mostrar_menu_tareas(update, "borrar")

async def callback_tareas(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cancelar":
        await query.edit_message_text("Cancelado.")
        return

    accion, tarea_id_str = query.data.rsplit("_", 1)
    tarea_id = int(tarea_id_str)

    if accion == "hecho":
        texto = db.completar_tarea(tarea_id)
        msg   = f"Completada: {texto}. Bien hecho!" if texto else "No encontre esa tarea."
        await query.edit_message_text(msg)
    elif accion == "borrar":
        texto = db.borrar_tarea(tarea_id)
        msg   = f"Eliminada: {texto}" if texto else "No encontre esa tarea."
        await query.edit_message_text(msg)

# ── /sap ──────────────────────────────────────────────────────────────────────

async def cmd_sap_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_me(update):
        await deny(update)
        return ConversationHandler.END

    if context.args:
        descripcion = " ".join(context.args).strip()
        await update.message.reply_text("Consultando...")
        respuesta = await features_module.consulta_sap_excel(descripcion)
        await update.message.reply_text(respuesta)
        return ConversationHandler.END

    await update.message.reply_text(
        "Describe tu situacion o pregunta sobre SAP o Excel.\n\n"
        "Ejemplos:\n"
        "- Necesito registrar una factura de proveedor extranjero\n"
        "- Como comparar gasto real vs presupuesto en Excel\n"
        "- Que transaccion uso para ver saldos de cuentas por pagar"
    )
    return WAITING_SAP

async def cmd_sap_recibir(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    descripcion = update.message.text.strip()
    await update.message.reply_text("Consultando...")
    respuesta = await features_module.consulta_sap_excel(descripcion)
    await update.message.reply_text(respuesta)
    return ConversationHandler.END

# ── /podcast ──────────────────────────────────────────────────────────────────

async def cmd_podcast(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    if not is_me(update):
        await deny(update)
        return
    await update.message.reply_text("Buscando podcasts entretenidos para ti...")
    recomendaciones = await features_module.recomendar_podcasts()
    await update.message.reply_text(
        "PODCASTS RECOMENDADOS PARA HOY\n\n" + recomendaciones
    )

# ── /finde ────────────────────────────────────────────────────────────────────

async def cmd_finde(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    if not is_me(update):
        await deny(update)
        return
    await update.message.reply_text("Buscando planes para el fin de semana en Chihuahua...")
    sugerencias = await features_module.actividades_finde()
    await update.message.reply_text(
        "QUE HACER ESTE FIN DE SEMANA EN CHIHUAHUA\n\n" + sugerencias
    )

# ── /hora ─────────────────────────────────────────────────────────────────────

async def cmd_hora_start(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    if not is_me(update):
        await deny(update)
        return ConversationHandler.END
    hora_actual = db.get_config("hora_envio", HORA_ENVIO)
    await update.message.reply_text(
        f"Hora actual del briefing manana: {hora_actual}\n\n"
        f"A que hora lo quieres recibir?\n"
        f"Escribe en formato HH:MM (ej: 06:00)"
    )
    return WAITING_HOUR

async def cmd_hora_recibir(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    try:
        h, m = texto.split(":")
        h, m = int(h), int(m)
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
        nueva_hora = f"{h:02d}:{m:02d}"
    except (ValueError, AttributeError):
        await update.message.reply_text("Formato invalido. Usa HH:MM (ej: 06:30).")
        return WAITING_HOUR

    db.set_config("hora_envio", nueva_hora)
    sched_module.programar_briefing(_enviar_briefing_manana, nueva_hora)
    await update.message.reply_text(f"Briefing programado para las {nueva_hora} todos los dias.")
    return ConversationHandler.END

# ── /config_cal ───────────────────────────────────────────────────────────────

async def cmd_config_cal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_me(update):
        await deny(update)
        return

    if not context.args:
        ical_actual = db.get_config("ical_url", "")
        estado = "Conectado" if ical_actual else "No configurado"
        await update.message.reply_text(
            f"Google Calendar: {estado}\n\n"
            f"Para conectarlo:\n"
            f"1. Abre Google Calendar en web\n"
            f"2. Configuracion de tu calendario\n"
            f"3. Busca 'Direccion secreta en formato iCal'\n"
            f"4. Copia esa URL y enviala asi:\n\n"
            f"/config_cal https://calendar.google.com/calendar/ical/..."
        )
        return

    url = context.args[0].strip()
    if not url.startswith("https://calendar.google.com"):
        await update.message.reply_text(
            "URL invalida. Debe ser una URL de Google Calendar iCal."
        )
        return

    db.set_config("ical_url", url)
    await update.message.reply_text(
        "Google Calendar conectado. El briefing de manana incluira tus eventos."
    )

# ── /estado ───────────────────────────────────────────────────────────────────

async def cmd_estado(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    if not is_me(update):
        await deny(update)
        return

    hora_m = db.get_config("hora_envio",      HORA_ENVIO)
    hora_t = db.get_config("hora_envio_tarde", HORA_ENVIO_TARDE)
    ical   = db.get_config("ical_url", "")
    ahora  = datetime.now().strftime("%H:%M:%S")

    # Proxima ejecucion desde el scheduler
    def next_run(job_id: str) -> str:
        job = sched_module.scheduler.get_job(job_id)
        if job and job.next_run_time:
            return job.next_run_time.strftime("%Y-%m-%d %H:%M")
        return "No programado"

    manana_next = next_run("briefing_manana")
    tarde_next  = next_run("briefing_tarde")

    lineas = [
        "ESTADO DEL BOT",
        "",
        f"Hora actual servidor: {ahora}",
        f"Scheduler activo: {'Si' if sched_module.scheduler.running else 'NO'}",
        "",
        f"Briefing manana ({hora_m})",
        f"  Proxima vez: {manana_next}",
        "",
        f"Resumen tarde ({hora_t})",
        f"  Proxima vez: {tarde_next}",
        "",
        f"Google Calendar: {'Conectado' if ical else 'No configurado'}",
    ]
    await update.message.reply_text("\n".join(lineas))

# ── CANCELAR ──────────────────────────────────────────────────────────────────

async def cmd_cancelar(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operacion cancelada.")
    return ConversationHandler.END

async def cmd_unknown(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    if not is_me(update):
        await deny(update)
        return
    await update.message.reply_text("No reconozco ese comando.\n\n" + AYUDA_TEXTO)

# ── CALLBACKS DEL SCHEDULER ───────────────────────────────────────────────────

async def _enviar_briefing_manana():
    if _app is None:
        return
    try:
        mensaje = await briefing_module.generar_briefing()
        await _app.bot.send_message(chat_id=MY_ID, text=mensaje)
        logger.info("Briefing matutino enviado.")
    except Exception as e:
        logger.error(f"Error enviando briefing manana: {e}")
        try:
            await _app.bot.send_message(
                chat_id=MY_ID,
                text=f"Error en el briefing matutino: {e}\nUsa /briefing para reintentarlo."
            )
        except Exception:
            pass

async def _enviar_briefing_tarde():
    if _app is None:
        return
    try:
        mensaje = await briefing_module.generar_briefing_tarde()
        await _app.bot.send_message(chat_id=MY_ID, text=mensaje)
        logger.info("Briefing vespertino enviado.")
    except Exception as e:
        logger.error(f"Error enviando briefing tarde: {e}")
        try:
            await _app.bot.send_message(
                chat_id=MY_ID,
                text=f"Error en el resumen vespertino: {e}\nUsa /tarde para reintentarlo."
            )
        except Exception:
            pass

# ── POST INIT ─────────────────────────────────────────────────────────────────

async def post_init(application: Application) -> None:
    global _app
    _app = application

    hora_m = db.get_config("hora_envio",      HORA_ENVIO)
    hora_t = db.get_config("hora_envio_tarde", HORA_ENVIO_TARDE)

    sched_module.init_scheduler(
        _enviar_briefing_manana,
        _enviar_briefing_tarde,
        hora_m,
        hora_t,
    )
    print(f"[OK] Morning Commander activo. Manana: {hora_m} | Tarde: {hora_t}")
    logger.info(f"Bot listo. Manana: {hora_m} | Tarde: {hora_t}")

# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    db.init_db()

    app = Application.builder().token(TOKEN).post_init(post_init).build()

    # ConversationHandler /tarea
    tarea_conv = ConversationHandler(
        entry_points=[CommandHandler("tarea", cmd_tarea_start)],
        states={WAITING_TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_tarea_recibir)]},
        fallbacks=[
            CommandHandler("cancelar", cmd_cancelar),
            MessageHandler(filters.COMMAND, cmd_cancelar),
        ],
    )

    # ConversationHandler /hora
    hora_conv = ConversationHandler(
        entry_points=[CommandHandler("hora", cmd_hora_start)],
        states={WAITING_HOUR: [MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_hora_recibir)]},
        fallbacks=[
            CommandHandler("cancelar", cmd_cancelar),
            MessageHandler(filters.COMMAND, cmd_cancelar),
        ],
    )

    # ConversationHandler /sap
    sap_conv = ConversationHandler(
        entry_points=[CommandHandler("sap", cmd_sap_start)],
        states={WAITING_SAP: [MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_sap_recibir)]},
        fallbacks=[
            CommandHandler("cancelar", cmd_cancelar),
            MessageHandler(filters.COMMAND, cmd_cancelar),
        ],
    )

    app.add_handler(CommandHandler("start",      cmd_start))
    app.add_handler(CommandHandler("ayuda",      cmd_ayuda))
    app.add_handler(CommandHandler("briefing",   cmd_briefing))
    app.add_handler(CommandHandler("tarde",      cmd_tarde))
    app.add_handler(CommandHandler("tareas",     cmd_tareas))
    app.add_handler(CommandHandler("hecho",      cmd_hecho))
    app.add_handler(CommandHandler("borrar",     cmd_borrar))
    app.add_handler(CommandHandler("podcast",    cmd_podcast))
    app.add_handler(CommandHandler("finde",      cmd_finde))
    app.add_handler(CommandHandler("config_cal", cmd_config_cal))
    app.add_handler(CommandHandler("estado",     cmd_estado))
    app.add_handler(tarea_conv)
    app.add_handler(hora_conv)
    app.add_handler(sap_conv)
    app.add_handler(CallbackQueryHandler(callback_tareas))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_unknown))

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
