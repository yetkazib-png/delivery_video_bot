from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


@dataclass
class SheetsConfig:
    sheet_id: str
    creds_path: str
    worksheet: str = "Logs"


def _client(creds_path: str) -> gspread.Client:
    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    return gspread.authorize(creds)


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
    Ustunlar:
    A Timestamp
    B Sana
    C Ism
    D Familiya
    E Telefon
    F Avto raqam
    G Bog'cha nomeri
    H Video link
    I ReminderAction
    J Sabab
    Qaytaradi: qo'shilgan qator raqami (1-based)
    """
    gc = _client(cfg.creds_path)
    ws = gc.open_by_key(cfg.sheet_id).worksheet(cfg.worksheet)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row = [
        ts,                 # A
        date_str,           # B
        first_name,         # C
        last_name,          # D
        phone,              # E
        car_plate,          # F
        kindergarten_no,    # G
        video_link,         # H
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
    """
    Reminder bosilganda (Yubordim / Yubormadim) event-qator yozadi.
    Video bo'lmasa ham action/reason saqlanadi.
    """
    gc = _client(cfg.creds_path)
    ws = gc.open_by_key(cfg.sheet_id).worksheet(cfg.worksheet)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row = [
        ts,         # A
        date_str,   # B
        first_name, # C
        last_name,  # D
        phone,      # E
        car_plate,  # F
        "",         # G Bog'cha nomeri
        "",         # H Video link
        action,     # I ReminderAction
        reason,     # J Sabab
    ]

    ws.append_row(row, value_input_option="USER_ENTERED")
    return len(ws.get_all_values())


def update_reason(cfg: SheetsConfig, *, sheet_row: int, reason: str) -> None:
    """
    Sabab ustuni = J (10)
    """
    gc = _client(cfg.creds_path)
    ws = gc.open_by_key(cfg.sheet_id).worksheet(cfg.worksheet)
    ws.update_cell(sheet_row, 10, reason)


def update_reminder_action(cfg: SheetsConfig, *, sheet_row: int, action: str) -> None:
    """
    ReminderAction ustuni = I (9)
    """
    gc = _client(cfg.creds_path)
    ws = gc.open_by_key(cfg.sheet_id).worksheet(cfg.worksheet)
    ws.update_cell(sheet_row, 9, action)
