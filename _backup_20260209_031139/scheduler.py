from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo
from datetime import datetime

from app.keyboards.common import reminder_kb
from app.db.database import get_all_users, ensure_daily_row
from app.services.report import send_daily_report


def today_str(tz: str) -> str:
    return datetime.now(ZoneInfo(tz)).strftime("%Y-%m-%d")


async def send_reminders(bot, timezone: str):
    users = await get_all_users()
    date = today_str(timezone)

    for row in users:
        # get_all_users() qaytargan row uzun bo‘lishi mumkin
        telegram_id = row[0]
        first_name = row[1] if len(row) > 1 else ""
        last_name = row[2] if len(row) > 2 else ""

        await ensure_daily_row(telegram_id, date)
        await bot.send_message(
            chat_id=telegram_id,
            text="🎥 Video jo'natish esingizdan chiqmadimi?",
            reply_markup=reminder_kb()
        )


def setup_scheduler(bot, timezone: str) -> AsyncIOScheduler:
    tz = ZoneInfo(timezone)
    scheduler = AsyncIOScheduler(timezone=tz)

    # Eslatmalar: 10:00, 15:00, 18:00 (Toshkent vaqti)
    scheduler.add_job(send_reminders, CronTrigger(hour=10, minute=0, timezone=tz), args=[bot, timezone])
    scheduler.add_job(send_reminders, CronTrigger(hour=15, minute=0, timezone=tz), args=[bot, timezone])
    scheduler.add_job(send_reminders, CronTrigger(hour=18, minute=0, timezone=tz), args=[bot, timezone])

    # Hisobot: 07:00 (Toshkent vaqti)
    scheduler.add_job(send_daily_report, CronTrigger(hour=7, minute=0, timezone=tz), args=[bot])

    return scheduler
