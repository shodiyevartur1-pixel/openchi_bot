import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from database import init_db

# Handlers - TO'G'RI IMPORT
from handlers import start, menu, vote, withdraw, admin

async def main():
    logging.basicConfig(level=logging.INFO)
    
    # Initialize Database
    await init_db()

    # Initialize Bot
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Routers - Admin routeri oxiriga qo'yildi
    dp.include_router(start.router)
    dp.include_router(menu.router)
    dp.include_router(vote.router)
    dp.include_router(withdraw.router)
    dp.include_router(admin.router) # Bu yerda 'admin' moduli handlers dan olinmoqda

    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped")

    async def main():
        # Jadvallarni yaratish (agar bazada yo'q bo'lsa)
        await init_db() 
        
        # Botni ishga tushirish
        await dp.start_polling(Bot)