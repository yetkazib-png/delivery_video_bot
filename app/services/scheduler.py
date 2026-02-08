from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from aiogram.exceptions import TelegramForbiddenError

from app.keyboards.common import reminder_kb
from app.db.database import (
    get_all_users,
    ensure_daily_row,
    get_pending_videos,
    bump_pending_attempt,
    delete_pending_video,
    get_user,
    add_video,
)
from app.services.report import send_daily_group_report
from app.config import load_config
from app.services.sheets import SheetsConfig, append_video_row


def today_str(tz: str) -> str:
    return datetime.now(ZoneInfo(tz)).strftime("%Y-%m-%d")


async def send_reminders(bot, tz: str):
    users = await get_all_users()
    date = today_str(tz)

    for row in users:
        telegram_id = row[0]
        await ensure_daily_row(telegram_id, date)
        try:
            await bot.send_message(
                chat_id=telegram_id,
                text="🎥 Video jo'natish esingizdan chiqmadimi?",
                reply_markup=reminder_kb(),
            )
        except TelegramForbiddenError:
            # user botni block qilgan — crash qilmaymiz
            continue
        except Exception:
            continue


async def flush_pending_videos(bot):
    """
    Internet sust bo'lganda navbatga tushgan videolarni keyinroq yuboradi.
    Har 2 daqiqada ishlaydi.
    """
    cfg = load_config()
    pendings = await get_pending_videos(limit=20)
    if not pendings:
        return

    for pid, telegram_id, date, kindergarten_no, file_id, attempts in pendings:
        # 1) user ma'lumotlari
        user = await get_user(telegram_id)
        if not user:
            await delete_pending_video(pid)
            continue

        first_name = user[1]
        last_name = user[2]
        phone = user[3] or ""
        car_plate = user[4] or ""

        # 2) caption (oddiy, username/personal mention bu yerda kerak emas — guruh uchun)
        stamp = datetime.now(ZoneInfo(cfg.timezone)).strftime("%Y-%m-%d %H:%M")
        caption = (
            "📦 Yetkazib berish tasdiqi\n"
            f"🏫 Bog'cha №: {kindergarten_no}\n"
            f"👤 Yetkazib beruvchi: {first_name} {last_name}\n"
            f"📞 Telefon: {phone}\n"
            f"🚗 Avto: {car_plate}\n"
            f"🕒 Vaqt: {stamp}\n"
            f"⏳ (Navbatdan yuborildi)"
        )

        try:
            sent = await bot.send_video(
                chat_id=cfg.group_chat_id,
                video=file_id,
                caption=caption,
            )
        except Exception as e:
            # ko'p urinish bo'lsa o'chirib yuboramiz (masalan 10 martadan keyin)
            await bump_pending_attempt(pid, f"{type(e).__name__}: {e}")
            if int(attempts) >= 9:
                await delete_pending_video(pid)
            continue

        # Telegram link (Sheets uchun)
        internal_id = str(cfg.group_chat_id)
        if internal_id.startswith("-100"):
            internal_id = internal_id[4:]
        else:
            internal_id = internal_id.lstrip("-")
        video_link = f"https://t.me/c/{internal_id}/{sent.message_id}"

        # Sheets
        sheet_row = None
        try:
            sheets_cfg = SheetsConfig(sheet_id=cfg.sheet_id)
            sheet_row = append_video_row(
                sheets_cfg,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                car_plate=car_plate,
                date_str=date,
                kindergarten_no=kindergarten_no,
                video_link=video_link,
            )
        except Exception:
            sheet_row = None

        # DB
        try:
            await add_video(telegram_id, date, kindergarten_no, file_id, sheet_row=sheet_row)
        except Exception:
            pass

        # navbatdan o'chiramiz
        await delete_pending_video(pid)


def setup_scheduler(bot, timezone: str) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=ZoneInfo(timezone))

    # ✅ 3 marotaba eslatma
    scheduler.add_job(send_reminders, CronTrigger(hour=10, minute=0), args=[bot, timezone])
    scheduler.add_job(send_reminders, CronTrigger(hour=15, minute=0), args=[bot, timezone])
    scheduler.add_job(send_reminders, CronTrigger(hour=18, minute=0), args=[bot, timezone])

    # ✅ pending videolarni flush (2 daqiqada bir)
    scheduler.add_job(flush_pending_videos, IntervalTrigger(minutes=2), args=[bot])

    # ✅ 07:00 guruhga hisobot
    scheduler.add_job(send_daily_group_report, CronTrigger(hour=7, minute=0), args=[bot])

    return scheduler
