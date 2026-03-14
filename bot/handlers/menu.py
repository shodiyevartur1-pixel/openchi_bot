from aiogram import Router, F, types
from sqlalchemy import select
from database import async_session
from models import User
from keyboards import get_main_keyboard
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text == "💰 Hisobim")
async def show_account(message: types.Message):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        
        if not user:
            return
        
        text = (
            f"👤 <b>{user.full_name}</b>\n\n"
            f"💰 Balans: <b>{int(user.balance)}</b> so'm\n"
            f"📦 Ovozlar: <b>{user.votes}</b> ta\n"
            f"👥 Takliflar: <b>{user.referrals}</b> ta\n\n"
            f"📅 Ro'yxatdan o'tgan: {user.created_at.strftime('%d.%m.%Y')}"
        )
        await message.answer(text, parse_mode="HTML")

@router.message(F.text == "👥 Taklif qilish")
async def show_referral(message: types.Message):
    bot_username = (await message.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={message.from_user.id}"
    
    text = (
        "🔗 Sizning shaxsiy havolangiz:\n"
        f"<code>{link}</code>\n\n"
        "Do'stlaringizni taklif qiling va har biridan <b>1000 so'm</b> ishlang!"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "📚 Qo'llanma")
async def show_guide(message: types.Message):
    text = (
        "📚 <b>Qo'llanma</b>\n\n"
        "1. <b>Ovoz berish:</b> Kuniga bir marta loyihalarga ovoz bering va daromad oling.\n"
        "2. <b>Taklif qilish:</b> Do'stlaringizni taklif qilib pul ishlang.\n"
        "3. <b>Pul yechish:</b> Balansdagi pulni kartangizga o'tkazing.\n\n"
        "Savollar bo'lsa: @ar1k_bro"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "⚙️ Sozlamalar")
async def show_settings(message: types.Message):
    # Placeholder for settings logic
    await message.answer("Sozlamalar bo'limi hozircha ishlab chiqilmoqda.", reply_markup=get_main_keyboard())