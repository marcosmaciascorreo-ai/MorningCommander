"""
scheduler.py — Programacion del briefing matutino y vespertino
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger   = logging.getLogger(__name__)
TIMEZONE = "America/Chihuahua"

scheduler = AsyncIOScheduler(timezone=TIMEZONE)


def init_scheduler(send_manana_func, send_tarde_func, hora_manana: str, hora_tarde: str):
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler iniciado.")

    programar_briefing(send_manana_func, hora_manana)
    programar_briefing_tarde(send_tarde_func, hora_tarde)


def programar_briefing(send_func, hora_str: str):
    """Programa o reprograma el briefing matutino."""
    try:
        hora, minuto = map(int, hora_str.split(":"))
    except ValueError:
        hora, minuto = 5, 50

    if scheduler.get_job("briefing_manana"):
        scheduler.remove_job("briefing_manana")

    scheduler.add_job(
        send_func,
        CronTrigger(hour=hora, minute=minuto, timezone=TIMEZONE),
        id="briefing_manana",
        name="Briefing Matutino",
        misfire_grace_time=300,
    )
    logger.info(f"Briefing manana programado: {hora:02d}:{minuto:02d} ({TIMEZONE})")


def programar_briefing_tarde(send_func, hora_str: str):
    """Programa o reprograma el briefing vespertino."""
    try:
        hora, minuto = map(int, hora_str.split(":"))
    except ValueError:
        hora, minuto = 18, 0

    if scheduler.get_job("briefing_tarde"):
        scheduler.remove_job("briefing_tarde")

    scheduler.add_job(
        send_func,
        CronTrigger(hour=hora, minute=minuto, timezone=TIMEZONE),
        id="briefing_tarde",
        name="Briefing Vespertino",
        misfire_grace_time=300,
    )
    logger.info(f"Briefing tarde programado: {hora:02d}:{minuto:02d} ({TIMEZONE})")
