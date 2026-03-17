from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from database import async_session
from models import User
from config import settings

class BanCheckMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = None
        
        # Message yoki CallbackQuery dan user ID ni olish
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id

        # Agar user mavjud bo'lsa va admin bo'lmasa, tekshiramiz
        if user_id and user_id not in settings.ADMIN_IDS:
            async with async_session() as session:
                user = await session.scalar(select(User).where(User.telegram_id == user_id))
                
                # Agar foydalanuvchi bazada bor va BAN bo'lsa
                if user and user.is_banned:
                    if isinstance(event, Message):
                        await event.answer("⛔️ Siz bloklangansiz! Botdan foydalanish taqiqlangan.")
                    elif isinstance(event, CallbackQuery):
                        await event.answer("⛔️ Siz bloklangansiz!", show_alert=True)
                    return  # Handler ga o'tkazib yubormaymiz (to'xtatamiz)
        
        # Agar ban bo'lmasa yoki admin bo'lsa, davom etadi
        return await handler(event, data)