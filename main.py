import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import load_config
from app.db.database import init_db

from app.handlers.admin import router as admin_router
from app.handlers.start import router as start_router
from app.handlers.video import router as video_router
from app.handlers.reminders import router as reminders_router
from app.handlers.group import router as group_router

from app.services.scheduler import setup_scheduler


async def main():
    cfg = load_config()
    await init_db()

    bot = Bot(token=cfg.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    # Admin routerni eng tepada qo'ying (muhim)
    dp.include_router(admin_router)

    dp.include_router(start_router)
    dp.include_router(video_router)
    dp.include_router(reminders_router)
    dp.include_router(group_router)

    scheduler = setup_scheduler(bot, cfg.timezone)
    scheduler.start()

    print("Bot ishga tushdi. GROUP_CHAT_ID =", cfg.group_chat_id)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
