from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, update
from database import async_session
from models import User
from keyboards import get_main_keyboard, get_vote_link_keyboard, get_back_keyboard, get_contact_keyboard
from states import VoteState
from config import settings
from datetime import datetime
import re

router = Router()

# --- 1. Ovoz berish bosilganda (Avval telefon so'raydi) ---
@router.message(F.text == "📦 Ovoz berish")
async def start_vote_process(message: types.Message, state: FSMContext):
    await state.clear()

    # Mantiq: User bazada bo'lsa ham, har safar ovoz berishda raqamni so'rash (xavfsizlik uchun)
    # Yoki bazadan olishni xohlasangiz, shu yerda tekshirib olish mumkin.
    # Sizning so'rovingiz: "Ovoz berish bosilganda avval buni yuborsin".
    
    await message.answer(
        "📞 Ovoz berish uchun telefon raqamingizni kiriting:\n\n"
        "Na'muna: +998991234567\n\n"
        "✅ Ovoz berish muvaffaqiyatli o'tganda, hisobingizga pul o'tkazib beriladi!",
        reply_markup=get_contact_keyboard() # Tugmali keyboard (Kontakt + Ortga)
    )
    await state.set_state(VoteState.waiting_for_phone)

# --- 2. Telefon raqamni qabul qilish va LINK yuborish ---
@router.message(VoteState.waiting_for_phone)
async def process_phone_and_send_link(message: types.Message, state: FSMContext):
    text = message.text
    phone = ""

    # Agar kontakt tugmasi bosilsa
    if message.contact:
        phone = message.contact.phone_number
    # Agar matn yozilsa
    elif text and text != "🔙 Ortga":
        phone = text.strip()
    # Agar ortga bosilsa
    elif text == "🔙 Ortga":
        await state.clear()
        await message.answer("❌ Bekor qilindi", reply_markup=get_main_keyboard())
        return

    # Validatsiya (O'zbekiston raqami)
    clean_phone = re.sub(r'[^\d]', '', phone)
    
    # Avtomatik tuzatish (+998 qo'shish)
    if len(clean_phone) == 9 and clean_phone.startswith('9'): 
        clean_phone = "998" + clean_phone
    elif len(clean_phone) == 10 and clean_phone.startswith('8'): 
        clean_phone = "998" + clean_phone[1:]

    # Tekshirish
    if not (len(clean_phone) == 12 and clean_phone.startswith('998')):
        await message.answer("❌ Iltimos, to'g'ri O'zbekiston raqami kiriting!\nNamuna: +998901234567")
        return

    formatted_phone = f"+{clean_phone}"
    
    # Raqamni saqlab qo'yamiz (State va Bazaga)
    await state.update_data(phone=formatted_phone)
    
    # Bazaga ham saqlash (agar userda yo'q bo'lsa)
    async with async_session() as session:
        res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = res.scalar_one_or_none()
        if user:
            if not user.phone_number:
                user.phone_number = formatted_phone
                await session.commit()

    # --- 3. LINK NI YUBORISH (Ortiqcha so'zsiz) ---
    # Siz so'ragan: "keyin link chiqsin va pastdagi tugma orqali degan joyi umuman kk emas"
    # Shuning uchun faqat Inline Keyboard yuboramiz.
    
    await message.answer(
        "Quyidagi tugma orqali ovoz bering:", # Judam qisqa matn yoki umuman yo'q qilsa ham bo'ladi
        reply_markup=get_vote_link_keyboard(settings.VOTE_LINK)
    )

# --- 3. "Ovoz berdim" tugmasi bosilganda ---
@router.callback_query(F.data == "vote_done")
async def ask_screenshot(callback: types.CallbackQuery, state: FSMContext):
    # Endi Reply Keyboardga o'tamiz (Ortga tugmasi uchun)
    await callback.message.answer("📸 Ovoz berilgandagi skrenshotni yuboring:", reply_markup=get_back_keyboard())
    await state.set_state(VoteState.waiting_for_screenshot)
    await callback.answer()

# --- 4. Skrinshot kelganda ---
@router.message(VoteState.waiting_for_screenshot, F.photo)
async def process_screenshot(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    phone = data.get("phone", "Noma'lum")
    
    admin_ids = settings.ADMIN_IDS
    photo_id = message.photo[-1].file_id
    
    # Adminga yuborish
    for admin_id in admin_ids:
        try:
            await bot.send_photo(
                admin_id,
                photo_id,
                caption=(
                    f"🆕 <b>Yangi Ovoz Tasdiqlash!</b>\n\n"
                    f"👤 User: {message.from_user.mention_html()}\n"
                    f"🆔 ID: <code>{message.from_user.id}</code>\n"
                    f"📱 Tel: {phone}\n"
                    f"📅 Sana: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
                ),
                parse_mode="HTML",
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                    [
                        types.InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"vote_ok_{message.from_user.id}"),
                        types.InlineKeyboardButton(text="❌ Rad", callback_data=f"vote_no_{message.from_user.id}")
                    ]
                ])
            )
        except Exception as e:
            print(f"Admin {admin_id} ga yuborilmadi: {e}")

    # User ga javob
    await message.answer(
        f"📱 Telefon raqam: {phone}\n\n"
        f"Raqam tekshiruv uchun yuborildi. Tez orada javob beriladi.\n"
        f"📆 {datetime.now().strftime('%d.%m.%Y')} ⏰ {datetime.now().strftime('%H:%M')}",
        reply_markup=get_main_keyboard() # Javobdan keyin asosiy menyu
    )
    await state.clear()

# --- 5. Ortga qaytish tugmasi (Skrenshot jarayonida) ---
@router.message(VoteState.waiting_for_screenshot, F.text == "🔙 Ortga")
async def back_from_screenshot(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Bekor qilindi", reply_markup=get_main_keyboard())

# --- Admin tasdiqlash ---
@router.callback_query(F.data.startswith("vote_ok_"))
async def vote_approved(callback: types.CallbackQuery, bot: Bot):
    user_id = int(callback.data.split("_")[2])
    async with async_session() as session:
        await session.execute(
            update(User).where(User.telegram_id == user_id)
            .values(balance=User.balance + settings.VOTE_REWARD, votes=User.votes + 1)
        )
        await session.commit()
    
    await callback.message.edit_caption(caption=callback.message.caption + "\n\n✅ TASDIQLANDI")
    try:
        await bot.send_message(user_id, f"✅ Ovozingiz tasdiqlandi! +{settings.VOTE_REWARD} so'm.")
    except: pass
    await callback.answer("Tasdiqlandi")

@router.callback_query(F.data.startswith("vote_no_"))
async def vote_rejected(callback: types.CallbackQuery, bot: Bot):
    user_id = int(callback.data.split("_")[2])
    await callback.message.edit_caption(caption=callback.message.caption + "\n\n❌ RAD ETILDI")
    try:
        await bot.send_message(user_id, "❌ Ovozingiz rad etildi.")
    except: pass
    await callback.answer("Rad etildi")