import logging
import re
from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, desc
from database import async_session
from models import User, WithdrawRequest  # WithdrawRequest import qilindi
from config import settings
from keyboards import get_main_keyboard

router = Router()
logger = logging.getLogger(__name__)

# --- FSM HOLATLARI ---
class SettingsState(StatesGroup):
    waiting_for_phone = State()

class WithdrawState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_card = State()

# --- 💰 HISOBIM ---
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

# --- 📜 TO'LAR TARIXI (YANGI) ---
@router.message(F.text == "📜 To'lovlar tarixi")
async def show_withdraw_history(message: types.Message):
    async with async_session() as session:
        # Foydalanuvchining so'rovlarini olish (oxirgi 10 ta)
        res = await session.execute(
            select(WithdrawRequest)
            .where(WithdrawRequest.user_id == message.from_user.id)
            .order_by(desc(WithdrawRequest.created_at))
            .limit(10)
        )
        requests = res.scalars().all()

    if not requests:
        await message.answer("📄 Sizda hali pul yechish so'rovlari yo'q.")
        return

    text = "📜 <b>So'nggi pul yechish tarixi:</b>\n\n"
    for r in requests:
        status_emoji = "⏳" if r.status == "pending" else "✅" if r.status == "approved" else "❌"
        status_text = "Kutilmoqda" if r.status == "pending" else "Tasdiqlandi" if r.status == "approved" else "Rad etildi"
        
        text += (
            f"{status_emoji} <b>{r.amount:,} so'm</b>\n"
            f"💳 Karta: <code>{r.card_number}</code>\n"
            f"📅 Sana: {r.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"Holat: {status_text}\n\n"
        )

    await message.answer(text, parse_mode="HTML")

# --- 📚 QO'LLANMA ---
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
        "⚠️ <b>Admin:</b> @budjet_uz"
    )
    await message.answer(text, parse_mode="HTML")

# --- 👆 TAKLIF QILISH ---
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
        
        bonus_amount = getattr(settings, 'REFERRAL_BONUS', 1000)
        
        text = (
            f"🔗 <b>Sizning shaxsiy taklif linkingiz:</b>\n\n"
            f"<code>{ref_link}</code>\n\n"
            f"📋 Ushbu linkni do'stlaringizga ulashing.\n\n"
            f"⚡️ <b>DIQQAT! SIZNING TAKLIF DARAJANGIZ KUCHAYTIRILDI!</b>\n"
            f"Har bir do'stingiz ro'yxatdan o'tganda hisobingizga <b>+{bonus_amount:,} so'm</b> tushadi!\n\n"
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

# --- 💳 PUL YECHISH (BOSHLASH) ---
@router.message(F.text == "💳 Pul yechish")
async def withdraw_start(message: types.Message, state: FSMContext):
    async with async_session() as session:
        res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = res.scalar_one_or_none()

    if not user:
        await message.answer("❌ Siz ro'yxatdan o'tmagansiz.")
        return

    if user.balance < 10000:
        await message.answer(f"❌ Hisobingizda mablag' yetarli emas.\nJoriy balans: <b>{user.balance:,} so'm</b>\nMinimal yechish: 10,000 so'm", parse_mode="HTML")
        return

    cancel_markup = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="🔙 Bekor qilish")]], 
        resize_keyboard=True
    )

    await message.answer(
        f"💰 <b>Pul yechish bo'limi</b>\n\n"
        f"Sizning balansingiz: <b>{user.balance:,} so'm</b>\n\n"
        f"Qancha miqdorni yechmoqchisiz? (faqat raqam kiriting):",
        parse_mode="HTML",
        reply_markup=cancel_markup
    )
    await state.set_state(WithdrawState.waiting_for_amount)

