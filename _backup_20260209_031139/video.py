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

TZ = "Asia/Tashkent"


def today_str() -> str:
    return datetime.now(ZoneInfo(TZ)).strftime("%Y-%m-%d")


def now_stamp() -> str:
    return datetime.now(ZoneInfo(TZ)).strftime("%Y-%m-%d %H:%M")


def extract_kindergarten_no(message: Message) -> str | None:
    """
    Bog'cha raqamini video caption (Добавить подпись) dan olamiz.
    Qoidalar:
      - faqat raqam bo'lsa: "43"
      - yoki "Bog'cha: 43", "№43", "KG 43" - ichidagi birinchi raqam olinadi
    """
    cap = (message.caption or "").strip()
    if not cap:
        return None

    if cap.isdigit():
        return cap

    import re
    m = re.search(r"\b(\d{1,5})\b", cap)
    if m:
        return m.group(1)

    return None


# ================= VIDEO YUBORISH BOSHLASH =================
@router.message(F.text == "🎥 Video yuborish")
async def start_video(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Avval /start orqali ro'yxatdan o'ting.")
        return

    await state.set_state(VideoFlow.waiting_video)
    await message.answer(
        "🎥 Videoni yuboring.\n\n"
        "⚠️ Video yuborayotganda pastdagi «Добавить подпись» joyiga bog'cha nomerini yozing.\n"
        "Masalan: 43",
        reply_markup=main_menu()
    )


# ================= VIDEO QABUL QILISH =================
@router.message(VideoFlow.waiting_video, F.video)
async def handle_video(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Avval /start orqali ro'yxatdan o'ting.")
        await state.clear()
        return

    kindergarten_no = extract_kindergarten_no(message)
    if not kindergarten_no:
        await message.answer(
            "❌ Bog'cha nomeri topilmadi.\n"
            "Iltimos videoni qaytadan yuboring va «Добавить подпись» joyiga bog'cha nomerini yozing.\n"
            "Masalan: 43"
        )
        return

    cfg = load_config()
    date = today_str()
    file_id = message.video.file_id

    # user = (telegram_id, first_name, last_name, phone, car_plate)
    first_name = user[1]
    last_name = user[2]
    phone = user[3] or ""
    car_plate = user[4] or ""

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

    caption = (
        "📦 Yetkazib berish tasdiqi\n"
        f"🏫 Bog'cha №: {kindergarten_no}\n"
        f"{contact_block}\n"
        f"📞 Telefon: {phone}\n"
        f"🚗 Avto: {car_plate}\n"
        f"🕒 Vaqt: {now_stamp()}"
    )

    try:
        sent = await message.bot.send_video(
            chat_id=cfg.group_chat_id,
            video=file_id,
            caption=caption,
            parse_mode="HTML",
        )
    except Exception as e:
        await message.answer(f"❌ Guruhga yuborilmadi:\n{type(e).__name__}: {e}")
        return

    internal_id = str(cfg.group_chat_id)
    if internal_id.startswith("-100"):
        internal_id = internal_id[4:]
    else:
        internal_id = internal_id.lstrip("-")

    video_link = f"https://t.me/c/{internal_id}/{sent.message_id}"

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

    await add_video(
        message.from_user.id,
        date,
        kindergarten_no,
        file_id,
        sheet_row=sheet_row
    )

    await message.answer("✅ Video qabul qilindi va guruhga yuborildi.", reply_markup=main_menu())
    await state.clear()


@router.message(VideoFlow.waiting_video)
async def waiting_video_wrong(message: Message):
    await message.answer(
        "Iltimos, videoni yuboring.\n"
        "Bog'cha nomerini «Добавить подпись» ga yozing."
    )


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
