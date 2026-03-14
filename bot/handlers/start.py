import logging
from aiogram import Router, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from database import async_session
from models import User
from keyboards import get_main_keyboard, get_contact_keyboard
from config import settings

router = Router()
logger = logging.getLogger(__name__)

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    args = message.text.split()
    referrer_id = None
    
    # Referral logic
    if len(args) > 1:
        try:
            referrer_id = int(args[1])
        except ValueError:
            pass

    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()

        if user:
            if not user.is_active:
                await message.answer("Siz bloklangansiz.")
                return
            await message.answer(f"Xush kelibsiz, {user.full_name}!", reply_markup=get_main_keyboard())
            return

        # New User Logic
        if referrer_id:
            # Check if referrer exists
            res_ref = await session.execute(select(User).where(User.telegram_id == referrer_id))
            referrer = res_ref.scalar_one_or_none()
            if referrer:
                # Will update referrer stats later after registration
                pass
            else:
                referrer_id = None

        # Ask for phone number
        await state.update_data(referrer_id=referrer_id)
        await message.answer(
            "Assalomu alaykum! Open Budget Botiga xush kelibsiz.\n"
            "Iltimos, ro'yxatdan o'tish uchun telefon raqamingizni yuboring:",
            reply_markup=get_contact_keyboard()
        )

@router.message(F.contact)
async def process_contact(message: types.Message, state: FSMContext):
    data = await state.get_data()
    referrer_id = data.get("referrer_id")
    
    phone = message.contact.phone_number
    
    # --- TUZATILGAN QISIM ---
    contact_name = message.contact.first_name
    if message.contact.last_name:
        contact_name += f" {message.contact.last_name}"
    
    full_name = contact_name or message.from_user.full_name
    # ------------------------

    async with async_session() as session:
        new_user = User(
            telegram_id=message.from_user.id,
            full_name=full_name,
            username=message.from_user.username,
            phone_number=phone,
            referred_by=referrer_id
        )
        session.add(new_user)
        
        # Update referrer
        if referrer_id:
            res_ref = await session.execute(select(User).where(User.telegram_id == referrer_id))
            referrer = res_ref.scalar_one_or_none()
            if referrer:
                referrer.referrals += 1
                referrer.balance += settings.REFERRAL_BONUS
        
        await session.commit()
    
    await state.clear()
    await message.answer("Tabriklaymiz! Siz muvaffaqiyatli ro'yxatdan o'tdingiz.", reply_markup=get_main_keyboard())