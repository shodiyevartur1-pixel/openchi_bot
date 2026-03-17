import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Sozlamalar va ma'lumotlar bazasi
from config import settings
from database import init_db

# Middleware
from middlewares import BanCheckMiddleware

# Handlerlar (Handlers papkasidagi fayllar)
from handlers import start, menu, vote, withdraw, admin

async def main():
    # Log sozlamalari
    logging.basicConfig(level=logging.INFO)
    
    # Ma'lumotlar bazasini ishga tushirish
    await init_db()

    # Bot va Dispatcher ni sozlash
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # --- MIDDLEWARE NI ULASH (MUHIM QISM) ---
    # Bu routerlardan AVVAL kelishi shart.
    # BanCheckMiddleware ban qilingan userlarni botdan to'xtatadi
    dp.message.middleware(BanCheckMiddleware())
    dp.callback_query.middleware(BanCheckMiddleware())

    # --- ROUTERLARNI ULASH ---
    # Handlerlar ketma-ketligi muhim emas, lekin odatda asosiy menu oxiriga qo'yiladi
    dp.include_router(start.router)
    dp.include_router(menu.router)
    dp.include_router(vote.router)
    dp.include_router(withdraw.router)
    dp.include_router(admin.router) # admin.router deb to'g'ri yozildi

    # Botni ishga tushirish (Polling)
    logging.info("Bot ishga tushirilmoqda...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot to'xtatildi")