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
    enqueue_pending_video,  # ✅ queue bo'lsa
)
from app.config import load_config
from app.services.sheets import SheetsConfig, append_video_row

router = Router()

TZ = "Asia/Tashkent"


def today_str() -> str:
    return datetime.now(ZoneInfo(TZ)).strftime("%Y-%m-%d")


def now_stamp() -> str:
    return datetime.now(ZoneInfo(TZ)).strftime("%Y-%m-%d %H:%M")


def extract_destination_text(message: Message) -> str | None:
    """
    Caption (Добавить подпись) dan 'borgan joyi' ni olamiz.
    Endi faqat raqam emas: text ham bo'lishi mumkin.
    Qoidalar:
      - caption bo'sh bo'lmasin
      - birinchi qatordagi matn olinadi (trim qilingan)
    """
    cap = (message.caption or "").strip()
    if not cap:
        return None

    # faqat 1-qatorni olamiz (agar ko'p qator yozsa ham)
    first_line = cap.splitlines()[0].strip()
    return first_line or None


@router.message(F.text == "🎥 Video yuborish")
async def start_video(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Avval /start orqali ro'yxatdan o'ting.")
        return

    await state.set_state(VideoFlow.waiting_video)
    await message.answer(
        "🎥 Videoni yuboring.\n\n"
        "⚠️ Video yuborayotganda pastdagi **Добавить подпись (caption)** joyiga "
        "**borgan joyi** ni yozing (raqam ham, text ham bo'ladi).\n"
        "Masalan: 14 yoki Muruvvatxona-2",
        reply_markup=main_menu(),
    )


@router.message(VideoFlow.waiting_video, F.video)
async def handle_video(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Avval /start orqali ro'yxatdan o'ting.")
        await state.clear()
        return

    destination = extract_destination_text(message)
    if not destination:
        await message.answer(
            "❌ Borgan joyi topilmadi.\n"
            "Iltimos videoni qaytadan yuboring va **Добавить подпись** joyiga "
            "borgan joyini yozing.\n"
            "Masalan: 14 yoki Muruvvatxona-2"
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
    tg_username = tg.username  # None bo'lishi mumkin

    if tg_username:
        t_user = f"@{tg_username}"
    else:
        t_user = f'<a href="tg://user?id={tg_id}">Yozish</a>'

    contact_block = (
        f"👤 Yetkazib beruvchi: {first_name} {last_name}\n"
        f"💬 Aloqa: {t_user}\n"
        f"🆔 Telegram ID: {tg_id}"
    )

    stamp = now_stamp()

    caption = (
        "📦 Yetkazib berish tasdiqi\n"
        f"🏫 Borgan joyi: {destination}\n"
        f"{contact_block}\n"
        f"📞 Telefon: {phone}\n"
        f"🚗 Avto: {car_plate}\n"
        f"🕒 Vaqt: {stamp}"
    )

    # 1) Guruhga yuborishga urinamiz
    try:
        sent = await message.bot.send_video(
            chat_id=cfg.group_chat_id,
            video=file_id,
            caption=caption,
            parse_mode="HTML",
        )
    except Exception as e:
        # ✅ internet sust bo'lsa queue
        await enqueue_pending_video(
            telegram_id=message.from_user.id,
            date=date,
            kindergarten_no=destination,  # eski nomi qolgan bo'lsa ham shu yerga destination ketadi
            video_file_id=file_id,
            caption=caption,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            car_plate=car_plate,
            tg_id=tg_id,
            tg_username=tg_username,
            error=f"{type(e).__name__}: {e}",
        )

        await message.answer(
            "⚠️ Internet sust yoki server javob bermadi.\n"
            "✅ Video saqlab qo'yildi. Internet yaxshilanganda avtomatik guruhga yuboriladi.",
            reply_markup=main_menu(),
        )
        await state.clear()
        return

    # 2) Telegram link (Sheets uchun)
    internal_id = str(cfg.group_chat_id)
    if internal_id.startswith("-100"):
        internal_id = internal_id[4:]
    else:
        internal_id = internal_id.lstrip("-")
    video_link = f"https://t.me/c/{internal_id}/{sent.message_id}"

    # 3) Sheets
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
            kindergarten_no=destination,  # Sheets ustuni eski nomda qolsa ham qiymat destination bo'ladi
            video_link=video_link,
        )
    except Exception as e:
        await message.answer(f"❌ Google Sheets xato: {e}")

    # 4) DB
    await add_video(
        message.from_user.id,
        date,
        destination,  # DBda ham shu joyga yoziladi
        file_id,
        sheet_row=sheet_row,
    )

    await message.answer("✅ Video qabul qilindi va guruhga yuborildi.", reply_markup=main_menu())
    await state.clear()


@router.message(VideoFlow.waiting_video)
async def waiting_video_wrong(message: Message):
    await message.answer(
        "Iltimos, videoni yuboring.\n"
        "Borgan joyini video caption (Добавить подпись)ga yozing."
    )


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
