from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func, update
# NUQTALARNI OLIB TASHLADIK
from database import async_session
from models import User, WithdrawRequest
from keyboards import (get_admin_keyboard, get_withdraw_action_keyboard, 
                       get_back_keyboard, get_user_manage_keyboard, 
                       get_confirm_keyboard)
from states import BroadcastState, AdminUserSearch, AdminEditBalance
from config import settings
import logging
import asyncio

# ... kodning qolgan qismi o'zgarishsiz qoladi ...

router = Router()
logger = logging.getLogger(__name__)

def is_admin(user_id):
    return int(user_id) in settings.ADMIN_IDS

# --- Panelga Kirish ---
@router.message(F.text == "/admin")
async def admin_panel(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.clear()
    await message.answer("👋 Admin Panelga Xush Kelibsiz!", reply_markup=get_admin_keyboard())

@router.message(F.text == "🔙 Ortga")
async def back_to_admin(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.clear()
    await message.answer("Admin Panel:", reply_markup=get_admin_keyboard())

# --- Statistika ---
@router.message(F.text == "📊 Statistika")
async def admin_stats(message: types.Message):
    if not is_admin(message.from_user.id): return
    async with async_session() as session:
        total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0
        total_votes = (await session.execute(select(func.sum(User.votes)))).scalar() or 0
        pending_reqs = (await session.execute(select(func.count(WithdrawRequest.id)).where(WithdrawRequest.status == "pending"))).scalar() or 0
        total_balance = (await session.execute(select(func.sum(User.balance)))).scalar() or 0
        banned_count = (await session.execute(select(func.count(User.id)).where(User.is_banned == True))).scalar() or 0

    stats = (
        f"📊 <b>Bot Statistikasi</b>\n\n"
        f"👥 Umumiy Foydalanuvchilar: <b>{total_users}</b>\n"
        f"🔨 Banlanganlar: <b>{banned_count}</b>\n\n"
        f"📦 Umumiy Ovozlar: <b>{total_votes}</b>\n"
        f"💰 Tizimdagi Balans: <b>{total_balance:,} so'm</b>\n"
        f"⏳ Kutilayotgan To'lovlar: <b>{pending_reqs}</b>"
    )
    await message.answer(stats, parse_mode="HTML")

# --- To'lovlar ---
@router.message(F.text == "💳 To'lovlar")
async def admin_withdraws(message: types.Message):
    if not is_admin(message.from_user.id): return
    async with async_session() as session:
        reqs = (await session.execute(select(WithdrawRequest).where(WithdrawRequest.status == "pending").limit(10))).scalars().all()
    
    if not reqs:
        await message.answer("✅ Hozircha kutilayotgan so'rovlar yo'q.")
        return

    for r in reqs:
        user = (await session.execute(select(User).where(User.id == r.user_id))).scalar_one()
        username = f"@{user.username}" if user.username else "yo'q"
        text = (
            f"🆔 So'rov ID: <b>{r.id}</b>\n"
            f"👤 User: {user.full_name} ({username})\n"
            f"🆔 Telegram ID: <code>{user.telegram_id}</code>\n"
            f"💰 Summa: <b>{int(r.amount):,} so'm</b>\n"
            f"💳 Karta: <code>{r.card_number}</code>"
        )
        await message.answer(text, parse_mode="HTML", reply_markup=get_withdraw_action_keyboard(r.id))

@router.callback_query(F.data.startswith("approve_"))
async def approve_withdraw(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    req_id = int(callback.data.split("_")[1])
    async with async_session() as session:
        req = (await session.execute(select(WithdrawRequest).where(WithdrawRequest.id == req_id))).scalar_one()
        req.status = "approved"
        await session.commit()
    await callback.message.edit_text(f"✅ To'lov tasdiqlandi (ID: {req_id})")
    await callback.answer("Tasdiqlandi")

@router.callback_query(F.data.startswith("reject_"))
async def reject_withdraw(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    req_id = int(callback.data.split("_")[1])
    async with async_session() as session:
        req = (await session.execute(select(WithdrawRequest).where(WithdrawRequest.id == req_id))).scalar_one()
        req.status = "rejected"
        user = (await session.execute(select(User).where(User.id == req.user_id))).scalar_one()
        user.balance += req.amount
        await session.commit()
    await callback.message.edit_text(f"❌ Rad etildi (ID: {req_id}). Pul qaytarildi.")
    await callback.answer("Rad etildi")

# --- User Qidirish ---
@router.message(F.text == "🔍 User Qidirish")
async def start_user_search(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await message.answer("🔍 User ID yoki Username kiriting:", reply_markup=get_back_keyboard())
    await state.set_state(AdminUserSearch.waiting_for_input)

@router.message(AdminUserSearch.waiting_for_input)
async def process_user_search(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    search_input = message.text.strip()
    async with async_session() as session:
        query = select(User)
        if search_input.isdigit():
            user_res = await session.execute(query.where(User.telegram_id == int(search_input)))
        else:
            user_res = await session.execute(query.where(User.username == search_input.replace("@", "")))
        user = user_res.scalar_one_or_none()

    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi.")
        return

    ban_status = "🔨 Banlangan" if user.is_banned else "✅ Faol"
    text = (
        f"👤 <b>Foydalanuvchi Topildi</b>\n\n"
        f"🆔 ID: <code>{user.telegram_id}</code>\n"
        f"👤 Ism: {user.full_name}\n"
        f"💰 Balans: {user.balance:,} so'm\n"
        f"📊 Status: {ban_status}"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_user_manage_keyboard(user.telegram_id))
    await state.clear()

# --- User Boshqaruv (Tugmalar) ---
@router.callback_query(F.data.startswith("ban_user_"))
async def ban_user(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    user_id = int(callback.data.split("_")[2])
    async with async_session() as session:
        await session.execute(update(User).where(User.telegram_id == user_id).values(is_banned=True))
        await session.commit()
    await callback.answer("User ban qilindi!")
    await callback.message.edit_reply_markup(reply_markup=get_user_manage_keyboard(user_id))

@router.callback_query(F.data.startswith("unban_user_"))
async def unban_user(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    user_id = int(callback.data.split("_")[2])
    async with async_session() as session:
        await session.execute(update(User).where(User.telegram_id == user_id).values(is_banned=False))
        await session.commit()
    await callback.answer("User bandan olindi!")
    await callback.message.edit_reply_markup(reply_markup=get_user_manage_keyboard(user_id))

@router.callback_query(F.data.startswith("add_bal_"))
async def ask_add_balance(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    user_id = callback.data.split("_")[2]
    await state.update_data(target_user_id=user_id, action="add")
    await callback.message.answer(f"➕ User (ID: {user_id}) balansiga qancha qo'shmoqchisiz?")
    await state.set_state(AdminEditBalance.waiting_for_amount)
    await callback.answer()

@router.message(AdminEditBalance.waiting_for_amount)
async def process_balance_edit(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Faqat raqam kiriting!")
        return
    amount = int(message.text)
    data = await state.get_data()
    user_id = data.get("target_user_id")
    async with async_session() as session:
        await session.execute(update(User).where(User.telegram_id == user_id).values(balance=User.balance + amount))
        await session.commit()
    await message.answer(f"✅ Balansga {amount:,} so'm qo'shildi.", reply_markup=get_admin_keyboard())
    await state.clear()

# --- Broadcast ---
@router.message(F.text == "📢 Xabar Tarqatish")
async def start_broadcast(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await message.answer("📝 Xabaringizni yuboring:", reply_markup=get_back_keyboard())
    await state.set_state(BroadcastState.waiting_for_content)

@router.message(BroadcastState.waiting_for_content)
async def get_broadcast_content(message: types.Message, state: FSMContext):
    await state.update_data(content_id=message.message_id, chat_id=message.chat.id)
    await message.answer("📢 Tasdiqlaysizmi?", reply_markup=get_confirm_keyboard())
    await state.set_state(BroadcastState.waiting_for_confirmation)

@router.callback_query(F.data == "confirm_broadcast")
async def send_broadcast(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await callback.message.edit_text("⏳ Tarqatilmoqda...")
    count, errors = 0, 0
    async with async_session() as session:
        users = (await session.execute(select(User.telegram_id))).scalars().all()
        for user_id in users:
            try:
                await bot.copy_message(user_id, data['chat_id'], data['content_id'])
                count += 1
                await asyncio.sleep(0.05)
            except: errors += 1
    await callback.message.answer(f"✅ Yakunlandi!\nYuborildi: {count}\nXatolik: {errors}")
    await state.clear()

@router.callback_query(F.data == "cancel_broadcast")
async def cancel_broadcast(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor qilindi.")