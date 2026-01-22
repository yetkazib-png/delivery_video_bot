from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command, CommandObject
from aiogram.filters.state import StateFilter
from aiogram.fsm.context import FSMContext

from app.config import get_admin_ids
from app.db.database import delete_user_by_telegram_id

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in get_admin_ids()


@router.message(StateFilter("*"), Command("delete"))
async def delete_user_cmd(message: Message, state: FSMContext, command: CommandObject):
    # Admin bo'lmasa
    if not is_admin(message.from_user.id):
        await message.answer("❌ Siz admin emassiz.")
        return

    # State ichida bo'lsa ham admin komandasi ishlashi uchun tozalab yuboramiz
    await state.clear()

    # /delete 7481592
    if not command.args:
        await message.answer(
            "❗ Foydalanish:\n"
            "/delete TELEGRAM_ID\n\n"
            "Masalan:\n"
            "/delete 7481592"
        )
        return

    arg = command.args.strip().split()[0]
    if not arg.isdigit():
        await message.answer("❌ Telegram ID raqam bo‘lishi kerak. Masalan: /delete 123456789")
        return

    target_id = int(arg)

    await delete_user_by_telegram_id(target_id)

    # Foydalanuvchiga xabar yuborishga urinamiz
    try:
        await message.bot.send_message(
            chat_id=target_id,
            text="❌ Siz botdan o‘chirildingiz.\nQayta kirish uchun /start bosing."
        )
    except Exception:
        pass

    await message.answer(f"✅ Foydalanuvchi o‘chirildi: {target_id}")