@router.message(WithdrawState.waiting_for_amount, F.text == "🔙 Bekor qilish")
async def cancel_withdraw_amount(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Amal bekor qilindi.", reply_markup=get_main_keyboard())

@router.message(WithdrawState.waiting_for_amount)
async def withdraw_amount(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Iltimos, faqat raqam kiriting!")
        return

    amount = int(message.text)
    
    async with async_session() as session:
        res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = res.scalar_one_or_none()
        
        if amount > user.balance:
            await message.answer(f"❌ Sizda buncha mablag' yo'q! Maksimum: {user.balance:,} so'm", parse_mode="HTML")
            return
        if amount < 10000:
            await message.answer("❌ Minimal yechish miqdori 10,000 so'm!")
            return
    
    await state.update_data(amount=amount)
    await message.answer("💳 Endi karta raqamingizni kiriting (16 xonali):")
    await state.set_state(WithdrawState.waiting_for_card)

@router.message(WithdrawState.waiting_for_card, F.text == "🔙 Bekor qilish")
async def cancel_withdraw_card(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Amal bekor qilindi.", reply_markup=get_main_keyboard())

@router.message(WithdrawState.waiting_for_card)
async def withdraw_card(message: types.Message, state: FSMContext, bot: Bot):
    card = message.text.strip()
    clean_card = re.sub(r'[^\d]', '', card)
    
    if len(clean_card) != 16:
        await message.answer("⚠️ Karta raqami noto'g'ri! 16 xonali bo'lishi kerak.")
        return

    data = await state.get_data()
    amount = data.get("amount")

    try:
        async with async_session() as session:
            res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
            user = res.scalar_one_or_none()
            
            if user:
                # 1. Balansdan pulni ayiramiz
                user.balance -= amount
                
                # 2. BAZAGA SO'ROVNI SAQLAYMIZ (MUHIM O'ZGARTIRISH)
                new_request = WithdrawRequest(
                    user_id=user.telegram_id,
                    amount=amount,
                    card_number=clean_card,
                    status="pending"
                )
                session.add(new_request)
                await session.commit()

                # Admin xabari
                phone_display = user.phone_number if user.phone_number else "Yo'q"
                admin_text = (
                    f"🆕 <b>Yangi Pul Yechish So'rovi!</b>\n\n"
                    f"👤 Ism: {user.full_name}\n"
                    f"🆔 ID: <code>{user.telegram_id}</code>\n"
                    f"📞 Tel: {phone_display}\n"
                    f"💰 Miqdor: <b>{amount:,} so'm</b>\n"
                    f"💳 Karta: <code>{clean_card}</code>"
                )
                
                # Admin tugmalari (Bazadagi ID ni ishlatamiz)
                markup = types.InlineKeyboardMarkup(inline_keyboard=[
                    [
                        types.InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{new_request.id}"),
                        types.InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{new_request.id}")
                    ]
                ])
                
                if hasattr(settings, 'ADMIN_IDS') and settings.ADMIN_IDS:
                    for admin_id in settings.ADMIN_IDS:
                        try:
                            await bot.send_message(admin_id, admin_text, parse_mode="HTML", reply_markup=markup)
                        except Exception as e:
                            logger.error(f"Adminga yuborishda xato: {e}")

        await message.answer(
            "✅ <b>So'rovingiz qabul qilindi!</b>\n\n"
            "Admin tekshirib, pulni kartangizga tushiradi.\n"
            "Jarayon 24 soat ichida amalga oshiriladi.",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )

    except Exception as e:
        logger.error(f"Pul yechish jarayonida xato: {e}")
        await message.answer("⚠️ Tizimda xatolik yuz berdi.")
    
    await state.clear()

# --- ADMIN CALLBACK HANDLERS (BAZADAN OLADI) ---
@router.callback_query(F.data.startswith("approve_"))
async def approve_withdraw(callback: types.CallbackQuery, bot: Bot):
    try:
        req_id = int(callback.data.split("_")[1])
        
        async with async_session() as session:
            req = (await session.execute(select(WithdrawRequest).where(WithdrawRequest.id == req_id))).scalar_one_or_none()
            
            if req and req.status == "pending":
                req.status = "approved"
                await session.commit()
                
                user = (await session.execute(select(User).where(User.telegram_id == req.user_id))).scalar_one_or_none()
                
                if user:
                    try:
                        await bot.send_message(
                            user.telegram_id, 
                            f"✅ <b>So'rovingiz tasdiqlandi!</b>\n\n"
                            f"💰 <b>{req.amount:,} so'm</b> pul kartangizga tushirildi.",
                            parse_mode="HTML"
                        )
                    except: pass

                await callback.message.edit_text(callback.message.text + "\n\n<b>✅ TASDIQLANDI</b>", parse_mode="HTML")
                await callback.answer("Tasdiqlandi!")
            else:
                await callback.answer("So'rov topilmadi yoki allaqachon ko'rib chiqilgan!", show_alert=True)

    except Exception as e:
        logger.error(f"Tasdiqlashda xato: {e}")

@router.callback_query(F.data.startswith("reject_"))
async def reject_withdraw(callback: types.CallbackQuery, bot: Bot):
    try:
        req_id = int(callback.data.split("_")[1])
        
        async with async_session() as session:
            req = (await session.execute(select(WithdrawRequest).where(WithdrawRequest.id == req_id))).scalar_one_or_none()
            
            if req and req.status == "pending":
                req.status = "rejected"
                
                user = (await session.execute(select(User).where(User.telegram_id == req.user_id))).scalar_one_or_none()
                if user:
                    user.balance += req.amount # Pulni qaytarish
                    try:
                        await bot.send_message(
                            user.telegram_id, 
                            f"❌ <b>So'rovingiz rad etildi.</b>\n\n"
                            f"💰 <b>{req.amount:,} so'm</b> hisobingizga qaytarildi.",
                            parse_mode="HTML"
                        )
                    except: pass
                
                await session.commit()
                await callback.message.edit_text(callback.message.text + "\n\n<b>❌ RAD ETILDI</b>", parse_mode="HTML")
                await callback.answer("Rad etildi!")
            else:
                await callback.answer("So'rov topilmadi!", show_alert=True)

    except Exception as e:
        logger.error(f"Rad etishda xato: {e}")


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

# --- TELEFON RAQAMNI O'ZGARTIRISH ---
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
        await message.answer("❌ Bekor qilindi.", reply_markup=get_main_keyboard())
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