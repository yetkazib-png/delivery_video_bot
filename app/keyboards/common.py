from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎥 Video yuborish")],
        ],
        resize_keyboard=True
    )


def onboarding_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Tanishib chiqdim", callback_data="onboard_ok")
    return b.as_markup()


def contact_kb() -> ReplyKeyboardMarkup:
    """
    Telefon raqamni CONTACT sifatida olish uchun
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def reminder_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Yubordim", callback_data="rem_yes")
    b.button(text="⛔ Yubormadim", callback_data="rem_no")
    b.adjust(2)
    return b.as_markup()
