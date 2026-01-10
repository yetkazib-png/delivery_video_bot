from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

router = Router()


def join_bot_kb(bot_username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🤖 Botdan ro'yxatdan o'tish",
                    url=f"https://t.me/{bot_username}?start=reg"
                )
            ]
        ]
    )


@router.message(F.new_chat_members)
async def new_member_handler(message: Message):
    bot = message.bot
    me = await bot.get_me()
    bot_username = me.username

    for member in message.new_chat_members:
        # Botning o'zi qo'shilsa — o'tkazib yuboramiz
        if member.is_bot:
            continue

        await message.reply(
            (
                "👋 Assalomu alaykum!\n\n"
                "Iltimos, yetkazib berish jarayoni uchun "
                "quyidagi tugma orqali botdan ro‘yxatdan o‘ting.\n\n"
                "📹 Video qo‘llanma va barcha qoidalar bot ichida mavjud."
            ),
            reply_markup=join_bot_kb(bot_username)
        )
