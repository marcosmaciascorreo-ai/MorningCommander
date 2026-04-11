"""
scheduler.py — Programación del envío diario con APScheduler
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

TIMEZONE = "America/Chihuahua"

# Instancia global del scheduler
scheduler = AsyncIOScheduler(timezone=TIMEZONE)


def init_scheduler(send_func, hora_str: str):
    """Inicia el scheduler y programa el primer envío.

    Args:
        send_func: coroutine async que envía el briefing
        hora_str:  hora en formato "HH:MM"
    """
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler iniciado.")

    programar_briefing(send_func, hora_str)


def programar_briefing(send_func, hora_str: str):
    """Programa o reprograma el envío diario.

    Elimina el job anterior (si existe) y crea uno nuevo.
    """
    try:
        hora, minuto = map(int, hora_str.split(":"))
    except ValueError:
        logger.error(f"Hora inválida: {hora_str}. Se usará 05:50.")
        hora, minuto = 5, 50

    # Eliminar job existente
    if scheduler.get_job("briefing_diario"):
        scheduler.remove_job("briefing_diario")

    scheduler.add_job(
        send_func,
        CronTrigger(hour=hora, minute=minuto, timezone=TIMEZONE),
        id="briefing_diario",
        name="Briefing Diario",
        misfire_grace_time=300,  # 5 minutos de margen si el sistema estaba dormido
    )

    logger.info(f"Briefing programado para las {hora:02d}:{minuto:02d} ({TIMEZONE})")
