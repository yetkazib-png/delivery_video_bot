from datetime import datetime, timedelta
from app.config import load_config
from app.db.database import get_report_rows_for_date

def date_str(d: datetime) -> str:
    return d.strftime("%Y-%m-%d")

async def send_daily_report(bot):
    cfg = load_config()

    yesterday = datetime.now() - timedelta(days=1)
    date = date_str(yesterday)

    rows = await get_report_rows_for_date(date)

    lines = [f"📊 {date} yetkazib berish hisoboti"]
    idx = 1

    # rows: (first_name, last_name, video_count, status, reason)
    for first_name, last_name, video_count, status, reason in rows:
        lines.append(f"\n{idx}) {first_name} {last_name}")
        lines.append(f"   📌 Bugun jo'natilgan videolar soni: {video_count} dona")

        if int(video_count) == 0:
            lines.append(f"   ✍️ Sabab: {reason if reason else '(kiritilmagan)'}")

        idx += 1

    await bot.send_message(chat_id=cfg.group_chat_id, text="\n".join(lines))
