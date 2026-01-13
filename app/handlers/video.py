from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from app.keyboards.common import main_menu
from app.utils.states import VideoFlow
from app.db.database import (
    get_user,
    ensure_daily_row,
    add_video,
    count_videos_for_user_date,
    get_daily_reason_and_status,
)
from app.config import load_config
from app.services.sheets import SheetsConfig, append_video_row

router = Router()


def today_str() -> str:
    return datetime.now(ZoneInfo("Asia/Tashkent")).strftime("%Y-%m-%d")


# ================= VIDEO YUBORISH BOSHLASH =================
@router.message(F.text == "🎥 Video yuborish")
async def ask_kindergarten_no(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Avval /start orqali ro'yxatdan o'ting.")
        return

    await message.answer(
        "🏫 Bog'cha nomerini kiriting (faqat raqam):",
        reply_markup=main_menu()
    )
    await state.set_state(VideoFlow.waiting_kindergarten_no)


@router.message(VideoFlow.waiting_kindergarten_no, F.text.regexp(r"^\d+$"))
async def got_kindergarten_no(message: Message, state: FSMContext):
    await state.update_data(kindergarten_no=message.text.strip())
    await state.set_state(VideoFlow.waiting_video)
    await message.answer("✅ Qabul qilindi. Endi videoni yuboring.")


# ================= VIDEO QABUL QILISH =================
@router.message(VideoFlow.waiting_video, F.video)
async def handle_video(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Avval /start orqali ro'yxatdan o'ting.")
        await state.clear()
        return

    data = await state.get_data()
    kindergarten_no = data.get("kindergarten_no")
    if not kindergarten_no:
        await message.answer("Bog'cha nomeri topilmadi.")
        await state.clear()
        return

    cfg = load_config()
    date = today_str()
    file_id = message.video.file_id

    # user = (telegram_id, first_name, last_name, phone, car_plate)
    first_name = user[1]
    last_name = user[2]
    phone = user[3] or ""
    car_plate = user[4] or ""

    # ===== TELEGRAM USER INFO =====
    tg = message.from_user
    tg_id = tg.id

    if tg.username:
        t_user = f"@{tg.username}"
    else:
        t_user = f'<a href="tg://user?id={tg_id}">Yozish</a>'

    contact_block = (
        f"👤 Yetkazib beruvchi: {first_name} {last_name}\n"
        f"💬 Aloqa: {t_user}\n"
        f"🆔 Telegram ID: {tg_id}"
    )

    stamp = datetime.now(ZoneInfo("Asia/Tashkent")).strftime("%Y-%m-%d %H:%M")

    caption = (
        "📦 Yetkazib berish tasdiqi\n"
        f"🏫 Bog'cha №: {kindergarten_no}\n"
        f"{contact_block}\n"
        f"📞 Telefon: {phone}\n"
        f"🚗 Avto: {car_plate}\n"
        f"🕒 Vaqt: {stamp}"
    )

    # ================= GURUHGA YUBORISH =================
    try:
        sent = await message.bot.send_video(
            chat_id=cfg.group_chat_id,
            video=file_id,
            caption=caption,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        await message.answer(f"❌ Guruhga yuborilmadi:\n{type(e).__name__}: {e}")
        await state.clear()
        return

    # ================= TELEGRAM LINK =================
    internal_id = str(cfg.group_chat_id)
    if internal_id.startswith("-100"):
        internal_id = internal_id[4:]
    else:
        internal_id = internal_id.lstrip("-")

    video_link = f"https://t.me/c/{internal_id}/{sent.message_id}"

    # ================= GOOGLE SHEETS =================
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
    except Exception as e:
        await message.answer(f"❌ Google Sheets xato: {e}")

    # ================= DB =================
    await add_video(
        message.from_user.id,
        date,
        kindergarten_no,
        file_id,
        sheet_row=sheet_row
    )

    await message.answer("✅ Video qabul qilindi.", reply_markup=main_menu())
    await state.clear()
    await state.set_state(VideoFlow.waiting_kindergarten_no)


# ================= BUGUNGI HOLAT =================
@router.message(F.text == "📄 Bugungi holatim")
async def today_status(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Avval /start orqali ro'yxatdan o'ting.")
        return

    date = today_str()
    await ensure_daily_row(message.from_user.id, date)

    count = await count_videos_for_user_date(message.from_user.id, date)
    status_reason = await get_daily_reason_and_status(message.from_user.id, date)
    _, reason = status_reason if status_reason else ("PENDING", None)

    text = (
        f"📄 Bugungi holat ({date})\n"
        f"📌 Bugun jo'natilgan videolar: {count} dona\n"
    )
    if count == 0:
        text += f"✍️ Sabab: {reason or '(kiritilmagan)'}"

    await message.answer(text, reply_markup=main_menu())
