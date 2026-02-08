from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import load_config
from app.db.database import get_senders_for_date


def now_tz(tz: str) -> datetime:
    return datetime.now(ZoneInfo(tz))


def date_str(d: datetime) -> str:
    return d.strftime("%Y-%m-%d")


async def send_daily_group_report(bot):
    """
    ✅ 07:00 da guruhga KECHAGI kunda video yuborgan haydovchilar ro'yxati.
    """
    cfg = load_config()

    yesterday = now_tz(cfg.timezone) - timedelta(days=1)
    date = date_str(yesterday)

    rows = await get_senders_for_date(date)  # [(tid, fn, ln, cnt), ...]

    total_videos = sum(r[3] for r in rows) if rows else 0
    total_drivers = len(rows)

    text = (
        f"📊 Kunlik hisobot ({date})\n"
        f"👥 Video yuborgan haydovchilar: {total_drivers}\n"
        f"🎥 Jami video: {total_videos}\n"
    )

    if not rows:
        text += "\n❗ Kecha hech kim video yubormagan."
        await bot.send_message(chat_id=cfg.group_chat_id, text=text)
        return

    text += "\n📌 Ro'yxat:\n"
    for i, (_tid, fn, ln, cnt) in enumerate(rows, start=1):
        text += f"{i}) {fn} {ln} — {cnt} ta\n"

    await bot.send_message(chat_id=cfg.group_chat_id, text=text)
