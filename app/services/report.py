from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import load_config
from app.db.database import get_report_rows_for_date, get_senders_for_date


def now_tz(tz: str) -> datetime:
    return datetime.now(ZoneInfo(tz))


def date_str(d: datetime) -> str:
    return d.strftime("%Y-%m-%d")


async def send_daily_report(bot):
    """
    Eski variant (qoldiramiz):
    Kechagi (yesterday) umumiy hisobot (hamma userlar).
    """
    cfg = load_config()

    yesterday = now_tz(cfg.timezone) - timedelta(days=1)
    date = date_str(yesterday)

    rows = await get_report_rows_for_date(date)

    lines = [f"📊 {date} yetkazib berish hisoboti"]
    idx = 1

    for first_name, last_name, video_count, status, reason in rows:
        lines.append(f"\n{idx}) {first_name} {last_name}")
        lines.append(f"   📌 Video: {video_count} dona")

        if int(video_count) == 0:
            lines.append(f"   ✍️ Sabab: {reason if reason else '(kiritilmagan)'}")

        idx += 1

    await bot.send_message(chat_id=cfg.group_chat_id, text="\n".join(lines))


async def send_daily_group_report(bot):
    """
    ✅ YANGI: Kechagi (yesterday) — faqat video yuborgan haydovchilar ro'yxati.
    Har kuni 07:00 da guruhga yuboriladi.
    """
    cfg = load_config()

    # 07:00 da "kechagi kun" bo‘yicha report
    yesterday = now_tz(cfg.timezone) - timedelta(days=1)
    date = date_str(yesterday)

    rows = await get_senders_for_date(date)  # [(tid, fn, ln, cnt), ...]

    total_videos = sum(r[3] for r in rows) if rows else 0
    total_drivers = len(rows)

    text = (
        f"📊 Kunlik hisobot ({date})\n"
        f"🎥 Jami video: {total_videos}\n"
        f"👥 Video yuborgan haydovchilar: {total_drivers}\n"
    )

    if not rows:
        text += "\n⚠️ Kecha hech kim video yubormagan."
        await bot.send_message(chat_id=cfg.group_chat_id, text=text)
        return

    text += "\n"
    for i, (_tid, fn, ln, cnt) in enumerate(rows, start=1):
        text += f"{i}) {fn} {ln} — {cnt} ta\n"

    await bot.send_message(chat_id=cfg.group_chat_id, text=text)
