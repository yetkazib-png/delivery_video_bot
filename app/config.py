from dataclasses import dataclass
import os
from dotenv import load_dotenv

@dataclass
class Config:
    bot_token: str
    group_chat_id: int
    timezone: str
    sheet_id: str
    google_creds_path: str

def load_config() -> Config:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("BOT_TOKEN topilmadi (.env tekshiring).")

    group_chat_id = int(os.getenv("GROUP_CHAT_ID", "0"))
    timezone = os.getenv("TIMEZONE", "Asia/Tashkent")

    sheet_id = os.getenv("SHEET_ID", "")
    google_creds_path = os.getenv("GOOGLE_CREDS_PATH", "service_account.json")

    if not sheet_id:
        raise RuntimeError("SHEET_ID topilmadi (.env tekshiring).")

    return Config(
        bot_token=bot_token,
        group_chat_id=group_chat_id,
        timezone=timezone,
        sheet_id=sheet_id,
        google_creds_path=google_creds_path,
    )
