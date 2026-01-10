from datetime import datetime

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
    return datetime.now().strftime("%Y-%m-%d")


# --- MENU tugmalari state ichida ham ishlashi uchun ---
@router.message(VideoFlow.waiting_kindergarten_no, F.text == "📄 Bugungi holatim")
@router.message(VideoFlow.waiting_video, F.text == "📄 Bugungi holatim")
async def today_status_from_state(message: Message, state: FSMContext):
    await state.clear()
    await today_status(message)


@router.message(VideoFlow.waiting_kindergarten_no, F.text == "Қӯлланма")
@router.message(VideoFlow.waiting_video, F.text == "Қӯлланма")
async def manual_from_state(message: Message, state: FSMContext):
    await state.clear()
    await manual(message)


@router.message(VideoFlow.waiting_kindergarten_no, F.text == "🎥 Video yuborish")
@router.message(VideoFlow.waiting_video, F.text == "🎥 Video yuborish")
async def restart_video_from_state(message: Message, state: FSMContext):
    await state.clear()
    await ask_kindergarten_no(message, state)


# --- Video yuborish oqimi ---
@router.message(F.text == "🎥 Video yuborish")
async def ask_kindergarten_no(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Avval /start orqali ro'yxatdan o'ting.")
        return

    await message.answer(
        "🏫 Bog'cha nomerini kiriting (faqat raqam, masalan: 12):",
        reply_markup=main_menu()
    )
    await state.set_state(VideoFlow.waiting_kindergarten_no)


@router.message(VideoFlow.waiting_kindergarten_no, F.text.regexp(r"^\d+$"))
async def got_kindergarten_no(message: Message, state: FSMContext):
    kg_no = message.text.strip()
    await state.update_data(kindergarten_no=kg_no)
    await state.set_state(VideoFlow.waiting_video)
    await message.answer("✅ Qabul qilindi. Endi videoni yuboring (video sifatida).")


@router.message(VideoFlow.waiting_kindergarten_no)
async def invalid_kindergarten_no(message: Message):
    await message.answer("Iltimos, bog'cha nomerini faqat raqam bilan kiriting (masalan: 12).")


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
        await message.answer("Bog'cha nomeri topilmadi. Qaytadan '🎥 Video yuborish' ni bosing.")
        await state.clear()
        return

    cfg = load_config()
    date = today_str()
    file_id = message.video.file_id

    # get_user qaytarishi: (telegram_id, first_name, last_name, phone, car_plate)
    first_name = user[1]
    last_name = user[2]
    phone = user[3] or ""
    car_plate = user[4] or ""

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    caption = (
        "📦 Yetkazib berish tasdiqi\n"
        f"🏫 Bog'cha №: {kindergarten_no}\n"
        f"👤 Yetkazib beruvchi: {first_name} {last_name}\n"
        f"📞 Telefon: {phone}\n"
        f"🚗 Avto: {car_plate}\n"
        f"🕒 Vaqt: {stamp}"
    )

    # ✅ 1) Avval guruhga yuboramiz va message_id olamiz
    try:
        sent = await message.bot.send_video(
            chat_id=cfg.group_chat_id,
            video=file_id,
            caption=caption
        )
    except Exception as e:
        await message.answer(f"❌ Guruhga yuborilmadi: {e.__class__.__name__}")
        await state.clear()
        return

    # ✅ 2) Telegram link yasaymiz (Sheets uchun)
    # -100XXXXXXXXXX -> XXXXXXXXXX
    internal_id = str(cfg.group_chat_id)
    if internal_id.startswith("-100"):
        internal_id = internal_id[4:]
    else:
        # ehtiyot chorasi: noto'g'ri format bo'lsa ham link yasashga urinamiz
        internal_id = internal_id.lstrip("-")

    video_link = f"https://t.me/c/{internal_id}/{sent.message_id}"

    # ✅ 3) Google Sheets'ga LINK yozamiz (phone + car_plate bilan)
    sheets_cfg = SheetsConfig(
        sheet_id=cfg.sheet_id,
        creds_path=cfg.google_creds_path,
        worksheet="Logs"
    )
    try:
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
        await message.answer(f"❌ Google Sheets'ga yozilmadi: {e.__class__.__name__}")
        sheet_row = None

    # ✅ 4) DBga saqlash (sheet_row bilan)
    await add_video(message.from_user.id, date, kindergarten_no, file_id, sheet_row=sheet_row)

    # ✅ 5) Userga javob
    await message.answer("✅ Video qabul qilindi va guruhga yuborildi.", reply_markup=main_menu())

    # Keyingi video uchun yana bog'cha nomerini so'raymiz
    await state.clear()
    await message.answer("Keyingi video uchun bog'cha nomerini kiriting (faqat raqam):")
    await state.set_state(VideoFlow.waiting_kindergarten_no)


@router.message(VideoFlow.waiting_video)
async def waiting_video_wrong(message: Message):
    await message.answer("Iltimos, endi videoni yuboring (video sifatida).")


@router.message(F.video)
async def video_without_flow(message: Message):
    await message.answer("Avval '🎥 Video yuborish' ni bosing va bog'cha nomerini kiriting.", reply_markup=main_menu())


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
    status, reason = status_reason if status_reason else ("PENDING", None)

    text = f"📄 Bugungi holat ({date})\n"
    text += f"📌 Bugun jo'natilgan videolar soni: {count} dona\n"
    if count == 0:
        text += f"✍️ Sabab: {reason if reason else '(kiritilmagan)'}\n"

    await message.answer(text, reply_markup=main_menu())


@router.message(F.text == "Қӯлланма")
async def manual(message: Message):
    from app.handlers.start import TUTORIAL_TEXT, TUTORIAL_VIDEO_FILE_ID

    await message.answer_video(TUTORIAL_VIDEO_FILE_ID)
    await message.answer(TUTORIAL_TEXT, reply_markup=main_menu())
