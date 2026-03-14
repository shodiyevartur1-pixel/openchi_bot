from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func
from database import async_session
from models import User, WithdrawRequest
from keyboards import get_admin_keyboard, get_withdraw_action_keyboard
from states import BroadcastState, AdminUserSearch
from config import settings

router = Router()

def is_admin(user_id):
    # Sizning ID ngiz bu yerga qo'shildi (8059999086)
    # Agar .env da ham bo'lsa, ishlaydi, bo'lmasa shu ID ishlaydi
    return user_id in settings.ADMIN_IDS or user_id == 8059999086

@router.message(F.text == "/admin")
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("Siz admin emassiz!")
        return
    await message.answer("Admin panel:", reply_markup=get_admin_keyboard())

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    async with async_session() as session:
        total_users = await session.execute(select(func.count(User.id)))
        total_votes = await session.execute(select(func.sum(User.votes)))
        pending_reqs = await session.execute(select(func.count(WithdrawRequest.id)).where(WithdrawRequest.status == "pending"))
        
        stats = (
            f"📊 <b>Statistika</b>\n\n"
            f"👥 Foydalanuvchilar: {total_users.scalar()}\n"
            f"📦 Umumiy ovozlar: {total_votes.scalar() or 0}\n"
            f"⏳ Kutilayotgan to'lovlar: {pending_reqs.scalar()}"
        )
    await callback.message.edit_text(stats, parse_mode="HTML")

@router.callback_query(F.data == "admin_withdraws")
async def admin_withdraws(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    async with async_session() as session:
        res = await session.execute(
            select(WithdrawRequest)
            .where(WithdrawRequest.status == "pending")
        )
        reqs = res.scalars().all()

    if not reqs:
        await callback.answer("Kutilayotgan so'rovlar yo'q", show_alert=True)
        return

    for r in reqs:
        user_res = await session.execute(select(User).where(User.id == r.user_id))
        user = user_res.scalar_one()
        
        # Foydalanuvchi username i bo'lsa olamiz, bo'lmasa 'yo'q'
        username = f"@{user.username}" if user.username else "yo'q"
        
        text = (
            f"🆔 So'rov ID: {r.id}\n"
            f"👤 User: {user.full_name} ({username})\n"
            f"🆔 Telegram ID: <code>{user.telegram_id}</code>\n" # ID qo'shildi
            f"💰 Summa: {int(r.amount)} so'm\n"
            f"💳 Karta: <code>{r.card_number}</code>"
        )
        await callback.message.answer(text, parse_mode="HTML", reply_markup=get_withdraw_action_keyboard(r.id))

@router.callback_query(F.data.startswith("approve_"))
async def approve_withdraw(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    req_id = int(callback.data.split("_")[1])
    async with async_session() as session:
        res = await session.execute(select(WithdrawRequest).where(WithdrawRequest.id == req_id))
        req = res.scalar_one()
        req.status = "approved"
        await session.commit()
    
    await callback.message.edit_text(f"✅ To'lov tasdiqlandi (ID: {req_id})")
    await callback.answer("Tasdiqlandi")

@router.callback_query(F.data.startswith("reject_"))
async def reject_withdraw(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    req_id = int(callback.data.split("_")[1])
    
    async with async_session() as session:
        res = await session.execute(select(WithdrawRequest).where(WithdrawRequest.id == req_id))
        req = res.scalar_one()
        req.status = "rejected"
        
        # Refund balance (Pulni user balansiga qaytarish)
        user_res = await session.execute(select(User).where(User.id == req.user_id))
        user = user_res.scalar_one()
        user.balance += req.amount
        
        await session.commit()
    
    await callback.message.edit_text(f"❌ To'lov rad etildi (ID: {req_id}). Pul qaytarildi.")
    await callback.answer("Rad etildi")

# Broadcast feature logic would go here...