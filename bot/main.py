import asyncio
import logging
import os
import signal
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Loyiha modullari
from config import settings
from database import init_db
from middlewares import BanCheckMiddleware
from handlers import start, menu, vote, withdraw, admin

# --- 1. OPTIMALLASHTIRILGAN SERVER ---
async def handle(request):
    """Render uchun 'Sog'lomlik' tekshiruvi (Health Check)"""
    return web.Response(text="Bot is running! 🚀", status=200)

async def start_fake_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render avtomatik beradigan PORT yoki standart 8080
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"✅ Render port-binding xizmati {port}-portda faollashdi.")

# --- 2. XATOLARNI BOSHQARISH VA TOZALASH ---
async def on_shutdown(dispatcher: Dispatcher, bot: Bot):
    logging.warning("⚠️ Bot to'xtatilmoqda...")
    await bot.session.close()
    logging.info("✅ Barcha ulanishlar xavfsiz yopildi.")

# --- 3. ASOSIY LOGIKA ---
async def main():
    # Loggingni yanada o'qishli qilish
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Ma'lumotlar bazasini ishga tushirish (Retry mexanizmi bilan)
    try:
        await init_db()
        logging.info("🗄 Ma'lumotlar bazasi muvaffaqiyatli ulandi.")
    except Exception as e:
        logging.error(f"❌ Bazaga ulanishda xato: {e}")
        return

    # Bot ob'ekti
    bot = Bot(
        token=settings.BOT_TOKEN, 
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Middlewarelarni ro'yxatdan o'tkazish
    dp.message.middleware(BanCheckMiddleware())
    dp.callback_query.middleware(BanCheckMiddleware())

    # Routerlarni ulash
    dp.include_routers(
        start.router,
        menu.router,
        vote.router,
        withdraw.router,
        admin.router
    )

    # O'chish jarayoni uchun registratsiya
    dp.shutdown.register(on_shutdown)

    # Webhookni tozalash va eski xabarlarni o'tkazib yuborish
    await bot.delete_webhook(drop_pending_updates=True)

    logging.info("🤖 Bot Polling rejimida ishga tushdi...")

    # Parallel ravishda server va botni yurgizish
    # asyncio.gather o'rniga asyncio.create_task ishlatish barqarorroq
    server_task = asyncio.create_task(start_fake_server())
    
    try:
        await dp.start_polling(bot)
    except Exception as ex:
        logging.critical(f"Kutilmagan xatolik: {ex}")
    finally:
        server_task.cancel() # Bot to'xtasa serverni ham to'xtatadi

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot qo'lda to'xtatildi.")