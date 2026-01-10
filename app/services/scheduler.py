from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo
from datetime import datetime

from app.keyboards.common import reminder_kb
from app.db.database import get_all_users, ensure_daily_row
from app.services.report import send_daily_report

def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")

async def send_reminders(bot):
    users = await get_all_users()
    date = today_str()

    for telegram_id, first_name, last_name in users:
        await ensure_daily_row(telegram_id, date)
        await bot.send_message(
            chat_id=telegram_id,
            text="🎥 Video jo'natish esingizdan chiqmadimi?",
            reply_markup=reminder_kb()
        )

def setup_scheduler(bot, timezone: str) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=ZoneInfo(timezone))

    scheduler.add_job(send_reminders, CronTrigger(hour=10, minute=0), args=[bot])
    scheduler.add_job(send_reminders, CronTrigger(hour=15, minute=0), args=[bot])
    scheduler.add_job(send_reminders, CronTrigger(hour=20, minute=0), args=[bot])

    scheduler.add_job(send_daily_report, CronTrigger(hour=6, minute=0), args=[bot])

    return scheduler
