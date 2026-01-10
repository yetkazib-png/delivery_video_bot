import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

dp = Dispatcher()

@dp.message(F.text)
async def any_text(message: Message):
    print("CHAT_ID:", message.chat.id, "| CHAT_TITLE:", message.chat.title)
    await message.answer("Chat ID terminalda chiqdi.")

async def main():
    bot = Bot(TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
