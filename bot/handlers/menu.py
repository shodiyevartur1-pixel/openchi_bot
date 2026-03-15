import logging
import re
from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, desc
from database import async_session
from models import User
from config import settings

router = Router()
logger = logging.getLogger(__name__)

# --- FSM HOLATLARI ---
class SettingsState(StatesGroup):
    waiting_for_phone = State()

# --- 💰 HISOBIM (TA'MIRLANDI) ---
@router.message(F.text == "💰 Hisobim")
async def show_account(message: types.Message):
    async with async_session() as session:
        res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = res.scalar_one_or_none()

    if not user:
        await message.answer("❌ Siz ro'yxatdan o'tmagansiz. Iltimos, /start bosing.")
        return

    text = (
        f"👤 <b>Shaxsiy Hisob</b>\n\n"
        f"🆔 ID: <code>{user.telegram_id}</code>\n"
        f"👤 Ism: {user.full_name}\n"
        f"📱 Telefon: {user.phone_number if user.phone_number else 'Kiritilmagan'}\n"
        f"💰 Balans: <b>{user.balance:,} so'm</b>\n"
        f"👥 Takliflar: <b>{user.referrals} ta</b>"
    )
    await message.answer(text, parse_mode="HTML")

# --- 📚 QO'LLANMA (TA'MIRLANDI) ---
@router.message(F.text == "📚 Qo'llanma")
async def show_guide(message: types.Message):
    text = (
        "📖 <b>Botdan foydalanish qo'llanmasi</b>\n\n"
        "1️⃣ <b>Ovoz berish:</b>\n"
        "   • 'Ovoz berish' tugmasini bosing.\n"
        "   • Raqamingizni kiriting va skrinshot qiling.\n"
        "   • Skrinshotni botga yuboring.\n"
        "   • Admin Tasdiqlashini kuting.\n\n"
        "2️⃣ <b>Pul ishlash:</b>\n"
        "   • Har bir tasdiqlangan ovoz uchun hisobingizga pul tushadi.\n"
        "   • Do'stlaringizni taklif qilish orqali ham pul ishlashingiz mumkin.\n\n"
        "3️⃣ <b>Pul yechish:</b>\n"
        "   • Balans yetarli bo'lsa, 'Pul yechish' bo'limidan so'rov yuboring.\n\n"
        "⚠️ <b>Admin:</b> @ar1k_bro"
    )
    await message.answer(text, parse_mode="HTML")

# --- 👆 TAKLIF QILISH (2 BAROBAR KUCHAYTIRILDI) ---
@router.message(F.text == "👥 Taklif qilish")
async def referral_system(message: types.Message, bot: Bot):
    async with async_session() as session:
        res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = res.scalar_one_or_none()

    if not user:
        await message.answer("❌ Siz ro'yxatdan o'tmagansiz. /start bosing.")
        return

    try:
        bot_info = await bot.get_me()
        bot_username = bot_info.username
        ref_link = f"https://t.me/{bot_username}?start={user.telegram_id}"
        
        # Bu yerda bonusni 2 barobar ko'paytiryapmiz
        doubled_bonus = settings.REFERRAL_BONUS
        
        text = (
            f"🔗 <b>Sizning shaxsiy taklif linkingiz:</b>\n\n"
            f"<code>{ref_link}</code>\n\n"
            f"📋 Ushbu linkni do'stlaringizga ulashing.\n\n"
            f"⚡️ <b>DIQQAT! SIZNING TAKLIF DARAJANGIZ 2 BARAVAR KUCHAYTIRILDI!</b>\n"
            f"Har bir do'stingiz ro'yxatdan o'tganda hisobingizga <b>+{doubled_bonus:,} so'm</b> tushadi!\n\n"
            f"📊 Siz hozirgacha: <b>{user.referrals} ta</b> do'st taklif qildingiz."
        )
        
        markup = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="📤 Do'stlarga ulashish", url=f"https://t.me/share/url?url={ref_link}&text=Qo'shiling!")]
        ])
        
        await message.answer(text, parse_mode="HTML", reply_markup=markup)
    except Exception as e:
        logger.error(f"Taklif qilishda xato: {e}")

# --- 🏆 TOP 10 ---
@router.message(F.text == "🏆 TOP 10")
async def show_top_users(message: types.Message):
    async with async_session() as session:
        res = await session.execute(select(User).order_by(desc(User.referrals)).limit(10))
        top_users = res.scalars().all()

    if not top_users:
        await message.answer("Hozircha hech kim ro'yxatda yo'q.")
        return

    text = "🏆 <b>Eng faol taklif qiluvchilar (TOP 10):</b>\n\n"
    for i, user in enumerate(top_users, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"<b>{i}.</b>"
        name = user.full_name[:20]
        text += f"{medal} {name} - <b>{user.referrals}</b> ta taklif\n"

    await message.answer(text, parse_mode="HTML")

# --- ⚙️ SOZLAMALAR ---
@router.message(F.text == "⚙️ Sozlamalar")
async def show_settings(message: types.Message):
    async with async_session() as session:
        res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = res.scalar_one_or_none()

    if not user:
        await message.answer("❌ Ma'lumot topilmadi.")
        return

    phone_display = user.phone_number if user.phone_number else "Kiritilmagan"

    text = (
        f"⚙️ <b>Shaxsiy Sozlamalar</b>\n\n"
        f"🆔 ID: <code>{user.telegram_id}</code>\n"
        f"👤 Ism: {user.full_name}\n"
        f"📱 Tel: {phone_display}\n"
        f"💰 Balans: {user.balance:,} so'm\n\n"
        f"Agar telefon raqamingizni o'zgartirmoqchi bo'lsangiz, quyidagi tugmani bosing."
    )
    
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✏️ Raqamni o'zgartirish", callback_data="change_phone")]
    ])
    
    await message.answer(text, parse_mode="HTML", reply_markup=markup)

# --- TELEFON RAQAMNI O'ZGARTIRISH (BOSQICHLAR) ---
@router.callback_query(F.data == "change_phone")
async def ask_new_phone(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer(
        "📞 <b>Yangi telefon raqamingizni kiriting:</b>\n\n"
        "Misol: <code>+998901234567</code>\n",
        parse_mode="HTML"
    )
    await state.set_state(SettingsState.waiting_for_phone)
    await callback.answer()

@router.message(SettingsState.waiting_for_phone)
async def save_new_phone(message: types.Message, state: FSMContext):
    text = message.text.strip()
    
    if text == "/cancel":
        await state.clear()
        await message.answer("❌ Bekor qilindi.")
        return

    clean_number = re.sub(r'[^\d+]', '', text)
    
    if not re.match(r'^\+?\d{9,15}$', clean_number):
        await message.answer("⚠️ Noto'g'ri format! Iltimos, quyidagicha kiriting:\n<code>+998901234567</code>", parse_mode="HTML")
        return

    try:
        async with async_session() as session:
            res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
            user = res.scalar_one_or_none()
            if user:
                user.phone_number = clean_number
                await session.commit()
        
        await state.clear()
        await message.answer(f"✅ Telefon raqamingiz muvaffaqiyatli yangilandi: <b>{clean_number}</b>", parse_mode="HTML")
    except Exception as e:
        logger.error(f"Raqamni saqlashda xato: {e}")
        await message.answer("⚠️ Server xatoligi.")