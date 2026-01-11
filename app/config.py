from dataclasses import dataclass
import os
from dotenv import load_dotenv

@dataclass
class Config:
    bot_token: str
    group_chat_id: int
    timezone: str
    sheet_id: str
    creds_path: str  # <-- qo'shildi

def load_config() -> Config:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("BOT_TOKEN topilmadi (.env tekshiring).")

    group_chat_id = int(os.getenv("GROUP_CHAT_ID", "0"))
    timezone = os.getenv("TIMEZONE", "Asia/Tashkent")

    sheet_id = os.getenv("SHEET_ID", "")
    if not sheet_id:
        raise RuntimeError("SHEET_ID topilmadi (.env tekshiring).")

    # service_account fayl yo'li (Railway'da ko'pincha /app/service_account.json bo'ladi)
    creds_path = os.getenv("CREDS_PATH", "service_account.json")
    if not creds_path:
        raise RuntimeError("CREDS_PATH topilmadi (.env tekshiring).")

    return Config(
        bot_token=bot_token,
        group_chat_id=group_chat_id,
        timezone=timezone,
        sheet_id=sheet_id,
        creds_path=creds_path,
    )
