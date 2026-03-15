import logging
from aiogram import Router, F, types, Bot
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from database import async_session
from models import User
from keyboards import get_main_keyboard, get_subscription_keyboard
from config import settings

router = Router()
logger = logging.getLogger(__name__)

# FSM holatlari
class RegisterState(StatesGroup):
    waiting_for_check = State()

# Obunani tekshiruvchi funksiya
async def check_subscription(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(settings.CHANNEL_ID, user_id)
        if member.status in ["left", "kicked"]:
            return False
        return True
    except Exception as e:
        logger.error(f"Kanal tekshirishda xatolik (User: {user_id}): {e}")
        return False

# Asosiy mantiq
async def process_user_logic(message: types.Message, bot: Bot, referrer_id: int = None, user_obj: types.User = None):
    if user_obj is None:
        user_obj = message.from_user
        
    user_id = user_obj.id
    full_name = user_obj.full_name
    username = user_obj.username
    
    try:
        async with async_session() as session:
            # 1. Bazadan foydalanuvchini qidiramiz
            result = await session.execute(select(User).where(User.telegram_id == user_id))
            user = result.scalar_one_or_none()

            if user:
                # Foydalanuvchi bazada BOR
                if user.is_banned:
                    await message.answer("⛔ Siz bot tomonidan bloklangansiz!")
                    return
                
                # Menyu ochiladi
                await message.answer(
                    f"👋 Xush kelibsiz, {user.full_name}!", 
                    reply_markup=get_main_keyboard()
                )
            else:
                # Foydalanuvchi bazada YO'Q
                
                if referrer_id == user_id:
                    referrer_id = None

                new_user = User(
                    telegram_id=user_id,
                    full_name=full_name,
                    username=username,
                    phone_number=None,
                    referred_by=referrer_id
                )
                session.add(new_user)
                
                # Referral bonusni qo'shamiz (SUMMA O'ZGARTIRILDI)
                if referrer_id:
                    res_ref = await session.execute(select(User).where(User.telegram_id == referrer_id))
                    referrer = res_ref.scalar_one_or_none()
                    
                    if referrer:
                        # Bonusni 1000 so'm qilib qo'ydim
                        bonus_amount = 1000
                        
                        referrer.referrals += 1
                        referrer.balance += bonus_amount
                        
                        try:
                            await bot.send_message(
                                referrer_id, 
                                f"🎉 <b>Tabriklaymiz!</b>\n\n"
                                f"Do'stingiz ro'yxatdan o'tdi.\n"
                                f"Hisobingizga <b>+{bonus_amount:,} so'm</b> qo'shildi!",
                                parse_mode="HTML"
                            )
                        except Exception as e:
                            logger.warning(f"Referrerga xabar yuborilmadi: {e}")

                await session.commit()

                # --- BU YERDA TUZATISH QILINDI ---
                # Matn bitta string ko'rinishiga keltirildi (vergullar olib tashlandi)
                await message.answer(
                    f"👋 Assalomu alaykum {user_obj.first_name} botimizga xush kelibsiz.\n\n"
                    "Aziz foydalanuvchi siz har bir ovozingiz berganingiz uchun botdan <b>30 000 so'm</b> pul ishlashingiz mumkin.\n\n"
                    "Hamda do'stlaringizni taklif qilish orqali ham pul ishlashingiz mumkin.\n\n"
                    f"Toʻlovlar: {settings.CHANNEL_ID}\n"
                    "Sizning ovozingiz bizning mahallamiz obodonlashtirilishi uchun juda muhim!",
                    parse_mode="HTML",
                    reply_markup=get_main_keyboard()
                )
                
                await message.answer(
                    "⚠️ Eslatma: Ovoz berayotganda screenshot qiling! Keyin esa screenshot qilgan rasmingizni yuboring, "
                    "admin rasmni ko'rib tasdiqlasa hisobingizga 30 000 so'm pul qo'shiladi!"
                )

    except Exception as e:
        logger.error(f"process_user_logic da xatolik: {e}")
        await message.answer("⚠️ Tizimda vaqtinchalik xatolik yuz berdi. Iltimos keyinroq urinib ko'ring.")

# Start komandasi
@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext, bot: Bot):
    await state.clear()
    
    user_id = message.from_user.id
    
    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])
    
    is_subscribed = await check_subscription(bot, user_id)
    
    if not is_subscribed:
        channel_link = f"https://t.me/{settings.CHANNEL_ID.replace('@', '')}"
        
        await state.update_data(referrer_id=referrer_id)
        await state.set_state(RegisterState.waiting_for_check)
        
        await message.answer(
            "⚠️ <b>Botdan foydalanish uchun kanalga obuna bo'lishingiz shart!</b>",
            parse_mode="HTML",
            reply_markup=get_subscription_keyboard(channel_link)
        )
        return

    await process_user_logic(message, bot, referrer_id)

# "Tekshirish" tugmasi bosilganda
@router.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    user_id = callback.from_user.id
    is_subscribed = await check_subscription(bot, user_id)

    if not is_subscribed:
        await callback.answer("❌ Siz hali kanalga obuna bo'lmadingiz!", show_alert=True)
        return

    try:
        await callback.message.delete()
    except:
        pass
    
    await callback.answer("✅ Obuna tasdiqlandi!")

    data = await state.get_data()
    referrer_id = data.get("referrer_id")
    
    await state.clear()

    # Menu ham ochiladi va referral hisoblanadi
    await process_user_logic(callback.message, bot, referrer_id, user_obj=callback.from_user)

# "Ovoz berish" tugmasi uchun handler
@router.message(F.text == "🗳 Ovoz berish")
async def vote_handler(message: types.Message):
    await message.answer(
        "🗳 Ovoz berish bo'limiga xush kelibsiz!\n\n"
        "Ovoz berish jarayonida screenshot olishni unutmang. "
        "Ovoz berganingizdan so'ng, screenshotni shu yerga yuboring.\n\n"
        "Har bir tasdiqlangan ovoz uchun <b>30 000 so'm</b> olasiz!",
        parse_mode="HTML"
    )