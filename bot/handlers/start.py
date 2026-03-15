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

# FSM holatlari (Referral ID ni vaqtincha saqlash uchun)
class RegisterState(StatesGroup):
    waiting_for_check = State()

# Obunani tekshiruvchi funksiya (Kuchaytirilgan)
async def check_subscription(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(settings.CHANNEL_ID, user_id)
        # Agar foydalanuvchi kanalni tark etgan bo'lsa yoki chiqarib yuborilgan bo'lsa
        if member.status in ["left", "kicked"]:
            return False
        return True
    except Exception as e:
        logger.error(f"Kanal tekshirishda xatolik (User: {user_id}): {e}")
        # Xatolik bo'lsa, foydalanuvchini bloklamaslik uchun True qaytarishimiz yoki qayta urinish mumkin.
        # Lekin xavfsizlik uchun False qaytaramiz.
        return False

# Foydalanuvchini ro'yxatdan o'tkazish va menyuni ko'rsatish uchun umumiy funksiya
# Bu yerda kod takrorlanmasligi uchun barcha mantiq birlashtirilgan
async def process_user_logic(message: types.Message, bot: Bot, referrer_id: int = None):
    user_id = message.from_user.id
    
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
                
                # Foydalanuvchiga xush kelibsiz deymiz
                await message.answer(
                    f"👋 Xush kelibsiz, {user.full_name}!", 
                    reply_markup=get_main_keyboard()
                )
            else:
                # Foydalanuvchi bazada YO'Q - Yangi foydalanuvchini ro'yxatdan o'tkazamiz
                
                # O'zini o'zi taklif qilishni tekshiramiz
                if referrer_id == user_id:
                    referrer_id = None

                new_user = User(
                    telegram_id=user_id,
                    full_name=message.from_user.full_name,
                    username=message.from_user.username,
                    phone_number=None,  # Telefon raqami talab qilinmaydi
                    referred_by=referrer_id
                )
                session.add(new_user)
                
                # Referral bonusni qo'shamiz
                if referrer_id:
                    res_ref = await session.execute(select(User).where(User.telegram_id == referrer_id))
                    referrer = res_ref.scalar_one_or_none()
                    
                    if referrer:
                        referrer.referrals += 1
                        referrer.balance += settings.REFERRAL_BONUS
                        
                        # Referrerga xabar yuboramiz
                        try:
                            await bot.send_message(
                                referrer_id, 
                                f"🎉 Tabriklaymiz! Do'stingiz ro'yxatdan o'tdi. Hisobingizga +{settings.REFERRAL_BONUS} so'm qo'shildi!"
                            )
                        except Exception as e:
                            logger.warning(f"Referrerga xabar yuborilmadi: {e}")

                # O'zgarishlarni saqlaymiz
                await session.commit()

                # Yangi foydalanuvchiga xabarlar
                await message.answer(
                    f"👋 Assalomu alaykum {message.from_user.first_name} botimizga xush kelibsiz.\n\n"
                    "Aziz foydalanuvchi siz har bir ovozingiz berganingiz uchun botdan pul ishlashingiz mumkin.\n\n"
                    "Hamda do'stlaringizni taklif qilish orqali kuniga 100 000 so'mgacha pul ishlab olishingiz mumkin.\n\n"
                    f"Toʻlovlar: {settings.CHANNEL_ID}\n"
                    "Sizning ovozingiz bizning mahallamiz obodonlashtirilishi uchun juda muhim!"
                )
                
                await message.answer(
                    "⚠️ Eslatma: Ovoz berayotganda screenshot qiling! Keyin esa screenshot qilgan rasmingizni yuboring, "
                    "admin rasmni ko'rib tasdiqlasa hisobingizga so'm pul qo'shiladi!"
                )

                # Asosiy menyuni ko'rsatamiz
                
    except Exception as e:
        logger.error(f"process_user_logic da xatolik: {e}")
        await message.answer("⚠️ Tizimda vaqtinchalik xatolik yuz berdi. Iltimos keyinroq urinib ko'ring.")

# Start komandasi
@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext, bot: Bot):
    await state.clear()
    
    user_id = message.from_user.id
    
    # Referral ID ni ajratib olamiz
    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])
    
    # Obunani tekshiramiz
    is_subscribed = await check_subscription(bot, user_id)
    
    if not is_subscribed:
        # Agar obuna bo'lmasa
        channel_link = f"https://t.me/{settings.CHANNEL_ID.replace('@', '')}"
        
        # Referral ID ni yo'qotmaslik uchun State ga saqlab qo'yamiz
        # Foydalanuvchi "Tekshirish"ni bosganda biz buni qayta olamiz
        await state.update_data(referrer_id=referrer_id)
        await state.set_state(RegisterState.waiting_for_check)
        
        await message.answer(
            "⚠️ <b>Botdan foydalanish uchun kanalga obuna bo'lishingiz shart!</b>",
            parse_mode="HTML",
            reply_markup=get_subscription_keyboard(channel_link)
        )
        return

    # Agar obuna bo'lsa, asosiy logikaga o'tamiz
    await process_user_logic(message, bot, referrer_id)

# "Tekshirish" tugmasi bosilganda
@router.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    user_id = callback.from_user.id
    is_subscribed = await check_subscription(bot, user_id)

    if not is_subscribed:
        await callback.answer("❌ Siz hali kanalga obuna bo'lmadingiz!", show_alert=True)
        return

    # Xabarni o'chirishga harakat qilamiz (obuna so'rash xabari)
    try:
        await callback.message.delete()
    except:
        pass
    
    await callback.answer("✅ Obuna tasdiqlandi!")

    # Referral ID ni state dan olamiz (agar start bilan kelgan bo'lsa)
    data = await state.get_data()
    referrer_id = data.get("referrer_id")
    
    # State ni tozalaymiz
    await state.clear()

    # Asosiy logikani ishga tushiramiz
    # callback.message orqali murojaat qilamiz
    await process_user_logic(callback.message, bot, referrer_id)

# "Ovoz berish" tugmasi uchun handler
@router.message(F.text == "🗳 Ovoz berish")
async def vote_handler(message: types.Message):
    # Bu yerda ovoz berish jarayoni boshlanadi
    # Telefon raqami so'ralmaydi, chunki foydalanuvchi allaqachon ro'yxatdan o'tgan
    await message.answer(
        "🗳 Ovoz berish bo'limiga xush kelibsiz!\n\n"
        "Ovoz berish jarayonida screenshot olishni unutmang. "
        "Ovoz berganingizdan so'ng, screenshotni shu yerga yuboring."
    )