from datetime import datetime

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from app.db.database import (
    get_user,
    ensure_daily_row,
    count_videos_for_user_date,
    save_reason,
    get_last_video_sheet_row,
)
from app.utils.states import ReasonFlow
from app.keyboards.common import main_menu
from app.config import load_config
from app.services.sheets import SheetsConfig, append_reminder_event, update_reminder_action, update_reason

router = Router()


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


@router.callback_query(F.data == "rem_yes")
async def rem_yes(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    if not user:
        await call.message.answer("Avval /start orqali ro'yxatdan o'ting.")
        await call.answer()
        return

    cfg = load_config()
    date = today_str()
    await ensure_daily_row(call.from_user.id, date)

    first_name, last_name = user[1], user[2]

    # ✅ Sheets: event yozamiz
    sheets_cfg = SheetsConfig(sheet_id=cfg.sheet_id, creds_path=cfg.google_creds_path, worksheet="Logs")
    try:
        append_reminder_event(
            sheets_cfg,
            first_name=first_name,
            last_name=last_name,
            date_str=date,
            action="YUBORDIM",
            reason="",
        )
    except Exception:
        pass

    # ✅ Agar bugun video bo'lsa, oxirgi video qatorini ham update qilamiz
    try:
        last_row = await get_last_video_sheet_row(call.from_user.id, date)
        if last_row:
            update_reminder_action(sheets_cfg, sheet_row=last_row, action="YUBORDIM")
    except Exception:
        pass

    count = await count_videos_for_user_date(call.from_user.id, date)
    if count == 0:
        await call.message.answer(
            "Hali video yuborilmagan. Iltimos, '🎥 Video yuborish' orqali yuboring.",
            reply_markup=main_menu()
        )
    else:
        await call.message.answer(f"✅ Qayd etildi. Bugun {count} ta video bor.", reply_markup=main_menu())

    await call.answer()


@router.callback_query(F.data == "rem_no")
async def rem_no(call: CallbackQuery, state: FSMContext):
    user = await get_user(call.from_user.id)
    if not user:
        await call.message.answer("Avval /start orqali ro'yxatdan o'ting.")
        await call.answer()
        return

    await call.message.answer("Nega video yuborilmadi? Sababini yozing:")
    await state.set_state(ReasonFlow.waiting_reason)
    await call.answer()


@router.message(ReasonFlow.waiting_reason)
async def got_reason(message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Avval /start orqali ro'yxatdan o'ting.")
        await state.clear()
        return

    cfg = load_config()
    date = today_str()
    reason_text = str(message.text).strip()

    # ✅ DB: sabab saqlanadi
    await save_reason(message.from_user.id, date, reason_text)

    first_name, last_name = user[1], user[2]

    # ✅ Sheets: event yozamiz
    sheets_cfg = SheetsConfig(sheet_id=cfg.sheet_id, worksheet="Logs")
    try:

        append_reminder_event(
            sheets_cfg,
            first_name=first_name,
            last_name=last_name,
            date_str=date,
            action="YUBORMADIM",
            reason=reason_text,
        )
    except Exception:
        pass

    # ✅ Agar bugun video bo'lsa, oxirgi video qatoriga ham sababni yozamiz
    try:
        last_row = await get_last_video_sheet_row(message.from_user.id, date)
        if last_row:
            update_reminder_action(sheets_cfg, sheet_row=last_row, action="YUBORMADIM")
            update_reason(sheets_cfg, sheet_row=last_row, reason=reason_text)
    except Exception:
        pass

    await message.answer("✅ Sabab saqlandi.", reply_markup=main_menu())
    await state.clear()
