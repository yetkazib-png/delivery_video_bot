from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import json

import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


@dataclass
class SheetsConfig:
    sheet_id: str
    worksheet: str = "Logs"
    timezone: str = "Asia/Tashkent"


def _client() -> gspread.Client:
    """
    Railway Variables -> GOOGLE_CREDS_JSON ichidan Service Account JSON olinadi.
    """
    creds_json = os.getenv("GOOGLE_CREDS_JSON")
    if not creds_json:
        raise RuntimeError("GOOGLE_CREDS_JSON topilmadi (Railway Variables tekshiring).")

    info = json.loads(creds_json)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)


def _now_str(tz: str) -> str:
    return datetime.now(ZoneInfo(tz)).strftime("%Y-%m-%d %H:%M:%S")


def append_video_row(
    cfg: SheetsConfig,
    *,
    first_name: str,
    last_name: str,
    phone: str,
    car_plate: str,
    date_str: str,
    kindergarten_no: str,
    video_link: str,
) -> int:
    """
    Video kelganda yangi qator qo'shadi.
    Qaytaradi: qo'shilgan qator raqami (1-based)
    """
    gc = _client()
    ws = gc.open_by_key(cfg.sheet_id).worksheet(cfg.worksheet)

    ts = _now_str(cfg.timezone)

    row = [
        ts,                 # A Timestamp
        date_str,           # B Sana
        first_name,         # C Ism
        last_name,          # D Familiya
        phone,              # E Telefon
        car_plate,          # F Avto raqam
        kindergarten_no,    # G Bog'cha nomeri
        video_link,         # H Video link
        "",                 # I ReminderAction
        "",                 # J Sabab
    ]

    ws.append_row(row, value_input_option="USER_ENTERED")
    return len(ws.get_all_values())


def append_reminder_event(
    cfg: SheetsConfig,
    *,
    first_name: str,
    last_name: str,
    phone: str,
    car_plate: str,
    date_str: str,
    action: str,
    reason: str = "",
) -> int:
    gc = _client()
    ws = gc.open_by_key(cfg.sheet_id).worksheet(cfg.worksheet)

    ts = _now_str(cfg.timezone)

    row = [
        ts,         # A
        date_str,   # B
        first_name, # C
        last_name,  # D
        phone,      # E
        car_plate,  # F
        "",         # G
        "",         # H
        action,     # I
        reason,     # J
    ]

    ws.append_row(row, value_input_option="USER_ENTERED")
    return len(ws.get_all_values())


def update_reason(cfg: SheetsConfig, *, sheet_row: int, reason: str) -> None:
    gc = _client()
    ws = gc.open_by_key(cfg.sheet_id).worksheet(cfg.worksheet)
    ws.update_cell(sheet_row, 10, reason)  # J = 10


def update_reminder_action(cfg: SheetsConfig, *, sheet_row: int, action: str) -> None:
    gc = _client()
    ws = gc.open_by_key(cfg.sheet_id).worksheet(cfg.worksheet)
    ws.update_cell(sheet_row, 9, action)  # I = 9
